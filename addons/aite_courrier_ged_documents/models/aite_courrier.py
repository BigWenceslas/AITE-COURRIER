# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AiteCourrier(models.Model):
    """Un dossier Documents par courrier, sous l'espace « Courrier »."""

    _inherit = 'aite.courrier'

    documents_folder_id = fields.Many2one(
        comodel_name='documents.document', string="Dossier GED",
        copy=False, readonly=True, domain="[('type', '=', 'folder')]",
        help="Dossier de l'app Documents regroupant les pièces de ce courrier.")

    def _documents_folder_name(self):
        self.ensure_one()
        return self.reference or self.subject or _("Courrier %s", self.id)

    def _get_or_create_documents_folder(self):
        """Dossier Documents du courrier, créé au besoin sous l'espace racine."""
        self.ensure_one()
        if self.documents_folder_id:
            return self.documents_folder_id
        root = self.env.ref('aite_courrier_ged_documents.documents_folder_courrier',
                            raise_if_not_found=False)
        folder = self.env['documents.document'].sudo().create({
            'name': self._documents_folder_name(), 'type': 'folder',
            'folder_id': root.id if root else False})
        self.sudo().documents_folder_id = folder.id
        return folder

    def write(self, vals):
        res = super().write(vals)
        if 'reference' in vals:
            for courrier in self.filtered('documents_folder_id'):
                new_name = courrier._documents_folder_name()
                if courrier.documents_folder_id.name != new_name:
                    courrier.documents_folder_id.sudo().name = new_name
        return res
