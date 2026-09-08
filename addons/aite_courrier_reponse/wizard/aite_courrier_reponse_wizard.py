# -*- coding: utf-8 -*-
import base64

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteCourrierReponseWizard(models.TransientModel):
    """Assistant « Répondre » : fusion d'un modèle, génération PDF, GED.

    Étapes exécutées par :meth:`action_generate` :

    1. rendu du PDF sur l'en-tête société (``web.external_layout``) ;
    2. si demandé, création du **courrier sortant lié** (brouillon, prêt à
       suivre son circuit) ; sinon la réponse est rattachée au courrier
       d'origine ;
    3. le PDF devient une **version GED** du courrier cible ;
    4. si demandé, **envoi par e-mail** à l'expéditeur (PDF joint) ;
    5. traçabilité : messages dans les chatters + journal d'audit.
    """

    _name = 'aite.courrier.reponse.wizard'
    _description = "Assistant de réponse courrier"

    courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Courrier d'origine",
        required=True, readonly=True, ondelete='cascade',
    )
    type_id = fields.Many2one(
        related='courrier_id.type_id', string="Type d'origine")
    sender_email = fields.Char(
        related='courrier_id.sender_email', string="E-mail expéditeur")
    template_id = fields.Many2one(
        comodel_name='aite.courrier.reponse.template', string="Modèle",
        help="Modèle de réponse à fusionner ; le corps reste retouchable.",
    )
    subject = fields.Char(string="Objet", required=True)
    body_html = fields.Html(string="Corps", required=True, sanitize=True)
    send_email = fields.Boolean(
        string="Envoyer par e-mail à l'expéditeur",
        help="Envoie la réponse (PDF joint) à l'adresse e-mail de "
             "l'expéditeur du courrier d'origine.",
    )
    create_outgoing = fields.Boolean(
        string="Créer le courrier sortant lié", default=True,
        help="Crée un courrier de catégorie « Sortant » lié au courrier "
             "d'origine ; le PDF de réponse y est versionné et le circuit "
             "sortant (préparation → … → émission) peut être lancé.",
    )
    outgoing_type_id = fields.Many2one(
        comodel_name='aite.courrier.type', string="Type du courrier sortant",
        domain=[('category', '=', 'sortant'), ('active', '=', True)],
        default=lambda self: self.env['aite.courrier.type'].search(
            [('category', '=', 'sortant'), ('active', '=', True)], limit=1),
    )

    # ------------------------------------------------------------------ #
    # Fusion du modèle
    # ------------------------------------------------------------------ #
    @api.onchange('template_id')
    def _onchange_template_id(self):
        for wizard in self:
            if wizard.template_id and wizard.courrier_id:
                rendered = wizard.template_id._render_on(wizard.courrier_id)
                wizard.subject = rendered['subject']
                wizard.body_html = rendered['body_html']

    # ------------------------------------------------------------------ #
    # Génération
    # ------------------------------------------------------------------ #
    def _render_pdf(self):
        """Rend le PDF de réponse (en-tête société) → bytes."""
        self.ensure_one()
        pdf_content, _dummy = self.env['ir.actions.report']._render_qweb_pdf(
            'aite_courrier_reponse.action_report_reponse',
            res_ids=self.courrier_id.ids,
            data={
                'reponse_subject': self.subject,
                # Markup : le corps HTML est injecté tel quel dans le QWeb.
                'reponse_body': Markup(self.body_html or ''),
                'reponse_date': fields.Date.context_today(self).strftime(
                    '%d/%m/%Y'),
            })
        return pdf_content

    def _create_outgoing_courrier(self):
        """Crée le courrier sortant lié (brouillon), tiers = expéditeur."""
        self.ensure_one()
        source = self.courrier_id
        if not self.outgoing_type_id:
            raise UserError(_(
                "Aucun type de courrier « Sortant » actif : créez-en un dans "
                "les référentiels ou décochez la création du courrier lié."))
        outgoing = self.env['aite.courrier'].create({
            'subject': self.subject,
            'type_id': self.outgoing_type_id.id,
            # Le « tiers » du courrier sortant est l'expéditeur d'origine.
            'sender': source.sender,
            'sender_partner_id': source.sender_partner_id.id,
            'sender_email': source.sender_email,
            'department_id': source.department_id.id,
            'priority_id': source.priority_id.id,
            'confidentiality_id': source.confidentiality_id.id,
            'responsible_id': self.env.user.id,
            'reply_to_courrier_id': source.id,
        })
        outgoing.message_post(body=_(
            "Courrier de réponse à %s.") % (source.reference
                                            or source.display_name))
        return outgoing

    def _attach_pdf_to_ged(self, target, pdf_content):
        """Versionne le PDF de réponse dans la GED du courrier cible."""
        self.ensure_one()
        filename = "%s.pdf" % (self.subject or _("Réponse"))
        document = self.env['aite.courrier.document'].create({
            'name': _("Réponse — %s") % (self.subject or ''),
            'courrier_id': target.id,
        })
        return document.add_version(
            filename, base64.b64encode(pdf_content))

    def _send_by_email(self, version):
        """Envoie la réponse (PDF joint) à l'expéditeur d'origine."""
        self.ensure_one()
        source = self.courrier_id
        if not source.sender_email:
            raise UserError(_(
                "L'expéditeur du courrier d'origine n'a pas d'adresse "
                "e-mail : renseignez « E-mail expéditeur » ou décochez "
                "l'envoi."))
        mail = self.env['mail.mail'].sudo().create({
            'subject': self.subject,
            'body_html': self.body_html,
            'email_to': source.sender_email,
            'attachment_ids': [(4, version.attachment_id.id)],
        })
        mail.send(raise_exception=False)
        return mail

    def action_generate(self):
        """Génère la réponse : PDF → GED (+ courrier sortant / e-mail)."""
        self.ensure_one()
        source = self.courrier_id
        pdf_content = self._render_pdf()
        target = source
        if self.create_outgoing:
            target = self._create_outgoing_courrier()
        version = self._attach_pdf_to_ged(target, pdf_content)
        if self.send_email:
            self._send_by_email(version)
        # Traçabilité : chatter du courrier d'origine + audit.
        parts = [_("Réponse générée : « %s »") % self.subject]
        if target != source:
            parts.append(_("courrier sortant %s créé")
                         % (target.reference or target.display_name))
        if self.send_email:
            parts.append(_("envoyée à %s") % source.sender_email)
        source.message_post(body=" — ".join(parts))
        self.env['aite.courrier.audit.log']._log(
            self.env, _("Génération de réponse"), 'ok', 'aite.courrier',
            source.id, source.reference or source.display_name,
            " — ".join(parts), 'ui')
        # Ouvre le courrier sortant créé, sinon reste sur l'origine.
        if target != source:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'aite.courrier',
                'res_id': target.id,
                'view_mode': 'form',
            }
        return {'type': 'ir.actions.act_window_close'}
