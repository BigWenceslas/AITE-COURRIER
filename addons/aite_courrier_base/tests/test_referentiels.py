# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestReferentiels(TransactionCase):
    """Tests des référentiels — aligné sur tests/test_01_referentiels.md."""

    # --- TC-01 : données par défaut chargées ---
    def test_tc01_default_types(self):
        codes = set(self.env['aite.courrier.type'].search([]).mapped('code'))
        self.assertEqual(
            {'ENTR', 'SORT', 'INT', 'FACT', 'DEVIS'} - codes,
            set(),
            "Les 5 types par défaut doivent être présents.",
        )

    def test_tc01_default_priorities(self):
        codes = set(self.env['aite.courrier.priority'].search([]).mapped('code'))
        self.assertEqual({'u', 'h', 'n'} - codes, set())

    def test_tc01_default_confidentialities(self):
        codes = set(self.env['aite.courrier.confidentiality'].search([]).mapped('code'))
        self.assertEqual({'PUB', 'INT', 'CONF', 'SEC'} - codes, set())

    # --- TC-02 : catégories des types ---
    def test_tc02_categories(self):
        expected = {
            'ENTR': 'entrant',
            'SORT': 'sortant',
            'INT': 'interne',
            'FACT': 'entrant',
            'DEVIS': 'sortant',
        }
        Type = self.env['aite.courrier.type']
        for code, category in expected.items():
            rec = Type.search([('code', '=', code)], limit=1)
            self.assertTrue(rec, "Le type %s doit exister." % code)
            self.assertEqual(rec.category, category)

    # --- TC-03 : unicité du code ---
    @mute_logger('odoo.sql_db')
    def test_tc03_code_unique(self):
        self.env['aite.courrier.type'].create({
            'code': 'ZZTEST', 'name': 'Test', 'category': 'interne',
        })
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env['aite.courrier.type'].create({
                'code': 'ZZTEST', 'name': 'Doublon', 'category': 'interne',
            })
            self.env.flush_all()

    # --- TC-04 : champs obligatoires ---
    @mute_logger('odoo.sql_db')
    def test_tc04_required_fields(self):
        # Note : on capture manuellement car le assertRaises d'Odoo n'accepte
        # pas un tuple d'exceptions (issubclass sur un tuple).
        raised = False
        try:
            with self.env.cr.savepoint():
                self.env['aite.courrier.type'].create({'category': 'interne'})
                self.env.flush_all()
        except (ValidationError, IntegrityError):
            raised = True
        self.assertTrue(raised, "Un type sans code ni libellé doit être refusé.")

    # --- TC-05 : soft delete via active ---
    def test_tc05_soft_delete(self):
        rec = self.env['aite.courrier.type'].create({
            'code': 'ZZSOFT', 'name': 'Soft', 'category': 'interne',
        })
        rec.active = False
        self.assertFalse(
            self.env['aite.courrier.type'].search([('code', '=', 'ZZSOFT')]),
            "Un enregistrement archivé est exclu des recherches standards.",
        )
        self.assertTrue(
            self.env['aite.courrier.type'].with_context(active_test=False).search(
                [('code', '=', 'ZZSOFT')]),
            "Il reste récupérable avec active_test=False.",
        )

    # --- TC-06 : ordonnancement ---
    def test_tc06_priority_order(self):
        priorities = self.env['aite.courrier.priority'].search(
            [('code', 'in', ['u', 'h', 'n'])])
        self.assertEqual(priorities.mapped('code'), ['u', 'h', 'n'])

    def test_tc06_confidentiality_order(self):
        conf = self.env['aite.courrier.confidentiality'].search(
            [('code', 'in', ['PUB', 'INT', 'CONF', 'SEC'])])
        self.assertEqual(conf.mapped('code'), ['PUB', 'INT', 'CONF', 'SEC'])

    # --- TC-07 : découplage workflow ---
    def test_tc07_no_circuit_field_in_base(self):
        self.assertNotIn(
            'circuit_id',
            self.env['aite.courrier.type']._fields,
            "circuit_id ne doit pas être défini dans aite_courrier_base "
            "(il est ajouté par le module workflow).",
        )
