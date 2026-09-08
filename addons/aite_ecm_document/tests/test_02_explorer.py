# -*- coding: utf-8 -*-
import base64
import io

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

PDF = base64.b64encode(b"%PDF-1.4\n%AITE explorer\n%%EOF\n")


def _png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (800, 600), (14, 92, 107)).save(buf, format='PNG')
    return base64.b64encode(buf.getvalue())


@tagged('post_install', '-at_install', 'aite_ecm_document')
class TestExplorer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.agent = Users.create({'name': "Agent X", 'login': "ecm_x_agent",
                                  'groups_id': [(6, 0, [cls.env.ref(
                                      'aite_courrier_base.group_agent').id])]})
        cls.manager = Users.create({'name': "Manager X", 'login': "ecm_x_manager",
                                    'groups_id': [(6, 0, [cls.env.ref(
                                        'aite_courrier_base.group_manager').id])]})
        cls.jur = cls.env.ref('aite_ecm_document.folder_juridique')
        cls.sub = cls.env['aite.ecm.folder'].create({'name': "Baux X",
                                                     'parent_id': cls.jur.id})
        cls.tag = cls.env['aite.ecm.tag'].create({'name': "Tag X"})
        internal = cls.env.ref('aite_courrier_base.confidentiality_internal')
        Doc = cls.env['aite.ecm.document'].with_user(cls.manager)
        cls.d1 = Doc.create({'name': "Bail agence", 'folder_id': cls.sub.id,
                             'confidentiality_id': internal.id,
                             'tag_ids': [(6, 0, [cls.tag.id])]})
        cls.d1.add_version("bail.pdf", PDF)
        cls.d2 = Doc.create({'name': "Contrat cadre", 'folder_id': cls.jur.id,
                             'confidentiality_id': internal.id})
        cls.d2.add_version("contrat.pdf", PDF)
        cls.d3 = Doc.create({'name': "Sans fichier", 'folder_id': cls.jur.id,
                             'confidentiality_id': internal.id})

    def test_01_meta(self):
        meta = self.env['aite.ecm.document'].with_user(self.manager).explorer_meta()
        folders = {f['id']: f for f in meta['folders']}
        self.assertEqual(folders[self.sub.id]['count'], 1)
        self.assertTrue(folders[self.sub.id]['can_write'])
        self.assertIn("Tag X", [t['name'] for t in meta['tags']])
        self.assertTrue(any(s['key'] == 'draft' for s in meta['states']))
        self.assertIn('trash_count', meta)

    def test_02_search(self):
        Doc = self.env['aite.ecm.document'].with_user(self.manager)
        res = Doc.explorer_search({'folder_id': self.jur.id})
        ids = [r['id'] for r in res['records']]
        self.assertIn(self.d1.id, ids)          # sous-dossier inclus
        self.assertIn(self.d2.id, ids)
        res = Doc.explorer_search({'tag_ids': [self.tag.id]})
        self.assertEqual([r['id'] for r in res['records']], [self.d1.id])
        res = Doc.explorer_search({'search': "contrat.pdf"})
        self.assertEqual([r['id'] for r in res['records']], [self.d2.id])
        res = Doc.explorer_search({'folder_id': self.jur.id, 'order': 'name', 'limit': 1})
        self.assertEqual(res['total'], 3)
        self.assertEqual(len(res['records']), 1)
        self.d3.action_trash()
        res = Doc.explorer_search({'trash': True})
        self.assertIn(self.d3.id, [r['id'] for r in res['records']])
        rec = Doc.explorer_search({'search': "Bail"})['records'][0]
        self.assertEqual(rec['file_extension'], 'pdf')
        self.assertEqual(rec['folder'], self.sub.complete_name)

    def test_03_thumbnails(self):
        self.assertEqual(self.d1.thumbnail_status, 'client')
        img = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Photo", 'folder_id': self.jur.id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        img.add_version("photo.png", _png())
        self.assertEqual(img.thumbnail_status, 'present')
        self.assertTrue(img.thumbnail)
        self.env['aite.ecm.document'].with_user(self.manager).explorer_set_thumbnail(
            self.d1.id, _png())
        self.assertEqual(self.d1.thumbnail_status, 'present')
        rec = self.env['aite.ecm.document'].with_user(self.manager).explorer_search(
            {'search': "Bail"})['records'][0]
        self.assertTrue(rec['thumbnail_url'])

    def test_04_bulk(self):
        res = self.env['aite.ecm.document'].with_user(self.manager).explorer_bulk(
            'final', [self.d1.id, self.d2.id, self.d3.id])
        self.assertEqual(res['done'], 2)
        self.assertEqual([e['id'] for e in res['errors']], [self.d3.id])
        self.assertEqual((self.d1.state, self.d2.state), ('final', 'final'))
        res = self.env['aite.ecm.document'].with_user(self.manager).explorer_bulk(
            'tag', [self.d2.id], {'tag_ids': [self.tag.id]})
        self.assertIn(self.tag, self.d2.tag_ids)

    def test_05_folder(self):
        Doc = self.env['aite.ecm.document']
        folder = Doc.with_user(self.manager).explorer_create_folder("Nouveau X", self.jur.id)
        self.assertEqual(self.env['aite.ecm.folder'].browse(folder['id']).parent_id, self.jur)
        with self.assertRaises(AccessError):
            Doc.with_user(self.agent).explorer_create_folder("Interdit", self.jur.id)

    def test_06_rights(self):
        conf = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Secret du manager", 'folder_id': self.jur.id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_confidential').id})
        conf.add_version("secret.pdf", PDF)
        res = self.env['aite.ecm.document'].with_user(self.agent).explorer_search(
            {'folder_id': self.jur.id})
        self.assertNotIn(conf.id, [r['id'] for r in res['records']])
        res = self.env['aite.ecm.document'].with_user(self.manager).explorer_search(
            {'folder_id': self.jur.id})
        self.assertIn(conf.id, [r['id'] for r in res['records']])
