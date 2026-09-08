# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierAuditLog(models.Model):
    """Nouvelle source d'événements : appels de l'API REST."""

    _inherit = 'aite.courrier.audit.log'

    source = fields.Selection(
        selection_add=[('api', "API")], ondelete={'api': 'set default'})
