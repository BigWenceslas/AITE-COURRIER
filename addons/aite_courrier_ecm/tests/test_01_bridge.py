# -*- coding: utf-8 -*-
import base64

from odoo.tests import TransactionCase, tagged

PDF1 = base64.b64encode(b"%PDF-1.4\n%pont v1\n%%EOF\n")
PDF2 = base64.b64encode(b"%PDF-1.4\n%pont v2\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_courrier_ecm')
class TestCourrierEcmBridge(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ctype = cls.env['aite.courrier.type'].search([('code', '=', 'ENTR')],
                                                     limit=1)
        cls.courrier = cls.env['aite.courrier'].create({
            'subject': "Demande d'agrément", 'type_id': ctype.id,
            'sender': "ETS KAMDEM",
            'confidentiality_id': cls.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        cls.piece = cls.env['aite.courrier.document'].create({
            'name': "Demande signée", 'courrier_id': cls.courrier.id})
        cls.piece.add_version("demande.pdf", PDF1)

    def test_01_mirror(self):
        ecm = self.piece.ecm_document_id
        self.assertTrue(ecm)
        self.assertEqual((ecm.res_model, ecm.res_id),
                         ('aite.courrier', self.courrier.id))
        self.assertEqual(ecm.type_id.code, 'COUR')
        self.assertIn("Courrier", ecm.folder_id.complete_name)
        self.assertEqual(ecm.confidentiality_id, self.courrier.confidentiality_id)
        self.assertEqual(ecm.latest_version_id.attachment_id,
                         self.piece.latest_version_id.attachment_id)
        self.assertEqual(self.env['ir.attachment'].search_count(
            [('id', '=', ecm.latest_version_id.attachment_id.id)]), 1)

    def test_02_versions(self):
        self.piece.add_version("demande_v2.pdf", PDF2)
        ecm = self.piece.ecm_document_id
        self.assertEqual(ecm.version_count, 2)
        self.assertEqual(ecm.latest_version_id.attachment_id,
                         self.piece.latest_version_id.attachment_id)
        ecm.add_version("depuis_ecm.pdf", PDF1)
        self.assertEqual(self.piece.version_count, 3)
        self.assertEqual(self.piece.latest_version_id.attachment_id,
                         ecm.latest_version_id.attachment_id)

    def test_03_rename_and_confidentiality(self):
        self.piece.write({'name': "Demande signée et datée"})
        self.assertEqual(self.piece.ecm_document_id.name,
                         "Demande signée et datée")
        secret = self.env.ref('aite_courrier_base.confidentiality_confidential')
        self.courrier.write({'confidentiality_id': secret.id})
        self.assertEqual(self.piece.ecm_document_id.confidentiality_id, secret)

    def test_05_unlink_to_trash(self):
        ecm = self.piece.ecm_document_id
        self.piece.unlink()
        ecm.invalidate_recordset()
        self.assertTrue(ecm.exists())
        self.assertFalse(ecm.active)

    def test_06_backfill(self):
        piece = self.env['aite.courrier.document'].with_context(
            ecm_from_courrier=True).create({
                'name': "Pièce héritée", 'courrier_id': self.courrier.id})
        piece.with_context(ecm_from_courrier=True).add_version("h.pdf", PDF1)
        piece.sudo().write({'ecm_document_id': False})
        self.assertGreaterEqual(
            self.env['aite.courrier.document']._ecm_mirror_all(), 1)
        piece.invalidate_recordset()
        self.assertTrue(piece.ecm_document_id)
