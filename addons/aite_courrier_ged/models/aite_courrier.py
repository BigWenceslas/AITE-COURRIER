# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteCourrier(models.Model):
    """Extension du courrier : pièces versionnées rattachées.

    L'adossement à l'app Documents (Enterprise) est porté par le module
    passerelle ``aite_courrier_ged_documents`` ; ce module reste compatible
    Odoo Community.
    """

    _inherit = 'aite.courrier'

    document_ids = fields.One2many(
        comodel_name='aite.courrier.document', inverse_name='courrier_id',
        string="Documents",
    )
    document_count = fields.Integer(
        string="Nombre de documents", compute='_compute_document_count')

    @api.depends('document_ids')
    def _compute_document_count(self):
        for courrier in self:
            courrier.document_count = len(courrier.document_ids)
