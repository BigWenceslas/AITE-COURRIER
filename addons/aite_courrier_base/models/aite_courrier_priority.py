# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierPriority(models.Model):
    """Niveau de priorité d'un courrier (référentiel paramétrable)."""

    _name = 'aite.courrier.priority'
    _description = "Niveau de priorité du courrier"
    _order = 'sequence, code'

    code = fields.Char(string="Code", required=True, help="Code court (u/h/n).")
    name = fields.Char(string="Libellé", required=True, translate=True)
    sequence = fields.Integer(string="Séquence", default=10)
    # Pastille de couleur utilisée dans les vues (widget kanban/badge).
    color = fields.Integer(string="Couleur")
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         "Le code de priorité doit être unique."),
    ]
