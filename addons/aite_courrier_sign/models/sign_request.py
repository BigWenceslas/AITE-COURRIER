# -*- coding: utf-8 -*-
from odoo import fields, models


class SignRequest(models.Model):
    """Rattachement des demandes de signature à leur courrier d'origine."""

    _inherit = 'sign.request'

    courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Courrier",
        ondelete='set null', index=True,
        help="Courrier AITE à l'origine de cette demande de signature.",
    )
