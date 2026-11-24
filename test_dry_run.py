"""End-to-end checks using generated PDFs in temporary folders only."""

import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont

from engine_v2 import Proposal, _destination, analyze, available_ocr, execute, extract_pdf, undo_last
from subject_classifier import classify_kind


def pdf(path: Path, text: str):
    document = canvas.Canvas(str(path))
    document.drawString(72, 720, text)
    document.save()


class DryRunTests(unittest.TestCase):
    def test_ocr_reads_scanned_page_when_available(self):
        if not available_ocr()[0]:
            self.skipTest("Tesseract em português não instalado neste ambiente")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "digitalizado.pdf"
            image = Image.new("RGB", (1400, 240), "white")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
            draw.text((40, 60), "MATEMATICA ARITMETICA", fill="black", font=font)
            document = canvas.Canvas(str(path), pagesize=(700, 120))
            document.drawImage(ImageReader(image), 0, 0, width=700, height=120)
            document.save()
            self.assertEqual(extract_pdf(path, False)["text"].strip(), "")
            result = extract_pdf(path, True)
            self.assertEqual(result["ocr_pages"], 1)
            self.assertIn("MATEMATICA", result["text"].upper())

    def test_mixed_batch_only_proposes_and_never_creates_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "IA NA PRATICA").mkdir()
            (root / "Matemática").mkdir()
            (root / "Pessoal").mkdir()
            examples = {
                "Prompt Mestre Claude.pdf": "Prompts mestres para Claude, ChatGPT e Windows",
                "Aula Matematica.pdf": "Univesp disciplina Matematica aritmetica",
                "Documento pessoal.pdf": "Documento pessoal CPF e comprovante de residencia",
                "Sem contexto.pdf": "Uma receita de bolo de cenoura",
            }
            for name, text in examples.items():
                pdf(root / name, text)
            original = {path.name: path.read_bytes() for path in root.glob("*.pdf")}
            proposals = {p.source.name: p for p in analyze(root, False, scope="inbox")}
            self.assertEqual(set(proposals), set(examples))
            self.assertEqual(proposals["Prompt Mestre Claude.pdf"].subject, "DEV/Prompts e IA")
            self.assertTrue(proposals["Prompt Mestre Claude.pdf"].needs_review)
            self.assertEqual(proposals["Aula Matematica.pdf"].subject, "Matemática")
            self.assertEqual(proposals["Documento pessoal.pdf"].kind, "Pessoal")
            self.assertEqual(proposals["Sem contexto.pdf"].kind, "Indefinido")
            self.assertEqual(proposals["Sem contexto.pdf"].subject, "")
            self.assertFalse((root / "DEV").exists())
            self.assertEqual(original, {path.name: path.read_bytes() for path in root.glob("*.pdf")})

    def test_pending_cannot_move_even_if_action_is_set(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf(root / "Prompt Claude.pdf", "Prompts mestres para Claude")
            proposal = analyze(root, False, scope="inbox")[0]
            proposal.action = "MOVE"
            outcome = execute(root, [proposal], root / "history.db")
            self.assertEqual(outcome["moved"], 0)
            self.assertTrue(proposal.source.exists())
            self.assertFalse((root / "DEV").exists())

    def test_ambiguous_course_and_prompt_stays_for_review(self):
        result = classify_kind("Prompts Claude para faculdade.pdf", "Manual de prompts para Claude publicado pela universidade")
        self.assertEqual(result["kind"], "Desenvolvimento")
        course = classify_kind("Aula IA na Pratica.pdf", "Univesp disciplina IA na Pratica: prompts para Claude")
        self.assertEqual(course["kind"], "Faculdade")

    def test_cancel_during_analysis_does_not_move_anything(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for n in range(3):
                pdf(root / f"aula{n}.pdf", "Univesp Matematica")
            progress = []
            result = analyze(root, False, progress=lambda done, total: progress.append(done), cancel=lambda: bool(progress), scope="inbox")
            self.assertEqual(len(result), 1)
            self.assertEqual(len(list(root.glob("*.pdf"))), 3)

    def test_undo_preserves_preexisting_and_nonempty_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "DEV").mkdir()
            source = root / "Prompts.pdf"
            pdf(source, "Prompts para Claude")
            proposal = Proposal(source, "DEV/Prompts e IA", "", "", "", source.name, source.name, "", False)
            db = root / "history.db"
            self.assertEqual(execute(root, [proposal], db)["moved"], 1)
            new_folder = root / "DEV" / "Prompts e IA"
            (new_folder / "anotacoes.txt").write_text("keep")
            self.assertEqual(undo_last(db)["restored"], 1)
            self.assertTrue((root / "DEV").exists())
            self.assertTrue((new_folder / "anotacoes.txt").exists())

    def test_invalid_or_external_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("../fora", "DEV/../../fora", "C:/fora", "DEV//Prompts", "CON", "DEV/LPT1"):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        _destination(root, name, "aula.pdf")

    def test_invalid_pdf_is_reported_without_moving(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            broken = root / "quebrado.pdf"
            broken.write_bytes(b"not a pdf")
            self.assertIn("inválido", extract_pdf(broken, False)["warning"])
            proposal = analyze(root, False, scope="inbox")[0]
            self.assertTrue(proposal.needs_review)
            self.assertEqual(proposal.action, "KEEP")


if __name__ == "__main__":
    unittest.main()
