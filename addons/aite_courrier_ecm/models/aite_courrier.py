# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AiteCourrier(models.Model):
    """Le courrier expose ses documents ECM et propage sa confidentialité."""

    _inherit = 'aite.courrier'

    ecm_document_count = fields.Integer(
        string="Documents ECM", compute='_compute_ecm_document_count')

    def _compute_ecm_document_count(self):
        Document = self.env['aite.ecm.document']
        for courrier in self:
            courrier.ecm_document_count = Document.search_count([
                ('res_model', '=', 'aite.courrier'),
                ('res_id', '=', courrier.id)]) if courrier.id else 0

    def action_view_ecm_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_document.action_aite_ecm_document')
        action['name'] = _("Documents ECM — %s") % (self.reference or self.subject)
        action['domain'] = [('res_model', '=', 'aite.courrier'),
                            ('res_id', '=', self.id)]
        action['context'] = {'default_res_model': 'aite.courrier',
                             'default_res_id': self.id}
        return action

    def write(self, vals):
        res = super().write(vals)
        if {'reference', 'confidentiality_id', 'state', 'subject',
                'responsible_id'} & set(vals):
            self.mapped('document_ids')._ecm_try_sync()
        return res
