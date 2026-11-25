import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

from adaptive_analysis import analyze_pdf, page_plan


class AdaptiveAnalysisTests(unittest.TestCase):
    def test_long_document_reads_later_chapter(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "livro.pdf"
            doc = canvas.Canvas(str(path))
            for index in range(30):
                if index == 15:
                    doc.bookmarkPage("chapter")
                    doc.addOutlineEntry("Capitulo de pensamento computacional", "chapter")
                    doc.drawString(72, 720, "Pensamento Computacional e decomposicao de problemas")
                doc.showPage()
            doc.save()
            row = analyze_pdf(path)
            self.assertIn("16", row["pages_read"].split(","))
            self.assertEqual(row["subject"], "Pensamento Computacional")

    def test_generic_ai_in_activity_is_not_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "atividade.pdf"
            doc = canvas.Canvas(str(path))
            doc.drawString(72, 720, "Atividade avaliativa: inteligencia artificial e IA generativa")
            doc.drawString(72, 690, "inteligencia artificial e IA generativa em um estudo de caso")
            doc.save()
            row = analyze_pdf(path)
            self.assertNotEqual(row["status"], "SEGURA")

    def test_plan_has_bound_and_later_samples(self):
        pages = page_plan(200, [12, 80, 120])
        self.assertLessEqual(len(pages), 16)
        self.assertIn((80, "capitulo"), pages)


if __name__ == "__main__":
    unittest.main()
