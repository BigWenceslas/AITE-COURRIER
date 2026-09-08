# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrier(models.Model):
    """Recherche plein texte : retrouver un courrier par le CONTENU des pièces."""

    _inherit = 'aite.courrier'

    document_fulltext = fields.Char(
        string="Contenu des pièces",
        compute='_compute_document_fulltext',
        search='_search_document_fulltext',
        help="Champ de recherche : interroge le texte extrait (OCR / couche "
             "texte PDF) de toutes les versions des pièces du courrier.",
    )

    def _compute_document_fulltext(self):
        # Champ de recherche uniquement : aucune valeur à afficher.
        for courrier in self:
            courrier.document_fulltext = False

    def _search_document_fulltext(self, operator, value):
        # Recherche en sudo sur le texte extrait, puis retour d'un domaine sur
        # les ids : les règles d'enregistrement (confidentialité) du courrier
        # s'appliquent ensuite normalement à l'affichage des résultats.
        versions = self.env['aite.courrier.document.version'].sudo().search(
            [('ocr_text', operator, value)])
        courrier_ids = versions.mapped('document_id.courrier_id').ids
        return [('id', 'in', courrier_ids)]
