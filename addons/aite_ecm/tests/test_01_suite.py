# -*- coding: utf-8 -*-
"""Cohérence de la suite installée par le module chapeau.

Ces contrôles ne testent pas une fonctionnalité : ils vérifient que
l'assemblage tient — dépendances installées, référentiels chargés, menus
atteignables, tâches planifiées armées, groupes cohérents. C'est ce qui
casse en premier quand un module est ajouté sans être branché.
"""
from odoo.tests import TransactionCase, tagged

# Modules que le chapeau doit entraîner.
EXPECTED = [
    'aite_courrier_base', 'aite_courrier_workflow', 'aite_courrier_core',
    'aite_courrier_validation', 'aite_courrier_ged', 'aite_courrier_capture',
    'aite_courrier_ocr', 'aite_courrier_reponse', 'aite_courrier_webdav',
    'aite_courrier', 'aite_ecm_document', 'aite_ecm_workflow',
    'aite_ecm_dossier', 'aite_ecm_share', 'aite_ecm_api', 'aite_courrier_ecm',
]
ROLES = ['group_agent', 'group_assistant', 'group_manager', 'group_compta',
         'group_signer', 'group_archive', 'group_audit', 'group_admin']


@tagged('post_install', '-at_install', 'aite_ecm')
class TestSuiteIntegrity(TransactionCase):

    def test_01_all_modules_installed(self):
        states = {m['name']: m['state']
                  for m in self.env['ir.module.module'].sudo().search_read(
                      [('name', 'in', EXPECTED)], ['name', 'state'])}
        for name in EXPECTED:
            self.assertEqual(states.get(name), 'installed',
                             "module %s non installé par le chapeau" % name)

    def test_02_roles_are_internal_users(self):
        """Chaque rôle AITE doit faire de son porteur un utilisateur interne,
        sans quoi il n'a accès ni aux menus ni aux séquences."""
        internal = self.env.ref('base.group_user')
        for role in ROLES:
            group = self.env.ref('aite_courrier_base.' + role)
            self.assertIn(internal, group.trans_implied_ids,
                          "%s n'implique pas « Utilisateur interne »" % role)

    def test_03_referentials_are_loaded(self):
        self.assertTrue(self.env['aite.courrier.type'].search_count(
            [('category', '=', 'entrant')]))
        self.assertTrue(self.env['aite.courrier.type'].search_count(
            [('category', '=', 'sortant')]))
        self.assertTrue(self.env['aite.courrier.confidentiality'].search_count(
            [('code', '=', 'CONF')]))
        self.assertTrue(self.env['aite.courrier.priority'].search([]))
        circuits = self.env['aite.workflow.circuit'].search(
            [('active', '=', True)])
        self.assertGreaterEqual(len(circuits), 5,
                                "les circuits de base ne sont pas chargés")
        for circuit in circuits:
            self.assertTrue(circuit.get_initial_step(),
                            "circuit « %s » sans étape initiale" % circuit.name)
        self.assertGreaterEqual(
            self.env['aite.ecm.document.type'].search_count([]), 6)
        self.assertGreaterEqual(
            self.env['aite.ecm.folder'].search_count([]), 7)

    def test_04_menus_and_actions_resolve(self):
        """Aucun menu ne doit pointer vers une action absente ou un modèle
        inconnu : c'est l'erreur type d'un module mal branché."""
        menus = self.env['ir.ui.menu'].sudo().with_context(
            ir_ui_menu_bypass=True).search([])
        aite_menus = menus.filtered(
            lambda m: (m.action and m.action.type == 'ir.actions.act_window'
                       and (m.action.res_model or '').startswith('aite.')))
        self.assertTrue(aite_menus, "aucun menu AITE trouvé")
        for menu in aite_menus:
            model = menu.action.res_model
            self.assertIn(model, self.env,
                          "menu « %s » → modèle inconnu %s"
                          % (menu.complete_name, model))
            self.env[model].search([], limit=1)

    def test_05_crons_are_scheduled(self):
        crons = self.env['ir.cron'].sudo().search([])
        aite = crons.filtered(
            lambda c: (c.model_id.model or '').startswith('aite.'))
        self.assertTrue(aite, "aucune tâche planifiée AITE")
        for cron in aite:
            self.assertIn(cron.model_id.model, self.env)
            if cron.active:
                self.assertTrue(cron.nextcall,
                                "tâche « %s » active sans prochaine "
                                "exécution" % cron.name)

    def test_06_dashboard_keys_are_unique(self):
        """Le gabarit OWL boucle sur ces listes : une clé dupliquée fait
        échouer l'affichage du tableau de bord (« duplicate key »)."""
        data = self.env['aite.courrier'].get_dashboard_data()
        self.assertTrue(data)
        for name, block in data.items():
            if not isinstance(block, list):
                continue
            for field in ('id', 'key'):
                keys = [row[field] for row in block
                        if isinstance(row, dict) and field in row]
                self.assertEqual(
                    len(keys), len(set(keys)),
                    "clés « %s » dupliquées dans « %s »" % (field, name))
            labels = [row.get('label') for row in block
                      if isinstance(row, dict) and 'label' in row]
            self.assertEqual(len(labels), len(set(labels)),
                             "libellés ambigus dans « %s »" % name)
