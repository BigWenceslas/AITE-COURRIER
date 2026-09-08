# -*- coding: utf-8 -*-
import re

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestCourrierLifecycle(TransactionCase):
    """Cycle de vie du courrier — aligné sur tests/test_02_courrier_lifecycle.md."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Courrier = cls.env['aite.courrier']
        cls.type_entr = cls.env.ref('aite_courrier_base.type_entr')
        cls.circuit_entr = cls.env.ref('aite_courrier_workflow.circuit_entrant_standard')
        cls.AuditLog = cls.env['aite.courrier.audit.log']

    def _new_courrier(self, **kw):
        vals = {'subject': "Demande de test", 'type_id': self.type_entr.id}
        vals.update(kw)
        return self.Courrier.create(vals)

    def _audit_for(self, courrier, name):
        return self.AuditLog.search([
            ('model_name', '=', 'aite.courrier'),
            ('res_id', '=', courrier.id),
            ('name', '=', name),
        ])

    # --- TC-01 : référence incrémentale ---
    def test_tc01_reference_increment(self):
        c1 = self._new_courrier()
        c1.action_launch_circuit()
        c2 = self._new_courrier()
        c2.action_launch_circuit()
        year = fields.Date.context_today(self.Courrier).year
        pattern = r'^COUR-%d-\d{4}$' % year
        self.assertRegex(c1.reference, pattern)
        self.assertRegex(c2.reference, pattern)
        n1 = int(c1.reference.split('-')[-1])
        n2 = int(c2.reference.split('-')[-1])
        self.assertEqual(n2, n1 + 1, "Les références doivent s'incrémenter.")

    # --- TC-02 : objet requis ---
    def test_tc02_subject_required(self):
        with self.assertRaises(ValidationError):
            self.Courrier.create({'type_id': self.type_entr.id})

    # --- TC-03 : aperçu du circuit en brouillon ---
    def test_tc03_circuit_preview(self):
        courrier = self._new_courrier()
        self.assertEqual(courrier.state, 'draft')
        self.assertEqual(courrier.preview_circuit_id, self.circuit_entr)
        self.assertEqual(len(courrier.preview_step_ids), 5)
        self.assertEqual(
            len(courrier.preview_step_ids.filtered('is_initial')), 1,
            "L'aperçu doit identifier l'étape initiale.",
        )

    # --- catégorie héritée du type (filtrage de l'espace courrier) ---
    def test_category_from_type(self):
        courrier = self._new_courrier()  # type ENTR -> catégorie « entrant »
        self.assertEqual(courrier.category, 'entrant')

    # --- TC-04 : brouillon non instancié ---
    def test_tc04_draft_not_instantiated(self):
        courrier = self._new_courrier()
        self.assertFalse(courrier.reference)
        self.assertFalse(courrier.circuit_id)
        self.assertFalse(courrier.current_step_id)
        self.assertEqual(courrier.state, 'draft')
        drafts = self.Courrier.search([('state', '=', 'draft')])
        self.assertIn(courrier, drafts)

    # --- TC-05 : lancement du circuit ---
    def test_tc05_launch_circuit(self):
        courrier = self._new_courrier()
        courrier.action_launch_circuit()
        self.assertTrue(courrier.reference)
        self.assertEqual(courrier.circuit_id, self.circuit_entr)
        self.assertEqual(courrier.current_step_id, self.circuit_entr.get_initial_step())
        self.assertEqual(courrier.state, 'nw')
        self.assertEqual(len(courrier.step_history_ids), 1)
        self.assertEqual(
            courrier.step_history_ids.step_id, self.circuit_entr.get_initial_step())

    # --- TC-06 : lecture seule une fois archivé ---
    def test_tc06_readonly_when_archived(self):
        courrier = self._new_courrier()
        courrier.action_launch_circuit()
        final_step = courrier.circuit_id.step_ids.filtered('is_final')[:1]
        courrier._enter_step(final_step)
        self.assertEqual(courrier.state, 'ar')
        self.assertTrue(courrier._is_locked())
        with self.assertRaises(UserError):
            courrier.write({'subject': "Tentative de modification"})

    # --- TC-07 : audit à la création ---
    def test_tc07_audit_on_creation(self):
        courrier = self._new_courrier()
        self.assertFalse(self._audit_for(courrier, "Création courrier"),
                         "Pas d'audit de création tant que le brouillon n'est pas lancé.")
        courrier.action_launch_circuit()
        creation = self._audit_for(courrier, "Création courrier")
        self.assertEqual(len(creation), 1)
        self.assertEqual(creation.action_type, 'info')

    # --- TC-08 : audit à la modification ---
    def test_tc08_audit_on_modification(self):
        courrier = self._new_courrier()
        courrier.action_launch_circuit()
        self.assertFalse(self._audit_for(courrier, "Modification courrier"))
        courrier.write({'subject': "Objet révisé"})
        self.assertTrue(self._audit_for(courrier, "Modification courrier"))

    # --- TC-09 : confidentialité ---
    def test_tc09_confidentiality_access(self):
        conf = self.env['aite.courrier.confidentiality'].search(
            [('code', '=', 'CONF')], limit=1)
        self.assertTrue(conf, "Le niveau CONF doit exister (socle).")
        courrier = self._new_courrier(confidentiality_id=conf.id)
        manager = self.env['res.users'].create({
            'name': 'Manager', 'login': 'core_manager',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_manager').id,
            ])],
        })
        agent = self.env['res.users'].create({
            'name': 'Agent', 'login': 'core_agent',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_agent').id,
            ])],
        })
        self.assertTrue(courrier._check_courrier_access(manager),
                        "Un manager accède à un courrier confidentiel.")
        self.assertFalse(courrier._check_courrier_access(agent),
                         "Un agent tiers n'accède pas à un courrier confidentiel.")
        courrier.responsible_id = agent
        self.assertTrue(courrier._check_courrier_access(agent),
                        "Le responsable accède au courrier confidentiel.")

    # --- Notifications : activité + échéance SLA à l'arrivée sur une étape ---
    def test_step_arrival_schedules_activity(self):
        agent = self.env['res.users'].create({
            'name': 'Agent notif', 'login': 'notif_agent',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_agent').id])],
        })
        courrier = self._new_courrier()
        courrier.action_launch_circuit()  # étape Réception (rôle agent, SLA 4h)
        self.assertTrue(courrier.sla_deadline, "L'échéance SLA doit être posée.")
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'aite.courrier'),
            ('res_id', '=', courrier.id),
        ])
        self.assertTrue(activities, "Une activité doit être programmée.")
        self.assertIn(agent, activities.mapped('user_id'),
                      "L'agent (rôle de l'étape) doit recevoir une activité.")
