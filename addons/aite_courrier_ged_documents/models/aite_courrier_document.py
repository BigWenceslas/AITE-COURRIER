# -*- coding: utf-8 -*-
from odoo import models


class AiteCourrierDocument(models.Model):
    """Chaque pièce ajoutée (``add_version``) apparaît dans Documents, dans le
    dossier du courrier — même ``ir.attachment``, aucune duplication."""

    _name = 'aite.courrier.document'
    _inherit = ['aite.courrier.document', 'documents.mixin']

    def _get_document_folder(self):
        self.ensure_one()
        if not self.courrier_id:
            return self.env['documents.document']
        return self.courrier_id._get_or_create_documents_folder()
