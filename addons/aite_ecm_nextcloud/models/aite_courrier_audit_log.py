# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierAuditLog(models.Model):
    _inherit = 'aite.courrier.audit.log'

    source = fields.Selection(
        selection_add=[('nextcloud', "Nextcloud")],
        ondelete={'nextcloud': 'set default'})
