# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AiteWorkflowMixin(models.AbstractModel):
    """Runtime générique d'un circuit sur n'importe quel modèle.

    Le modèle concret doit :

    * hériter de ``mail.thread`` et ``mail.activity.mixin`` (notifications) ;
    * implémenter :meth:`_wf_find_circuit` (quel circuit s'applique) ;
    * exposer les boutons d'action (``action_wf_launch``, assistant de
      transition, ``action_wf_reject``).

    Les habilitations sont celles des étapes (``step.can_user_act``), les
    managers court-circuitent, le contrôle est **serveur**.
    """

    _name = 'aite.workflow.mixin'
    _description = "Mixin circuit de validation"

    wf_circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit', string="Circuit",
        copy=False, readonly=True, ondelete='restrict')
    wf_step_id = fields.Many2one(
        comodel_name='aite.workflow.step', string="Étape courante",
        copy=False, readonly=True, ondelete='restrict', tracking=True)
    wf_status = fields.Selection(
        selection=[('none', "Non lancé"), ('running', "En cours"),
                   ('done', "Terminé"), ('rejected', "Rejeté")],
        string="Circuit — statut", default='none', copy=False, tracking=True)
    wf_deadline = fields.Datetime(string="Échéance SLA", copy=False,
                                  readonly=True)
    wf_is_overdue = fields.Boolean(
        string="En retard", compute='_compute_wf_is_overdue',
        search='_search_wf_is_overdue')
    wf_reject_reason = fields.Text(string="Motif de rejet", copy=False,
                                   readonly=True)
    wf_history_ids = fields.One2many(
        comodel_name='aite.workflow.history', inverse_name='res_id',
        string="Historique du circuit",
        domain=lambda self: [('res_model', '=', self._name)])
    wf_transition_ids = fields.Many2many(
        comodel_name='aite.workflow.transition',
        string="Transitions disponibles", compute='_compute_wf_transitions')
    wf_can_act = fields.Boolean(string="Je peux agir",
                                compute='_compute_wf_transitions')

    # ------------------------------------------------------------------ #
    # Calculs
    # ------------------------------------------------------------------ #
    @api.depends('wf_deadline', 'wf_status')
    def _compute_wf_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.wf_is_overdue = bool(
                rec.wf_status == 'running' and rec.wf_deadline
                and rec.wf_deadline < now)

    def _search_wf_is_overdue(self, operator, value):
        now = fields.Datetime.now()
        overdue = [('wf_status', '=', 'running'),
                   ('wf_deadline', '!=', False), ('wf_deadline', '<', now)]
        truthy = (operator == '=' and value) or (operator == '!=' and not value)
        if truthy:
            return overdue
        return ['|', '|', ('wf_status', '!=', 'running'),
                ('wf_deadline', '=', False), ('wf_deadline', '>=', now)]

    @api.depends('wf_step_id', 'wf_status')
    def _compute_wf_transitions(self):
        user = self.env.user
        for rec in self:
            step = rec.wf_step_id
            if rec.wf_status != 'running' or not step:
                rec.wf_transition_ids = False
                rec.wf_can_act = False
                continue
            rec.wf_transition_ids = step.outgoing_transitions()
            rec.wf_can_act = rec._wf_user_can_act(step, user)

    # ------------------------------------------------------------------ #
    # Points d'accroche
    # ------------------------------------------------------------------ #
    def _wf_find_circuit(self):
        """Circuit applicable à l'enregistrement (à implémenter)."""
        raise NotImplementedError(
            "%s doit implémenter _wf_find_circuit()." % self._name)

    def _wf_reference(self):
        self.ensure_one()
        return self.display_name

    def _wf_on_finished(self):
        """Appelé à l'arrivée sur l'étape finale (surcharge libre)."""
        return True

    # ------------------------------------------------------------------ #
    # Habilitations
    # ------------------------------------------------------------------ #
    def _wf_is_manager(self, user=None):
        user = user or self.env.user
        return user._is_superuser() or user.has_group(
            'aite_courrier_base.group_manager') or user.has_group(
            'aite_courrier_base.group_admin')

    def _wf_user_can_act(self, step, user=None):
        user = user or self.env.user
        return self._wf_is_manager(user) or step.can_user_act(user)

    def _wf_check_can_act(self, step):
        if not self._wf_user_can_act(step):
            raise AccessError(_(
                "Vous n'êtes pas habilité à agir sur l'étape « %s ».",
                step.name))

    # ------------------------------------------------------------------ #
    # Runtime
    # ------------------------------------------------------------------ #
    def action_wf_launch(self):
        for rec in self:
            if rec.wf_status == 'running':
                raise UserError(_("Le circuit est déjà lancé."))
            circuit = rec._wf_find_circuit()
            if not circuit:
                raise UserError(_(
                    "Aucun circuit actif ne s'applique à « %s ».",
                    rec._wf_reference()))
            initial = circuit.get_initial_step()
            if not initial:
                raise UserError(_(
                    "Le circuit « %s » n'a pas d'étape initiale.",
                    circuit.name))
            rec.write({'wf_circuit_id': circuit.id, 'wf_status': 'running',
                       'wf_reject_reason': False})
            rec._wf_enter_step(initial)
            rec.message_post(body=_(
                "Circuit « %s » lancé — étape « %s ».") % (
                circuit.name, initial.name))
            rec._wf_audit(_("Lancement du circuit"), 'info', circuit.name)
        return True

    def _as_transition(self, transition):
        if isinstance(transition, int):
            transition = self.env['aite.workflow.transition'].browse(transition)
        return transition

    def wf_do_transition(self, transition, comment=False):
        """Applique une transition depuis l'étape courante (contrôle serveur)."""
        self.ensure_one()
        transition = self._as_transition(transition)
        if self.wf_status != 'running':
            raise UserError(_("Le circuit n'est pas en cours."))
        step = self.wf_step_id
        self._wf_check_can_act(step)
        if transition.step_from_id != step:
            raise UserError(_(
                "La transition « %s » ne part pas de l'étape courante.",
                transition.label))
        if transition.comment_required and not (comment or '').strip():
            raise UserError(_(
                "Un commentaire est obligatoire pour « %s ».",
                transition.label))
        self._wf_leave_step(transition, comment)
        target = transition.step_to_id
        self._wf_enter_step(target)
        body = _("%s — %s") % (transition.label, target.name)
        if comment:
            body += "<br/>%s" % comment
        self.message_post(body=body)
        self._wf_audit(_("Transition « %s »") % transition.label, 'ok',
                       _("%s → %s") % (step.name, target.name))
        if target.is_final:
            self.write({'wf_status': 'done'})
            self._wf_on_finished()
        return True

    def action_wf_reject(self, reason):
        self.ensure_one()
        if self.wf_status != 'running':
            raise UserError(_("Le circuit n'est pas en cours."))
        if not (reason or '').strip():
            raise UserError(_("Le motif de rejet est obligatoire."))
        self._wf_check_can_act(self.wf_step_id)
        self._wf_leave_step(None, reason)
        self.write({'wf_status': 'rejected', 'wf_reject_reason': reason,
                    'wf_deadline': False})
        self.message_post(body=_("Rejeté — %s") % reason)
        self._wf_audit(_("Rejet"), 'warn', reason)
        return True

    def action_wf_reset(self):
        """Manager : réinitialise le circuit (retour à « non lancé »)."""
        if not self._wf_is_manager():
            raise AccessError(_("Réservé aux managers."))
        for rec in self:
            rec.write({'wf_circuit_id': False, 'wf_step_id': False,
                       'wf_status': 'none', 'wf_deadline': False})
            rec._wf_audit(_("Réinitialisation du circuit"), 'warn', '')
        return True

    # ------------------------------------------------------------------ #
    # Étapes
    # ------------------------------------------------------------------ #
    def _wf_enter_step(self, step):
        self.ensure_one()
        deadline = (fields.Datetime.now() + timedelta(hours=step.sla_hours)
                    if step.sla_hours else False)
        self.write({'wf_step_id': step.id, 'wf_deadline': deadline})
        self.env['aite.workflow.history'].sudo().create({
            'res_model': self._name, 'res_id': self.id,
            'res_ref': self._wf_reference(), 'circuit_id': self.wf_circuit_id.id,
            'step_id': step.id, 'user_id': self.env.user.id,
        })
        if not step.is_final:
            self._wf_notify_step(step)
        return True

    def _wf_leave_step(self, transition=None, comment=None):
        self.ensure_one()
        current = self.env['aite.workflow.history'].sudo().search([
            ('res_model', '=', self._name), ('res_id', '=', self.id),
            ('left_date', '=', False)], order='id desc', limit=1)
        if current:
            current.write({
                'left_date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'transition_id': transition.id if transition else False,
                'comment': comment or False,
            })
        # Clôture des activités « à faire » de l'étape quittée.
        self.activity_ids.filtered(
            lambda a: a.summary and a.summary.startswith("[Circuit]")
        ).action_feedback(feedback=_("Étape traitée"))
        return True

    def _wf_step_assignees(self, step):
        users = step.user_ids
        if not users and step.role_ids:
            users = self.env['res.users'].search([
                ('groups_id', 'in', step.role_ids.ids), ('share', '=', False)])
        return users

    def _wf_notify_step(self, step):
        self.ensure_one()
        for user in self._wf_step_assignees(step):
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("[Circuit] %s — %s") % (step.name,
                                                  self._wf_reference()),
                note=_("Étape « %s » à traiter.") % step.name,
                user_id=user.id,
                date_deadline=(self.wf_deadline.date()
                               if self.wf_deadline else None))
        return True

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #
    def _wf_audit(self, action, action_type, detail):
        self.env['aite.courrier.audit.log']._log(
            self.env, action, action_type, self._name, self.id,
            self._wf_reference(), detail,
            self.env.context.get('audit_source', 'ui'))

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def action_wf_open_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Action — %s") % self._wf_reference(),
            'res_model': 'aite.workflow.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_res_model': self._name,
                        'default_res_id': self.id},
        }
