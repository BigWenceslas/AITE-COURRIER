# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteEcmDossier(models.Model):
    """Dossier métier : pièces, complétude, circuit, documents rattachés."""

    _name = 'aite.ecm.dossier'
    _description = "Dossier métier"
    _inherit = ['aite.ecm.document.mixin', 'aite.workflow.mixin',
                'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    reference = fields.Char(
        string="Référence", readonly=True, copy=False, index=True,
        default=lambda self: _("Nouveau"))
    name = fields.Char(string="Objet", required=True, tracking=True)
    type_id = fields.Many2one(
        comodel_name='aite.ecm.dossier.type', string="Type de dossier",
        required=True, ondelete='restrict', tracking=True, index=True)
    properties = fields.Properties(
        string="Métadonnées", definition='type_id.metadata_definition',
        copy=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Tiers concerné", tracking=True)
    responsible_id = fields.Many2one(
        comodel_name='res.users', string="Responsable", tracking=True,
        default=lambda self: self.env.user)
    company_id = fields.Many2one(
        comodel_name='res.company', string="Société",
        default=lambda self: self.env.company)
    state = fields.Selection(
        selection=[('draft', "Brouillon"), ('open', "En cours"),
                   ('done', "Clôturé"), ('cancel', "Annulé")],
        string="Statut", default='draft', required=True, tracking=True,
        index=True)
    date_open = fields.Date(string="Ouvert le", readonly=True, copy=False)
    date_done = fields.Date(string="Clôturé le", readonly=True, copy=False)
    deadline = fields.Date(string="Échéance du dossier")
    description = fields.Text(string="Description")
    piece_ids = fields.One2many(
        comodel_name='aite.ecm.dossier.piece', inverse_name='dossier_id',
        string="Pièces")
    completion_rate = fields.Float(
        string="Complétude (%)", compute='_compute_completion', store=True)
    missing_required_count = fields.Integer(
        string="Pièces obligatoires manquantes",
        compute='_compute_completion', store=True)
    is_complete = fields.Boolean(
        string="Complet", compute='_compute_completion', store=True)

    # ------------------------------------------------------------------ #
    # Calculs
    # ------------------------------------------------------------------ #
    @api.depends('piece_ids.document_id', 'piece_ids.required',
                 'piece_ids.state')
    def _compute_completion(self):
        for dossier in self:
            pieces = dossier.piece_ids
            provided = pieces.filtered(lambda p: p.state != 'missing')
            required_missing = pieces.filtered(
                lambda p: p.required and p.state == 'missing')
            dossier.completion_rate = (
                100.0 * len(provided) / len(pieces)) if pieces else 100.0
            dossier.missing_required_count = len(required_missing)
            dossier.is_complete = not required_missing

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals['reference'] == _("Nouveau"):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'aite.ecm.dossier') or _("Nouveau")
        dossiers = super().create(vals_list)
        for dossier in dossiers:
            if not dossier.piece_ids:
                dossier._generate_pieces()
            dossier._wf_audit(_("Création du dossier"), 'info',
                              dossier.type_id.name)
        return dossiers

    def _generate_pieces(self):
        """Instancie la liste des pièces attendues depuis le type."""
        self.ensure_one()
        existing = self.piece_ids.mapped('template_id')
        lines = []
        for tmpl in self.type_id.piece_template_ids:
            if tmpl in existing:
                continue
            lines.append((0, 0, {
                'template_id': tmpl.id, 'name': tmpl.name,
                'sequence': tmpl.sequence, 'required': tmpl.required,
                'document_type_id': tmpl.document_type_id.id,
                'note': tmpl.note,
            }))
        if lines:
            self.write({'piece_ids': lines})
        return True

    def action_generate_pieces(self):
        for dossier in self:
            dossier._generate_pieces()
        return True

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    def action_open(self):
        for dossier in self:
            if dossier.state != 'draft':
                raise UserError(_("Seul un dossier en brouillon s'ouvre."))
            dossier.write({'state': 'open',
                           'date_open': fields.Date.context_today(self)})
            dossier._wf_audit(_("Ouverture du dossier"), 'ok', '')
            if dossier._wf_find_circuit():
                dossier.action_wf_launch()
        return True

    def action_close(self):
        for dossier in self:
            if not dossier.is_complete and not dossier._wf_is_manager():
                raise UserError(_(
                    "Le dossier est incomplet : %d pièce(s) obligatoire(s) "
                    "manquante(s). Seul un manager peut forcer la clôture.",
                    dossier.missing_required_count))
            if dossier.wf_status == 'running':
                raise UserError(_(
                    "Le circuit de validation est encore en cours."))
            dossier.write({'state': 'done',
                           'date_done': fields.Date.context_today(self)})
            dossier._wf_audit(_("Clôture du dossier"), 'ok',
                              _("Complétude : %d %%") % dossier.completion_rate)
        return True

    def action_cancel(self):
        for dossier in self:
            dossier.write({'state': 'cancel'})
            dossier._wf_audit(_("Annulation du dossier"), 'warn', '')
        return True

    def action_reset_draft(self):
        if not self._wf_is_manager():
            raise UserError(_("Réservé aux managers."))
        for dossier in self:
            dossier.write({'state': 'draft', 'date_open': False,
                           'date_done': False})
            if dossier.wf_status != 'none':
                dossier.action_wf_reset()
        return True

    # ------------------------------------------------------------------ #
    # Circuit (mixin)
    # ------------------------------------------------------------------ #
    def _wf_find_circuit(self):
        self.ensure_one()
        return self.type_id.active_circuit_id

    def _wf_reference(self):
        self.ensure_one()
        return self.reference or self.name

    def _wf_on_finished(self):
        """Étape finale atteinte : le dossier se clôture s'il est complet."""
        for dossier in self:
            if dossier.is_complete and dossier.state == 'open':
                dossier.write({'state': 'done',
                               'date_done': fields.Date.context_today(self)})
        return True

    # ------------------------------------------------------------------ #
    # Documents (mixin)
    # ------------------------------------------------------------------ #
    def _ecm_document_defaults(self):
        defaults = super()._ecm_document_defaults()
        defaults['default_name'] = False
        if self.type_id.folder_id:
            defaults['default_folder_id'] = self.type_id.folder_id.id
        if self.partner_id:
            defaults['default_description'] = _(
                "Dossier %s — %s") % (self.reference, self.partner_id.name)
        return defaults

    def _attach_document_to_piece(self, document):
        """Rattache un document à la première pièce manquante de son type."""
        self.ensure_one()
        piece = self.piece_ids.filtered(
            lambda p: not p.document_id and p.document_type_id
            and p.document_type_id == document.type_id)[:1]
        if piece:
            piece.document_id = document.id
            self.message_post(body=_(
                "Pièce « %s » fournie : %s") % (piece.name,
                                                document.display_name))
        return piece


class AiteEcmDossierPiece(models.Model):
    """Pièce d'un dossier : attendue, fournie (document rattaché), validée."""

    _name = 'aite.ecm.dossier.piece'
    _description = "Pièce de dossier"
    _order = 'sequence, id'

    dossier_id = fields.Many2one(
        comodel_name='aite.ecm.dossier', string="Dossier", required=True,
        ondelete='cascade', index=True)
    template_id = fields.Many2one(
        comodel_name='aite.ecm.dossier.piece.template', string="Modèle",
        ondelete='set null')
    sequence = fields.Integer(string="Séquence", default=10)
    name = fields.Char(string="Pièce", required=True)
    document_type_id = fields.Many2one(
        comodel_name='aite.ecm.document.type', string="Type attendu")
    required = fields.Boolean(string="Obligatoire", default=True)
    note = fields.Char(string="Consigne")
    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document fourni",
        domain="[('res_model', '=', 'aite.ecm.dossier'), ('res_id', '=', parent.id)]")
    validated = fields.Boolean(string="Validée")
    state = fields.Selection(
        selection=[('missing', "Manquante"), ('provided', "Fournie"),
                   ('validated', "Validée")],
        string="État", compute='_compute_state', store=True)

    @api.depends('document_id', 'validated')
    def _compute_state(self):
        for piece in self:
            if not piece.document_id:
                piece.state = 'missing'
            elif piece.validated:
                piece.state = 'validated'
            else:
                piece.state = 'provided'

    def action_open_document(self):
        self.ensure_one()
        if not self.document_id:
            raise UserError(_("Aucun document fourni pour cette pièce."))
        return {'type': 'ir.actions.act_window',
                'res_model': 'aite.ecm.document',
                'res_id': self.document_id.id, 'view_mode': 'form'}

    def action_new_document(self):
        """Crée le document ECM de la pièce (type et rattachement préremplis)."""
        self.ensure_one()
        ctx = self.dossier_id._ecm_document_defaults()
        ctx.update({'default_type_id': self.document_type_id.id,
                    'default_name': self.name,
                    'default_dossier_piece_id': self.id})
        return {'type': 'ir.actions.act_window',
                'res_model': 'aite.ecm.document', 'view_mode': 'form',
                'target': 'new', 'context': ctx}

    def action_toggle_validated(self):
        for piece in self:
            piece.validated = not piece.validated
        return True


class AiteEcmDocument(models.Model):
    """Rattachement automatique des documents créés depuis un dossier."""

    _inherit = 'aite.ecm.document'

    @api.model_create_multi
    def create(self, vals_list):
        docs = super().create(vals_list)
        piece_id = self.env.context.get('default_dossier_piece_id')
        for doc in docs:
            if doc.res_model != 'aite.ecm.dossier' or not doc.res_id:
                continue
            dossier = self.env['aite.ecm.dossier'].browse(doc.res_id)
            if not dossier.exists():
                continue
            if piece_id:
                piece = self.env['aite.ecm.dossier.piece'].browse(piece_id)
                if piece.exists() and not piece.document_id:
                    piece.document_id = doc.id
                    continue
            dossier._attach_document_to_piece(doc)
        return docs
