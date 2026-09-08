# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierConfidentiality(models.Model):
    """Niveau de confidentialité d'un courrier (référentiel paramétrable)."""

    _name = 'aite.courrier.confidentiality'
    _description = "Niveau de confidentialité du courrier"
    _order = 'sequence, code'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Libellé", required=True, translate=True)
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         "Le code de confidentialité doit être unique."),
    ]
