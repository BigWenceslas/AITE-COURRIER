# -*- coding: utf-8 -*-
"""Le document ECM vu par le records management : règle applicable, échéance,
cycle de vie archivistique, gel juridique et protection contre la destruction.
"""
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RETENTION_STATES = [
    ('none', "Sans politique"),
    ('current', "Utilité courante"),
    ('intermediate', "Archive intermédiaire"),
    ('expired', "Échue — sort final à appliquer"),
    ('permanent', "Conservation définitive"),
    ('disposed', "Éliminée"),
]


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    retention_rule_id = fields.Many2one(
        comodel_name='aite.ecm.retention.rule', string="Règle de conservation",
        readonly=True, index=True,
        help="Déterminée automatiquement d'après le type, le dossier et la "
             "confidentialité ; forcée si « Règle imposée » est renseignée.")
    retention_rule_forced_id = fields.Many2one(
        comodel_name='aite.ecm.retention.rule', string="Règle imposée",
        help="Choisir une règle ici l'emporte sur la détermination "
             "automatique.")
    retention_start = fields.Date(string="Départ de la conservation",
                                  readonly=True)
    retention_deadline = fields.Date(string="Échéance de conservation",
                                     readonly=True, index=True)
    retention_state = fields.Selection(
        selection=RETENTION_STATES, string="Cycle de vie archivistique",
        default='none', readonly=True, index=True)
    final_fate = fields.Selection(
        selection=[('destroy', "Élimination"),
                   ('keep', "Conservation définitive"),
                   ('review', "Revue avant décision")],
        string="Sort final", readonly=True)
    retention_note = fields.Char(string="Précision", readonly=True)
    legal_hold_ids = fields.Many2many(
        comodel_name='aite.ecm.legal.hold',
        relation='aite_ecm_legal_hold_document_rel',
        column1='document_id', column2='hold_id', string="Gels juridiques")
    legal_hold_active = fields.Boolean(
        string="Sous gel juridique", compute='_compute_legal_hold',
        store=True, index=True)
    legal_hold_names = fields.Char(compute='_compute_legal_hold')
    disposition_line_ids = fields.One2many(
        comodel_name='aite.ecm.disposition.line', inverse_name='document_id',
        string="Bordereaux")
    box_id = fields.Many2one(comodel_name='aite.ecm.box',
                             string="Boîte d'archives physique")
    paper_original = fields.Boolean(
        string="Original papier conservé",
        help="Cochez si l'exemplaire papier fait foi et doit être conservé.")
    personal_data = fields.Boolean(
        string="Contient des données personnelles",
        help="Signale les documents soumis à une purge à échéance et au "
             "registre des traitements.")

    # ================================================================== #
    # Gel juridique
    # ================================================================== #
    @api.depends('legal_hold_ids.state', 'folder_id')
    def _compute_legal_hold(self):
        Hold = self.env['aite.ecm.legal.hold'].sudo()
        active_holds = Hold.search([('state', '=', 'active')])
        by_folder = {}
        for hold in active_holds:
            for folder in hold.folder_ids:
                by_folder.setdefault(folder.id, self.env['aite.ecm.legal.hold'])
                by_folder[folder.id] |= hold
        for doc in self:
            holds = doc.legal_hold_ids.filtered(lambda h: h.state == 'active')
            folder = doc.folder_id
            while folder:
                holds |= by_folder.get(folder.id, Hold.browse())
                folder = folder.parent_id
            doc.legal_hold_active = bool(holds)
            doc.legal_hold_names = ", ".join(holds.mapped('name'))

    # ================================================================== #
    # Détermination de la règle et de l'échéance
    # ================================================================== #
    def _retention_find_rule(self):
        self.ensure_one()
        if self.retention_rule_forced_id:
            return self.retention_rule_forced_id
        rules = self.env['aite.ecm.retention.rule'].sudo().search(
            [], order='sequence, id')
        for rule in rules:
            if rule.matches(self):
                return rule
        return self.env['aite.ecm.retention.rule']

    def _retention_start_date(self, rule):
        """Date de départ selon le déclencheur de la règle."""
        self.ensure_one()
        if rule.trigger == 'create':
            return fields.Date.to_date(self.create_date)
        if rule.trigger == 'final':
            return fields.Date.to_date(self.write_date) \
                if self.state in ('final', 'archived') else False
        if rule.trigger == 'archive':
            return fields.Date.to_date(self.write_date) \
                if self.state == 'archived' else False
        if rule.trigger == 'close':
            if self.res_model and self.res_id:
                record = self.env[self.res_model].sudo().browse(self.res_id)
                for field_name in ('date_done', 'date_close', 'date_archived'):
                    if field_name in record._fields and record[field_name]:
                        return fields.Date.to_date(record[field_name])
            return fields.Date.to_date(self.write_date) \
                if self.state == 'archived' else False
        if rule.trigger == 'meta':
            value = (self.properties or {})
            if isinstance(value, list):     # format liste de définitions
                value = {p.get('name'): p.get('value') for p in value
                         if isinstance(p, dict)}
            raw = value.get(rule.trigger_property) if isinstance(value, dict) \
                else False
            return fields.Date.to_date(raw) if raw else False
        return False

    def _retention_compute(self):
        """Applique la politique à ces documents (silencieux, idempotent)."""
        today = fields.Date.context_today(self)
        for doc in self:
            rule = doc._retention_find_rule()
            if not rule:
                doc.sudo().write({
                    'retention_rule_id': False, 'retention_start': False,
                    'retention_deadline': False, 'final_fate': False,
                    'retention_state': 'none',
                    'retention_note': _("Aucune règle applicable")})
                continue
            start = doc._retention_start_date(rule)
            vals = {'retention_rule_id': rule.id, 'final_fate': rule.final_fate,
                    'retention_start': start}
            if not start:
                vals.update({'retention_deadline': False,
                             'retention_state': 'current',
                             'retention_note': _(
                                 "En attente du déclencheur : %s")
                             % dict(rule._fields['trigger'].selection).get(
                                 rule.trigger)})
                doc.sudo().write(vals)
                continue
            deadline = start + rule._delta()
            vals['retention_deadline'] = deadline
            if doc.legal_hold_active:
                state = 'intermediate'
                note = _("Gel juridique : %s") % doc.legal_hold_names
            elif rule.final_fate == 'keep' and deadline <= today:
                state, note = 'permanent', _("Conservation définitive")
            elif deadline <= today:
                state = 'expired'
                note = _("Échue le %s — sort final : %s") % (
                    deadline, dict(rule._fields['final_fate'].selection).get(
                        rule.final_fate))
            elif doc.state == 'archived':
                state, note = 'intermediate', _("Archive intermédiaire")
            else:
                state, note = 'current', _("Utilité courante")
            vals.update({'retention_state': state, 'retention_note': note})
            doc.sudo().write(vals)
        return True

    def _retention_recompute_ids(self):
        return self._retention_compute()

    @api.model
    def _retention_recompute(self, limit=None):
        docs = self.sudo().search([], limit=limit)
        docs._retention_compute()
        return len(docs)

    @api.model
    def _cron_retention(self):
        """Recalcule la politique et signale les échéances (quotidien)."""
        count = self._retention_recompute()
        expired = self.sudo().search([('retention_state', '=', 'expired'),
                                      ('legal_hold_active', '=', False)])
        to_review = expired.filtered(lambda d: d.final_fate == 'review')
        for doc in to_review:
            user = doc.retention_rule_id.review_user_id or doc.owner_id
            if not user or doc.activity_ids.filtered(
                    lambda a: a.summary and a.summary.startswith("[Conservation]")):
                continue
            doc.sudo().activity_schedule(
                'mail.mail_activity_data_todo', user_id=user.id,
                summary=_("[Conservation] Revue de %s") % doc.reference,
                note=_("La durée de conservation est échue (%s). Décidez du "
                       "sort final : conserver, éliminer ou prolonger.")
                % doc.retention_deadline)
        _logger.info("[records] %d documents évalués, %d échus, %d en revue",
                     count, len(expired), len(to_review))
        return True

    # ================================================================== #
    # Décisions manuelles
    # ================================================================== #
    def _records_manager(self):
        return self.env.user._is_superuser() or self.env.user.has_group(
            'aite_courrier_base.group_archive') or self.env.user.has_group(
            'aite_courrier_base.group_manager') or self.env.user.has_group(
            'aite_courrier_base.group_admin')

    def action_retention_keep(self):
        """Décider la conservation définitive."""
        if not self._records_manager():
            raise UserError(_("Réservé aux archivistes et managers."))
        for doc in self:
            doc.sudo().write({'retention_state': 'permanent',
                              'final_fate': 'keep',
                              'retention_note': _("Conservation définitive "
                                                  "décidée par %s")
                              % self.env.user.name})
            doc._audit(doc, _("Conservation définitive"), 'ok', '')
        return True

    def action_retention_extend(self):
        """Prolonger d'un an (décision motivée par l'activité en cours)."""
        if not self._records_manager():
            raise UserError(_("Réservé aux archivistes et managers."))
        for doc in self:
            if not doc.retention_deadline:
                continue
            new_deadline = doc.retention_deadline + relativedelta(years=1)
            doc.sudo().write({'retention_deadline': new_deadline,
                              'retention_state': 'intermediate',
                              'retention_note': _("Prolongée jusqu'au %s par %s")
                              % (new_deadline, self.env.user.name)})
            doc._audit(doc, _("Conservation prolongée"), 'warn',
                       str(new_deadline))
        return True

    def action_view_legal_holds(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'name': _("Gels juridiques — %s") % self.reference,
                'res_model': 'aite.ecm.legal.hold', 'view_mode': 'list,form',
                'domain': [('id', 'in', self.legal_hold_ids.ids)]}

    # ================================================================== #
    # Protections
    # ================================================================== #
    def write(self, vals):
        if not self.env.context.get('records_bypass'):
            protected = set(vals) - {'legal_hold_ids', 'retention_rule_id',
                                     'retention_start', 'retention_deadline',
                                     'retention_state', 'final_fate',
                                     'retention_note', 'legal_hold_active',
                                     'box_id', 'message_ids', 'activity_ids',
                                     'message_follower_ids'}
            if protected:
                held = self.filtered('legal_hold_active')
                if held:
                    raise UserError(_(
                        "Gel juridique actif (%s) : le document « %s » ne peut "
                        "pas être modifié.",
                        held[0].legal_hold_names, held[0].name))
        return super().write(vals)

    def action_trash(self):
        held = self.filtered('legal_hold_active')
        if held:
            raise UserError(_(
                "Gel juridique actif (%s) : impossible de mettre « %s » à la "
                "corbeille.", held[0].legal_hold_names, held[0].name))
        return super().action_trash()

    def unlink(self):
        held = self.filtered('legal_hold_active')
        if held:
            raise UserError(_(
                "Gel juridique actif : suppression impossible (%s).",
                ", ".join(held.mapped('reference'))))
        if not self.env.context.get('disposition'):
            kept = self.filtered(
                lambda d: d.retention_state in ('current', 'intermediate',
                                                'permanent'))
            if kept and not self.env.context.get('force_unlink'):
                raise UserError(_(
                    "Ces documents sont sous politique de conservation : "
                    "passez par un bordereau d'élimination (%s).",
                    ", ".join(kept[:5].mapped('reference'))))
        return super().unlink()

    @api.model
    def _cron_purge_trash(self):
        """La purge automatique de la corbeille épargne les documents gelés
        ou encore sous conservation."""
        protected = self.with_context(active_test=False).sudo().search([
            ('active', '=', False), '|',
            ('legal_hold_active', '=', True),
            ('retention_state', 'in', ('current', 'intermediate', 'permanent'))])
        if protected:
            return super(AiteEcmDocument, self.with_context(
                purge_skip_ids=protected.ids))._cron_purge_trash()
        return super()._cron_purge_trash()

    # ================================================================== #
    # Recalcul au fil de l'eau
    # ================================================================== #
    @api.model_create_multi
    def create(self, vals_list):
        docs = super().create(vals_list)
        docs._retention_compute()
        return docs

    def _explorer_record(self):
        rec = super()._explorer_record()
        rec.update({
            'retention_state': self.retention_state,
            'retention_deadline': fields.Date.to_string(self.retention_deadline)
            if self.retention_deadline else False,
            'legal_hold': self.legal_hold_active,
        })
        return rec
