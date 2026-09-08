# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestAiteCourrierGroups(TransactionCase):
    """Vérifie la présence des 8 groupes et la hiérarchie de l'administrateur."""

    OPERATIONAL_XMLIDS = [
        'aite_courrier_base.group_agent',
        'aite_courrier_base.group_assistant',
        'aite_courrier_base.group_manager',
        'aite_courrier_base.group_compta',
        'aite_courrier_base.group_signer',
        'aite_courrier_base.group_archive',
        'aite_courrier_base.group_audit',
    ]

    def test_groups_exist(self):
        for xmlid in self.OPERATIONAL_XMLIDS + ['aite_courrier_base.group_admin']:
            self.assertTrue(
                self.env.ref(xmlid),
                "Le groupe %s doit exister." % xmlid,
            )

    def test_admin_implies_all_operational_groups(self):
        admin = self.env.ref('aite_courrier_base.group_admin')
        implied = set(admin.implied_ids.ids)
        for xmlid in self.OPERATIONAL_XMLIDS:
            self.assertIn(
                self.env.ref(xmlid).id,
                implied,
                "group_admin doit impliquer %s." % xmlid,
            )

    def test_groups_share_category(self):
        category = self.env.ref('aite_courrier_base.module_category_aite_courrier')
        for xmlid in self.OPERATIONAL_XMLIDS + ['aite_courrier_base.group_admin']:
            self.assertEqual(
                self.env.ref(xmlid).category_id,
                category,
                "Le groupe %s doit appartenir à la catégorie AITE Courrier." % xmlid,
            )
