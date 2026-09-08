# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AiteEcmDocumentMixin(models.AbstractModel):
    """Ajoute à n'importe quel modèle ses documents ECM rattachés.

    Usage : ``_inherit = ['mon.modele', 'aite.ecm.document.mixin']`` puis
    un bouton statistique appelant :meth:`action_view_ecm_documents`.
    Le rattachement se fait par (``res_model``, ``res_id``) — même mécanique
    que les pièces jointes et le fil de discussion d'Odoo.
    """

    _name = 'aite.ecm.document.mixin'
    _description = "Mixin documents ECM"

    ecm_document_ids = fields.One2many(
        comodel_name='aite.ecm.document', inverse_name='res_id',
        string="Documents ECM",
        domain=lambda self: [('res_model', '=', self._name)])
    ecm_document_count = fields.Integer(
        string="Documents", compute='_compute_ecm_document_count')

    def _compute_ecm_document_count(self):
        Document = self.env['aite.ecm.document']
        for record in self:
            record.ecm_document_count = Document.search_count([
                ('res_model', '=', record._name),
                ('res_id', '=', record.id)]) if record.id else 0

    def _ecm_document_defaults(self):
        """Valeurs par défaut des nouveaux documents (surcharge libre)."""
        self.ensure_one()
        return {
            'default_res_model': self._name,
            'default_res_id': self.id,
            'default_name': self.display_name,
        }

    def action_view_ecm_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_document.action_aite_ecm_document')
        action['name'] = _("Documents — %s") % self.display_name
        action['domain'] = [('res_model', '=', self._name),
                            ('res_id', '=', self.id)]
        action['context'] = dict(self._ecm_document_defaults(),
                                 search_default_group_type=0)
        return action


class ResPartner(models.Model):
    """Documents ECM du tiers (contrats, agréments, pièces d'identité…)."""

    _name = 'res.partner'
    _inherit = ['res.partner', 'aite.ecm.document.mixin']
