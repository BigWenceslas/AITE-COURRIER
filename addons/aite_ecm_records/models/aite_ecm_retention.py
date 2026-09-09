# -*- coding: utf-8 -*-
"""Records management : durées de conservation, sort final, gel juridique.

Vocabulaire (ISO 15489) :

* **DUA** — durée d'utilité administrative : combien de temps le document
  reste utile à l'activité, à compter d'un **événement déclencheur** ;
* **sort final** — ce qu'il advient à l'échéance : élimination, conservation
  définitive, ou revue par un responsable ;
* **gel juridique** — suspension de toute destruction (litige, audit) ;
* **bordereau d'élimination** — la liste, validée et signée, de ce qui est
  détruit ; le certificat reste dans l'ECM.
"""
import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

TRIGGERS = [
    ('create', "Création du document"),
    ('final', "Finalisation"),
    ('archive', "Archivage"),
    ('close', "Clôture du dossier / du courrier"),
    ('meta', "Date portée par une métadonnée"),
]
FINAL_FATES = [
    ('destroy', "Élimination"),
    ('keep', "Conservation définitive"),
    ('review', "Revue avant décision"),
]


class AiteEcmRetentionRule(models.Model):
    """Règle de conservation : à quels documents elle s'applique, combien de
    temps, à partir de quand, et ce qu'il advient ensuite."""

    _name = 'aite.ecm.retention.rule'
    _description = "Règle de conservation"
    _order = 'sequence, id'

    sequence = fields.Integer(string="Priorité", default=10,
                              help="La première règle applicable l'emporte.")
    name = fields.Char(string="Libellé", required=True, translate=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)
    legal_basis = fields.Char(
        string="Base légale",
        help="Texte de référence : OHADA (10 ans comptable), Code du travail, "
             "code fiscal, politique interne…")
    note = fields.Text(string="Commentaire")

    # périmètre
    document_type_ids = fields.Many2many(
        comodel_name='aite.ecm.document.type', string="Types de documents")
    folder_ids = fields.Many2many(
        comodel_name='aite.ecm.folder', string="Dossiers de classement",
        help="La règle s'applique au dossier et à toute sa branche.")
    confidentiality_ids = fields.Many2many(
        comodel_name='aite.courrier.confidentiality',
        string="Niveaux de confidentialité")

    # durée
    duration = fields.Integer(string="Durée", required=True, default=10)
    duration_unit = fields.Selection(
        selection=[('year', "années"), ('month', "mois"), ('day', "jours")],
        string="Unité", default='year', required=True)
    trigger = fields.Selection(selection=TRIGGERS, string="Point de départ",
                               default='final', required=True)
    trigger_property = fields.Char(
        string="Métadonnée de départ",
        help="Nom technique de la propriété de type date (ex. contrat_date_fin) "
             "quand le point de départ est « Date portée par une métadonnée ».")

    # sort final
    final_fate = fields.Selection(selection=FINAL_FATES, string="Sort final",
                                  default='review', required=True)
    review_user_id = fields.Many2one(
        comodel_name='res.users', string="Responsable de la revue")
    document_count = fields.Integer(compute='_compute_document_count')

    _sql_constraints = [
        ('duration_positive', 'CHECK(duration > 0)',
         "La durée de conservation doit être positive."),
    ]

    @api.constrains('trigger', 'trigger_property')
    def _check_trigger_property(self):
        for rule in self:
            if rule.trigger == 'meta' and not rule.trigger_property:
                raise ValidationError(_(
                    "Précisez la métadonnée servant de point de départ."))

    def _compute_document_count(self):
        counts = dict(self.env['aite.ecm.document']._read_group(
            [('retention_rule_id', 'in', self.ids)], ['retention_rule_id'],
            ['__count']))
        for rule in self:
            rule.document_count = counts.get(rule, 0)

    def _delta(self):
        self.ensure_one()
        return {'year': relativedelta(years=self.duration),
                'month': relativedelta(months=self.duration),
                'day': timedelta(days=self.duration)}[self.duration_unit]

    def matches(self, document):
        """La règle couvre-t-elle ce document ?"""
        self.ensure_one()
        if self.document_type_ids and document.type_id not in self.document_type_ids:
            return False
        if self.folder_ids:
            folder = document.folder_id
            branch = set()
            while folder:
                branch.add(folder.id)
                folder = folder.parent_id
            if not (branch & set(self.folder_ids.ids)):
                return False
        if self.confidentiality_ids and \
                document.confidentiality_id not in self.confidentiality_ids:
            return False
        return True

    def action_view_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_document.action_aite_ecm_document')
        action['domain'] = [('retention_rule_id', '=', self.id)]
        return action

    def action_apply_now(self):
        """Recalcule la règle sur tout le fonds (bouton)."""
        self.ensure_one()
        count = self.env['aite.ecm.document']._retention_recompute()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _("Conservation"), 'type': 'success',
                           'message': _("%d document(s) réévalué(s).") % count}}


class AiteEcmLegalHold(models.Model):
    """Gel juridique : tant qu'il est actif, aucun document visé ne peut être
    détruit, ni mis à la corbeille, ni modifié."""

    _name = 'aite.ecm.legal.hold'
    _description = "Gel juridique"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="Objet", required=True, tracking=True)
    reference = fields.Char(string="Référence du dossier (litige, audit)")
    state = fields.Selection(
        selection=[('draft', "Brouillon"), ('active', "Actif"),
                   ('lifted', "Levé")],
        default='draft', required=True, tracking=True)
    requested_by = fields.Char(string="À la demande de", tracking=True)
    responsible_id = fields.Many2one(
        comodel_name='res.users', string="Responsable", tracking=True,
        default=lambda self: self.env.user)
    date_start = fields.Date(string="Posé le", readonly=True, copy=False)
    date_end = fields.Date(string="Levé le", readonly=True, copy=False)
    reason = fields.Text(string="Motif", tracking=True)
    lift_reason = fields.Text(string="Motif de la levée", readonly=True)
    document_ids = fields.Many2many(
        comodel_name='aite.ecm.document',
        relation='aite_ecm_legal_hold_document_rel',
        column1='hold_id', column2='document_id', string="Documents gelés")
    folder_ids = fields.Many2many(
        comodel_name='aite.ecm.folder', string="Dossiers gelés",
        help="Tous les documents de ces dossiers et de leurs sous-dossiers.")
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('document_ids', 'folder_ids')
    def _compute_document_count(self):
        for hold in self:
            hold.document_count = len(hold._all_documents())

    def _all_documents(self):
        self.ensure_one()
        docs = self.document_ids
        if self.folder_ids:
            docs |= self.env['aite.ecm.document'].search(
                [('folder_id', 'child_of', self.folder_ids.ids)])
        return docs

    def _is_manager(self):
        return self.env.user._is_superuser() or self.env.user.has_group(
            'aite_courrier_base.group_manager') or self.env.user.has_group(
            'aite_courrier_base.group_admin')

    def action_activate(self):
        for hold in self:
            if not hold._is_manager():
                raise AccessError(_("Seul un manager peut poser un gel."))
            if not hold._all_documents():
                raise UserError(_("Aucun document visé par ce gel."))
            hold.write({'state': 'active',
                        'date_start': fields.Date.context_today(self)})
            docs = hold._all_documents()
            docs._retention_recompute_ids()
            hold.message_post(body=_("Gel posé sur %d document(s).") % len(docs))
            for doc in docs:
                doc._audit(doc, _("Gel juridique posé"), 'warn', hold.name)
        return True

    def action_lift(self):
        for hold in self:
            if not hold._is_manager():
                raise AccessError(_("Seul un manager peut lever un gel."))
            if not hold.lift_reason:
                raise UserError(_("Indiquez le motif de la levée."))
            docs = hold._all_documents()
            hold.write({'state': 'lifted',
                        'date_end': fields.Date.context_today(self)})
            docs._retention_recompute_ids()
            hold.message_post(body=_("Gel levé : %s") % hold.lift_reason)
            for doc in docs:
                doc._audit(doc, _("Gel juridique levé"), 'ok', hold.lift_reason)
        return True

    def action_view_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_document.action_aite_ecm_document')
        action['domain'] = [('id', 'in', self._all_documents().ids)]
        return action


class AiteEcmDisposition(models.Model):
    """Bordereau d'élimination : la liste des documents à détruire, validée
    puis exécutée ; le bordereau reste comme preuve."""

    _name = 'aite.ecm.disposition'
    _description = "Bordereau d'élimination"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="Référence", readonly=True, copy=False,
                       default=lambda self: _("Nouveau"))
    state = fields.Selection(
        selection=[('draft', "Projet"), ('to_approve', "À valider"),
                   ('approved', "Validé"), ('done', "Exécuté"),
                   ('cancel', "Annulé")],
        default='draft', required=True, tracking=True)
    date = fields.Date(string="Date du bordereau",
                       default=fields.Date.context_today, required=True)
    prepared_by = fields.Many2one(
        comodel_name='res.users', string="Préparé par",
        default=lambda self: self.env.user, readonly=True)
    approved_by = fields.Many2one(comodel_name='res.users',
                                  string="Validé par", readonly=True)
    approval_date = fields.Datetime(readonly=True)
    executed_date = fields.Datetime(string="Exécuté le", readonly=True)
    note = fields.Text(string="Observations")
    line_ids = fields.One2many(
        comodel_name='aite.ecm.disposition.line', inverse_name='disposition_id',
        string="Documents")
    line_count = fields.Integer(compute='_compute_line_count', store=True)
    certificate_document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Certificat de destruction",
        readonly=True, copy=False)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for slip in self:
            slip.line_count = len(slip.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _("Nouveau"):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'aite.ecm.disposition') or _("Nouveau")
        return super().create(vals_list)

    def _is_manager(self):
        return self.env.user._is_superuser() or self.env.user.has_group(
            'aite_courrier_base.group_manager') or self.env.user.has_group(
            'aite_courrier_base.group_admin')

    def action_collect(self):
        """Rassemble les documents échus dont le sort final est l'élimination."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Le bordereau n'est plus modifiable."))
        docs = self.env['aite.ecm.document'].sudo().search([
            ('retention_state', '=', 'expired'),
            ('final_fate', '=', 'destroy'),
            ('legal_hold_active', '=', False),
            ('disposition_line_ids', '=', False)])
        self.line_ids.unlink()
        self.write({'line_ids': [(0, 0, {
            'document_id': doc.id, 'reference': doc.reference,
            'title': doc.name, 'folder': doc.folder_id.complete_name or '',
            'retention_rule': doc.retention_rule_id.name or '',
            'retention_deadline': doc.retention_deadline,
        }) for doc in docs]})
        return len(docs)

    def action_submit(self):
        for slip in self:
            if not slip.line_ids:
                raise UserError(_("Le bordereau est vide."))
            slip.write({'state': 'to_approve'})
        return True

    def action_approve(self):
        for slip in self:
            if not slip._is_manager():
                raise AccessError(_("Seul un manager valide un bordereau."))
            slip.write({'state': 'approved', 'approved_by': self.env.user.id,
                        'approval_date': fields.Datetime.now()})
            slip.message_post(body=_("Bordereau validé : %d document(s).")
                              % len(slip.line_ids))
        return True

    def action_execute(self):
        """Élimination effective : les documents sont supprimés, le bordereau
        et le certificat conservent la trace."""
        for slip in self:
            if slip.state != 'approved':
                raise UserError(_("Le bordereau doit être validé."))
            if not slip._is_manager():
                raise AccessError(_("Seul un manager exécute un bordereau."))
            held = slip.line_ids.filtered(
                lambda l: l.document_id and l.document_id.legal_hold_active)
            if held:
                raise UserError(_(
                    "Gel juridique actif sur %d document(s) : retirez-les du "
                    "bordereau avant exécution.") % len(held))
            for line in slip.line_ids:
                doc = line.document_id
                if not doc:
                    continue
                doc._audit(doc, _("Élimination (bordereau %s)") % slip.name,
                           'warn', line.retention_rule or '')
                line.write({'destroyed': True,
                            'sha256': doc.latest_version_id.sha256 or ''})
                doc.sudo().with_context(disposition=True).unlink()
            slip.write({'state': 'done',
                        'executed_date': fields.Datetime.now()})
            slip._create_certificate()
        return True

    def _create_certificate(self):
        """Dépose le bordereau exécuté comme document ECM (preuve)."""
        self.ensure_one()
        content = self.env['ir.actions.report']._render_qweb_pdf(
            'aite_ecm_records.report_disposition', self.ids)[0] \
            if self.env.ref('aite_ecm_records.report_disposition',
                            raise_if_not_found=False) else None
        if not content:
            return False
        import base64
        folder = self.env.ref('aite_ecm_records.folder_records',
                              raise_if_not_found=False)
        doc = self.env['aite.ecm.document'].sudo().create({
            'name': _("Certificat de destruction %s") % self.name,
            'folder_id': folder.id if folder else False,
            'description': _("Bordereau %s exécuté le %s") % (
                self.name, self.executed_date)})
        doc.add_version("%s.pdf" % self.name, base64.b64encode(content))
        doc.action_mark_final()
        self.write({'certificate_document_id': doc.id})
        return doc

    def action_cancel(self):
        self.filtered(lambda s: s.state != 'done').write({'state': 'cancel'})
        return True


class AiteEcmDispositionLine(models.Model):
    """Ligne de bordereau : conserve l'identité du document même après
    destruction (référence, titre, dossier, empreinte)."""

    _name = 'aite.ecm.disposition.line'
    _description = "Ligne de bordereau d'élimination"

    disposition_id = fields.Many2one(
        comodel_name='aite.ecm.disposition', required=True, ondelete='cascade')
    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document",
        ondelete='set null')
    reference = fields.Char(string="Référence", required=True)
    title = fields.Char(string="Titre")
    folder = fields.Char(string="Dossier")
    retention_rule = fields.Char(string="Règle appliquée")
    retention_deadline = fields.Date(string="Échéance")
    sha256 = fields.Char(string="Empreinte au moment de la destruction")
    destroyed = fields.Boolean(string="Détruit", readonly=True)


class AiteEcmBox(models.Model):
    """Boîte d'archives physiques : le lien entre le document numérique et
    son exemplaire papier."""

    _name = 'aite.ecm.box'
    _description = "Boîte d'archives"
    _order = 'code'

    code = fields.Char(string="Code", required=True, copy=False,
                       default=lambda self: _("Nouvelle"))
    name = fields.Char(string="Libellé", required=True)
    location = fields.Char(string="Emplacement",
                           help="Salle, travée, étagère…")
    state = fields.Selection(
        selection=[('open', "En constitution"), ('stored', "Rangée"),
                   ('lent', "Sortie (prêt)"), ('destroyed', "Détruite")],
        default='open', required=True)
    borrower_id = fields.Many2one(comodel_name='res.users',
                                  string="Emprunteur")
    borrow_date = fields.Date(string="Sortie le")
    return_due = fields.Date(string="Retour prévu")
    note = fields.Text()
    document_ids = fields.One2many(
        comodel_name='aite.ecm.document', inverse_name='box_id',
        string="Documents")
    document_count = fields.Integer(compute='_compute_document_count')

    _sql_constraints = [('code_uniq', 'unique(code)',
                         "Ce code de boîte existe déjà.")]

    @api.depends('document_ids')
    def _compute_document_count(self):
        for box in self:
            box.document_count = len(box.document_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals['code'] == _("Nouvelle"):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'aite.ecm.box') or _("Nouvelle")
        return super().create(vals_list)

    def action_store(self):
        self.write({'state': 'stored', 'borrower_id': False,
                    'borrow_date': False, 'return_due': False})
        return True

    def action_lend(self):
        for box in self:
            box.write({'state': 'lent', 'borrower_id': self.env.user.id,
                       'borrow_date': fields.Date.context_today(self),
                       'return_due': fields.Date.context_today(self)
                       + timedelta(days=30)})
        return True
