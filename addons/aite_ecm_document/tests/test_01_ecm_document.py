# -*- coding: utf-8 -*-
import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import EcmTransactionCase

PDF = base64.b64encode(b"%PDF-1.4\n%AITE ECM test\n%%EOF\n")
PDF2 = base64.b64encode(b"%PDF-1.4\n%AITE ECM test v2\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_ecm_document')
class TestEcmDocument(EcmTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.g_agent = cls.env.ref('aite_courrier_base.group_agent')
        cls.g_manager = cls.env.ref('aite_courrier_base.group_manager')
        cls.agent = cls._make_user("Agent A", "ecm_agent_a", 'group_agent')
        cls.agent_b = cls._make_user("Agent B", "ecm_agent_b", 'group_agent')
        cls.manager = cls._make_user("Manager", "ecm_manager", 'group_manager')
        cls.type_contrat = cls.env.ref('aite_ecm_document.type_contrat')
        cls.folder_jur = cls.env.ref('aite_ecm_document.folder_juridique')

    def _doc(self, user, **vals):
        values = {'name': "Contrat de maintenance", 'type_id': self.type_contrat.id}
        values.update(vals)
        return self.env['aite.ecm.document'].with_user(user).create(values)

    def test_01_create_defaults(self):
        doc = self._doc(self.manager)
        self.assertTrue(doc.reference.startswith("DOC-"))
        self.assertEqual(doc.folder_id, self.folder_jur)
        self.assertEqual(doc.confidentiality_id.code, 'CONF')

    def test_02_add_version(self):
        doc = self._doc(self.manager)
        v1 = doc.add_version("contrat.pdf", PDF)
        v2 = doc.add_version("contrat.pdf", PDF2, comment="corrections")
        self.assertEqual((v1.version, v2.version), ("v1", "v2"))
        self.assertEqual(len(v1.sha256), 64)
        self.assertEqual(doc.latest_version_id, v2)
        self.assertEqual(doc.version_count, 2)

    def test_03_extension_refused(self):
        doc = self._doc(self.manager)
        with self.assertRaises(ValidationError):
            doc.add_version("virus.exe", PDF)

    def test_04_duplicates(self):
        d1 = self._doc(self.manager)
        d2 = self._doc(self.manager, name="Copie")
        d1.add_version("a.pdf", PDF)
        d2.add_version("b.pdf", PDF)
        self.assertEqual(d1.duplicate_count, 1)
        self.assertIn(d1, d2.duplicate_ids)

    def test_05_checkout(self):
        doc = self._doc(self.manager, confidentiality_id=self.env.ref(
            'aite_courrier_base.confidentiality_internal').id)
        doc.with_user(self.agent).action_checkout()
        self.assertTrue(doc.is_checked_out)
        with self.assertRaises(AccessError):
            doc.with_user(self.agent_b).add_version("x.pdf", PDF)
        with self.assertRaises(UserError):
            doc.with_user(self.agent_b).action_checkin()
        doc.with_user(self.manager).action_checkin()
        self.assertFalse(doc.is_checked_out)

    def test_06_locked_when_final(self):
        doc = self._doc(self.manager)
        v1 = doc.add_version("a.pdf", PDF)
        doc.action_mark_final()
        with self.assertRaises(AccessError):
            doc.add_version("b.pdf", PDF2)
        with self.assertRaises(UserError):
            v1.unlink()

    def test_07_trash_and_purge(self):
        # type générique : aucune règle de conservation ne s'y applique, la
        # purge automatique peut donc détruire le document même lorsque
        # ``aite_ecm_records`` est installé (un contrat, lui, est protégé et
        # ne part que par un bordereau d'élimination).
        doc = self._doc(self.manager,
                        type_id=self.env.ref(
                            'aite_ecm_document.type_generique').id)
        doc.action_trash()
        self.assertFalse(doc.active)
        doc.action_restore()
        self.assertTrue(doc.active)
        doc.action_trash()
        doc.sudo().write({'trashed_date': fields.Datetime.now() - timedelta(days=45)})
        self.env['aite.ecm.document']._cron_purge_trash()
        self.assertFalse(doc.exists())

    def test_08_confidentiality(self):
        doc = self._doc(self.manager)  # CONF par défaut, propriétaire = manager
        with self.assertRaises(AccessError):
            doc.with_user(self.agent).read(['name'])
        self.assertEqual(doc.with_user(self.manager).name, "Contrat de maintenance")
        self.assertFalse(doc._check_document_access('read', self.agent))

    def test_09_folder_rights(self):
        folder = self.env['aite.ecm.folder'].create({
            'name': "Direction restreinte",
            'write_group_ids': [(6, 0, [self.g_manager.id])]})
        internal = self.env.ref('aite_courrier_base.confidentiality_internal')
        with self.assertRaises(AccessError):
            self._doc(self.agent, folder_id=folder.id,
                      confidentiality_id=internal.id)
        doc = self._doc(self.manager, folder_id=folder.id,
                        confidentiality_id=internal.id)
        self.assertTrue(doc.folder_id.user_can(self.agent, 'read'))
        self.assertFalse(doc.folder_id.user_can(self.agent, 'write'))

    def test_10_partner_mixin(self):
        partner = self.env['res.partner'].create({'name': "ETS KAMDEM"})
        self._doc(self.manager, res_model='res.partner', res_id=partner.id)
        self.assertEqual(partner.ecm_document_count, 1)
        self.assertEqual(partner.ecm_document_ids.res_display,
                         "Contact : ETS KAMDEM")


@tagged('post_install', '-at_install', 'aite_ecm_document')
class TestEcmRightsAndScan(EcmTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        g_manager = cls.env.ref('aite_courrier_base.group_manager')
        cls.agent_a = cls._make_user("Agent A2", "ecm_r_agent_a", 'group_agent')
        cls.agent_b = cls._make_user("Agent B2", "ecm_r_agent_b", 'group_agent')
        cls.manager = cls._make_user("Manager 2", "ecm_r_manager", 'group_manager')
        cls.internal = cls.env.ref('aite_courrier_base.confidentiality_internal')
        cls.conf = cls.env.ref('aite_courrier_base.confidentiality_confidential')
        cls.g_manager = g_manager

    def test_11_folder_named_users(self):
        folder = self.env['aite.ecm.folder'].create({
            'name': "Direction — nommés",
            'read_group_ids': [(6, 0, [self.g_manager.id])],
            'read_user_ids': [(6, 0, [self.agent_a.id])],
            'write_group_ids': [(6, 0, [self.g_manager.id])],
            'write_user_ids': [(6, 0, [self.agent_a.id])]})
        doc = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Note de direction", 'folder_id': folder.id,
            'confidentiality_id': self.internal.id})
        self.assertEqual(doc.with_user(self.agent_a).name, "Note de direction")
        with self.assertRaises(AccessError):
            doc.with_user(self.agent_b).read(['name'])
        created = self.env['aite.ecm.document'].with_user(self.agent_a).create({
            'name': "Créé par la rédactrice nommée", 'folder_id': folder.id,
            'confidentiality_id': self.internal.id})
        self.assertTrue(created)
        with self.assertRaises(AccessError):
            self.env['aite.ecm.document'].with_user(self.agent_b).create({
                'name': "Refusé", 'folder_id': folder.id,
                'confidentiality_id': self.internal.id})
        self.assertIn("Agent A2", folder.access_summary)

    def test_12_document_sharing(self):
        doc = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Contrat confidentiel", 'confidentiality_id': self.conf.id,
            'folder_id': self.env.ref('aite_ecm_document.folder_juridique').id})
        doc.add_version("c.pdf", PDF)
        with self.assertRaises(AccessError):
            doc.with_user(self.agent_a).read(['name'])
        doc.write({'shared_user_ids': [(4, self.agent_a.id)]})
        self.assertEqual(doc.with_user(self.agent_a).name, "Contrat confidentiel")
        with self.assertRaises(AccessError):
            doc.with_user(self.agent_a).add_version("c2.pdf", PDF2)
        doc.write({'editor_user_ids': [(4, self.agent_b.id)]})
        doc.with_user(self.agent_b).add_version("c2.pdf", PDF2)
        self.assertEqual(doc.version_count, 2)
        self.assertIn("Agent A2", doc.access_summary)
        self.assertIn("Agent B2", doc.access_summary)

    def test_13_scan(self):
        import io
        import os
        import tempfile
        from PIL import Image
        Doc = self.env['aite.ecm.document']
        images = []
        for color in ((255, 0, 0), (0, 0, 255)):
            buf = io.BytesIO()
            Image.new('RGB', (600, 800), color).save(buf, format='JPEG')
            images.append(buf.getvalue())
        pdf = Doc._images_to_pdf(images)
        self.assertTrue(pdf.startswith(b'%PDF'))
        from pypdf import PdfReader
        self.assertEqual(len(PdfReader(io.BytesIO(pdf)).pages), 2)
        # dossier de dépôt surveillé
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "facture_scan.pdf"), 'wb') as fh:
            fh.write(base64.b64decode(PDF))
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param('aite_ecm.hotfolder_path', tmp)
        Param.set_param('aite_ecm.hotfolder_min_age', 0)
        Param.set_param('aite_ecm.hotfolder_folder_id',
                        self.env.ref('aite_ecm_document.folder_finance').id)
        self.assertEqual(Doc._cron_hotfolder_import(), 1)
        doc = Doc.search([('name', '=', "facture scan")], limit=1)
        self.assertTrue(doc and doc.version_count == 1)
        self.assertEqual(doc.folder_id, self.env.ref('aite_ecm_document.folder_finance'))
        self.assertTrue(os.listdir(os.path.join(tmp, 'traites')))
