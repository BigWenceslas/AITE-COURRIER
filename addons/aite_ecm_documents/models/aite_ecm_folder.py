# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteEcmFolder(models.Model):
    """Le plan de classement est reflété intégralement dans Documents."""

    _inherit = 'aite.ecm.folder'

    documents_folder_id = fields.Many2one(
        comodel_name='documents.document', string="Dossier Documents",
        readonly=True, copy=False,
        help="Dossier miroir dans l'app Documents.")

    def _documents_root(self):
        return self.env.ref('aite_ecm_documents.documents_folder_ecm',
                            raise_if_not_found=False)

    def _get_or_create_documents_folder(self):
        """Dossier Documents miroir, créé au besoin (chaîne parentale)."""
        self.ensure_one()
        if self.documents_folder_id:
            return self.documents_folder_id
        parent_folder = self.parent_id._get_or_create_documents_folder() \
            if self.parent_id else self._documents_root()
        folder = self.env['documents.document'].sudo().with_context(
            ecm_skip_adopt=True).create({
                'name': self.name, 'type': 'folder',
                'folder_id': parent_folder.id if parent_folder else False})
        self.sudo().documents_folder_id = folder.id
        return folder

    @api.model_create_multi
    def create(self, vals_list):
        folders = super().create(vals_list)
        for folder in folders:
            folder._get_or_create_documents_folder()
        return folders

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for folder in self.filtered('documents_folder_id'):
                folder.documents_folder_id.sudo().name = folder.name
        if 'parent_id' in vals:
            for folder in self.filtered('documents_folder_id'):
                parent = folder.parent_id._get_or_create_documents_folder() \
                    if folder.parent_id else self._documents_root()
                folder.documents_folder_id.sudo().write(
                    {'folder_id': parent.id if parent else False})
        return res

    @api.model
    def _from_documents_folder(self, documents_folder):
        """Dossier ECM correspondant à un dossier Documents (ou à son plus
        proche ancêtre reflété) ; vide si hors de l'espace ECM."""
        root = self._documents_root()
        current = documents_folder
        seen = 0
        while current and seen < 50:
            folder = self.sudo().search(
                [('documents_folder_id', '=', current.id)], limit=1)
            if folder:
                return folder, True
            if root and current == root:
                return self.browse(), True
            current = current.folder_id
            seen += 1
        return self.browse(), False
