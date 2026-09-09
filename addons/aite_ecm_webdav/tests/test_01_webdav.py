# -*- coding: utf-8 -*-
import base64
from urllib.parse import quote

from odoo.tests import HttpCase, tagged

DOCX = base64.b64encode(b"PK\x03\x04 fake docx v1")
DOCX2 = base64.b64encode(b"PK\x03\x04 fake docx v2")


@tagged('post_install', '-at_install', 'aite_ecm_webdav')
class TestEcmWebdav(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.agent = Users.create({'name': "Agent DAV", 'login': "dav_agent",
                                  'password': "dav_agent_pwd",
                                  'groups_id': [(6, 0, [cls.env.ref(
                                      'aite_courrier_base.group_agent').id])]})
        cls.other = Users.create({'name': "Autre DAV", 'login': "dav_other",
                                  'password': "dav_other_pwd",
                                  'groups_id': [(6, 0, [cls.env.ref(
                                      'aite_courrier_base.group_agent').id])]})
        cls.folder = cls.env.ref('aite_ecm_document.folder_juridique')
        cls.doc = cls.env['aite.ecm.document'].with_user(cls.agent).create({
            'name': "Contrat DAV", 'folder_id': cls.folder.id,
            'confidentiality_id': cls.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        cls.doc.add_version("contrat.docx", DOCX)

    def _dav(self, method, path, user="dav_agent", password="dav_agent_pwd",
             data=None, headers=None):
        hdrs = {'Authorization': 'Basic ' + base64.b64encode(
            ("%s:%s" % (user, password)).encode()).decode()}
        hdrs.update(headers or {})
        url = '/webdav/aite_ecm/' + '/'.join(quote(p) for p in path.split('/')) \
            if path else '/webdav/aite_ecm/'
        return self.opener.request(method, self.base_url() + url, data=data,
                                   headers=hdrs, timeout=30)

    def test_01_propfind(self):
        resp = self._dav('PROPFIND', '', headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 207)
        self.assertIn("Sans classement", resp.text)
        self.assertIn("Juridique et contrats", resp.text)
        resp = self._dav('PROPFIND', "Juridique et contrats", headers={'Depth': '1'})
        self.assertIn("%s - Contrat DAV.docx" % self.doc.reference, resp.text)

    def test_02_get(self):
        resp = self._dav('GET', "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, base64.b64decode(DOCX))
        self.assertIn(self.doc.latest_version_id.sha256, resp.headers.get('ETag', ''))

    def test_03_put(self):
        path = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        resp = self._dav('PUT', path, data=base64.b64decode(DOCX2))
        self.assertEqual(resp.status_code, 204)
        self.doc.invalidate_recordset()
        self.assertEqual(self.doc.version_count, 2)
        self.assertEqual(self.doc.latest_version_id.uploaded_by, self.agent)
        resp = self._dav('PUT', "Juridique et contrats/Nouveau depuis le lecteur.docx",
                         data=base64.b64decode(DOCX))
        self.assertEqual(resp.status_code, 201)
        new = self.env['aite.ecm.document'].search([('name', '=', "Nouveau depuis le lecteur")])
        self.assertEqual(new.folder_id, self.folder)

    def test_04_lock(self):
        path = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        resp = self._dav('LOCK', path, headers={'Timeout': 'Second-3600'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('opaquelocktoken', resp.headers.get('Lock-Token', ''))
        self.doc.invalidate_recordset()
        self.assertEqual(self.doc.checkout_user_id, self.agent)
        resp = self._dav('PUT', path, user="dav_other", password="dav_other_pwd",
                         data=base64.b64decode(DOCX2))
        self.assertEqual(resp.status_code, 423)
        resp = self._dav('UNLOCK', path)
        self.assertEqual(resp.status_code, 204)
        self.doc.invalidate_recordset()
        self.assertFalse(self.doc.is_checked_out)

    def test_05_move(self):
        path = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        dest = self.base_url() + '/webdav/aite_ecm/' + quote(
            "Direction générale/%s - Contrat renommé.docx" % self.doc.reference)
        resp = self._dav('MOVE', path, headers={'Destination': dest})
        self.assertEqual(resp.status_code, 201)
        self.doc.invalidate_recordset()
        self.assertEqual(self.doc.folder_id, self.env.ref('aite_ecm_document.folder_direction'))
        self.assertEqual(self.doc.name, "Contrat renommé")

    def test_06_office_uri(self):
        self.assertTrue(self.doc.office_uri.startswith("ms-word:ofe|u|"))
        self.assertIn("/webdav/aite_ecm/", self.doc.office_uri)
        self.assertEqual(self.doc.office_app, "Word")
        pdf = self.env['aite.ecm.document'].create({'name': "PDF"})
        pdf.add_version("x.pdf", base64.b64encode(b"%PDF-1.4"))
        self.assertFalse(pdf.office_uri)

    def test_07_security(self):
        resp = self.opener.request('PROPFIND', self.base_url() + '/webdav/aite_ecm/',
                                   headers={'Depth': '1'}, timeout=30)
        self.assertEqual(resp.status_code, 401)
        secret = self.env['aite.ecm.document'].with_user(self.other).create({
            'name': "Secret de l'autre", 'folder_id': self.folder.id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_confidential').id})
        secret.add_version("s.docx", DOCX)
        resp = self._dav('PROPFIND', "Juridique et contrats", headers={'Depth': '1'})
        self.assertNotIn("Secret de l'autre", resp.text)
