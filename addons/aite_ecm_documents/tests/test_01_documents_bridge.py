# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

PDF1 = base64.b64encode(b"%PDF-1.4\n%AITE bridge v1\n%%EOF\n")
PDF2 = base64.b64encode(b"%PDF-1.4\n%AITE bridge v2\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_ecm_documents')
class TestDocumentsBridge(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = cls.env.ref('aite_ecm_documents.documents_folder_ecm')
        cls.folder = cls.env.ref('aite_ecm_document.folder_juridique')
        cls.Card = cls.env['documents.document'].sudo()
        cls.Doc = cls.env['aite.ecm.document']

    def _doc(self, **vals):
        values = {'name': "Contrat", 'folder_id': self.folder.id}
        values.update(vals)
        return self.Doc.create(values)

    def test_01_folder_mirror(self):
        folder = self.env['aite.ecm.folder'].create({'name': "Baux"})
        self.assertTrue(folder.documents_folder_id)
        self.assertEqual(folder.documents_folder_id.folder_id, self.root)
        folder.parent_id = self.folder
        self.assertEqual(folder.documents_folder_id.folder_id,
                         self.folder.documents_folder_id)

    def test_02_single_card(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", PDF1)
        doc.add_version("contrat.pdf", PDF2)
        cards = self.Card.search([('res_model', '=', 'aite.ecm.document'),
                                  ('res_id', '=', doc.id)])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards.attachment_id, doc.latest_version_id.attachment_id)
        self.assertEqual(doc.documents_document_id, cards)

    def test_03_adoption(self):
        mirror = self.folder._get_or_create_documents_folder()
        attachment = self.env['ir.attachment'].create({
            'name': "Bail commercial.pdf", 'datas': PDF1})
        card = self.Card.create({'name': "Bail commercial.pdf", 'type': 'binary',
                                 'folder_id': mirror.id,
                                 'attachment_id': attachment.id})
        doc = self.Doc.search([('documents_document_id', '=', card.id)])
        self.assertEqual(len(doc), 1)
        self.assertEqual(doc.name, "Bail commercial")
        self.assertEqual(doc.folder_id, self.folder)
        self.assertEqual(doc.version_count, 1)
        self.assertEqual(doc.latest_version_id.attachment_id, attachment)
        self.assertEqual((card.res_model, card.res_id), ('aite.ecm.document', doc.id))
        self.assertEqual(self.env['ir.attachment'].search_count(
            [('res_model', '=', 'aite.ecm.document'), ('res_id', '=', doc.id)]), 1)

    def test_04_replacement(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", PDF1)
        card = doc.documents_document_id
        new_att = self.env['ir.attachment'].create({'name': "contrat.pdf",
                                                    'datas': PDF2})
        card.write({'attachment_id': new_att.id})
        self.assertEqual(doc.version_count, 2)
        self.assertEqual(doc.latest_version_id.attachment_id, new_att)

    def test_05_locked(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", PDF1)
        doc.action_mark_final()
        new_att = self.env['ir.attachment'].create({'name': "contrat.pdf",
                                                    'datas': PDF2})
        with self.assertRaises(UserError):
            doc.documents_document_id.write({'attachment_id': new_att.id})

    def test_06_unlink_guard(self):
        doc = self._doc()
        doc.add_version("contrat.pdf", PDF1)
        with self.assertRaises(UserError):
            doc.documents_document_id.unlink()

    def test_07_tags_and_trash(self):
        tag = self.env['aite.ecm.tag'].create({'name': "Urgent-bridge"})
        doc = self._doc(tag_ids=[(6, 0, [tag.id])])
        doc.add_version("contrat.pdf", PDF1)
        card = doc.documents_document_id
        self.assertIn("Urgent-bridge", card.tag_ids.mapped('name'))
        doc.action_trash()
        if 'active' in card._fields:
            self.assertFalse(card.with_context(active_test=False).active)
        doc.action_restore()
        if 'active' in card._fields:
            self.assertTrue(card.active)
