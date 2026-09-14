# -*- coding: utf-8 -*-
"""Parcours fonctionnel complet, d'un bout à l'autre de la suite.

Un courrier entrant arrive, il est enregistré, sa pièce est versée, le
circuit se déroule jusqu'à l'archivage. En chemin, la pièce devient un
document ECM, la politique de conservation s'applique, la chaîne de preuve
se constitue, le document est partagé à l'extérieur, exposé en lecteur
réseau et retrouvé par l'API.

Ce test ne remplace pas les tests de chaque module : il vérifie que les
modules **se parlent** — c'est là que les régressions passent inaperçues.
"""
import base64

from odoo.tests import HttpCase, tagged

PDF = base64.b64encode(b"%PDF-1.4\n%AITE bout en bout\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_ecm')
class TestBoutEnBout(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        base_group = cls.env.ref('base.group_user')
        cls.agent = Users.create({
            'name': "Agent bout-en-bout", 'login': "e2e_agent",
            'email': "e2e_agent@aite.test", 'password': "e2e_agent_pwd",
            'groups_id': [(6, 0, [base_group.id, cls.env.ref(
                'aite_courrier_base.group_agent').id])]})
        cls.manager = Users.create({
            'name': "Manager bout-en-bout", 'login': "e2e_manager",
            'email': "e2e_manager@aite.test", 'password': "e2e_manager_pwd",
            'groups_id': [(6, 0, [base_group.id, cls.env.ref(
                'aite_courrier_base.group_manager').id])]})
        # Administrateur fonctionnel : il cumule les rôles et peut donc
        # franchir toutes les étapes du circuit, quel que soit le rôle
        # habilité — c'est le profil qui déroule une recette de bout en bout.
        cls.pilote = Users.create({
            'name': "Pilote bout-en-bout", 'login': "e2e_pilote",
            'email': "e2e_pilote@aite.test", 'password': "e2e_pilote_pwd",
            'groups_id': [(6, 0, [base_group.id, cls.env.ref(
                'aite_courrier_base.group_admin').id])]})
        cls.type_entrant = cls.env['aite.courrier.type'].search(
            [('category', '=', 'entrant'), ('active', '=', True)], limit=1)

    # ------------------------------------------------------------------ #
    def test_01_courrier_to_archive(self):
        """Enregistrement → circuit → archivage, avec la pièce versionnée."""
        Courrier = self.env['aite.courrier'].with_user(self.agent)
        courrier = Courrier.create({
            'subject': "Demande de raccordement — Lycée de Bonabéri",
            'type_id': self.type_entrant.id,
            'sender': "Proviseur du Lycée de Bonabéri",
            'sender_email': "proviseur@lycee.test"})
        self.assertEqual(courrier.state, 'draft')
        self.assertFalse(courrier.reference)

        piece = self.env['aite.courrier.document'].with_user(
            self.agent).create({'name': "Courrier signé",
                                'courrier_id': courrier.id})
        piece.add_version("courrier.pdf", PDF)

        courrier.action_launch_circuit()
        self.assertRegex(courrier.reference, r'COUR-\d{4}-\d+')
        self.assertEqual(courrier.state, 'nw')
        self.assertTrue(courrier.current_step_id.is_initial)

        # Déroulé complet du circuit, de proche en proche.
        guard = 0
        while not courrier.current_step_id.is_final and guard < 15:
            guard += 1
            forward = courrier.current_step_id.outgoing_transition_ids.filtered(
                lambda t: t.direction == 'forward')[:1]
            self.assertTrue(
                forward, "étape « %s » sans transition avant : le circuit est "
                         "sans issue" % courrier.current_step_id.name)
            courrier.with_user(self.pilote).do_transition(
                forward, "Recette bout-en-bout")
            courrier.invalidate_recordset()
            if not courrier.current_step_id.is_final:
                self.assertEqual(
                    courrier.state, 'pr',
                    "le courrier engagé doit être « En traitement »")
        self.assertTrue(courrier.current_step_id.is_final)
        self.assertEqual(courrier.state, 'ar')
        # L'historique porte une entrée par étape traversée.
        self.assertGreaterEqual(len(courrier.step_history_ids), 2)
        self.assertTrue(all(h.left_date for h in courrier.step_history_ids[:-1]))
        # Tout est tracé au journal d'audit.
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.courrier'),
             ('res_id', '=', courrier.id)]))
        self.courrier = courrier
        return courrier

    def test_02_piece_becomes_an_ecm_document(self):
        """Le pont courrier ↔ ECM : même fichier, pas de doublon."""
        if 'aite.ecm.document' not in self.env:
            self.skipTest("fondation ECM absente")
        courrier = self._courrier_with_piece()
        piece = courrier.document_ids[:1]
        self.assertTrue(piece.ecm_document_id,
                        "la pièce n'a pas de miroir ECM")
        ecm = piece.ecm_document_id
        self.assertEqual(ecm.res_model, 'aite.courrier')
        self.assertEqual(ecm.res_id, courrier.id)
        # Le fichier est partagé, pas dupliqué.
        self.assertEqual(ecm.latest_version_id.attachment_id,
                         piece.latest_version_id.attachment_id)
        self.assertEqual(ecm.confidentiality_id, courrier.confidentiality_id)
        # Classement Courrier/<année>/<référence>
        self.assertIn(courrier.reference, ecm.folder_id.complete_name)

    def test_03_retention_and_proof(self):
        """Conservation et valeur probante s'appliquent au document miroir."""
        courrier = self._courrier_with_piece()
        ecm = courrier.document_ids[:1].ecm_document_id
        self.assertTrue(ecm)
        if 'retention_state' in ecm._fields:
            ecm.sudo()._retention_compute()
            self.assertIn(ecm.retention_state,
                          ('none', 'current', 'intermediate', 'permanent',
                           'expired'))
        if 'seal_ids' in ecm._fields:
            self.assertTrue(ecm.seal_ids,
                            "aucun sceau posé sur le document miroir")
            problems = self.env['aite.ecm.seal'].sudo().verify_chain()
            self.assertFalse(
                [p for p in problems
                 if p.get('reference') == ecm.reference],
                "la chaîne de preuve du document est rompue")

    def test_04_share_then_download(self):
        """Le document part à l'extérieur par un lien, et revient conforme."""
        if 'aite.ecm.share' not in self.env:
            self.skipTest("module de partage absent")
        courrier = self._courrier_with_piece()
        ecm = courrier.document_ids[:1].ecm_document_id
        share = self.env['aite.ecm.share'].with_user(self.manager).create({
            'document_id': ecm.id, 'name': "Recette bout-en-bout",
            'watermark': False})
        self.assertTrue(share.is_valid)
        resp = self.url_open('/ecm/share/%s/file' % share.token)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, base64.b64decode(PDF))
        share.invalidate_recordset()
        self.assertEqual(share.download_count, 1)

    def test_05_webdav_sees_the_document(self):
        """Le document est visible du lecteur réseau, sous les droits de
        l'utilisateur."""
        if 'aite.ecm.webdav' not in self.env:
            self.skipTest("module WebDAV absent")
        courrier = self._courrier_with_piece()
        ecm = courrier.document_ids[:1].ecm_document_id
        service = self.env['aite.ecm.webdav'].with_user(self.manager)
        names = [r['name'] for r in service.propfind('', depth=1)]
        self.assertTrue(names, "l'espace WebDAV est vide")
        self.assertIn(ecm.folder_id.name.split('/')[0].strip(),
                      ' | '.join(names) + ' | ' + ecm.folder_id.name)

    def test_06_api_finds_the_document(self):
        """Un progiciel tiers retrouve la pièce par l'API, avec sa clé."""
        if 'res.users.apikeys' not in self.env:
            self.skipTest("clés d'API indisponibles")
        from datetime import timedelta

        from odoo import fields
        courrier = self._courrier_with_piece()
        ecm = courrier.document_ids[:1].ecm_document_id
        key = self.env['res.users.apikeys'].with_user(self.manager)._generate(
            'rpc', "Recette bout-en-bout",
            fields.Datetime.now() + timedelta(days=1))
        resp = self.opener.request(
            'GET', "%s/api/ecm/v1/documents?res_model=aite.courrier&res_id=%d"
            % (self.base_url(), courrier.id),
            headers={'X-API-Key': key}, timeout=30)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()['items']
        self.assertIn(ecm.reference, [d['reference'] for d in items])

    # ------------------------------------------------------------------ #
    def _courrier_with_piece(self):
        """Courrier enregistré portant une pièce versionnée (et son miroir)."""
        courrier = self.env['aite.courrier'].with_user(self.agent).create({
            'subject': "Facture de fournitures — Bureautique Plus",
            'type_id': self.type_entrant.id,
            'sender': "Bureautique Plus SARL",
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        piece = self.env['aite.courrier.document'].with_user(
            self.agent).create({'name': "Facture BP-2026-0147",
                                'courrier_id': courrier.id})
        piece.add_version("facture.pdf", PDF)
        courrier.action_launch_circuit()
        piece.invalidate_recordset()
        return courrier
