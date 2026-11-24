import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

from engine_v2 import Proposal, analyze, execute, extract_pdf, last_undoable, undo_last
from subject_classifier import classify


class DocOrganizerV2Tests(unittest.TestCase):
    def test_analysis_scopes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subject = root / "Matemática"
            subject.mkdir()
            for path in (root / "solto.pdf", subject / "organizado.pdf"):
                document = canvas.Canvas(str(path))
                document.drawString(72, 720, "Matematica e aritmetica")
                document.save()
            inbox = analyze(root, False, scope="inbox")
            audit = analyze(root, False, scope="audit")
            self.assertEqual([p.source.name for p in inbox], ["solto.pdf"])
            self.assertEqual([p.source.name for p in audit], ["organizado.pdf"])
            self.assertIn("Matematica", inbox[0].excerpt)

    def test_subject_ranking_and_ambiguity(self):
        subjects = ["Matemática", "Ética e Cidadania"]
        result = classify("aula.pdf", "Matemática. Aritmética e álgebra.", subjects)
        self.assertEqual(result["suggestion"], "Matemática")
        self.assertFalse(result["needs_review"])
        ambiguous = classify("arquivo.pdf", "conteúdo sem identificação", subjects)
        self.assertTrue(ambiguous["needs_review"])
        broken_pdf_text = classify("arquivo.pdf", "Média aritm etica simples dos termos. Matemática", subjects)
        self.assertEqual(broken_pdf_text["suggestion"], "Matemática")

    def test_analyze_real_pdf_and_undo_exact_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Matemática").mkdir()
            source = root / "aula.pdf"
            document = canvas.Canvas(str(source))
            document.drawString(72, 720, "Matematica: aritmetica e algebra")
            document.showPage()
            document.save()
            result = extract_pdf(source, False)
            self.assertIn("Matematica", result["text"])
            proposals = analyze(root, False)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0].subject, "Matemática")
            db = root / "history.db"
            outcome = execute(root, proposals, db)
            self.assertEqual(outcome["moved"], 1)
            destination = root / "Matemática" / "aula.pdf"
            self.assertTrue(destination.exists())
            self.assertEqual(last_undoable(db), outcome["session_id"])
            undone = undo_last(db)
            self.assertEqual(undone["restored"], 1)
            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())

    def test_conflict_does_not_overwrite_and_changed_file_blocks_undo(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Matemática").mkdir()
            source = root / "aula.pdf"
            source.write_bytes(b"first")
            existing = root / "Matemática" / "aula.pdf"
            existing.write_bytes(b"another")
            proposal = Proposal(source, "Matemática", "", "", "", "aula.pdf", "aula.pdf", "", False)
            db = root / "history.db"
            outcome = execute(root, [proposal], db)
            self.assertEqual(outcome["moved"], 1)
            moved = root / "Matemática" / "aula_1.pdf"
            self.assertEqual(existing.read_bytes(), b"another")
            self.assertEqual(moved.read_bytes(), b"first")
            moved.write_bytes(b"edited")
            undone = undo_last(db)
            self.assertEqual(undone["blocked"], 1)
            self.assertFalse(source.exists())
            self.assertEqual(moved.read_bytes(), b"edited")


if __name__ == "__main__":
    unittest.main()
