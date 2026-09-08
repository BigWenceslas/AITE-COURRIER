# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AiteCourrier(models.Model):
    """Signature électronique du courrier via Odoo Sign.

    * :meth:`action_request_signature` transforme la dernière version PDF en
      modèle Sign (zone de signature pré-positionnée) et envoie la demande au
      responsable du courrier.
    * :meth:`do_transition` est gardée : une étape « Signature requise »
      n'autorise aucune transition en avant sans demande complétée — le
      contrôle est côté serveur, cohérent avec le reste du moteur.
    """

    _inherit = 'aite.courrier'

    sign_request_ids = fields.One2many(
        comodel_name='sign.request', inverse_name='courrier_id',
        string="Demandes de signature",
    )
    sign_request_count = fields.Integer(
        string="Signatures", compute='_compute_sign_requests')
    has_completed_signature = fields.Boolean(
        string="Signature complétée", compute='_compute_sign_requests',
        help="Au moins une demande de signature rattachée est signée.",
    )
    # Exposé pour la visibilité du bouton « Demander la signature » dans la vue.
    current_step_require_signature = fields.Boolean(
        related='current_step_id.require_signature', string="Étape à signer",
    )

    @api.depends('sign_request_ids', 'sign_request_ids.state')
    def _compute_sign_requests(self):
        for courrier in self:
            courrier.sign_request_count = len(courrier.sign_request_ids)
            courrier.has_completed_signature = any(
                request.state == 'signed'
                for request in courrier.sign_request_ids)

    # ------------------------------------------------------------------ #
    # Demande de signature
    # ------------------------------------------------------------------ #
    def _signature_source_version(self):
        """Dernière version PDF parmi les documents du courrier."""
        self.ensure_one()
        versions = self.document_ids.mapped('latest_version_id').filtered(
            lambda v: v.file_extension == 'pdf')
        return versions.sorted(
            key=lambda v: (v.upload_date or fields.Datetime.now(), v.id))[-1:]

    def action_request_signature(self):
        """Crée le modèle Sign + la demande depuis la dernière version PDF.

        Le signataire est le responsable du courrier (à défaut, l'utilisateur
        courant). La zone de signature est pré-positionnée en bas à droite de
        la première page ; le destinataire est notifié par Odoo Sign.
        """
        self.ensure_one()
        version = self._signature_source_version()
        if not version:
            raise UserError(_(
                "Aucune version PDF n'est disponible : la signature "
                "électronique porte sur un document PDF du courrier."))
        signer = self.responsible_id or self.env.user
        if not signer.partner_id.email:
            raise UserError(_(
                "Le signataire « %s » n'a pas d'adresse e-mail : Odoo Sign "
                "en a besoin pour envoyer la demande.", signer.name))
        # Copie de la pièce : Sign s'approprie l'attachement de son modèle ;
        # la version GED d'origine reste intacte.
        attachment = version.attachment_id.sudo().copy({
            'res_model': 'sign.template', 'res_id': 0,
        })
        template = self.env['sign.template'].sudo().create({
            'attachment_id': attachment.id,
            'name': _("Signature — %s") % (self.reference or self.subject),
        })
        role = self.env.ref('sign.sign_item_role_default',
                            raise_if_not_found=False) \
            or self.env['sign.item.role'].sudo().search([], limit=1)
        item_type = self.env.ref('sign.sign_item_type_signature',
                                 raise_if_not_found=False)
        if role and item_type:
            # Zone de signature pré-positionnée (page 1, bas droite).
            self.env['sign.item'].sudo().create({
                'template_id': template.id,
                'type_id': item_type.id,
                'responsible_id': role.id,
                'required': True,
                'page': 1,
                'posX': 0.66, 'posY': 0.88,
                'width': 0.22, 'height': 0.06,
            })
        request = self.env['sign.request'].sudo().create({
            'template_id': template.id,
            'reference': template.name,
            'courrier_id': self.id,
            'request_item_ids': [Command.create({
                'partner_id': signer.partner_id.id,
                'role_id': role.id if role else False,
            })],
        })
        self.message_post(body=_(
            "✍️ Demande de signature envoyée à %s (document « %s »).") % (
            signer.name, version.file_name or ''))
        self.env['aite.courrier.audit.log']._log(
            self.env, _("Demande de signature"), 'info', 'aite.courrier',
            self.id, self.reference or self.display_name,
            _("Signataire : %s — %s") % (signer.name,
                                         version.file_name or ''), 'ui')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Demande de signature"),
            'res_model': 'sign.request',
            'res_id': request.id,
            'view_mode': 'form',
        }

    def action_view_sign_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Signatures — %s") % (self.reference or self.subject),
            'res_model': 'sign.request',
            'view_mode': 'list,form',
            'domain': [('courrier_id', '=', self.id)],
        }

    # ------------------------------------------------------------------ #
    # Garde serveur : étape « Signature requise »
    # ------------------------------------------------------------------ #
    def do_transition(self, transition, comment=False):
        self.ensure_one()
        transition = self._as_transition(transition)
        if transition.direction == 'forward' \
                and self.current_step_id.require_signature \
                and not self.has_completed_signature:
            self.env['aite.courrier.audit.log']._log(
                self.env, _("Action bloquée"), 'err', 'aite.courrier',
                self.id, self.reference or self.display_name,
                _("Étape « %s » : signature électronique manquante.")
                % self.current_step_id.name, 'ui')
            raise UserError(_(
                "Cette étape exige une signature électronique : aucune "
                "demande de signature complétée n'est rattachée au courrier. "
                "Utilisez « Demander la signature » puis attendez sa "
                "complétion."))
        return super().do_transition(transition, comment=comment)
