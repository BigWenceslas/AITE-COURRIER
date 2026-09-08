# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteCourrierActionWizard(models.TransientModel):
    """Assistant unique pour traiter / rejeter / commenter un courrier."""

    _name = 'aite.courrier.action.wizard'
    _description = "Assistant d'action sur courrier"

    courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Courrier", required=True)
    kind = fields.Selection(
        selection=[
            ('validate', "Traiter (valider / retourner)"),
            ('reject', "Rejeter"),
            ('comment', "Commenter"),
        ],
        string="Action", required=True, default='validate')
    transition_id = fields.Many2one(
        comodel_name='aite.workflow.transition', string="Transition")
    transition_comment_required = fields.Boolean(
        related='transition_id.comment_required')
    allowed_transition_ids = fields.Many2many(
        comodel_name='aite.workflow.transition',
        string="Transitions autorisées",
        compute='_compute_allowed_transitions')
    comment = fields.Text(string="Commentaire")

    @api.depends('courrier_id')
    def _compute_allowed_transitions(self):
        for wizard in self:
            wizard.allowed_transition_ids = wizard.courrier_id.available_transition_ids

    def action_confirm(self):
        self.ensure_one()
        if self.kind == 'validate':
            if not self.transition_id:
                raise UserError(_("Sélectionnez l'action à effectuer."))
            self.courrier_id.do_transition(self.transition_id, self.comment)
        elif self.kind == 'reject':
            self.courrier_id.action_reject(self.comment)
        else:
            self.courrier_id.action_post_comment(self.comment)
        return {'type': 'ir.actions.act_window_close'}
