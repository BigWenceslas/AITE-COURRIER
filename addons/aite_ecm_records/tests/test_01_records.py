# -*- coding: utf-8 -*-
import base64
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.aite_ecm_document.tests.common import EcmTransactionCase

PDF = base64.b64encode(b"%PDF-1.4\n%records\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_ecm_records')
class TestRecords(EcmTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal = cls.env.ref('aite_courrier_base.confidentiality_internal')
        cls.manager = cls._make_user("Manager records", "rec_manager",
                                     'group_manager')
        cls.Document = cls.env['aite.ecm.document']

    def _doc(self, type_xmlid, folder_xmlid, **vals):
        values = {'name': "Document records",
                  'type_id': self.env.ref(type_xmlid).id,
                  'folder_id': self.env.ref(folder_xmlid).id,
                  'confidentiality_id': self.internal.id}
        values.update(vals)
        doc = self.Document.create(values)
        doc.add_version("piece.pdf", PDF)
        return doc

    def test_01_rule_selection(self):
        facture = self._doc('aite_ecm_document.type_facture_fournisseur',
                            'aite_ecm_document.folder_finance')
        facture._retention_compute()
        self.assertEqual(facture.retention_rule_id,
                         self.env.ref('aite_ecm_records.rule_comptable'))
        contrat = self._doc('aite_ecm_document.type_contrat',
                            'aite_ecm_document.folder_juridique')
        contrat._retention_compute()
        self.assertEqual(contrat.retention_rule_id,
                         self.env.ref('aite_ecm_records.rule_contrat'))
        forced = self.env.ref('aite_ecm_records.rule_pv')
        contrat.write({'retention_rule_forced_id': forced.id})
        contrat._retention_compute()
        self.assertEqual(contrat.retention_rule_id, forced)

    def test_02_deadline_and_lifecycle(self):
        facture = self._doc('aite_ecm_document.type_facture_fournisseur',
                            'aite_ecm_document.folder_finance')
        facture._retention_compute()
        self.assertEqual(facture.retention_state, 'current')
        self.assertFalse(facture.retention_deadline)   # déclencheur non atteint
        facture.action_mark_final()
        facture._retention_compute()
        self.assertTrue(facture.retention_deadline)
        self.assertEqual(facture.retention_state, 'current')
        # échéance dépassée
        facture.sudo().write({'date_final': fields.Datetime.now()
                              - relativedelta(years=11)})
        facture.sudo()._retention_compute()
        facture.invalidate_recordset()
        self.assertEqual(facture.retention_state, 'expired')
        self.assertEqual(facture.final_fate, 'destroy')
        # conservation définitive
        pv = self._doc('aite_ecm_document.type_pv',
                       'aite_ecm_document.folder_direction')
        pv.action_mark_final()
        pv.sudo().write({'date_final': fields.Datetime.now()
                         - relativedelta(years=2)})
        pv.sudo()._retention_compute()
        self.assertEqual(pv.retention_state, 'permanent')

    def test_03_legal_hold(self):
        folder = self.env['aite.ecm.folder'].create({'name': "Contentieux test"})
        doc = self._doc('aite_ecm_document.type_contrat',
                        'aite_ecm_document.folder_juridique',
                        folder_id=folder.id)
        hold = self.env['aite.ecm.legal.hold'].with_user(self.manager).create({
            'name': "Litige ETS", 'folder_ids': [(6, 0, [folder.id])],
            'reason': "Contentieux commercial"})
        hold.with_user(self.manager).action_activate()
        doc.invalidate_recordset()
        self.assertTrue(doc.legal_hold_active)
        with self.assertRaises(UserError):
            doc.write({'name': "Renommé"})
        with self.assertRaises(UserError):
            doc.action_trash()
        with self.assertRaises(UserError):
            doc.unlink()
        hold.write({'lift_reason': "Litige clos"})
        hold.with_user(self.manager).action_lift()
        doc.invalidate_recordset()
        self.assertFalse(doc.legal_hold_active)
        doc.write({'name': "Renommé après levée"})

    def test_04_disposition(self):
        expired = self._doc('aite_ecm_document.type_facture_fournisseur',
                            'aite_ecm_document.folder_finance')
        expired.action_mark_final()
        expired.sudo().write({'date_final': fields.Datetime.now()
                              - relativedelta(years=11)})
        expired.sudo()._retention_compute()
        keep = self._doc('aite_ecm_document.type_pv',
                         'aite_ecm_document.folder_direction')
        keep.action_mark_final()
        keep.sudo()._retention_compute()
        slip = self.env['aite.ecm.disposition'].with_user(self.manager).create(
            {'name': "Nouveau"})
        slip.action_collect()
        refs = slip.line_ids.mapped('reference')
        self.assertIn(expired.reference, refs)
        self.assertNotIn(keep.reference, refs)
        self.assertTrue(slip.name.startswith("BORD-"))
        slip.action_submit()
        slip.with_user(self.manager).action_approve()
        self.assertEqual(slip.state, 'approved')
        expired_id, expired_ref = expired.id, expired.reference
        slip.with_user(self.manager).action_execute()
        self.assertEqual(slip.state, 'done')
        self.assertFalse(self.Document.browse(expired_id).exists())
        # le document est détruit : la référence doit être lue avant l'exécution
        line = slip.line_ids.filtered(lambda l: l.reference == expired_ref)
        self.assertTrue(line.destroyed and line.sha256)

    def test_05_protection(self):
        doc = self._doc('aite_ecm_document.type_facture_fournisseur',
                        'aite_ecm_document.folder_finance')
        doc.action_mark_final()
        doc.sudo()._retention_compute()
        with self.assertRaises(UserError):
            doc.sudo().unlink()
        doc.sudo().with_context(force_unlink=True).unlink()

    def test_06_box(self):
        box = self.env['aite.ecm.box'].create({'name': "Factures 2019",
                                               'location': "Salle 2"})
        self.assertTrue(box.code.startswith("BTE-"))
        self._doc('aite_ecm_document.type_facture_fournisseur',
                  'aite_ecm_document.folder_finance', box_id=box.id)
        self.assertEqual(box.document_count, 1)
        box.action_store()
        box.action_lend()
        self.assertEqual(box.state, 'lent')
        self.assertEqual(box.borrower_id, self.env.user)
        box.action_store()
        self.assertEqual(box.state, 'stored')
