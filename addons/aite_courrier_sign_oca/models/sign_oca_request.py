# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SignOcaRequest(models.Model):
    _inherit = 'sign.oca.request'

    # Calculés pour les demandes créées depuis sign_oca (objet lié = un
    # courrier) ; action_request_signature les fournit directement.
    courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Courrier",
        compute='_compute_courrier_id', store=True, index=True, readonly=True,
    )
    courrier_step_history_id = fields.Many2one(
        comodel_name='aite.courrier.step.history', string="Passage d'étape",
        compute='_compute_courrier_id', store=True, readonly=True,
        ondelete='set null',
        help="Passage du courrier sur son étape au moment de la demande : "
             "la signature ne vaut que pour ce passage.",
    )
    courrier_step_id = fields.Many2one(
        related='courrier_step_history_id.step_id', string="Étape du circuit")
    courrier_document_id = fields.Many2one(
        comodel_name='aite.courrier.document', string="Pièce source",
        readonly=True, copy=False, ondelete='set null',
        help="Pièce GED dont le PDF a été soumis à signature.",
    )
    # Les lignes signataires portent le jeton du lien de signature : le
    # demandeur ne les lit pas (security/sign_oca_rules.xml). Ce résumé lui
    # dit qui doit signer, sans le jeton.
    courrier_signers_summary = fields.Char(
        string="Signataires", compute='_compute_courrier_signers_summary',
        compute_sudo=True)

    @api.depends('record_ref')
    def _compute_courrier_id(self):
        for request in self:
            ref = request.record_ref
            courrier = ref.exists() if ref and ref._name == 'aite.courrier' \
                else self.env['aite.courrier']
            request.courrier_id = courrier
            request.courrier_step_history_id = \
                courrier._sign_oca_current_visit() if courrier else False

    @api.depends('signer_ids.partner_id', 'signer_ids.signed_on')
    def _compute_courrier_signers_summary(self):
        # Recherche explicite plutôt que request.signer_ids : le cache est
        # partagé entre environnements, et le formulaire y a peut-être déjà
        # mis la liste vue par le demandeur (vide, cf. to_sign).
        signers = self.env['sign.oca.request.signer'].sudo().search(
            [('request_id', 'in', self._origin.ids)])
        # Hors du générateur : _() y retrouve la langue de self.env.
        signed, pending = _("signé"), _("en attente")
        for request in self:
            request.courrier_signers_summary = ", ".join(
                "%s (%s)" % (signer.partner_id.name,
                             signed if signer.signed_on else pending)
                for signer in signers
                if signer.request_id == request._origin)

    def _check_signed(self):
        # Méthode privée (non appelable par RPC), appelée par action_sign
        # après chaque signature : on ne réagit qu'au passage à « signé ».
        was_signed = self.state == '2_signed'
        res = super()._check_signed()
        if not was_signed and self.state == '2_signed' and self.courrier_id:
            self.courrier_id.sudo()._sign_oca_on_request_signed(self.sudo())
        return res

