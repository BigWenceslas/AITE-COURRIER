# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form, TransactionCase
from odoo.tools import mute_logger


class TestCircuitsEditor(TransactionCase):
    """Tests éditeur de circuits — aligné sur tests/test_04_circuits_editor.md."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Circuit = cls.env['aite.workflow.circuit']
        cls.Step = cls.env['aite.workflow.step']
        cls.Transition = cls.env['aite.workflow.transition']
        cls.wf_type = cls.env['aite.courrier.type'].create({
            'code': 'ZZWF', 'name': 'Type test workflow', 'category': 'interne',
        })

    def _build_circuit(self, type_rec, steps_def, name='Circuit test', active=True):
        """Crée un circuit + ses étapes en un seul lot (topologie validée une
        fois le circuit complet). ``steps_def`` : liste de
        (name, is_initial, is_final)."""
        circuit = self.Circuit.create({
            'name': name, 'type_id': type_rec.id, 'active': active,
        })
        vals = [{
            'circuit_id': circuit.id,
            'sequence': i,
            'name': sname,
            'is_initial': is_initial,
            'is_final': is_final,
        } for i, (sname, is_initial, is_final) in enumerate(steps_def, start=1)]
        steps = self.Step.create(vals)
        return circuit, steps

    # --- TC-01 : un seul circuit actif par type ---
    def test_tc01_unique_active_circuit_per_type(self):
        self._build_circuit(self.wf_type, [('A', True, False), ('B', False, True)])
        # Un second circuit actif sur le même type est refusé.
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.Circuit.create({'name': 'Doublon', 'type_id': self.wf_type.id})
        # Un circuit inactif sur le même type est autorisé.
        self.Circuit.create({
            'name': 'Inactif', 'type_id': self.wf_type.id, 'active': False,
        })

    # --- TC-02 : exactement une étape initiale (0 interdit) ---
    def test_tc02_initial_step_required(self):
        circuit = self.Circuit.create({'name': 'C', 'type_id': self.wf_type.id})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            # Une seule étape, finale mais non initiale -> 0 initiale.
            self.Step.create({
                'circuit_id': circuit.id, 'sequence': 1,
                'name': 'Finale', 'is_final': True,
            })

    # --- TC-03 : au moins une étape finale ---
    def test_tc03_final_step_required(self):
        circuit = self.Circuit.create({'name': 'C', 'type_id': self.wf_type.id})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            # Une seule étape, initiale mais non finale -> 0 finale.
            self.Step.create({
                'circuit_id': circuit.id, 'sequence': 1,
                'name': 'Initiale', 'is_initial': True,
            })

    # --- TC-04 : cocher is_initial décoche les autres ---
    def test_tc04_single_initial_autoreset(self):
        circuit, steps = self._build_circuit(
            self.wf_type,
            [('A', True, False), ('B', False, False), ('C', False, True)],
        )
        step_a, step_b, step_c = steps
        self.assertTrue(step_a.is_initial)
        step_b.is_initial = True
        self.assertFalse(step_a.is_initial, "L'ancienne initiale doit être décochée.")
        self.assertTrue(step_b.is_initial)
        self.assertEqual(
            len(circuit.step_ids.filtered('is_initial')), 1,
            "Il ne doit rester qu'une seule étape initiale.",
        )

    # --- TC-05 : suppression circuit -> cascade étapes + transitions ---
    def test_tc05_delete_circuit_cascades(self):
        circuit, steps = self._build_circuit(
            self.wf_type, [('A', True, False), ('B', False, True)])
        step_a, step_b = steps
        transition = self.Transition.create({
            'circuit_id': circuit.id, 'step_from_id': step_a.id,
            'step_to_id': step_b.id, 'label': 'Avancer',
        })
        step_ids, trans_id = steps.ids, transition.id
        circuit.unlink()
        self.assertFalse(self.Step.search_count([('id', 'in', step_ids)]))
        self.assertFalse(self.Transition.search_count([('id', '=', trans_id)]))

    # --- TC-06 : suppression étape -> cascade transitions entrantes/sortantes ---
    def test_tc06_delete_step_cascades_transitions(self):
        circuit, steps = self._build_circuit(
            self.wf_type,
            [('A', True, False), ('B', False, False), ('C', False, True)],
        )
        step_a, step_b, step_c = steps
        t_ab = self.Transition.create({
            'circuit_id': circuit.id, 'step_from_id': step_a.id,
            'step_to_id': step_b.id, 'label': 'A->B'})
        t_bc = self.Transition.create({
            'circuit_id': circuit.id, 'step_from_id': step_b.id,
            'step_to_id': step_c.id, 'label': 'B->C'})
        t_ba = self.Transition.create({
            'circuit_id': circuit.id, 'step_from_id': step_b.id,
            'step_to_id': step_a.id, 'label': 'B->A', 'direction': 'backward'})
        t_ac = self.Transition.create({
            'circuit_id': circuit.id, 'step_from_id': step_a.id,
            'step_to_id': step_c.id, 'label': 'A->C'})
        touching_b = [t_ab.id, t_bc.id, t_ba.id]
        step_b.unlink()
        self.assertFalse(
            self.Transition.search_count([('id', 'in', touching_b)]),
            "Les transitions entrantes et sortantes de B doivent être supprimées.",
        )
        self.assertTrue(
            t_ac.exists(),
            "La transition ne touchant pas B doit être conservée.",
        )

    # --- TC-07 : type non supprimable s'il est rattaché à un circuit ---
    @mute_logger('odoo.sql_db')
    def test_tc07_type_ondelete_restrict(self):
        protected_type = self.env['aite.courrier.type'].create({
            'code': 'ZZRES', 'name': 'Type protégé', 'category': 'interne',
        })
        self._build_circuit(
            protected_type, [('A', True, False), ('B', False, True)])
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            protected_type.unlink()
            self.env.flush_all()

    # --- TC-08 : champs obligatoires et transition réflexive interdite ---
    @mute_logger('odoo.sql_db')
    def test_tc08_required_fields(self):
        circuit = self.Circuit.create({'name': 'C', 'type_id': self.wf_type.id})
        # Une étape sans nom est refusée (NOT NULL / contrainte requise).
        raised = False
        try:
            with self.env.cr.savepoint():
                self.Step.create({'circuit_id': circuit.id, 'sequence': 1})
                self.env.flush_all()
        except (ValidationError, IntegrityError):
            raised = True
        self.assertTrue(raised, "Une étape sans nom doit être refusée.")

    def test_tc08_transition_not_reflexive(self):
        circuit, steps = self._build_circuit(
            self.wf_type, [('A', True, False), ('B', False, True)])
        step_a = steps[0]
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.Transition.create({
                'circuit_id': circuit.id, 'step_from_id': step_a.id,
                'step_to_id': step_a.id, 'label': 'Boucle',
            })

    # --- TC-10 : ergonomie de l'étape initiale (onchange UI) ---
    def test_tc10_initial_checkbox_onchange_ui(self):
        form = Form(self.Circuit)
        form.name = "Circuit UI"
        form.type_id = self.wf_type
        with form.step_ids.new() as step_a:
            step_a.name = "A"
            step_a.is_initial = True
            # L'étape initiale ne doit pas se décocher toute seule à la création.
            self.assertTrue(step_a.is_initial)
        with form.step_ids.new() as step_b:
            step_b.name = "B"
            step_b.is_final = True
        with form.step_ids.new() as step_c:
            step_c.name = "C"
            step_c.is_initial = True  # doit décocher l'étape A
        circuit = form.save()
        initials = circuit.step_ids.filtered('is_initial')
        self.assertEqual(len(initials), 1, "Une seule étape initiale.")
        self.assertEqual(initials.name, "C",
                         "La dernière étape cochée devient l'initiale.")

    # --- TC-09 : sécurité (lecture opérationnels, CRUD admin) ---
    def test_tc09_security_operational_read_only(self):
        agent = self.env['res.users'].create({
            'name': 'Agent', 'login': 'wf_sec_agent',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_agent').id,
            ])],
        })
        circuit, _steps = self._build_circuit(
            self.wf_type, [('A', True, False), ('B', False, True)])
        # Lecture autorisée.
        circuit.with_user(agent).read(['name'])
        # Création refusée pour un opérationnel (lecture seule).
        with self.assertRaises(AccessError):
            self.Circuit.with_user(agent).create({
                'name': 'Interdit', 'type_id': self.wf_type.id,
            })
