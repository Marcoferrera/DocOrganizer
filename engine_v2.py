"""Local analysis and reversible file operations for DocOrganizer 2."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sqlite3
import uuid
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Callable

import pypdfium2 as pdfium
import pytesseract
from PIL import Image

from subject_classifier import FolderModel, classify, classify_kind, normalize, subject_names
from adaptive_analysis import analyze_pdf, title_is_useful


APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "DocOrganizer"
DB_PATH = APP_DIR / "history_v2.db"
MAX_OCR_PAGES = 10
MAX_OCR_RENDER_PAGES = 2
MAX_PDF_MB = 100


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def available_ocr() -> tuple[bool, str]:
    candidates = [Path(sys.executable).parent / "Tesseract-OCR" / "tesseract.exe" if getattr(sys, "frozen", False) else None,
                  shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            try:
                langs = set(pytesseract.get_languages(config=""))
                return ("por" in langs, "por+eng" if "eng" in langs else "por")
            except Exception:
                continue
    return False, ""


def extract_pdf(path: Path, use_ocr: bool = True) -> dict:
    if path.stat().st_size > MAX_PDF_MB * 1024 * 1024:
        return {"text": "", "title": "", "warning": "PDF acima do limite de leitura de 100 MB", "ocr_pages": 0}
    result = analyze_pdf(path, ocr=use_ocr, include_text=True)
    return {"text": result.get("text", ""), "title": result["metadata_title"],
            "warning": result["warning"], "ocr_pages": len(result["ocr_pages"].split(",")) if result["ocr_pages"] else 0,
            "pages_read": result["pages_read"], "evidence": result["evidence"],
            "adaptive_subject": result["subject"], "adaptive_status": result["status"]}


def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name).strip(" .")
    name = re.sub(r"\s+", " ", name)
    if not name or name.upper() in {"CON", "PRN", "AUX", "NUL"}:
        raise ValueError("Nome de arquivo inválido")
    return name[:150].rstrip(" .") + ".pdf"


def suggested_filename(original: str, title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    if title_is_useful(title, original):
        try:
            return safe_name(title)
        except ValueError:
            pass
    return original


@dataclass
class Proposal:
    source: Path
    subject: str
    alternative: str
    evidence: str
    warning: str
    proposed_name: str
    original_name: str
    current_folder: str
    needs_review: bool
    action: str = "MOVE"
    excerpt: str = ""
    kind: str = "Indefinido"
    new_folder: bool = False


def analyze(root: Path, use_ocr: bool = True, progress: Callable[[int, int], None] | None = None,
            cancel: Callable[[], bool] | None = None, scope: str = "all") -> list[Proposal]:
    root = root.resolve(strict=True)
    if scope not in {"all", "inbox", "audit"}:
        raise ValueError("Modo de análise inválido")
    subjects = subject_names(root)
    all_documents = sorted((p for p in root.rglob("*.pdf") if p.is_file() and not p.is_symlink() and "triagem" not in {normalize(part) for part in p.relative_to(root).parts[:-1]}), key=lambda p: str(p).lower())
    documents = [p for p in all_documents if scope == "all" or (p.parent == root) == (scope == "inbox")]
    extracted = []
    for index, path in enumerate(documents, 1):
        if cancel and cancel():
            break
        try:
            result = extract_pdf(path, use_ocr)
        except Exception as error:
            result = {"text": "", "title": "", "warning": str(error), "ocr_pages": 0}
        extracted.append((path, result))
        if progress:
            progress(index, len(documents))
    examples = [(path.parent.name, path.name + " " + result["text"])
                for path, result in extracted if path.parent != root and result["text"].strip()]
    if scope == "inbox":
        per_folder = {}
        for path in all_documents:
            if cancel and cancel():
                break
            if path.parent == root or path.parent.name not in subjects:
                continue
            count = per_folder.get(path.parent.name, 0)
            if count >= 15:
                continue
            per_folder[path.parent.name] = count + 1
            try:
                sample = extract_pdf(path, use_ocr=False)
                if sample["text"].strip():
                    examples.append((path.parent.name, path.name + " " + sample["text"]))
            except Exception:
                continue
    model = FolderModel(examples, subjects)
    proposals = []
    for path, result in extracted:
        try:
            current = path.parent.name if path.parent != root else ""
            kind = classify_kind(path.name, result["text"])
            ranked = classify(path.name, result["text"], subjects, current)
            adaptive = result.get("adaptive_subject", "")
            if adaptive and ranked["score"] < 6:
                ranked["suggestion"] = adaptive
                ranked["evidence"] = [result.get("evidence", "")]
                ranked["needs_review"] = True
            if kind["kind"] != "Faculdade":
                ranked["suggestion"] = kind["suggestion"]
                ranked["alternative"] = ""
                ranked["evidence"] = [kind["evidence"]]
                ranked["needs_review"] = True
            elif not current and ranked["score"] < 6:
                learned = model.suggest(path.name + " " + result["text"])
                if learned and learned[0][1] > 0.10:
                    ranked["suggestion"] = learned[0][0]
                    ranked["alternative"] = learned[1][0] if len(learned) > 1 else ranked["alternative"]
                    ranked["evidence"] = ["semelhança com PDFs já organizados: " + ", ".join(learned[0][2])]
                    ranked["needs_review"] = True
            subject = ranked["suggestion"]
            if subject == adaptive and result.get("evidence"):
                ranked["evidence"] = list(ranked["evidence"]) + ["Pistas por página: " + result["evidence"]]
            confidence = ranked["needs_review"]
            warning = result["warning"]
            if result.get("pages_read"):
                warning = "; ".join(filter(None, (warning, "Páginas analisadas: " + result["pages_read"])))
            proposed_name = suggested_filename(path.name, result["title"])
            needs_review = confidence or kind["new_folder"] or (bool(warning) and not result["text"].strip()) or proposed_name != path.name
            proposal = Proposal(path, subject, ranked["alternative"], ", ".join(ranked["evidence"]), warning,
                                proposed_name, path.name, current, needs_review,
                                "KEEP" if needs_review or not subject or subject == current else "MOVE",
                                " ".join(result["text"].split())[:1400], kind["kind"],
                                bool(subject and not (root / subject).is_dir()))
            proposals.append(proposal)
        except Exception as error:
            proposals.append(Proposal(path, "", "", "", str(error), path.name, path.name,
                                      path.parent.name if path.parent != root else "", True, "KEEP"))
    return proposals


def _connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, started TEXT NOT NULL, status TEXT NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS moves (id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, source TEXT NOT NULL, destination TEXT NOT NULL, hash TEXT NOT NULL, status TEXT NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS created_dirs (session_id TEXT NOT NULL, path TEXT NOT NULL, PRIMARY KEY (session_id, path))")
    connection.commit()
    # Recover a completed move whose final database update was interrupted.
    for row in connection.execute("SELECT * FROM moves WHERE status='PLANNED'").fetchall():
        source, destination = Path(row["source"]), Path(row["destination"])
        if not source.exists() and destination.is_file() and sha256(destination) == row["hash"]:
            connection.execute("UPDATE moves SET status='MOVED' WHERE id=?", (row["id"],))
    connection.commit()
    return connection


def _destination(root: Path, subject: str, filename: str) -> Path:
    parts = subject.replace("\\", "/").split("/")
    if not parts or any(not part or part in {".", ".."} or part.strip(" .") != part or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part) or any(c in part for c in '<>:"|?*') for part in parts):
        raise ValueError("Pasta de destino inválida")
    if Path(filename).name != filename or Path(filename).suffix.lower() != ".pdf":
        raise ValueError("Nome de PDF inválido")
    destination = root.joinpath(*parts) / filename
    if any(parent.is_symlink() for parent in (root.joinpath(*parts[:i]) for i in range(1, len(parts) + 1))) or not destination.parent.resolve().is_relative_to(root.resolve()):
        raise ValueError("Destino fora da pasta selecionada")
    return destination


def _unique_destination(destination: Path, source_hash: str) -> Path | None:
    if not destination.exists():
        return destination
    if sha256(destination) == source_hash:
        return None
    for number in range(1, 10000):
        candidate = destination.with_name(f"{destination.stem}_{number}{destination.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Não foi possível escolher nome livre")


def _safe_copy_then_delete(source: Path, destination: Path, expected_hash: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.parent / f".docorganizer-{uuid.uuid4().hex}.tmp"
    try:
        with source.open("rb") as reader, temp.open("xb") as writer:
            shutil.copyfileobj(reader, writer, 1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        shutil.copystat(source, temp)
        if sha256(temp) != expected_hash or sha256(source) != expected_hash:
            raise RuntimeError("Arquivo mudou durante a cópia")
        os.rename(temp, destination)  # Windows refuses an existing destination.
        try:
            if sha256(source) != expected_hash:
                raise RuntimeError("Origem mudou antes da remoção")
            source.unlink()
        except Exception:
            if destination.is_file() and sha256(destination) == expected_hash:
                destination.unlink()
            raise
    finally:
        temp.unlink(missing_ok=True)


def execute(root: Path, proposals: list[Proposal], db_path: Path = DB_PATH, progress: Callable[[int, int], None] | None = None, cancel: Callable[[], bool] | None = None) -> dict:
    root = root.resolve(strict=True)
    approved = [p for p in proposals if p.action == "MOVE" and p.subject and not p.needs_review]
    session_id = uuid.uuid4().hex
    counts = {"moved": 0, "skipped": 0, "failed": 0}
    errors = []
    with closing(_connection(db_path)) as db:
        db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (session_id, datetime.now().isoformat(), "RUNNING"))
        db.commit()
        for index, proposal in enumerate(approved, 1):
            if cancel and cancel():
                break
            source = proposal.source
            try:
                if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(root):
                    raise ValueError("Origem inválida ou ausente")
                source_hash = sha256(source)
                target = _destination(root, proposal.subject, proposal.proposed_name)
                if source.resolve() == target.resolve():
                    counts["skipped"] += 1
                    continue
                target = _unique_destination(target, source_hash)
                if target is None:
                    counts["skipped"] += 1
                    continue
                absent_dirs = []
                parent = target.parent
                while parent != root and not parent.exists():
                    absent_dirs.append(parent)
                    parent = parent.parent
                cursor = db.execute("INSERT INTO moves (session_id, source, destination, hash, status) VALUES (?, ?, ?, ?, 'PLANNED')", (session_id, str(source), str(target), source_hash))
                db.commit()
                _safe_copy_then_delete(source, target, source_hash)
                for directory in absent_dirs:
                    db.execute("INSERT OR IGNORE INTO created_dirs VALUES (?, ?)", (session_id, str(directory)))
                db.execute("UPDATE moves SET status='MOVED' WHERE id=?", (cursor.lastrowid,))
                db.commit()
                counts["moved"] += 1
            except Exception as error:
                counts["failed"] += 1
                errors.append(f"{source.name}: {error}")
            if progress:
                progress(index, len(approved))
        status = "CANCELLED" if cancel and cancel() else "PARTIAL" if counts["failed"] else "DONE"
        db.execute("UPDATE sessions SET status = ? WHERE id = ?", (status, session_id))
        db.commit()
    return {"session_id": session_id, **counts, "status": status, "errors": errors}


def last_undoable(db_path: Path = DB_PATH) -> str | None:
    with closing(_connection(db_path)) as db:
        row = db.execute("SELECT s.id FROM sessions s JOIN moves m ON m.session_id=s.id AND m.status='MOVED' GROUP BY s.id ORDER BY s.started DESC LIMIT 1").fetchone()
        return row[0] if row else None


def undo_last(db_path: Path = DB_PATH) -> dict:
    session_id = last_undoable(db_path)
    if not session_id:
        return {"restored": 0, "blocked": 0, "session_id": None}
    restored = blocked = 0
    errors = []
    with closing(_connection(db_path)) as db:
        items = db.execute("SELECT * FROM moves WHERE session_id=? AND status='MOVED' ORDER BY id DESC", (session_id,)).fetchall()
        for item in items:
            source, destination = Path(item["source"]), Path(item["destination"])
            try:
                if not destination.is_file() or source.exists() or sha256(destination) != item["hash"]:
                    raise RuntimeError("Arquivo ausente, alterado ou origem ocupada")
                _safe_copy_then_delete(destination, source, item["hash"])
                db.execute("UPDATE moves SET status='UNDONE' WHERE id=?", (item["id"],))
                db.commit()
                restored += 1
            except Exception as error:
                blocked += 1
                errors.append(f"{destination.name}: {error}")
        for row in db.execute("SELECT path FROM created_dirs WHERE session_id=? ORDER BY LENGTH(path) DESC", (session_id,)).fetchall():
            try:
                Path(row["path"]).rmdir()  # Removes only empty folders made by this session.
            except OSError:
                pass
        db.execute("UPDATE sessions SET status=? WHERE id=?", ("UNDO_PARTIAL" if blocked else "UNDONE", session_id))
        db.commit()
    return {"restored": restored, "blocked": blocked, "session_id": session_id, "errors": errors}
