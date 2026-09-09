# -*- coding: utf-8 -*-
import base64
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from odoo.addons.aite_ecm_document.tests.common import EcmTransactionCase

from odoo.addons.aite_ecm_office.models import aite_ecm_document as ecm_doc_module

DOCX = base64.b64encode(b"PK\x03\x04 fake docx v1")
DOCX2 = base64.b64encode(b"PK\x03\x04 fake docx v2")


class FakeDrive:
    """Google Drive simulé, sans réseau.

    Les signatures reprennent exactement celles de ``GoogleDriveClient``
    (``ensure_folder``, ``upload``, ``metadata``, ``download``, ``delete``) :
    toute dérive entre le simulateur et le client réel ferait passer les tests
    sur une interface qui n'existe pas.
    """

    def __init__(self):
        self.files = {}
        self.calls = []
        self._seq = 0

    def ensure_folder(self, name):
        self.calls.append(('ensure_folder', name))
        return "gfolder-%s" % name.replace(' ', '-').lower()

    def upload(self, name, content, mimetype, folder_id=None, convert_to=None):
        self._seq += 1
        file_id = "gfile-%d" % self._seq
        self.files[file_id] = {'name': name, 'content': content,
                               'mimetype': convert_to or mimetype,
                               'modified': '2026-09-09T10:00:00.000Z'}
        self.calls.append(('upload', name))
        return dict(self.files[file_id], id=file_id,
                    mimeType=self.files[file_id]['mimetype'],
                    modifiedTime=self.files[file_id]['modified'],
                    webViewLink="https://drive.google.com/file/d/%s/view" % file_id)

    def metadata(self, file_id):
        self.calls.append(('metadata', file_id))
        entry = self.files[file_id]
        return dict(entry, id=file_id, mimeType=entry['mimetype'],
                    modifiedTime=entry['modified'], trashed=False,
                    webViewLink="https://drive.google.com/file/d/%s/view" % file_id)

    def download(self, file_id, mimetype):
        """Contrat du client réel : (contenu, type MIME, extension)."""
        self.calls.append(('download', file_id))
        return self.files[file_id]['content'], mimetype, 'docx'

    def delete(self, file_id):
        self.calls.append(('delete', file_id))
        self.files.pop(file_id, None)

    def edit(self, file_id, content):
        """Simule une modification faite dans l'éditeur Google."""
        self.files[file_id]['content'] = content
        self.files[file_id]['modified'] = '2026-09-09T11:30:00.000Z'


@tagged('post_install', '-at_install', 'aite_ecm_office')
class TestOfficeGoogle(EcmTransactionCase):

    def setUp(self):
        super().setUp()
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param('aite_ecm_office.google_client_id', 'client-id')
        Param.set_param('aite_ecm_office.google_client_secret', 'secret')
        Param.set_param('web.base.url', 'https://ecm.test')
        self.user = self._make_user("Agent GD", "gd_agent", 'group_agent')
        self.doc = self.env['aite.ecm.document'].with_user(self.user).create({
            'name': "Note", 'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        self.doc.add_version("note.docx", DOCX)
        self.fake = FakeDrive()

    def test_06_google_round_trip(self):
        doc = self.doc.with_user(self.user)
        action = doc.action_open_google()
        self.assertIn('accounts.google.com', action['url'])       # pas encore autorisé
        self.user.sudo().write({'ecm_google_refresh_token': 'rt',
                                'ecm_google_access_token': 'at',
                                'ecm_google_token_expiry': '2099-01-01 00:00:00'})
        with patch.object(ecm_doc_module, 'GoogleDriveClient', lambda token: self.fake):
            action = doc.action_open_google()
            self.assertTrue(action['url'].startswith('https://docs.google.com/document/d/gfile-1'))
            self.assertEqual(doc.gdrive_file_id, 'gfile-1')
            self.assertTrue(doc.is_checked_out)
            self.assertFalse(doc._gdrive_pull())                       # rien n'a bougé
            self.fake.edit('gfile-1', base64.b64decode(DOCX2))
            self.assertTrue(doc._gdrive_pull())
            self.assertEqual(doc.version_count, 2)
            self.assertEqual(doc.latest_version_id.file_name, "note.docx")
            doc.action_google_finish()
            self.assertIn(('delete', 'gfile-1'), self.fake.calls)
            self.assertFalse(doc.gdrive_file_id)
            self.assertFalse(doc.is_checked_out)


DISCOVERY = """<?xml version="1.0" encoding="UTF-8"?>
<wopi-discovery><net-zone name="external-http">
<app name="writer"><action name="edit" ext="docx" urlsrc="https://office.test/browser/abc/cool.html?"/>
<action name="view" ext="docx" urlsrc="https://office.test/browser/abc/cool.html?"/></app>
<app name="calc"><action name="edit" ext="xlsx" urlsrc="https://office.test/browser/abc/cool.html?"/></app>
<app name="draw"><action name="view" ext="pdf" urlsrc="https://office.test/browser/abc/cool.html?"/></app>
</net-zone></wopi-discovery>"""


@tagged('post_install', '-at_install', 'aite_ecm_office')
class TestOfficeWopi(EcmTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = cls._make_user("Agent WOPI", "wopi_agent", 'group_agent')
        cls.other = cls._make_user("Autre WOPI", "wopi_other", 'group_agent')
        Param = cls.env['ir.config_parameter'].sudo()
        Param.set_param('web.base.url', 'https://ecm.test')
        Param.set_param('aite_ecm_office.wopi_server_url', 'https://office.test')
        cls.Token = cls.env['aite.ecm.office.token']
        cls.doc = cls.env['aite.ecm.document'].with_user(cls.agent).create({
            'name': "Procédure qualité",
            'folder_id': cls.env.ref('aite_ecm_document.folder_qualite').id,
            'confidentiality_id': cls.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        cls.doc.add_version("procedure.docx", DOCX)

    def setUp(self):
        super().setUp()
        patcher = patch.object(self.env.registry['aite.ecm.office.token'],
                               '_discovery', lambda *a, **k: DISCOVERY)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_07_wopi(self):
        self.assertTrue(self.doc.wopi_available)
        self.assertIn('cool.html', self.Token._editor_urlsrc('docx', 'edit'))
        token = self.Token._issue(self.doc, self.agent, True)
        self.assertEqual(self.Token._resolve(token.token, self.doc.id), token)
        self.assertIsNone(self.Token._resolve('faux', self.doc.id))
        token.write({'expiry': fields.Datetime.now() - timedelta(minutes=1)})
        self.assertIsNone(self.Token._resolve(token.token, self.doc.id))
        token = self.Token._issue(self.doc, self.agent, True)
        info = token.check_file_info()
        self.assertEqual(info['BaseFileName'], "procedure.docx")
        self.assertTrue(info['UserCanWrite'] and info['SupportsLocks'])
        self.assertEqual(info['Version'], str(self.doc.latest_version_id.id))
        content, mimetype = token.get_file()
        self.assertEqual(content, base64.b64decode(DOCX))
        self.assertIn('WOPISrc=https%%3A%%2F%%2Fecm.test%%2Fecm%%2Fwopi%%2Ffiles%%2F%d' % self.doc.id,
                      token._editor_url('edit'))
        # verrou = réservation
        code, _headers = token.lock('lock-1')
        self.assertEqual(code, 200)
        self.assertTrue(self.doc.is_checked_out)
        self.assertEqual(self.doc.checkout_user_id, self.agent)
        other = self.Token._issue(self.doc, self.other, True)
        code, headers = other.lock('lock-2')
        self.assertEqual(code, 409)
        self.assertIn('X-WOPI-Lock', headers)
        code, _headers = other.put_file(b"%DOCX autre", 'lock-2')
        self.assertEqual(code, 409)
        # sauvegarde = version
        code, headers = token.put_file(b"PK contenu modifie", 'lock-1')
        self.assertEqual(code, 200)
        self.assertEqual(self.doc.version_count, 2)
        self.assertEqual(headers['X-WOPI-ItemVersion'], str(self.doc.latest_version_id.id))
        code, _headers = token.unlock('lock-1')
        self.assertEqual(code, 200)
        self.assertFalse(self.doc.is_checked_out)
        # pdf : aperçu seulement
        pdf = self.env['aite.ecm.document'].with_user(self.agent).create({
            'name': "Note", 'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        pdf.add_version("note.pdf", base64.b64encode(b"%PDF-1.4\n%%EOF"))
        self.assertTrue(pdf.wopi_available)
        self.assertIn('cool.html', self.Token._editor_urlsrc('pdf', 'edit'))
        self.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_office.wopi_server_url', '')
        pdf.invalidate_recordset(['wopi_available'])
        self.assertFalse(pdf.wopi_available)
