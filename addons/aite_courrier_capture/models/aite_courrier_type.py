# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierType(models.Model):
    _inherit = 'aite.courrier.type'

    mail_capture_default = fields.Boolean(
        string="Type par défaut (capture e-mail)",
        help="Type appliqué aux courriers créés automatiquement depuis la "
             "boîte e-mail dédiée. À défaut, le premier type « Entrant » "
             "actif est utilisé.",
    )
