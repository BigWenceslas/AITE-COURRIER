# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AiteEcmDossierType(models.Model):
    """Type de dossier métier : pièces attendues, métadonnées, circuit."""

    _name = 'aite.ecm.dossier.type'
    _description = "Type de dossier métier"
    _order = 'sequence, name'

    sequence = fields.Integer(string="Séquence", default=10)
    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Libellé", required=True, translate=True)
    active = fields.Boolean(string="Actif", default=True)
    description = fields.Text(string="Description")
    folder_id = fields.Many2one(
        comodel_name='aite.ecm.folder', string="Dossier de classement",
        help="Dossier de classement appliqué aux pièces du dossier.")
    metadata_definition = fields.PropertiesDefinition(
        string="Modèle de métadonnées")
    piece_template_ids = fields.One2many(
        comodel_name='aite.ecm.dossier.piece.template',
        inverse_name='dossier_type_id', string="Pièces attendues")
    circuit_ids = fields.One2many(
        comodel_name='aite.workflow.circuit', inverse_name='dossier_type_id',
        string="Circuits")
    active_circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit', string="Circuit actif",
        compute='_compute_active_circuit')
    dossier_count = fields.Integer(compute='_compute_dossier_count')

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         "Le code du type de dossier doit être unique."),
    ]

    @api.depends('circuit_ids.active')
    def _compute_active_circuit(self):
        for dtype in self:
            dtype.active_circuit_id = dtype.circuit_ids.filtered(
                'active')[:1]

    def _compute_dossier_count(self):
        counts = dict(self.env['aite.ecm.dossier']._read_group(
            [('type_id', 'in', self.ids)], ['type_id'], ['__count']))
        for dtype in self:
            dtype.dossier_count = counts.get(dtype, 0)

    def action_view_dossiers(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_dossier.action_aite_ecm_dossier')
        action['domain'] = [('type_id', '=', self.id)]
        action['context'] = {'default_type_id': self.id}
        return action


class AiteEcmDossierPieceTemplate(models.Model):
    """Pièce attendue par un type de dossier."""

    _name = 'aite.ecm.dossier.piece.template'
    _description = "Pièce attendue (modèle)"
    _order = 'sequence, id'

    dossier_type_id = fields.Many2one(
        comodel_name='aite.ecm.dossier.type', string="Type de dossier",
        required=True, ondelete='cascade')
    sequence = fields.Integer(string="Séquence", default=10)
    name = fields.Char(string="Pièce", required=True, translate=True)
    document_type_id = fields.Many2one(
        comodel_name='aite.ecm.document.type', string="Type de document",
        help="Type de document ECM attendu (rattachement automatique).")
    required = fields.Boolean(string="Obligatoire", default=True)
    note = fields.Char(string="Consigne")


class AiteWorkflowCircuit(models.Model):
    """Les circuits peuvent gouverner un type de dossier métier."""

    _inherit = 'aite.workflow.circuit'

    res_model = fields.Selection(
        selection_add=[('aite.ecm.dossier', "Dossier métier")],
        ondelete={'aite.ecm.dossier': 'set default'})
    dossier_type_id = fields.Many2one(
        comodel_name='aite.ecm.dossier.type', string="Type de dossier",
        ondelete='restrict', index=True)

    @api.constrains('active', 'dossier_type_id', 'res_model')
    def _check_unique_active_per_dossier_type(self):
        for circuit in self:
            if circuit.res_model != 'aite.ecm.dossier':
                continue
            if not circuit.dossier_type_id:
                raise ValidationError(_(
                    "Un circuit de dossier métier doit préciser son type "
                    "de dossier."))
            if circuit.active and self.search_count([
                    ('dossier_type_id', '=', circuit.dossier_type_id.id),
                    ('active', '=', True), ('id', '!=', circuit.id)]):
                raise ValidationError(_(
                    "Un seul circuit actif par type de dossier : « %s » "
                    "en possède déjà un.", circuit.dossier_type_id.name))
