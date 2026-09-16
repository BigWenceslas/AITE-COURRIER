# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteCourrierStepHistory(models.Model):
    """Trace du passage d'un courrier sur une étape de son circuit."""

    _name = 'aite.courrier.step.history'
    _description = "Historique d'étape de courrier"
    _order = 'entered_date, id'

    courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Courrier", required=True,
        ondelete='cascade', index=True,
    )
    step_id = fields.Many2one(
        comodel_name='aite.workflow.step', string="Étape", required=True,
        ondelete='restrict',
    )
    entered_date = fields.Datetime(string="Entrée le")
    left_date = fields.Datetime(string="Sortie le")
    user_id = fields.Many2one(comodel_name='res.users', string="Intervenant")
    comment = fields.Text(string="Commentaire")
    transition_label = fields.Char(string="Transition")
    actor_function = fields.Char(
        string="Fonction", compute='_compute_actor_function',
        help="Rôle au titre duquel l'intervenant a agi sur cette étape. "
             "C'est la seule identification exposée au tiers sur le portail, "
             "où les noms ne sont jamais affichés.")

    @api.depends('step_id.role_ids', 'step_id.name', 'user_id.groups_id')
    def _compute_actor_function(self):
        for line in self:
            roles = line.step_id.role_ids
            # Le rôle réellement porté par l'intervenant, quand l'étape en
            # autorise plusieurs ; à défaut, les rôles habilités de l'étape.
            held = roles.filtered(lambda g: g in line.user_id.groups_id) \
                if line.user_id else roles.browse()
            line.actor_function = ', '.join(
                (held or roles).mapped('name')) or line.step_id.name
