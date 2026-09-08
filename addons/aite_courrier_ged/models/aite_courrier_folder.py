# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteCourrierFolder(models.Model):
    """Dossier de classement de l'espace documentaire (arborescence)."""

    _name = 'aite.courrier.folder'
    _description = "Dossier documentaire"
    _parent_store = True
    _parent_name = 'parent_id'
    _order = 'complete_name'

    name = fields.Char(string="Nom", required=True, translate=True)
    description = fields.Char(string="Description", translate=True)
    color = fields.Integer(string="Couleur")
    parent_id = fields.Many2one(
        comodel_name='aite.courrier.folder', string="Dossier parent",
        ondelete='cascade', index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        comodel_name='aite.courrier.folder', inverse_name='parent_id',
        string="Sous-dossiers",
    )
    complete_name = fields.Char(
        string="Nom complet", compute='_compute_complete_name',
        recursive=True, store=True,
    )
    document_ids = fields.One2many(
        comodel_name='aite.courrier.document', inverse_name='folder_id',
        string="Documents",
    )
    document_count = fields.Integer(
        string="Nombre de documents", compute='_compute_document_count',
        help="Documents classés directement dans ce dossier (hors sous-dossiers).",
    )
    active = fields.Boolean(string="Actif", default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = "%s / %s" % (
                    folder.parent_id.complete_name, folder.name)
            else:
                folder.complete_name = folder.name

    @api.depends('document_ids')
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)
