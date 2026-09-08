# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteWorkflowActionWizard(models.TransientModel):
    """Assistant d'action générique : transition ou rejet sur tout objet
    porteur du mixin ``aite.workflow.mixin``."""

    _name = 'aite.workflow.action.wizard'
    _description = "Action de circuit"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    record_ref = fields.Char(string="Objet", compute='_compute_record')
    step_name = fields.Char(string="Étape courante", compute='_compute_record')
    action_kind = fields.Selection(
        selection=[('transition', "Appliquer une transition"),
                   ('reject', "Rejeter")],
        string="Action", default='transition', required=True)
    transition_id = fields.Many2one(
        comodel_name='aite.workflow.transition', string="Transition")
    allowed_transition_ids = fields.Many2many(
        comodel_name='aite.workflow.transition', compute='_compute_record')
    comment_required = fields.Boolean(related='transition_id.comment_required')
    comment = fields.Text(string="Commentaire")

    def _record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.depends('res_model', 'res_id')
    def _compute_record(self):
        for wizard in self:
            record = wizard._record() if wizard.res_model else None
            wizard.record_ref = record._wf_reference() if record else False
            wizard.step_name = record.wf_step_id.name if record else False
            wizard.allowed_transition_ids = (
                record.wf_transition_ids if record else False)

    def action_confirm(self):
        self.ensure_one()
        record = self._record()
        if self.action_kind == 'reject':
            record.action_wf_reject(self.comment)
        else:
            if not self.transition_id:
                raise UserError(_("Choisissez une transition."))
            record.wf_do_transition(self.transition_id, self.comment)
        return {'type': 'ir.actions.act_window_close'}
