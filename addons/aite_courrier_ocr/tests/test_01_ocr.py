# -*- coding: utf-8 -*-
"""Indexation plein texte des pièces : mise en file, extraction de la couche
texte des PDF, repli OCR, et recherche d'un courrier par le contenu.

L'OCR d'images dépend de Tesseract, absent de la plupart des serveurs : le
module doit rester utilisable sans lui, c'est ce que ces tests vérifient.
"""
import base64
import io

from odoo.tests import TransactionCase, tagged

SCAN = base64.b64encode(b"%PDF-1.4\n%page scannee sans couche texte\n%%EOF\n")
IMAGE = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 2048)
NOT_INDEXED = base64.b64encode(b"texte brut")


def _pdf_with_text(text):
    """Vrai PDF portant une couche texte, écrit avec reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    for i, line in enumerate(text.split('\n')):
        pdf.drawString(60, 780 - 18 * i, line)
    pdf.showPage()
    pdf.save()
    return base64.b64encode(buf.getvalue())


@tagged('post_install', '-at_install', 'aite_courrier_ocr')
class TestOcr(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Version = cls.env['aite.courrier.document.version']
        cls.courrier = cls.env['aite.courrier'].create({
            'subject': "Facture groupe électrogène",
            'type_id': cls.env['aite.courrier.type'].search(
                [('category', '=', 'entrant')], limit=1).id})
        cls.doc = cls.env['aite.courrier.document'].create({
            'name': "Pièce OCR", 'courrier_id': cls.courrier.id})

    # ------------------------------------------------------------------ #
    def test_01_queue_on_create(self):
        """Seules les extensions indexables entrent dans la file."""
        version = self.doc.add_version("facture.pdf", SCAN)
        self.assertEqual(version.ocr_state, 'pending')
        other = self.env['aite.courrier.document'].create(
            {'name': "Note bureautique", 'courrier_id': self.courrier.id})
        version2 = other.add_version("note.docx", NOT_INDEXED)
        self.assertEqual(version2.ocr_state, 'none')

    def test_02_native_pdf_text(self):
        text = ("Facture n° FA-2026-0147 du 12 mars 2026\n"
                "Fourniture d'un groupe électrogène 60 kVA\n"
                "Montant total : 12 450 000 FCFA")
        version = self.doc.add_version("facture.pdf", _pdf_with_text(text))
        version._process_ocr()
        self.assertEqual(version.ocr_state, 'done')
        self.assertIn("FA-2026-0147", version.ocr_text)
        self.assertIn("groupe", version.ocr_text.lower())
        # Le texte alimente aussi l'index natif d'Odoo.
        self.assertIn("FA-2026-0147",
                      version.attachment_id.sudo().index_content or '')
        self.assertTrue(version.ocr_date)

    def test_03_scan_without_text_layer(self):
        """Sans couche texte ni Tesseract : état « indexé », texte vide —
        surtout pas d'erreur qui bloquerait le cron."""
        version = self.doc.add_version("scan.pdf", SCAN)
        version._process_ocr()
        self.assertEqual(version.ocr_state, 'done')
        self.assertEqual(version.ocr_text or '', '')

    def test_04_cron_processes_the_queue(self):
        text = "Procès-verbal du conseil d'administration du 4 avril 2026"
        self.doc.add_version("pv.pdf", _pdf_with_text(text))
        self.doc.add_version("scan.pdf", SCAN)
        self.assertTrue(self.Version.search_count(
            [('ocr_state', '=', 'pending')]))
        self.Version._cron_process_ocr(limit=50)
        self.assertFalse(self.Version.search_count(
            [('document_id', '=', self.doc.id), ('ocr_state', '=', 'pending')]))

    def test_05_reprocess(self):
        version = self.doc.add_version("pv.pdf", _pdf_with_text("Ordre du jour"))
        version._process_ocr()
        self.assertEqual(version.ocr_state, 'done')
        version.action_reprocess_ocr()
        self.assertEqual(version.ocr_state, 'pending')
        self.assertFalse(version.ocr_text)

    def test_06_broken_file_is_flagged_not_raised(self):
        version = self.doc.add_version("casse.pdf", SCAN)
        version.attachment_id.sudo().write({'datas': False})
        version.sudo().write({'ocr_state': 'pending'})
        version._process_ocr()
        # Fichier vide : pas d'exception, le cron continue.
        self.assertIn(version.ocr_state, ('done', 'error'))

    def test_07_search_courrier_by_content(self):
        version = self.doc.add_version(
            "facture.pdf",
            _pdf_with_text("Facture FA-2026-0147 — groupe électrogène"))
        version._process_ocr()
        found = self.env['aite.courrier'].search(
            [('document_fulltext', 'ilike', "FA-2026-0147")])
        self.assertIn(self.courrier, found)
        self.assertFalse(self.env['aite.courrier'].search(
            [('document_fulltext', 'ilike', "mot-qui-nexiste-nulle-part")]))

    def test_08_image_ocr_is_optional(self):
        """Sans Tesseract, l'OCR d'image renvoie une chaîne vide."""
        self.assertIsInstance(
            self.Version._ocr_image(base64.b64decode(IMAGE)), str)
