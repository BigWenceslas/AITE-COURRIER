# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'aite_ecm_dossier')
class TestEcmDossier(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.agent = Users.create({
            'name': "Agent", 'login': "dos_agent",
            'groups_id': [(6, 0, [cls.env.ref('aite_courrier_base.group_agent').id])]})
        cls.manager = Users.create({
            'name': "Manager", 'login': "dos_manager",
            'groups_id': [(6, 0, [cls.env.ref('aite_courrier_base.group_manager').id])]})
        cls.dtype = cls.env.ref('aite_ecm_dossier.dossier_type_fournisseur')
        cls.partner = cls.env['res.partner'].create({'name': "ETS KAMDEM"})

    def _dossier(self, user):
        return self.env['aite.ecm.dossier'].with_user(user).create({
            'name': "Agrément ETS KAMDEM", 'type_id': self.dtype.id,
            'partner_id': self.partner.id})

    def test_01_create(self):
        dossier = self._dossier(self.agent)
        self.assertTrue(dossier.reference.startswith("DOS-"))
        self.assertEqual(len(dossier.piece_ids), 5)
        self.assertEqual(dossier.completion_rate, 0.0)
        self.assertFalse(dossier.is_complete)

    def test_02_auto_attach(self):
        dossier = self._dossier(self.agent)
        generic = self.env.ref('aite_ecm_document.type_generique')
        self.env['aite.ecm.document'].with_user(self.agent).create({
            'name': "RCCM", 'type_id': generic.id,
            'res_model': 'aite.ecm.dossier', 'res_id': dossier.id})
        rc = dossier.piece_ids.filtered(lambda p: 'RCCM' in p.name)
        self.assertTrue(rc.document_id)
        self.assertEqual(rc.state, 'provided')
        self.assertEqual(dossier.completion_rate, 20.0)

    def test_03_close_requires_completeness(self):
        dossier = self._dossier(self.agent)
        dossier.action_open()
        dossier.with_user(self.manager).action_wf_reset()
        with self.assertRaises(UserError):
            dossier.with_user(self.agent).action_close()
        dossier.with_user(self.manager).action_close()
        self.assertEqual(dossier.state, 'done')

    def test_04_workflow(self):
        dossier = self._dossier(self.agent)
        dossier.with_user(self.agent).action_open()
        self.assertEqual(dossier.wf_status, 'running')
        self.assertEqual(dossier.wf_step_id,
                         self.env.ref('aite_ecm_dossier.step_fourn_instruction'))
        self.assertEqual(len(dossier.wf_history_ids), 1)
        forward = self.env.ref('aite_ecm_dossier.trans_fourn_instruire')
        dossier.with_user(self.agent).wf_do_transition(forward)
        self.assertEqual(dossier.wf_step_id,
                         self.env.ref('aite_ecm_dossier.step_fourn_validation'))
        back = self.env.ref('aite_ecm_dossier.trans_fourn_retour')
        with self.assertRaises(UserError):
            dossier.with_user(self.manager).wf_do_transition(back)
        dossier.with_user(self.manager).wf_do_transition(back, "pièce illisible")
        dossier.with_user(self.agent).wf_do_transition(forward)
        approve = self.env.ref('aite_ecm_dossier.trans_fourn_valider')
        dossier.with_user(self.manager).wf_do_transition(approve)
        self.assertEqual(dossier.wf_status, 'done')
        self.assertEqual(len(dossier.wf_history_ids), 5)

    def test_05_habilitation(self):
        dossier = self._dossier(self.agent)
        dossier.with_user(self.agent).action_open()
        forward = self.env.ref('aite_ecm_dossier.trans_fourn_instruire')
        dossier.with_user(self.agent).wf_do_transition(forward)
        approve = self.env.ref('aite_ecm_dossier.trans_fourn_valider')
        with self.assertRaises(AccessError):
            dossier.with_user(self.agent).wf_do_transition(approve)
