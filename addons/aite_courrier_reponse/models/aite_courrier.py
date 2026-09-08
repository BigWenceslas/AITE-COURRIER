# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AiteCourrier(models.Model):
    """Liens de réponse entre courriers (fil « demande → réponse »)."""

    _inherit = 'aite.courrier'

    reply_to_courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Réponse à",
        readonly=True, copy=False, index=True, ondelete='set null',
        help="Courrier d'origine auquel ce courrier sortant répond.",
    )
    reply_ids = fields.One2many(
        comodel_name='aite.courrier', inverse_name='reply_to_courrier_id',
        string="Réponses",
    )
    reply_count = fields.Integer(
        string="Réponses", compute='_compute_reply_count')

    @api.depends('reply_ids')
    def _compute_reply_count(self):
        for courrier in self:
            courrier.reply_count = len(courrier.reply_ids)

    def action_open_reponse_wizard(self):
        """Bouton « Répondre » : ouvre l'assistant de réponse."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Répondre — %s") % (self.reference or self.subject),
            'res_model': 'aite.courrier.reponse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_courrier_id': self.id},
        }

    def action_view_replies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Réponses — %s") % (self.reference or self.subject),
            'res_model': 'aite.courrier',
            'view_mode': 'list,form',
            'domain': [('reply_to_courrier_id', '=', self.id)],
        }

    def action_open_reply_source(self):
        """Ouvre le courrier d'origine auquel ce courrier répond."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aite.courrier',
            'res_id': self.reply_to_courrier_id.id,
            'view_mode': 'form',
        }
