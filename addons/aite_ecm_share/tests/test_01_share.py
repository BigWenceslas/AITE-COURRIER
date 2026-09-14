# -*- coding: utf-8 -*-
"""Partage externe par lien : validité (expiration, quota, corbeille),
filigrane, consultation seule, traçabilité des accès.
"""
import base64
import io
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged


def _pdf(text="Document partagé"):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    pdf.drawString(60, 780, text)
    pdf.showPage()
    pdf.save()
    return base64.b64encode(buf.getvalue())


DOCX = base64.b64encode(b"PK\x03\x04 faux docx")


@tagged('post_install', '-at_install', 'aite_ecm_share')
class TestEcmShare(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env['res.users'].with_context(
            no_reset_password=True).create({
                'name': "Manager partage", 'login': "share_manager",
                'email': "share_manager@aite.test",
                'groups_id': [(6, 0, [cls.env.ref(
                    'aite_courrier_base.group_manager').id])]})
        cls.doc = cls.env['aite.ecm.document'].with_user(cls.manager).create({
            'name': "Contrat partagé",
            'folder_id': cls.env.ref('aite_ecm_document.folder_juridique').id,
            'confidentiality_id': cls.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        cls.doc.add_version("contrat.pdf", _pdf())
        cls.Share = cls.env['aite.ecm.share']

    def _share(self, **vals):
        values = {'document_id': self.doc.id, 'name': "Lien de recette"}
        values.update(vals)
        return self.Share.with_user(self.manager).create(values)

    def _get(self, path):
        return self.opener.request('GET', self.base_url() + path, timeout=30)

    # ------------------------------------------------------------------ #
    def test_01_token_and_url(self):
        share = self._share()
        self.assertTrue(share.token and len(share.token) > 20)
        self.assertTrue(share.is_valid)
        self.assertIn("/ecm/share/%s" % share.token, share.url)
        # Deux partages ne partagent jamais le même jeton.
        self.assertNotEqual(share.token, self._share().token)

    def test_02_validity_rules(self):
        expired = self._share(expiry_date=fields.Datetime.now()
                              - timedelta(hours=1))
        self.assertFalse(expired.is_valid)
        quota = self._share(max_downloads=1)
        self.assertTrue(quota.is_valid)
        quota._register_access()
        quota.invalidate_recordset()
        self.assertFalse(quota.is_valid)
        off = self._share()
        off.action_deactivate()
        self.assertFalse(off.is_valid)
        # Document à la corbeille : le lien tombe aussi.
        trashed_doc = self.env['aite.ecm.document'].with_user(
            self.manager).create({
                'name': "À jeter",
                'confidentiality_id': self.env.ref(
                    'aite_courrier_base.confidentiality_internal').id})
        trashed_doc.add_version("x.pdf", _pdf())
        share = self._share(document_id=trashed_doc.id)
        trashed_doc.action_trash()
        share.invalidate_recordset()
        self.assertFalse(share.is_valid)

    def test_03_confidential_forces_watermark(self):
        secret = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Note confidentielle",
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_confidential').id})
        secret.add_version("note.pdf", _pdf())
        share = self._share(document_id=secret.id, watermark=False)
        self.assertTrue(share.watermark,
                        "un document confidentiel doit être filigrané")

    def test_04_creation_is_audited(self):
        share = self._share()
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.ecm.document'),
             ('res_id', '=', self.doc.id),
             ('name', 'ilike', "partage")]))
        share._register_access()
        self.assertEqual(share.download_count, 1)
        self.assertTrue(share.last_access)

    def test_05_served_content_and_watermark(self):
        plain = self._share(watermark=False)
        name, raw, mimetype = plain._served_content()
        self.assertEqual(name, "contrat.pdf")
        self.assertEqual(mimetype, 'application/pdf')
        marked = self._share(watermark=True,
                             watermark_text="Diffusion contrôlée")
        _n, raw2, _m = marked._served_content()
        self.assertTrue(raw2.startswith(b'%PDF'))
        self.assertNotEqual(raw, raw2, "le filigrane n'a pas été appliqué")

    def test_06_public_download(self):
        share = self._share(watermark=False)
        resp = self._get('/ecm/share/%s' % share.token)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Contrat partagé", resp.text)
        resp = self._get('/ecm/share/%s/file' % share.token)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertIn("contrat.pdf",
                      resp.headers.get('Content-Disposition', ''))
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        share.invalidate_recordset()
        self.assertEqual(share.download_count, 1)

    def test_07_invalid_token_is_404(self):
        resp = self._get('/ecm/share/jeton-inexistant')
        self.assertEqual(resp.status_code, 404)
        resp = self._get('/ecm/share/jeton-inexistant/file')
        self.assertEqual(resp.status_code, 404)
        expired = self._share(expiry_date=fields.Datetime.now()
                              - timedelta(days=1))
        self.assertEqual(
            self._get('/ecm/share/%s' % expired.token).status_code, 404)

    def test_08_view_only_serves_inline(self):
        share = self._share(view_only=True, watermark=False)
        resp = self._get('/ecm/share/%s/file' % share.token)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('Content-Disposition'), 'inline')
        # Consultation seule d'un fichier non PDF : refus explicite.
        other = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Tableur partagé",
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        other.add_version("tableau.docx", DOCX)
        share2 = self._share(document_id=other.id, view_only=True,
                             watermark=False)
        resp = self._get('/ecm/share/%s/file' % share2.token)
        self.assertEqual(resp.status_code, 403)

    def test_09_quota_closes_the_link(self):
        share = self._share(max_downloads=2, watermark=False)
        for _i in range(2):
            self.assertEqual(
                self._get('/ecm/share/%s/file' % share.token).status_code, 200)
        self.assertEqual(
            self._get('/ecm/share/%s/file' % share.token).status_code, 404)
