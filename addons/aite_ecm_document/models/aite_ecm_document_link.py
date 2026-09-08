# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteEcmTag(models.Model):
    _name = 'aite.ecm.tag'
    _description = "Étiquette ECM"
    _order = 'name'

    name = fields.Char(string="Nom", required=True, translate=True)
    color = fields.Integer(string="Couleur")
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "L'étiquette existe déjà."),
    ]


class AiteEcmLinkType(models.Model):
    """Type de relation entre documents (annexe de, remplace, référence…)."""

    _name = 'aite.ecm.link.type'
    _description = "Type de relation ECM"
    _order = 'sequence, name'

    sequence = fields.Integer(string="Séquence", default=10)
    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Libellé (source → cible)", required=True,
                       translate=True)
    inverse_name = fields.Char(string="Libellé inverse (cible → source)",
                               translate=True)
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         "Le code du type de relation doit être unique."),
    ]


class AiteEcmDocumentLink(models.Model):
    """Relation typée et orientée entre deux documents."""

    _name = 'aite.ecm.document.link'
    _description = "Relation entre documents ECM"
    _order = 'id desc'

    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document source",
        required=True, ondelete='cascade', index=True)
    target_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document cible",
        required=True, ondelete='cascade', index=True)
    link_type_id = fields.Many2one(
        comodel_name='aite.ecm.link.type', string="Relation", required=True,
        ondelete='restrict')
    note = fields.Char(string="Note")
    inverse_label = fields.Char(
        string="Vu de la cible", compute='_compute_inverse_label')

    _sql_constraints = [
        ('link_uniq', 'unique(document_id, target_id, link_type_id)',
         "Cette relation existe déjà entre ces deux documents."),
        ('no_self_link', 'CHECK(document_id <> target_id)',
         "Un document ne peut pas être relié à lui-même."),
    ]

    @api.depends('link_type_id.inverse_name', 'link_type_id.name')
    def _compute_inverse_label(self):
        for link in self:
            link.inverse_label = (link.link_type_id.inverse_name
                                  or link.link_type_id.name)
