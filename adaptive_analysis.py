"""Read-only PDF evidence inventory. No organizer operations are imported here."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path

import pypdfium2 as pdfium


SUBJECTS = {
    "Matemática": ("matematica", "aritmetica", "algebra", "estatistica", "probabilidade", "geometria"),
    "Método para Produção de Trabalhos Científicos": ("metodologia cientifica", "abnt", "referencias bibliograficas", "trabalho cientifico", "citacao"),
    "Ética e Cidadania": ("etica e cidadania", "direitos humanos", "cidadania", "etica", "sociedade"),
    "IA na Prática": ("ia na pratica", "inteligencia artificial", "ia generativa", "vieses algoritmicos"),
    "Leitura e Produção de Texto": ("leitura e producao de texto", "producao de textos", "escrita", "leitura", "coesao"),
    "Pensamento Computacional": ("pensamento computacional", "computacao criativa", "scratch", "algoritmo", "decomposicao"),
    "Guitarra": ("guitarra", "tablatura", "arpejos", "escala maior", "acordes", "violao"),
    "Desenvolvimento": ("desenvolvimento de software", "codigo fonte", "python", "github", "programacao", "prompt mestre"),
}

DOCUMENT_TYPES = {
    "certificado": ("certificado de conclusao", "certificamos que"),
    "comprovante": ("comprovante", "declaracao de vinculo", "atestado de vinculo", "certidao"),
    "atividade": ("atividade avaliativa", "atividade em grupo", "atividade individual"),
    "artigo": ("resumo", "abstract", "doi"),
    "apostila": ("apostila", "material teorico"),
    "manual": ("manual", "guia de usuario"),
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in value if not unicodedata.combining(c)).lower()


def contains(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text))


def page_plan(count: int, bookmarks: list[int], budget: int = 16) -> list[tuple[int, str]]:
    """Keep structural pages, then sample the body; deterministic and bounded."""
    selected: dict[int, str] = {}
    for i in range(min(count, 6)):
        selected[i] = "inicio"
    for i in bookmarks[:6]:
        if 0 <= i < count:
            selected.setdefault(i, "capitulo")
    if count > 6:
        for fraction in (0.25, 0.5, 0.75):
            selected.setdefault(min(count - 1, round((count - 1) * fraction)), "amostra")
    for i in range(6, min(count, 12)):
        if len(selected) >= budget:
            break
        selected.setdefault(i, "continuidade")
    return sorted(list(selected.items())[:budget])


def title_is_useful(title: str, filename: str) -> bool:
    title = normalize(title).strip()
    return (12 <= len(title) <= 120 and title not in {"untitled", "microsoft word", "documento sem titulo"}
            and not re.fullmatch(r"[a-z]{0,4}\d{3,}", title) and not title.endswith(".pdf"))


def analyze_pdf(path: Path, ocr: bool = False, include_text: bool = False) -> dict:
    row = {"path": str(path), "filename": path.name, "folder": path.parent.name,
           "status": "TRIAGEM", "subject": "", "alternative": "", "kind": "",
           "evidence": "", "pages_read": "", "ocr_pages": "", "warning": "",
           "pages_total": 0, "metadata_title": "", "bookmarks": 0,
           "score": 0, "margin": 0, "text_chars": 0}
    try:
        with pdfium.PdfDocument(path) as doc:
            row["pages_total"] = len(doc)
            title = (doc.get_metadata_value("Title") or "").strip()
            row["metadata_title"] = title
            toc = list(doc.get_toc())
            row["bookmarks"] = len(toc)
            chapters = []
            for bookmark in toc:
                if bookmark.level == 0:
                    destination = bookmark.get_dest()
                    if destination is not None:
                        chapters.append(destination.get_index())
            plan = page_plan(len(doc), chapters)
            scores = Counter()
            evidence = []
            page_numbers, ocr_numbers = [], []
            filename = normalize(path.stem.replace("_", " ").replace("-", " "))
            metadata_text = normalize(title) if title_is_useful(title, path.name) else ""
            kind_sample = filename + " " + metadata_text
            meaningful = 0
            chunks = []
            for subject, aliases in SUBJECTS.items():
                for alias in aliases:
                    if contains(filename, alias):
                        scores[subject] += 8
                        evidence.append((subject, "nome", alias, 8))
                    if metadata_text and contains(metadata_text, alias):
                        scores[subject] += 3
                        evidence.append((subject, "metadado", alias, 3))
            for index, role in plan:
                page = doc.get_page(index)
                try:
                    text_page = page.get_textpage()
                    try:
                        raw = text_page.get_text_range() or ""
                    finally:
                        text_page.close()
                finally:
                    page.close()
                if len(raw.strip()) < 80 and ocr and len(ocr_numbers) < 3:
                    try:
                        import pytesseract
                        executable = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                        if Path(executable).is_file():
                            pytesseract.pytesseract.tesseract_cmd = executable
                        page = doc.get_page(index)
                        try:
                            bitmap = page.render(scale=140 / 72)
                            try:
                                raw += "\n" + pytesseract.image_to_string(bitmap.to_pil(), lang="por+eng")
                            finally:
                                bitmap.close()
                        finally:
                            page.close()
                        ocr_numbers.append(index + 1)
                    except Exception as exc:
                        row["warning"] = "OCR indisponível ou falhou: " + type(exc).__name__
                page_numbers.append(index + 1)
                if include_text:
                    chunks.append(raw)
                normalized = normalize(raw)
                meaningful += len(normalized.strip())
                kind_sample += " " + normalized[:1000]
                for subject, aliases in SUBJECTS.items():
                    for alias in aliases:
                        # A phrase is counted at most once per page, not by frequency.
                        if contains(normalized[:1200], alias):
                            weight = 8 if index == 0 else 5 if role in {"inicio", "capitulo"} else 2
                            scores[subject] += weight
                            evidence.append((subject, "página " + str(index + 1), alias, weight))
                        elif contains(normalized[1200:4500], alias):
                            scores[subject] += 1
                            evidence.append((subject, "corpo " + str(index + 1), alias, 1))
            ranked = scores.most_common(2)
            row["subject"] = ranked[0][0] if ranked else ""
            row["alternative"] = ranked[1][0] if len(ranked) > 1 else ""
            row["score"] = ranked[0][1] if ranked else 0
            row["margin"] = row["score"] - (ranked[1][1] if len(ranked) > 1 else 0)
            chosen = [e for e in evidence if e[0] == row["subject"]]
            locations = {e[1] for e in chosen if e[3] >= 3}
            row["evidence"] = "; ".join(f"{place}: {term} (+{weight})" for _, place, term, weight in chosen[:12])
            row["pages_read"] = ",".join(map(str, page_numbers))
            row["ocr_pages"] = ",".join(map(str, ocr_numbers))
            row["text_chars"] = meaningful
            if include_text:
                row["text"] = "\n".join(chunks)
            for kind, aliases in DOCUMENT_TYPES.items():
                if any(contains(kind_sample[:7000], alias) for alias in aliases):
                    row["kind"] = kind
                    break
            strong = any(e[1] in {"nome", "página 1"} and e[3] >= 8 for e in chosen)
            row["status"] = ("SEGURA" if row["score"] >= 14 and row["margin"] >= 7
                             and len(locations) >= 2 and strong and meaningful >= 80
                             and row["kind"] not in {"atividade", "certificado", "comprovante"}
                             else "REVISÃO" if row["score"] else "TRIAGEM")
    except Exception as exc:
        row["warning"] = "PDF protegido ou inválido" if isinstance(exc, (pdfium.PdfiumError, ValueError)) else type(exc).__name__
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventário de evidências PDF; somente leitura da origem")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ocr", action="store_true", help="OCR seletivo local (até 3 páginas por PDF)")
    args = parser.parse_args()
    if not args.source.is_dir() or args.output.resolve().is_relative_to(args.source.resolve()):
        parser.error("A origem deve existir e a saída deve ficar fora dela")
    rows = [analyze_pdf(path, args.ocr) for path in sorted(args.source.rglob("*.pdf")) if path.is_file() and not path.is_symlink()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["path"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} PDFs; " + ", ".join(f"{label}: {sum(r['status'] == label for r in rows)}" for label in ("SEGURA", "REVISÃO", "TRIAGEM")))


if __name__ == "__main__":
    main()
