# -*- coding: utf-8 -*-
"""Portail tiers : un correspondant externe dépose une demande, suit son
avancement et télécharge les pièces — sans jamais voir les courriers des
autres.
"""
import base64
import re

from odoo.tests import HttpCase, tagged

PDF = base64.b64encode(b"%PDF-1.4\n%piece portail\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_courrier_portal')
class TestPortal(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        portal_group = cls.env.ref('base.group_portal')
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.partner = cls.env['res.partner'].create({
            'name': "Brasserie du Littoral", 'email': "brasserie@portail.test",
            'is_company': True})
        cls.portal_user = Users.create({
            'name': "Brasserie du Littoral", 'login': "portal_brasserie",
            'password': "portal_brasserie_pwd",
            'email': "brasserie@portail.test",
            'partner_id': cls.partner.id,
            'groups_id': [(6, 0, [portal_group.id])]})
        cls.other_partner = cls.env['res.partner'].create({
            'name': "Autre tiers", 'email': "autre@portail.test"})
        cls.other_user = Users.create({
            'name': "Autre tiers", 'login': "portal_autre",
            'password': "portal_autre_pwd", 'email': "autre@portail.test",
            'partner_id': cls.other_partner.id,
            'groups_id': [(6, 0, [portal_group.id])]})
        cls.type_entrant = cls.env['aite.courrier.type'].search(
            [('category', '=', 'entrant'), ('active', '=', True)], limit=1)
        cls.courrier = cls.env['aite.courrier'].create({
            'subject': "Demande de raccordement",
            'type_id': cls.type_entrant.id,
            'sender': cls.partner.name,
            'sender_partner_id': cls.partner.id,
            'sender_email': cls.partner.email})
        cls.courrier.action_launch_circuit()
        doc = cls.env['aite.courrier.document'].create({
            'name': "Accusé de réception", 'courrier_id': cls.courrier.id})
        doc.add_version("accuse.pdf", PDF)
        cls.foreign = cls.env['aite.courrier'].create({
            'subject': "Dossier d'un autre tiers",
            'type_id': cls.type_entrant.id,
            'sender': cls.other_partner.name,
            'sender_partner_id': cls.other_partner.id})

    # ------------------------------------------------------------------ #
    def test_01_list_shows_only_my_courriers(self):
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self.url_open('/my/courriers')
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Demande de raccordement", resp.text)
        self.assertNotIn("Dossier d'un autre tiers", resp.text)

    def test_02_detail_and_progress(self):
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self.url_open('/my/courriers/%d' % self.courrier.id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.courrier.reference, resp.text)
        # Le lien de téléchargement porte le nom du fichier.
        self.assertIn("accuse.pdf", resp.text)
        self.assertIn("access_token=", resp.text)
        # Les étapes du circuit sont affichées (suivi d'avancement).
        self.assertIn(self.courrier.current_step_id.name, resp.text)

    def test_03_foreign_courrier_is_refused(self):
        self.authenticate("portal_autre", "portal_autre_pwd")
        resp = self.url_open('/my/courriers/%d' % self.courrier.id,
                             allow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))
        self.assertIn('/my', resp.headers.get('Location', ''))

    def test_04_home_counter(self):
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self.url_open('/my')
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ourrier", resp.text)

    def test_05_deposit_form(self):
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self.url_open('/my/courriers/new')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.type_entrant.name, resp.text)

    def test_06_deposit_creates_a_courrier(self):
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        before = self.env['aite.courrier'].search_count(
            [('sender_partner_id', '=', self.partner.id)])
        resp = self.url_open('/my/courriers/new', data={
            'subject': "Réclamation sur la facture de mars",
            'type_id': str(self.type_entrant.id),
            'description': "La consommation relevée nous semble erronée.",
            'csrf_token': self._csrf_token(),
        })
        self.assertEqual(resp.status_code, 200)
        courriers = self.env['aite.courrier'].search(
            [('sender_partner_id', '=', self.partner.id)])
        self.assertEqual(len(courriers), before + 1)
        new = courriers.filtered(
            lambda c: c.subject == "Réclamation sur la facture de mars")
        self.assertTrue(new)
        self.assertEqual(new.sender_partner_id, self.partner)
        # La demande et son commentaire sont tracés.
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.courrier'), ('res_id', '=', new.id),
             ('name', 'ilike', "portail")]))
        self.assertTrue(new.message_ids.filtered(
            lambda m: "consommation" in (m.body or '')))

    def test_07_deposit_rejects_empty_subject(self):
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self.url_open('/my/courriers/new', data={
            'subject': "   ", 'type_id': str(self.type_entrant.id),
            'csrf_token': self._csrf_token()})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("obligatoire", resp.text)

    def test_08_anonymous_is_redirected_to_login(self):
        resp = self.url_open('/my/courriers', allow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))
        self.assertIn('/web/login', resp.headers.get('Location', ''))

    # ------------------------------------------------------------------ #
    # Dépôt de pièces jointes
    # ------------------------------------------------------------------ #
    def _deposit(self, subject, files):
        return self.url_open('/my/courriers/new', data={
            'subject': subject,
            'type_id': str(self.type_entrant.id),
            'csrf_token': self._csrf_token(),
        }, files=files)

    def _deposited(self, subject):
        return self.env['aite.courrier'].search(
            [('sender_partner_id', '=', self.partner.id),
             ('subject', '=', subject)], limit=1)

    def test_09_deposit_accepts_several_files(self):
        """Plusieurs fichiers en une fois : chacun devient une pièce
        versionnée. Le dépôt multiple était annoncé par le formulaire mais
        n'avait jamais été éprouvé."""
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self._deposit("Dépôt à trois pièces", [
            ('attachments', ('contrat.pdf', b"%PDF-1.4\n%a\n%%EOF\n",
                             'application/pdf')),
            ('attachments', ('photo.png', b"\x89PNG\r\n\x1a\n" + b"0" * 40,
                             'image/png')),
            ('attachments', ('note.txt', b"bonjour", 'text/plain')),
        ])
        self.assertEqual(resp.status_code, 200)
        courrier = self._deposited("Dépôt à trois pièces")
        self.assertTrue(courrier, "le dépôt n'a pas créé de courrier")
        self.assertEqual(sorted(courrier.document_ids.mapped('name')),
                         ["contrat.pdf", "note.txt", "photo.png"])
        for document in courrier.document_ids:
            self.assertTrue(
                document.latest_version_id,
                "« %s » est annoncée sans fichier téléchargeable"
                % document.name)

    def test_10_rejected_file_is_reported(self):
        """Un format écarté est dit au tiers, tracé en audit, et ne laisse
        pas derrière lui une pièce vide accrochée au courrier."""
        self.authenticate("portal_brasserie", "portal_brasserie_pwd")
        resp = self._deposit("Dépôt avec exécutable", [
            ('attachments', ('bon.pdf', b"%PDF-1.4\n%a\n%%EOF\n",
                             'application/pdf')),
            ('attachments', ('outil.exe', b"MZ\x90\x00",
                             'application/octet-stream')),
        ])
        self.assertEqual(resp.status_code, 200)
        self.assertIn("outil.exe", resp.text,
                      "le refus n'est pas signalé au tiers")
        self.assertIn("non accept", resp.text)
        courrier = self._deposited("Dépôt avec exécutable")
        self.assertEqual(courrier.document_ids.mapped('name'), ["bon.pdf"])
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.courrier'),
             ('res_id', '=', courrier.id), ('name', 'ilike', "refus")]),
            "le refus n'est pas tracé au journal d'audit")

    def test_11_allowed_extensions_are_configurable(self):
        Document = self.env['aite.courrier.document']
        Param = self.env['ir.config_parameter'].sudo()
        for extension in ('pdf', 'docx', 'doc', 'xls', 'txt', 'webp', 'heic'):
            self.assertIn(extension, Document._allowed_extensions())
        Param.set_param('aite_courrier.allowed_extensions', 'pdf, .PNG ,pdf')
        self.assertEqual(Document._allowed_extensions(), ('pdf', 'png'))
        Param.set_param('aite_courrier.allowed_extensions', '')
        self.assertEqual(Document._allowed_extensions(),
                         Document.ALLOWED_EXTENSIONS)

    def _csrf_token(self):
        """Jeton CSRF lu sur le formulaire, comme le ferait un navigateur."""
        page = self.url_open('/my/courriers/new').text
        match = re.search(
            r'name="csrf_token"[^>]*value="([^"]+)"', page)
        self.assertTrue(match, "jeton CSRF absent du formulaire")
        return match.group(1)
