# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierType(models.Model):
    """Type de courrier (référentiel paramétrable)."""

    _name = 'aite.courrier.type'
    _description = "Type de courrier"
    _order = 'code'

    # Code court et unique servant de clé fonctionnelle (ex : ENTR, SORT, FACT).
    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Libellé", required=True, translate=True)
    category = fields.Selection(
        selection=[
            ('entrant', "Entrant"),
            ('sortant', "Sortant"),
            ('interne', "Interne"),
        ],
        string="Catégorie",
        required=True,
        help="Sens de circulation du courrier de ce type.",
    )
    # Soft toggle : on désactive plutôt que de supprimer (préserve l'historique).
    active = fields.Boolean(string="Actif", default=True)

    # NB : le champ circuit_id (vers aite.workflow.circuit) n'est volontairement
    # PAS défini ici. Il est ajouté par héritage dans le module
    # aite_courrier_workflow afin de garder aite_courrier_base installable seul,
    # sans dépendance vers le module workflow.

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         "Le code du type de courrier doit être unique."),
    ]
