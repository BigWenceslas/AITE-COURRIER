# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests.common import TransactionCase


class TestWorkflowEngine(TransactionCase):
    """Tests moteur de workflow — aligné sur tests/test_05_workflow_engine.md."""

    def _ref(self, name):
        return self.env.ref('aite_courrier_workflow.%s' % name)

    def _make_user(self, login, group_xmlids):
        return self.env['res.users'].create({
            'name': login,
            'login': login,
            'groups_id': [Command.set(
                [self.env.ref('base.group_user').id]
                + [self.env.ref(x).id for x in group_xmlids]
            )],
        })

    # --- TC-01 : les 5 circuits de base sont instanciés ---
    def test_tc01_five_base_circuits(self):
        expected = {
            'circuit_entrant_standard': ('ENTR', 5, 7),
            'circuit_sortant': ('SORT', 5, 7),
            'circuit_interne': ('INT', 4, 4),
            'circuit_facture': ('FACT', 7, 10),
            'circuit_devis': ('DEVIS', 6, 9),
        }
        for xmlid, (type_code, n_steps, n_trans) in expected.items():
            circuit = self._ref(xmlid)
            self.assertEqual(circuit.type_id.code, type_code,
                             "Type incorrect pour %s." % xmlid)
            self.assertEqual(len(circuit.step_ids), n_steps,
                             "Nombre d'étapes incorrect pour %s." % xmlid)
            self.assertEqual(len(circuit.transition_ids), n_trans,
                             "Nombre de transitions incorrect pour %s." % xmlid)

    # --- TC-02 : étape initiale ---
    def test_tc02_get_initial_step(self):
        circuit = self._ref('circuit_entrant_standard')
        initial = circuit.get_initial_step()
        self.assertEqual(len(initial), 1)
        self.assertTrue(initial.is_initial)
        self.assertEqual(initial, self._ref('step_entr_1'))
        self.assertEqual(initial.name, 'Réception')

    # --- TC-03 : topologie valide des circuits livrés ---
    def test_tc03_base_circuits_topology(self):
        for xmlid in ('circuit_entrant_standard', 'circuit_sortant',
                      'circuit_interne', 'circuit_facture', 'circuit_devis'):
            circuit = self._ref(xmlid)
            self.assertEqual(
                len(circuit.step_ids.filtered('is_initial')), 1,
                "%s doit avoir exactement une étape initiale." % xmlid)
            self.assertTrue(
                circuit.step_ids.filtered('is_final'),
                "%s doit avoir au moins une étape finale." % xmlid)

    # --- TC-04 : transitions sortantes ---
    def test_tc04_outgoing_transitions(self):
        step = self._ref('step_entr_2')  # Qualification
        outgoing = step.outgoing_transitions()
        self.assertEqual(len(outgoing), 2)
        self.assertEqual(set(outgoing.mapped('label')), {'Affecter', 'Retourner'})

    # --- TC-05 : habilitation par rôle ---
    def test_tc05_can_user_act_by_role(self):
        step = self._ref('step_entr_1')  # rôle : agent
        agent = self._make_user('wf_agent', ['aite_courrier_base.group_agent'])
        archivist = self._make_user('wf_arch', ['aite_courrier_base.group_archive'])
        self.assertTrue(step.can_user_act(agent),
                        "Un agent doit pouvoir agir sur l'étape Réception.")
        self.assertFalse(step.can_user_act(archivist),
                         "Un archiviste (sans rôle agent) ne doit pas pouvoir agir.")

    # --- TC-06 : restriction par utilisateurs ---
    def test_tc06_can_user_act_by_user_ids(self):
        step = self._ref('step_entr_1')  # rôle : agent
        agent1 = self._make_user('wf_agent1', ['aite_courrier_base.group_agent'])
        agent2 = self._make_user('wf_agent2', ['aite_courrier_base.group_agent'])
        no_role = self._make_user('wf_norole', [])  # interne sans rôle métier

        # user_ids vide : tout agent peut agir.
        self.assertTrue(step.can_user_act(agent1))
        self.assertTrue(step.can_user_act(agent2))

        # user_ids restreint à agent1 (+ un utilisateur sans rôle).
        step.user_ids = [Command.set([agent1.id, no_role.id])]
        self.assertTrue(step.can_user_act(agent1),
                        "Agent listé et habilité : autorisé.")
        self.assertFalse(step.can_user_act(agent2),
                         "Agent non listé : refusé malgré le rôle.")
        self.assertFalse(step.can_user_act(no_role),
                         "Utilisateur listé mais sans rôle : refusé.")

    # --- TC-07 : libellé lisible d'une transition ---
    def test_tc07_transition_display_name(self):
        transition = self._ref('trans_entr_2_1')  # Retourner : 2 -> 1
        name = transition.display_name
        self.assertIn('Retourner', name)
        self.assertIn('→', name)
        self.assertIn(transition.step_from_id.name, name)
        self.assertIn(transition.step_to_id.name, name)
