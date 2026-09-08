# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteEcmDocumentType(models.Model):
    """Type de document ECM et son modèle de métadonnées.

    Le modèle de métadonnées s'appuie sur les champs ``Properties`` natifs
    d'Odoo 18 : la définition (liste de propriétés typées) est portée par le
    type, les valeurs par chaque document. Les administrateurs ajoutent ou
    modifient les propriétés directement depuis une fiche document du type
    (bouton « Ajouter une propriété »), sans développement.
    """

    _name = 'aite.ecm.document.type'
    _description = "Type de document ECM"
    _order = 'sequence, name'

    sequence = fields.Integer(string="Séquence", default=10)
    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Libellé", required=True, translate=True)
    active = fields.Boolean(string="Actif", default=True)
    description = fields.Text(string="Description")
    metadata_definition = fields.PropertiesDefinition(
        string="Modèle de métadonnées")
    default_folder_id = fields.Many2one(
        comodel_name='aite.ecm.folder', string="Dossier par défaut",
        help="Dossier de classement appliqué aux nouveaux documents de ce "
             "type lorsqu'aucun dossier n'est précisé.")
    default_confidentiality_id = fields.Many2one(
        comodel_name='aite.courrier.confidentiality',
        string="Confidentialité par défaut")
    allowed_extensions = fields.Char(
        string="Extensions autorisées",
        help="Liste séparée par des virgules (ex. pdf,docx). Vide = liste "
             "standard de la GED.")
    document_count = fields.Integer(
        string="Documents", compute='_compute_document_count')

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         "Le code du type de document doit être unique."),
    ]

    def _compute_document_count(self):
        counts = dict(self.env['aite.ecm.document']._read_group(
            [('type_id', 'in', self.ids)], ['type_id'], ['__count']))
        for rec in self:
            rec.document_count = counts.get(rec, 0)

    def _allowed_extensions(self):
        """Extensions effectives du type (repli : liste standard)."""
        self.ensure_one()
        if self.allowed_extensions:
            return tuple(
                e.strip().lower().lstrip('.')
                for e in self.allowed_extensions.split(',') if e.strip())
        return self.env['aite.ecm.document'].ALLOWED_EXTENSIONS

    def action_view_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_document.action_aite_ecm_document')
        action['domain'] = [('type_id', '=', self.id)]
        action['context'] = {'default_type_id': self.id}
        return action
