# -*- coding: utf-8 -*-
from odoo import fields, models


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
