# -*- coding: utf-8 -*-
import base64
import hashlib
import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.aite_ecm_document.tests.common import (
    EcmHttpCase, EcmTransactionCase,
)

from odoo.addons.aite_ecm_nextcloud.models import nextcloud_client as ncc

PDF1 = b"%PDF-1.4\n%AITE v1\n%%EOF\n"
PDF2 = b"%PDF-1.4\n%AITE v2 (modifie dans Nextcloud)\n%%EOF\n"
CLIENT = 'odoo.addons.aite_ecm_nextcloud.models.nextcloud_client.NextcloudClient'


class FakeNextcloud:
    """Serveur Nextcloud en mémoire : dossiers, fichiers, ETags, partages."""

    def __init__(self):
        self.files = {}          # chemin -> (fileid, etag, contenu)
        self.dirs = {''}
        self.calls = []
        self.shares = {}
        self._seq = 100

    def ensure_dir(self, path):
        self.calls.append(('ensure_dir', path))
        self.dirs.add(path.strip('/'))

    def upload(self, path, data):
        self._seq += 1
        fileid, etag = str(self._seq), "etag-%d" % self._seq
        self.files[path] = (fileid, etag, data)
        self.calls.append(('upload', path))
        return fileid, etag

    def stat(self, path=''):
        self.calls.append(('stat', path))
        if path in self.files:
            fileid, etag, data = self.files[path]
            return {'fileid': fileid, 'etag': etag, 'size': len(data),
                    'is_dir': False, 'name': path.rsplit('/', 1)[-1]}
        if path.strip('/') in self.dirs:
            # Nextcloud propage l'ETag d'un fichier modifié jusqu'à la racine :
            # l'empreinte d'un dossier doit donc changer à chaque écriture, pas
            # seulement quand le nombre de fichiers varie — sinon le sondage
            # se court-circuite et ne détecte jamais de modification.
            return {'fileid': 'dir', 'etag': 'dir-%d' % self._seq,
                    'is_dir': True, 'name': path}
        return None

    def listdir(self, path=''):
        self.calls.append(('listdir', path))
        return [dict(self.stat(p), name=p.rsplit('/', 1)[-1])
                for p in self.files if p.rsplit('/', 1)[0] == path]

    def download(self, path):
        self.calls.append(('download', path))
        return self.files[path][2]

    def move(self, src, dst):
        self.calls.append(('move', src, dst))
        self.files[dst] = self.files.pop(src)

    def delete(self, path):
        self.calls.append(('delete', path))

    def modify(self, path, data):
        """Simule une modification côté Nextcloud (client de synchronisation)."""
        fileid = self.files[path][0]
        self._seq += 1
        self.files[path] = (fileid, "etag-%d" % self._seq, data)

    def create_public_link(self, path, password=None, expire_date=None,
                           label=None, permissions=1):
        self.calls.append(('share', path, bool(password), expire_date))
        self.shares['42'] = path
        return {'id': '42', 'url': 'https://cloud.test/s/abc'}

    def delete_share(self, share_id):
        self.calls.append(('unshare', share_id))
        self.shares.pop(share_id, None)


@tagged('post_install', '-at_install', 'aite_ecm_nextcloud')
class TestNextcloud(EcmTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_nextcloud.url', 'https://cloud.test')
        cls.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_nextcloud.user', 'odoo-ecm')
        cls.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_nextcloud.password', 'app-password')
        cls.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_nextcloud.mode', 'bidir')
        cls.folder = cls.env.ref('aite_ecm_document.folder_juridique')
        cls.ctype = cls.env.ref('aite_ecm_document.type_contrat')
        cls.manager = cls._make_user("Manager NC", "nc_manager",
                                     'group_manager')

    def setUp(self):
        super().setUp()
        self.fake = FakeNextcloud()
        patcher = patch.object(
            self.env.registry['aite.ecm.document'], '_nc_client',
            lambda *a, **k: self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _doc(self, name="Contrat de maintenance : groupe électrogène"):
        doc = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': name, 'type_id': self.ctype.id,
            'folder_id': self.folder.id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        return doc

    def test_01_target_path(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        self.assertEqual(
            doc.nc_path,
            "Juridique et contrats/%s - Contrat de maintenance _ groupe "
            "électrogène/contrat.pdf" % doc.reference)
        self.assertNotIn(':', doc.nc_path.split('/')[1])

    def test_02_push_on_version(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        self.assertIn(('upload', doc.nc_path), self.fake.calls)
        self.assertEqual(doc.nc_sync_state, 'synced')
        self.assertTrue(doc.nc_file_id and doc.nc_etag)
        log = self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.ecm.document'), ('res_id', '=', doc.id),
             ('source', '=', 'nextcloud')])
        self.assertTrue(log)

    def test_03_pull_new_version(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        doc.with_user(self.manager).action_checkout()
        self.fake.modify(doc.nc_path, PDF2)
        self.assertTrue(doc._nc_pull())
        self.assertEqual(doc.version_count, 2)
        self.assertEqual(doc.latest_version_id.uploaded_by, self.manager)
        self.assertEqual(doc.nc_etag, self.fake.files[doc.nc_path][1])
        self.assertEqual(doc.nc_sync_state, 'synced')

    def test_04_pull_unchanged(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        self.assertFalse(doc._nc_pull())
        self.assertEqual(doc.version_count, 1)

    def test_05_conflict_when_locked(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        doc.action_mark_final()
        self.fake.modify(doc.nc_path, PDF2)
        self.assertFalse(doc._nc_pull())
        self.assertEqual(doc.nc_sync_state, 'conflict')
        self.assertEqual(doc.version_count, 1)

    def test_06_same_content(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        self.fake.modify(doc.nc_path, PDF1)      # réenregistré à l'identique
        self.assertFalse(doc._nc_pull())
        self.assertEqual(doc.version_count, 1)
        self.assertEqual(doc.nc_etag, self.fake.files[doc.nc_path][1])
        self.assertEqual(hashlib.sha256(PDF1).hexdigest(),
                         doc.latest_version_id.sha256)

    def test_07_move_on_reclassify(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        old = doc.nc_path
        doc.folder_id = self.env.ref('aite_ecm_document.folder_direction')
        self.assertEqual(doc.nc_sync_state, 'todo')
        doc._nc_push()
        self.assertIn(('move', old, doc.nc_path), self.fake.calls)
        self.assertTrue(doc.nc_path.startswith("Direction générale/"))

    def test_08_poll(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        Doc = self.env['aite.ecm.document']
        Doc._nc_poll(self.fake)                       # mémorise l'ETag racine
        self.fake.modify(doc.nc_path, PDF2)
        self.assertEqual(Doc._nc_poll(self.fake), 1)
        self.assertEqual(doc.version_count, 2)
        calls_before = len(self.fake.calls)
        Doc._nc_poll(self.fake)                       # rien n'a bougé
        self.assertEqual([c for c in self.fake.calls[calls_before:]
                          if c[0] == 'listdir'], [])

    def test_09_public_link(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        action = doc.action_nc_share()
        self.assertEqual(action['url'], 'https://cloud.test/s/abc')
        self.assertEqual(doc.nc_share_url, 'https://cloud.test/s/abc')
        share_call = [c for c in self.fake.calls if c[0] == 'share'][0]
        self.assertTrue(share_call[2] and share_call[3])
        doc.action_nc_unshare()
        self.assertFalse(doc.nc_share_url)
        self.assertIn(('unshare', '42'), self.fake.calls)

    def test_11_disabled(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_nextcloud.mode', 'off')
        doc = self._doc()
        doc.add_version("contrat.pdf", base64.b64encode(PDF1))
        self.assertEqual(doc.nc_sync_state, 'none')
        with self.assertRaises(UserError):
            doc.action_nc_push()


@tagged('post_install', '-at_install', 'aite_ecm_nextcloud')
class TestNextcloudWebhook(EcmHttpCase):

    def test_10_webhook(self):
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param('aite_ecm_nextcloud.webhook_secret', 'top-secret')
        Param.set_param('aite_ecm_nextcloud.mode', 'bidir')
        Param.set_param('aite_ecm_nextcloud.url', 'https://cloud.test')
        Param.set_param('aite_ecm_nextcloud.user', 'odoo-ecm')
        doc = self.env['aite.ecm.document'].create({
            'name': "Procédure", 'nc_file_id': '777',
            'nc_path': 'Qualité/x/proc.pdf', 'nc_sync_state': 'synced'})
        payload = json.dumps({'event': {
            'class': ncc.EVENT_NODE_WRITTEN,
            'node': {'id': 777, 'path': '/odoo-ecm/files/AITE ECM/Qualité/x/proc.pdf'}}})
        resp = self.url_open('/ecm/nextcloud/webhook', data=payload,
                             headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 403)
        resp = self.url_open('/ecm/nextcloud/webhook', data=payload,
                             headers={'Content-Type': 'application/json',
                                      'X-AITE-Secret': 'top-secret'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['marked'], 1)
        doc.invalidate_recordset()
        self.assertEqual(doc.nc_sync_state, 'pull')
