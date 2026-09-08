# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteEcmDocumentType(models.Model):
    _inherit = 'aite.ecm.document.type'

    circuit_ids = fields.One2many(
        comodel_name='aite.workflow.circuit', inverse_name='document_type_id',
        string="Circuits")
    active_circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit', string="Circuit actif",
        compute='_compute_active_circuit')
    wf_finalize = fields.Boolean(
        string="Finaliser en fin de circuit", default=True,
        help="À l'arrivée sur l'étape finale, le document passe au statut "
             "Finalisé (verrouillé).")

    @api.depends('circuit_ids.active')
    def _compute_active_circuit(self):
        for dtype in self:
            dtype.active_circuit_id = dtype.circuit_ids.filtered('active')[:1]


class AiteEcmDocument(models.Model):
    """Circuit de validation par type de document (mixin polymorphe)."""

    _name = 'aite.ecm.document'
    _inherit = ['aite.ecm.document', 'aite.workflow.mixin']

    wf_has_circuit = fields.Boolean(
        string="Circuit disponible", compute='_compute_wf_has_circuit')

    @api.depends('type_id.active_circuit_id')
    def _compute_wf_has_circuit(self):
        for doc in self:
            doc.wf_has_circuit = bool(doc.type_id.active_circuit_id)

    def _wf_find_circuit(self):
        self.ensure_one()
        return self.type_id.active_circuit_id

    def _wf_reference(self):
        self.ensure_one()
        return self.reference or self.name

    def action_wf_launch(self):
        for doc in self:
            if not doc.latest_version_id:
                raise UserError(_(
                    "Ajoutez un fichier avant de lancer le circuit de « %s ».",
                    doc.name))
            if doc.state != 'draft':
                raise UserError(_(
                    "Le circuit ne se lance que sur un document en brouillon."))
            if doc.is_checked_out:
                raise UserError(_("Libérez la réservation avant de lancer "
                                  "le circuit."))
        return super().action_wf_launch()

    def _wf_on_finished(self):
        """Étape finale : finalisation (verrouillage) si le type le prévoit."""
        for doc in self:
            if doc.type_id.wf_finalize and doc.state == 'draft':
                doc.sudo().with_context(audit_source='system').write(
                    {'state': 'final'})
                doc._audit(doc, _("Finalisé en fin de circuit"), 'ok',
                           doc.wf_circuit_id.name)
        return True

    def action_wf_reject(self, reason):
        res = super().action_wf_reject(reason)
        return res

    def add_version(self, filename, datas, comment=False):
        for doc in self:
            if doc.wf_status == 'running' and not doc._wf_user_can_act(
                    doc.wf_step_id):
                raise UserError(_(
                    "Le document est en cours de validation (étape « %s ») : "
                    "seules les personnes habilitées à cette étape peuvent y "
                    "ajouter une version.", doc.wf_step_id.name))
        return super().add_version(filename, datas, comment)
