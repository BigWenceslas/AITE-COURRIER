# -*- coding: utf-8 -*-
"""Le jeu de données de test doit produire *vraiment* ce qu'il annonce.

L'anomalie que ces tests verrouillent : lorsque toute la suite s'installe en
une seule commande, les modèles du courrier ne sont pas encore au registre au
moment du crochet d'installation ; les 150 courriers du profil étaient alors
tous ignorés, mais comptés comme créés dans le résumé.
"""
from odoo.tests import TransactionCase, tagged

from odoo.addons.aite_ecm_demo.seed.generator import (
    DemoSeeder, PHASES, PROFILES, purge)


@tagged('post_install', '-at_install', 'aite_ecm_demo')
class TestDemoSeeder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Param = cls.env['ir.config_parameter'].sudo()
        # On repart d'un plan neuf : la base de test peut déjà porter le jeu
        # de données produit à l'installation du module.
        cls.Param.set_param('aite_ecm_demo.state', False)

    def _seeder(self):
        return DemoSeeder(self.env, log=lambda _m: None)

    # ------------------------------------------------------------------ #
    def test_01_plan_and_phases(self):
        seeder = self._seeder()
        seeder.setup('leger')
        self.assertEqual(seeder.state['profile'], 'leger')
        self.assertEqual(seeder.phase, PHASES[0])
        self.assertFalse(seeder.is_done)
        self.assertIn("leger", seeder.summary())
        # Chaque phase déclarée doit avoir son unité de travail.
        for phase in PHASES:
            self.assertTrue(hasattr(seeder, '_unit_' + phase),
                            "phase « %s » sans méthode _unit_%s" % (phase, phase))
        # Chaque profil déclare les mêmes clés de volume.
        keys = set(PROFILES['leger'])
        for name, profile in PROFILES.items():
            self.assertEqual(set(profile), keys, "profil %s incomplet" % name)

    def test_02_users_and_roles(self):
        seeder = self._seeder()
        seeder.setup('leger')
        seeder._unit_users(0)
        seeder._register_xmlids()
        users = self.env['res.users'].search([('login', 'like', 'demo.')])
        self.assertTrue(users, "aucun utilisateur de démonstration")
        internal = self.env.ref('base.group_user')
        for user in users:
            self.assertIn(internal, user.groups_id,
                          "%s n'est pas un utilisateur interne" % user.login)
            self.assertTrue(user.email, "%s sans adresse" % user.login)

    def test_03_courrier_phase_is_planned(self):
        """La phase courriers n'est comptée que si toute la pile est là —
        et, quand elle l'est, elle doit produire des courriers."""
        seeder = self._seeder()
        seeder.setup('leger')
        total = seeder._phase_total('courriers')
        has_stack = ('aite.courrier' in self.env
                     and 'aite.courrier.document' in self.env)
        self.assertEqual(bool(total), has_stack)
        if not has_stack:
            return
        self.assertEqual(
            total, PROFILES['leger']['courriers_per_type'] * 5)
        # Une unité complète : courrier + pièce + circuit lancé.
        for phase in ('users', 'departments', 'partners', 'structure'):
            seeder.state['phase'], seeder.state['index'] = phase, 0
            seeder._loaded = False
            seeder._register_xmlids()
            seeder._load_context()
            getattr(seeder, '_unit_' + phase)(0)
            seeder._register_xmlids()
        seeder._loaded = False
        seeder._load_context()
        seeder._seed_unit('courriers', 0)
        seeder._unit_courriers(0)
        seeder._register_xmlids()
        courriers = seeder._demo_records('aite.courrier')
        self.assertTrue(courriers, "la phase courriers n'a rien produit")
        self.assertTrue(courriers[0].document_ids,
                        "courrier sans pièce jointe")
        self.assertFalse(
            [k for k in seeder.stats if k.startswith('ignorés')],
            "des unités ont été ignorées : %s" % seeder.stats)

    def test_04_failed_unit_does_not_inflate_stats(self):
        """Une unité annulée ne doit pas laisser ses compteurs derrière elle."""
        seeder = self._seeder()
        seeder.setup('leger')

        def boom(_index):
            seeder._count('courriers ENTR')
            raise ValueError("panne simulée")

        if not seeder._phase_total('courriers'):
            self.skipTest("pile courrier absente")
        # Une seule unité en tout : la phase courriers compte pour 1, les
        # autres pour 0 (elles sont sautées), le lot s'arrête donc aussitôt.
        seeder.state['phase'] = 'courriers'
        seeder._phase_total = lambda phase: 1 if phase == 'courriers' else 0
        seeder._unit_courriers = boom
        seeder._loaded = True
        seeder.run_batch(budget=30)
        self.assertNotIn('courriers ENTR', seeder.stats)
        self.assertEqual(seeder.stats.get('ignorés (unité courriers)'), 1)

    def test_05_optional_models(self):
        seeder = self._seeder()
        self.assertIsNone(seeder._model('modele.qui.nexiste.pas'))
        self.assertIsNotNone(seeder._model('aite.ecm.document'))
        self.assertIsNone(seeder._demo_records('modele.qui.nexiste.pas'))

    def test_06_records_and_sae_phases(self):
        """Les phases v2.1 s'exécutent quand leurs modules sont présents."""
        seeder = self._seeder()
        seeder.setup('leger')
        if not seeder._phase_total('records'):
            self.skipTest("aite_ecm_records non installé")
        for phase in ('users', 'partners', 'structure', 'documents'):
            seeder.state['phase'], seeder.state['index'] = phase, 0
            seeder._loaded = False
            seeder._register_xmlids()
            seeder._load_context()
            getattr(seeder, '_unit_' + phase)(0)
            seeder._register_xmlids()
        seeder._loaded = False
        seeder._load_context()
        seeder._seed_unit('records', 0)
        seeder._unit_records(0)
        seeder._register_xmlids()
        holds = self.env['aite.ecm.legal.hold'].search([])
        self.assertTrue(holds, "aucun gel juridique produit")
        self.assertTrue(any(h.state == 'active' for h in holds))
        boxes = self.env['aite.ecm.box'].search([])
        self.assertTrue(boxes, "aucune boîte d'archives produite")
        self.assertTrue(any(b.state == 'lent' for b in boxes),
                        "aucun prêt de boîte en cours")
        # Le gel doit effectivement protéger : le marqueur stocké est posé.
        frozen = self.env['aite.ecm.document'].search(
            [('legal_hold_active', '=', True)])
        self.assertTrue(frozen, "le gel n'a marqué aucun document")
        if seeder._phase_total('sae'):
            seeder._seed_unit('sae', 0)
            seeder._unit_sae(0)
            self.assertEqual(seeder.stats.get('anomalies de chaîne', 0), 0,
                             "la chaîne de preuve est rompue")

    def test_07_purge_removes_everything(self):
        seeder = self._seeder()
        seeder.setup('leger')
        for phase in ('users', 'partners', 'structure', 'documents'):
            seeder.state['phase'], seeder.state['index'] = phase, 0
            seeder._loaded = False
            seeder._register_xmlids()
            seeder._load_context()
            getattr(seeder, '_unit_' + phase)(0)
            seeder._register_xmlids()
        if seeder._phase_total('records'):
            seeder._loaded = False
            seeder._load_context()
            seeder._seed_unit('records', 0)
            seeder._unit_records(0)
            seeder._register_xmlids()
        self.assertTrue(self.env['ir.model.data'].search_count(
            [('module', '=', 'aite_ecm_demo')]))
        purge(self.env, log=lambda _m: None)
        # Restent seulement les identifiants techniques du module lui-même
        # (vues, menus, tâche planifiée, droits) — pas les données produites.
        leftovers = self.env['ir.model.data'].search(
            [('module', '=', 'aite_ecm_demo')])
        self.assertFalse(
            leftovers.filtered(lambda d: not d.model.startswith('ir.')),
            "la purge a laissé des données : %s"
            % leftovers.mapped('model'))
        self.assertFalse(self.Param.get_param('aite_ecm_demo.state'))

    def test_08_purge_removes_bridge_leftovers(self):
        """La purge nettoie aussi ce que les ponts ont produit.

        Le miroir ECM d'une pièce de courrier et son dossier
        `Courrier/<année>/<référence>` ne portent pas d'identifiant externe
        du module : sans nettoyage, la désinstallation laisserait des
        documents rattachés à des courriers disparus.
        """
        if 'aite.courrier' not in self.env \
                or 'ecm_document_id' not in self.env[
                    'aite.courrier.document']._fields:
            self.skipTest("pont courrier ↔ ECM absent")
        import base64
        from odoo.addons.aite_ecm_demo.seed.generator import _purge_orphans
        courrier = self.env['aite.courrier'].create({
            'subject': "Courrier voué à disparaître",
            'type_id': self.env['aite.courrier.type'].search(
                [('category', '=', 'entrant')], limit=1).id})
        piece = self.env['aite.courrier.document'].create({
            'name': "Pièce", 'courrier_id': courrier.id})
        piece.add_version("piece.pdf",
                          base64.b64encode(b"%PDF-1.4\n%x\n%%EOF\n"))
        piece.invalidate_recordset()
        mirror = piece.ecm_document_id
        self.assertTrue(mirror, "le pont n'a pas créé de miroir")
        # Suppression brutale du courrier, comme à la purge du jeu de données.
        piece.with_context(force_unlink=True).unlink()
        courrier.with_context(force_unlink=True).unlink()
        self.assertTrue(
            mirror.with_context(active_test=False).exists(),
            "prérequis du test : le miroir survit au courrier")
        _purge_orphans(self.env(su=True), lambda _m: None)
        self.assertFalse(
            mirror.with_context(active_test=False).exists(),
            "le miroir d'un courrier disparu doit être nettoyé")
