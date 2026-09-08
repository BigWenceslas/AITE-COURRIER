# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AiteWorkflowCircuit(models.Model):
    """Le circuit déclare l'objet qu'il gouverne (``res_model``).

    Pour un courrier, le type reste la clé (un seul circuit actif par
    type) ; pour les autres objets, chaque application ajoute sa propre
    valeur de ``res_model`` (``selection_add``) et sa propre clé
    d'unicité (ex. type de dossier métier).
    """

    _inherit = 'aite.workflow.circuit'

    res_model = fields.Selection(
        selection=[('aite.courrier', "Courrier"),
                   ('aite.ecm.document', "Document ECM")],
        string="Objet gouverné", default='aite.courrier', required=True,
        index=True)
    # Le type de courrier n'est requis que pour les circuits de courrier.
    type_id = fields.Many2one(required=False)
    document_type_id = fields.Many2one(
        comodel_name='aite.ecm.document.type', string="Type de document ECM",
        ondelete='restrict', index=True)

    @api.constrains('active', 'type_id', 'document_type_id', 'res_model')
    def _check_unique_active_per_type(self):
        for circuit in self:
            if circuit.res_model == 'aite.courrier' and not circuit.type_id:
                raise ValidationError(_(
                    "Un circuit de courrier doit préciser son type de "
                    "courrier."))
            if circuit.res_model == 'aite.ecm.document' \
                    and not circuit.document_type_id:
                raise ValidationError(_(
                    "Un circuit de document ECM doit préciser son type de "
                    "document."))
            if not circuit.active:
                continue
            if circuit.type_id and self.search_count([
                    ('type_id', '=', circuit.type_id.id),
                    ('active', '=', True), ('id', '!=', circuit.id)]):
                raise ValidationError(_(
                    "Un seul circuit actif est autorisé par type de "
                    "courrier : le type « %s » possède déjà un circuit "
                    "actif.", circuit.type_id.display_name))
            if circuit.document_type_id and self.search_count([
                    ('document_type_id', '=', circuit.document_type_id.id),
                    ('active', '=', True), ('id', '!=', circuit.id)]):
                raise ValidationError(_(
                    "Un seul circuit actif par type de document : « %s » en "
                    "possède déjà un.", circuit.document_type_id.name))


class AiteWorkflowHistory(models.Model):
    """Historique d'étapes générique (tout objet gouverné par un circuit)."""

    _name = 'aite.workflow.history'
    _description = "Historique de circuit"
    _order = 'id desc'

    res_model = fields.Char(string="Modèle", required=True, index=True)
    res_id = fields.Many2oneReference(
        string="ID enregistrement", model_field='res_model', required=True,
        index=True)
    res_ref = fields.Char(string="Référence")
    circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit', string="Circuit",
        ondelete='set null')
    step_id = fields.Many2one(
        comodel_name='aite.workflow.step', string="Étape", required=True,
        ondelete='restrict')
    entered_date = fields.Datetime(string="Entrée", required=True,
                                   default=fields.Datetime.now)
    left_date = fields.Datetime(string="Sortie")
    user_id = fields.Many2one(
        comodel_name='res.users', string="Par",
        default=lambda self: self.env.user)
    transition_id = fields.Many2one(
        comodel_name='aite.workflow.transition', string="Transition",
        ondelete='set null')
    comment = fields.Text(string="Commentaire")
    duration_hours = fields.Float(
        string="Durée (h)", compute='_compute_duration', store=True)

    @api.depends('entered_date', 'left_date')
    def _compute_duration(self):
        for line in self:
            if line.entered_date and line.left_date:
                delta = line.left_date - line.entered_date
                line.duration_hours = delta.total_seconds() / 3600.0
            else:
                line.duration_hours = 0.0
