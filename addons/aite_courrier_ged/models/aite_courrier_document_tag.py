# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierDocumentTag(models.Model):
    """Étiquette libre de classement transversal des documents."""

    _name = 'aite.courrier.document.tag'
    _description = "Étiquette de document"
    _order = 'name'

    name = fields.Char(string="Nom", required=True, translate=True)
    color = fields.Integer(string="Couleur")

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Cette étiquette existe déjà."),
    ]
