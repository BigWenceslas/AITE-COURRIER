# -*- coding: utf-8 -*-
import re

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestValidation(TransactionCase):
    """Actions de validation — aligné sur tests/test_06_validation_actions.md."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Courrier = cls.env['aite.courrier']
        cls.AuditLog = cls.env['aite.courrier.audit.log']

    def _ref(self, xmlid):
        return self.env.ref(xmlid)

    def _launch(self, type_code='type_entr'):
        courrier = self.Courrier.create({
            'subject': "Courrier validation",
            'type_id': self.env.ref('aite_courrier_base.%s' % type_code).id,
        })
        courrier.action_launch_circuit()
        return courrier

    def _audits(self, courrier, action_type=None):
        domain = [('model_name', '=', 'aite.courrier'), ('res_id', '=', courrier.id)]
        if action_type:
            domain.append(('action_type', '=', action_type))
        return self.AuditLog.search(domain)

    def _make_user(self, login, group_xmlids):
        return self.env['res.users'].create({
            'name': login, 'login': login,
            'groups_id': [Command.set(
                [self.env.ref('base.group_user').id]
                + [self.env.ref(x).id for x in group_xmlids])],
        })

    # --- TC-01 : validation nominale ---
    def test_tc01_validate_forward(self):
        courrier = self._launch()
        self.assertEqual(courrier.current_step_id, self._ref('aite_courrier_workflow.step_entr_1'))
        courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))
        self.assertEqual(courrier.current_step_id, self._ref('aite_courrier_workflow.step_entr_2'))
        self.assertEqual(len(courrier.step_history_ids), 2)
        closed = courrier.step_history_ids.filtered(
            lambda h: h.step_id == self._ref('aite_courrier_workflow.step_entr_1'))
        self.assertTrue(closed.left_date, "L'historique de l'étape quittée est clôturé.")
        self.assertTrue(self._audits(courrier, 'ok'))

    # --- TC-02 : rejet avec commentaire ---
    def test_tc02_reject_with_comment(self):
        courrier = self._launch()
        step_before = courrier.current_step_id
        courrier.action_reject("Pièces manquantes")
        self.assertEqual(courrier.state, 'rj')
        self.assertNotEqual(courrier.state, 'ar')
        self.assertEqual(courrier.current_step_id, step_before)
        self.assertTrue(self._audits(courrier, 'warn'))

    # --- TC-03 : rejet sans commentaire ---
    def test_tc03_reject_without_comment(self):
        courrier = self._launch()
        with self.assertRaises(UserError):
            courrier.action_reject("")
        self.assertEqual(courrier.state, 'nw')

    # --- TC-04 : retour (backward) ---
    def test_tc04_return_backward(self):
        courrier = self._launch()
        courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))
        courrier.do_transition(
            self._ref('aite_courrier_workflow.trans_entr_2_1'), comment="À corriger")
        self.assertEqual(courrier.current_step_id, self._ref('aite_courrier_workflow.step_entr_1'))
        self.assertTrue(self._audits(courrier, 'warn'))

    # --- TC-05 : commentaire simple ---
    def test_tc05_comment_only(self):
        courrier = self._launch()
        step_before = courrier.current_step_id
        state_before = courrier.state
        courrier.action_post_comment("Pour information")
        self.assertEqual(courrier.current_step_id, step_before)
        self.assertEqual(courrier.state, state_before)
        self.assertTrue(self._audits(courrier, 'info'))

    # --- TC-06 : horodatage et signature ---
    def test_tc06_signature_timestamp(self):
        courrier = self._launch()
        courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))
        bodies = courrier.message_ids.mapped('body')
        signed = [b for b in bodies if self.env.user.name in (b or '')
                  and re.search(r'\d{2}/\d{2}\s', b or '')
                  and re.search(r'\d{1,2}h\d{2}', b or '')]
        self.assertTrue(signed, "Un message signé et horodaté (JJ/MM HHhMM) doit exister.")

    # --- TC-07/08/09 : ciblage par utilisateur ---
    def test_tc07_08_09_user_targeting(self):
        step = self._ref('aite_courrier_workflow.step_entr_1')  # rôle : agent
        listed = self._make_user('val_listed', ['aite_courrier_base.group_agent'])
        unlisted = self._make_user('val_unlisted', ['aite_courrier_base.group_agent'])
        no_role = self._make_user('val_norole', [])
        step.user_ids = [Command.set([listed.id])]
        transition = self._ref('aite_courrier_workflow.trans_entr_1_2')

        # TC-08 : rôle mais non listé -> 403
        courrier = self._launch()
        with self.assertRaises(AccessError):
            courrier.with_user(unlisted).do_transition(transition)
        # TC-09 : pas de rôle -> 403
        with self.assertRaises(AccessError):
            courrier.with_user(no_role).do_transition(transition)
        # TC-07 : listé et habilité -> succès
        courrier.with_user(listed).do_transition(transition)
        self.assertEqual(courrier.current_step_id,
                         self._ref('aite_courrier_workflow.step_entr_2'))

    # --- TC-10 : workflow complet facture archivé (>= 7 audits) ---
    def test_tc10_full_invoice_archived(self):
        courrier = self._launch('type_fact')
        path = ['trans_fact_1_2', 'trans_fact_2_3', 'trans_fact_3_4',
                'trans_fact_4_5', 'trans_fact_5_6', 'trans_fact_6_7']
        for xmlid in path:
            courrier.do_transition(self._ref('aite_courrier_workflow.%s' % xmlid))
        self.assertEqual(courrier.current_step_id,
                         self._ref('aite_courrier_workflow.step_fact_7'))
        self.assertEqual(courrier.state, 'ar')
        self.assertGreaterEqual(len(self._audits(courrier)), 7)

    # --- TC-11 : devis rejeté non archivé ---
    def test_tc11_quote_rejected_not_archived(self):
        courrier = self._launch('type_devis')
        courrier.action_reject("Hors budget")
        self.assertEqual(courrier.state, 'rj')
        self.assertNotEqual(courrier.state, 'ar')

    # --- TC-12 : entrant avec retour puis re-validation ---
    def test_tc12_incoming_return_then_revalidate(self):
        courrier = self._launch()
        courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))
        courrier.do_transition(
            self._ref('aite_courrier_workflow.trans_entr_2_1'), comment="Retour")
        self.assertEqual(courrier.current_step_id, self._ref('aite_courrier_workflow.step_entr_1'))
        courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))
        self.assertEqual(courrier.current_step_id, self._ref('aite_courrier_workflow.step_entr_2'))

    # --- TC-13 : actions bloquées sur courrier archivé ---
    def test_tc13_blocked_when_archived(self):
        courrier = self._launch()
        courrier.write({'state': 'ar'})
        self.assertFalse(courrier.available_transition_ids)
        with self.assertRaises(UserError):
            courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))

    # --- TC-14 : actions bloquées sur courrier rejeté ---
    def test_tc14_blocked_when_rejected(self):
        courrier = self._launch()
        courrier.action_reject("Motif")
        self.assertEqual(courrier.state, 'rj')
        self.assertFalse(courrier.available_transition_ids)
        with self.assertRaises(UserError):
            courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))

    # --- TC-15 : commentaire obligatoire d'une transition (contrôle serveur) ---
    def test_tc15_transition_comment_required(self):
        courrier = self._launch()
        courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_1_2'))
        # « Retourner » (2→1) exige un commentaire : refusé sans commentaire.
        with self.assertRaises(UserError):
            courrier.do_transition(self._ref('aite_courrier_workflow.trans_entr_2_1'))
        # avec commentaire, l'action passe.
        courrier.do_transition(
            self._ref('aite_courrier_workflow.trans_entr_2_1'), comment="Motif")
        self.assertEqual(courrier.current_step_id,
                         self._ref('aite_courrier_workflow.step_entr_1'))
