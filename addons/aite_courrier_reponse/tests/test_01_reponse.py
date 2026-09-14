# -*- coding: utf-8 -*-
"""Réponse à un courrier : fusion d'un modèle, PDF versionné dans la GED,
courrier sortant lié, envoi par e-mail, traçabilité.
"""
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'aite_courrier_reponse')
class TestReponse(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Type = cls.env['aite.courrier.type']
        cls.type_entrant = Type.search([('category', '=', 'entrant')], limit=1)
        cls.type_sortant = Type.search([('category', '=', 'sortant')], limit=1)
        cls.partner = cls.env['res.partner'].create({
            'name': "Mairie de Douala 3e", 'email': "courrier@mairie.test"})
        cls.courrier = cls.env['aite.courrier'].create({
            'subject': "Demande d'attestation de conformité",
            'type_id': cls.type_entrant.id,
            'sender': "Mairie de Douala 3e",
            'sender_partner_id': cls.partner.id,
            'sender_email': "courrier@mairie.test"})
        # La référence COUR-AAAA-NNNN n'est attribuée qu'au lancement du
        # circuit : on enregistre le courrier comme le ferait un agent.
        cls.courrier.action_launch_circuit()
        cls.Wizard = cls.env['aite.courrier.reponse.wizard']

    def _wizard(self, **vals):
        values = {'courrier_id': self.courrier.id,
                  'subject': "Réponse à votre demande",
                  'body_html': "<p>Madame, Monsieur,</p>",
                  'create_outgoing': False}
        values.update(vals)
        return self.Wizard.create(values)

    # ------------------------------------------------------------------ #
    def test_01_templates_are_shipped(self):
        templates = self.env['aite.courrier.reponse.template'].search([])
        self.assertTrue(templates, "aucun modèle de réponse livré")
        for template in templates:
            self.assertTrue(template.subject and template.body_html)

    def test_02_merge_fields(self):
        template = self.env['aite.courrier.reponse.template'].create({
            'name': "Accusé de réception (test)",
            'subject': "Votre courrier {{ object.reference }}",
            'body_html': "<p>Objet : {{ object.subject }} — "
                         "reçu le {{ object.date_received }}.</p>"})
        rendered = template._render_on(self.courrier)
        self.assertIn(self.courrier.reference, rendered['subject'])
        self.assertIn("attestation de conformité", rendered['body_html'])
        self.assertNotIn("{{", rendered['body_html'])

    def test_03_onchange_fills_the_wizard(self):
        template = self.env['aite.courrier.reponse.template'].search([], limit=1)
        wizard = self._wizard(template_id=template.id)
        wizard._onchange_template_id()
        self.assertTrue(wizard.subject and wizard.body_html)

    def test_04_generate_attaches_pdf_to_source(self):
        wizard = self._wizard()
        result = wizard.action_generate()
        self.assertEqual(result['type'], 'ir.actions.act_window_close')
        doc = self.courrier.document_ids.filtered(
            lambda d: d.name.startswith("Réponse"))
        self.assertTrue(doc, "le PDF de réponse n'a pas été versionné")
        self.assertEqual(doc.version_count, 1)
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.courrier'),
             ('res_id', '=', self.courrier.id),
             ('name', 'ilike', "réponse")]))

    def test_05_generate_creates_outgoing_courrier(self):
        wizard = self._wizard(create_outgoing=True,
                              outgoing_type_id=self.type_sortant.id)
        result = wizard.action_generate()
        self.assertEqual(result['res_model'], 'aite.courrier')
        outgoing = self.env['aite.courrier'].browse(result['res_id'])
        self.assertEqual(outgoing.type_id, self.type_sortant)
        self.assertEqual(outgoing.reply_to_courrier_id, self.courrier)
        self.assertEqual(outgoing.sender_partner_id, self.partner)
        self.assertTrue(outgoing.document_ids,
                        "le PDF doit être versionné sur le courrier sortant")
        self.courrier.invalidate_recordset()
        self.assertIn(outgoing, self.courrier.reply_ids)
        self.assertEqual(self.courrier.reply_count, 1)

    def test_06_email_requires_an_address(self):
        orphan = self.env['aite.courrier'].create({
            'subject': "Courrier sans e-mail",
            'type_id': self.type_entrant.id, 'sender': "Anonyme"})
        wizard = self._wizard(courrier_id=orphan.id, send_email=True)
        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_07_email_is_sent_with_the_pdf(self):
        wizard = self._wizard(send_email=True)
        wizard.action_generate()
        mail = self.env['mail.mail'].sudo().search(
            [('email_to', '=', "courrier@mairie.test")], order='id desc',
            limit=1)
        self.assertTrue(mail, "aucun e-mail de réponse préparé")
        self.assertEqual(mail.subject, "Réponse à votre demande")
        self.assertTrue(mail.attachment_ids,
                        "la réponse doit partir avec son PDF")

    def test_08_outgoing_type_is_required(self):
        wizard = self._wizard(create_outgoing=True)
        wizard.outgoing_type_id = False
        with self.assertRaises(UserError):
            wizard.action_generate()
