# -*- coding: utf-8 -*-
"""Miroir Nextcloud des pièces de courrier : classement
``Courrier/<année>/<référence> - <objet>``, envoi à la création d'une
version, import d'une modification faite dans Nextcloud.

La synchronisation du courrier est **optionnelle** (paramètre
``sync_courrier``) : le module doit rester inerte tant qu'elle est décochée.
"""
import base64
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

PDF1 = b"%PDF-1.4\n%courrier v1\n%%EOF\n"
PDF2 = b"%PDF-1.4\n%courrier v2 (modifie dans Nextcloud)\n%%EOF\n"
PARAM = 'aite_ecm_nextcloud.'


class FakeNextcloud:
    """Serveur Nextcloud en mémoire (mêmes signatures que le client réel)."""

    def __init__(self):
        self.files = {}
        self.dirs = {''}
        self.calls = []
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
        if path in self.files:
            fileid, etag, data = self.files[path]
            return {'fileid': fileid, 'etag': etag, 'size': len(data),
                    'is_dir': False, 'name': path.rsplit('/', 1)[-1]}
        if path.strip('/') in self.dirs:
            return {'fileid': 'dir', 'etag': 'root-%d' % self._seq,
                    'is_dir': True, 'name': path}
        return None

    def download(self, path):
        self.calls.append(('download', path))
        return self.files[path][2]

    def move(self, src, dst):
        self.calls.append(('move', src, dst))
        self.files[dst] = self.files.pop(src)

    def delete(self, path):
        self.calls.append(('delete', path))

    def modify(self, path, data):
        fileid = self.files[path][0]
        self._seq += 1
        self.files[path] = (fileid, "etag-%d" % self._seq, data)


@tagged('post_install', '-at_install', 'aite_ecm_nextcloud_courrier')
class TestNextcloudCourrier(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Param = cls.env['ir.config_parameter'].sudo()
        Param.set_param(PARAM + 'url', 'https://cloud.test')
        Param.set_param(PARAM + 'user', 'odoo-ecm')
        Param.set_param(PARAM + 'password', 'app-password')
        Param.set_param(PARAM + 'mode', 'bidir')
        Param.set_param(PARAM + 'sync_courrier', 'True')
        # L'enregistrement d'un courrier est le métier de l'agent : seuls
        # les groupes « Agent » et « Administrateur » peuvent en créer.
        cls.agent = cls.env['res.users'].with_context(
            no_reset_password=True).create({
                'name': "Agent NC courrier", 'login': "nc_c_agent",
                'email': "nc_c_agent@aite.test",
                'groups_id': [(6, 0, [cls.env.ref(
                    'aite_courrier_base.group_agent').id])]})
        cls.courrier = cls.env['aite.courrier'].with_user(cls.agent).create({
            'subject': "Facture : groupe électrogène 60 kVA",
            'type_id': cls.env['aite.courrier.type'].search(
                [('category', '=', 'entrant')], limit=1).id,
            'responsible_id': cls.agent.id})
        cls.courrier.action_launch_circuit()

    def setUp(self):
        super().setUp()
        self.fake = FakeNextcloud()
        patcher = patch.object(
            self.env.registry['aite.courrier.document'], '_nc_client',
            lambda *a, **k: self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _piece(self, name="Facture fournisseur"):
        return self.env['aite.courrier.document'].with_user(
            self.agent).create({'name': name,
                                'courrier_id': self.courrier.id})

    # ------------------------------------------------------------------ #
    def test_01_model_is_mirrored(self):
        piece = self._piece()
        self.assertIn('nc_sync_state', piece._fields,
                      "la pièce de courrier n'a pas reçu le mixin Nextcloud")
        self.assertIn('aite.courrier.document',
                      self.env['aite.ecm.document']._nc_models())

    def test_02_target_path(self):
        piece = self._piece()
        piece.add_version("facture.pdf", base64.b64encode(PDF1))
        self.assertTrue(piece.nc_path.startswith("Courrier/"))
        self.assertIn(self.courrier.reference, piece.nc_path)
        self.assertTrue(piece.nc_path.endswith("facture.pdf"))
        # Les caractères interdits d'un système de fichiers sont neutralisés.
        self.assertNotIn(':', piece.nc_path)

    def test_03_push_on_version(self):
        piece = self._piece()
        piece.add_version("facture.pdf", base64.b64encode(PDF1))
        self.assertIn(('upload', piece.nc_path), self.fake.calls)
        self.assertEqual(piece.nc_sync_state, 'synced')
        self.assertTrue(piece.nc_file_id and piece.nc_etag)

    def test_04_pull_modification(self):
        piece = self._piece()
        piece.add_version("facture.pdf", base64.b64encode(PDF1))
        self.fake.modify(piece.nc_path, PDF2)
        self.assertTrue(piece._nc_pull())
        piece.invalidate_recordset()
        self.assertEqual(len(piece.version_ids), 2)
        self.assertEqual(
            base64.b64decode(piece.latest_version_id.file_data), PDF2)
        self.assertEqual(piece.nc_sync_state, 'synced')
        # L'auteur de l'import est le responsable du courrier.
        self.assertEqual(piece.latest_version_id.uploaded_by, self.agent)

    def test_05_unchanged_file_creates_no_version(self):
        piece = self._piece()
        piece.add_version("facture.pdf", base64.b64encode(PDF1))
        self.assertFalse(piece._nc_pull())
        self.assertEqual(len(piece.version_ids), 1)

    def test_06_disabled_when_option_is_off(self):
        self.env['ir.config_parameter'].sudo().set_param(
            PARAM + 'sync_courrier', 'False')
        piece = self._piece("Pièce hors synchronisation")
        piece.add_version("hors.pdf", base64.b64encode(PDF1))
        self.assertNotIn(('upload', piece.nc_path or ''), self.fake.calls)
        self.assertIn(piece.nc_sync_state, (False, 'none', ''))
