# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDashboard(TransactionCase):
    """Données du tableau de bord (méthode get_dashboard_data)."""

    def test_dashboard_data_structure(self):
        Courrier = self.env['aite.courrier']
        type_entr = self.env.ref('aite_courrier_base.type_entr')
        courrier = Courrier.create({'subject': "KPI", 'type_id': type_entr.id})
        courrier.action_launch_circuit()  # devient « en cours »

        data = Courrier.get_dashboard_data()

        for key in ('active', 'overdue', 'received_month', 'archived_month',
                    'rejected', 'reject_rate', 'avg_days', 'by_step',
                    'by_category', 'now', 'month_start'):
            self.assertIn(key, data, "Clé manquante : %s" % key)
        self.assertGreaterEqual(data['active'], 1,
                                "Le courrier lancé doit compter parmi les actifs.")
        self.assertIsInstance(data['by_step'], list)
        self.assertTrue(
            any(row['count'] >= 1 for row in data['by_step']),
            "La charge par étape doit refléter le courrier en cours.",
        )
