# -*- coding: utf-8 -*-
"""Capture e-mail : un message arrivé sur l'alias devient un courrier
pré-qualifié, ses pièces jointes deviennent des pièces GED versionnées.
"""
import base64

from odoo import fields
from odoo.tests import TransactionCase, tagged

PDF = base64.b64encode(b"%PDF-1.4\n%piece jointe\n%%EOF\n")
PNG_SMALL = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 200)
PNG_BIG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * (9 * 1024))


@tagged('post_install', '-at_install', 'aite_courrier_capture')
class TestCapture(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Courrier = cls.env['aite.courrier']
        cls.Type = cls.env['aite.courrier.type']
        cls.partner = cls.env['res.partner'].create({
            'name': "Brasserie du Littoral",
            'email': "contact@littoral.test", 'is_company': True})

    def _msg(self, **kw):
        values = {
            'subject': "Réclamation facture 2026-0147",
            'email_from': '"Brasserie du Littoral" <contact@littoral.test>',
            'to': "courrier@aite.test",
            'message_id': "<capture-1@littoral.test>",
            'body': "<p>Bonjour, nous contestons la facture…</p>",
        }
        values.update(kw)
        return values

    # ------------------------------------------------------------------ #
    def test_01_default_type(self):
        """Le type « capture » l'emporte ; à défaut, le premier type entrant."""
        fallback = self.Courrier._capture_default_type()
        self.assertTrue(fallback)
        self.assertEqual(fallback.category, 'entrant')
        marked = self.Type.search([('category', '=', 'entrant')],
                                  order='id desc', limit=1)
        marked.mail_capture_default = True
        self.assertEqual(self.Courrier._capture_default_type(), marked)

    def test_02_parse_sender(self):
        name, email = self.Courrier._parse_sender(
            '"Brasserie du Littoral" <contact@littoral.test>')
        self.assertEqual(email, "contact@littoral.test")
        self.assertIn("Littoral", name)
        name, email = self.Courrier._parse_sender("simple@aite.test")
        self.assertEqual(email, "simple@aite.test")
        self.assertEqual(self.Courrier._parse_sender(''), ('', ''))

    def test_03_message_new_creates_courrier(self):
        courrier = self.Courrier.message_new(self._msg())
        self.assertTrue(courrier.exists())
        self.assertEqual(courrier.subject, "Réclamation facture 2026-0147")
        self.assertEqual(courrier.sender_email, "contact@littoral.test")
        self.assertEqual(courrier.type_id.category, 'entrant')
        self.assertEqual(courrier.date_received,
                         fields.Date.context_today(courrier))
        self.assertEqual(courrier.state, 'draft')
        # Tracé au journal d'audit avec la source « system ».
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.courrier'),
             ('res_id', '=', courrier.id), ('source', '=', 'system')]))

    def test_04_message_without_subject(self):
        courrier = self.Courrier.message_new(
            self._msg(subject=False, message_id="<capture-2@littoral.test>"))
        self.assertTrue(courrier.subject)

    def test_05_attachments_become_ged_documents(self):
        courrier = self.Courrier.message_new(
            self._msg(message_id="<capture-3@littoral.test>"))
        attachments = self.env['ir.attachment'].create([
            {'name': "facture.pdf", 'datas': PDF},
            {'name': "signature.png", 'datas': PNG_SMALL},
            {'name': "photo_compteur.png", 'datas': PNG_BIG},
            {'name': "malware.exe", 'datas': PDF},
        ])
        courrier._capture_attachments_to_ged(attachments)
        names = courrier.document_ids.mapped('name')
        self.assertIn("facture.pdf", names)
        self.assertIn("photo_compteur.png", names)
        # Signature d'e-mail (petite image) et exécutable : écartés.
        self.assertNotIn("signature.png", names)
        self.assertNotIn("malware.exe", names)
        doc = courrier.document_ids.filtered(
            lambda d: d.name == "facture.pdf")
        self.assertEqual(doc.version_count, 1)
        self.assertEqual(doc.latest_version_id.version, 'v1')

    def test_06_already_versioned_attachment_is_skipped(self):
        courrier = self.Courrier.message_new(
            self._msg(message_id="<capture-4@littoral.test>"))
        doc = self.env['aite.courrier.document'].create({
            'name': "deja.pdf", 'courrier_id': courrier.id})
        doc.add_version("deja.pdf", PDF)
        before = len(courrier.document_ids)
        courrier._capture_attachments_to_ged(
            doc.version_ids.mapped('attachment_id'))
        courrier.invalidate_recordset()
        self.assertEqual(len(courrier.document_ids), before,
                         "une pièce déjà versionnée a été dupliquée")

    def test_07_incoming_email_posts_and_captures(self):
        """Parcours complet de la passerelle : message_process crée le
        courrier et archive la pièce jointe."""
        raw = (
            "MIME-Version: 1.0\n"
            "Content-Type: multipart/mixed; boundary=\"frontier\"\n"
            "From: \"Brasserie du Littoral\" <contact@littoral.test>\n"
            "To: courrier@aite.test\n"
            "Subject: Demande de devis groupe électrogène\n"
            "Message-Id: <capture-5@littoral.test>\n"
            "\n"
            "--frontier\n"
            "Content-Type: text/plain\n\n"
            "Merci de nous adresser un devis.\n"
            "--frontier\n"
            "Content-Type: application/pdf\n"
            "Content-Disposition: attachment; filename=\"cahier_des_charges.pdf\"\n"
            "Content-Transfer-Encoding: base64\n\n"
            "%s\n"
            "--frontier--\n" % PDF.decode()
        )
        courrier_id = self.env['mail.thread'].message_process(
            'aite.courrier', raw)
        courrier = self.env['aite.courrier'].browse(courrier_id)
        self.assertTrue(courrier.exists())
        self.assertEqual(courrier.subject,
                         "Demande de devis groupe électrogène")
        self.assertIn("cahier_des_charges.pdf",
                      courrier.document_ids.mapped('name'))
