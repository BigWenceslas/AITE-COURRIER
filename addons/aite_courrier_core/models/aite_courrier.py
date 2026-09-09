# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AiteCourrier(models.Model):
    """Courrier et son cycle de vie.

    Un courrier naît en brouillon (sans référence ni circuit). Au lancement
    du circuit, il reçoit une référence unique (``COUR-YYYY-NNNN``), une copie
    du circuit actif de son type, se positionne sur l'étape initiale et trace
    sa création. L'exécution des transitions est pilotée par le module
    ``aite_courrier_validation`` ; ce modèle expose pour cela les méthodes
    :meth:`_enter_step` et :meth:`_is_locked`.
    """

    _name = 'aite.courrier'
    _description = "Courrier"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_received desc, id desc'

    # Champs métier dont la modification déclenche un audit et qui sont
    # verrouillés une fois le courrier archivé.
    _BUSINESS_FIELDS = {
        'subject', 'sender', 'sender_partner_id', 'sender_email', 'type_id',
        'department_id', 'priority_id', 'confidentiality_id', 'date_received',
        'responsible_id',
    }

    reference = fields.Char(
        string="Référence", copy=False, readonly=True, index=True, tracking=True,
        help="Identifiant unique COUR-AAAA-NNNN, attribué au lancement du circuit.",
    )
    subject = fields.Char(string="Objet", required=True, tracking=True)
    sender = fields.Char(string="Expéditeur")
    # Lien vers le référentiel de contacts : permet de retrouver en un clic
    # tout l'historique des courriers échangés avec un même tiers (benchmark
    # GEC : « vue 360° des échanges avec un client ou fournisseur »).
    sender_partner_id = fields.Many2one(
        comodel_name='res.partner', string="Contact expéditeur", tracking=True,
        help="Contact associé à l'expéditeur : centralise l'historique des "
             "courriers d'un même tiers.",
    )
    sender_email = fields.Char(
        string="E-mail expéditeur",
        help="Adresse utilisée pour l'accusé de réception automatique "
             "(si le type de courrier l'active).",
    )
    type_id = fields.Many2one(
        comodel_name='aite.courrier.type', string="Type", required=True,
        ondelete='restrict', tracking=True,
    )
    # Catégorie héritée du type (entrant/sortant/interne) : permet de filtrer
    # l'espace courrier par un panneau de sélection.
    category = fields.Selection(
        related='type_id.category', string="Catégorie", store=True, index=True,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department', string="Service destinataire",
        ondelete='restrict', tracking=True,
    )
    priority_id = fields.Many2one(
        comodel_name='aite.courrier.priority', string="Priorité", ondelete='restrict',
    )
    confidentiality_id = fields.Many2one(
        comodel_name='aite.courrier.confidentiality', string="Confidentialité",
        ondelete='restrict',
    )
    date_received = fields.Date(string="Date de réception", default=fields.Date.context_today)
    state = fields.Selection(
        selection=[
            ('draft', "Brouillon"),
            ('nw', "Nouveau"),
            ('pr', "En traitement"),
            ('rj', "Rejeté"),
            ('ar', "Archivé"),
        ],
        string="Statut", default='draft', required=True, tracking=True,
    )
    circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit', string="Circuit", readonly=True,
        copy=False, ondelete='restrict',
        help="Circuit instancié (copié du type) au lancement.",
    )
    current_step_id = fields.Many2one(
        comodel_name='aite.workflow.step', string="Étape courante", readonly=True,
        copy=False, tracking=True, ondelete='restrict',
    )
    current_sla_hours = fields.Integer(
        string="SLA (h)", related='current_step_id.sla_hours', store=True,
        help="SLA de l'étape courante (permet le tri des listes).",
    )
    sla_deadline = fields.Datetime(
        string="Échéance SLA", readonly=True, copy=False,
        help="Échéance de traitement de l'étape courante (entrée + SLA).",
    )
    is_overdue = fields.Boolean(
        string="En retard", compute='_compute_is_overdue',
        search='_search_is_overdue',
        help="Étape courante dont l'échéance SLA est dépassée.",
    )
    # Anti-spam du cron SLA : chaque cycle d'étape ne déclenche qu'UNE relance
    # et qu'UNE escalade (drapeaux remis à zéro à l'entrée d'une étape).
    sla_reminder_sent = fields.Boolean(
        string="Relance SLA envoyée", copy=False, readonly=True,
        help="Une relance a déjà été envoyée aux habilités de l'étape courante.",
    )
    sla_escalated = fields.Boolean(
        string="SLA escaladé", copy=False, readonly=True,
        help="Le retard a déjà été escaladé à la hiérarchie.",
    )
    step_history_ids = fields.One2many(
        comodel_name='aite.courrier.step.history', inverse_name='courrier_id',
        string="Historique des étapes",
    )
    responsible_id = fields.Many2one(
        comodel_name='res.users', string="Responsable", tracking=True,
    )

    # Aperçu (brouillon) : circuit qui sera instancié pour le type choisi.
    preview_circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit', string="Circuit prévu",
        compute='_compute_preview_circuit',
    )
    preview_step_ids = fields.Many2many(
        comodel_name='aite.workflow.step', string="Étapes prévues",
        compute='_compute_preview_circuit',
    )

    _sql_constraints = [
        ('reference_uniq', 'unique(reference)',
         "La référence du courrier doit être unique."),
    ]

    # ------------------------------------------------------------------ #
    # Calculs / affichage
    # ------------------------------------------------------------------ #
    @api.depends('reference', 'subject')
    def _compute_display_name(self):
        for courrier in self:
            if courrier.reference:
                courrier.display_name = courrier.reference
            elif courrier.subject:
                courrier.display_name = "%s (%s)" % (courrier.subject, _("brouillon"))
            else:
                courrier.display_name = _("Nouveau courrier")

    @api.depends('type_id')
    def _compute_preview_circuit(self):
        for courrier in self:
            circuit = courrier._active_circuit_for_type()
            courrier.preview_circuit_id = circuit
            courrier.preview_step_ids = circuit.step_ids

    # ------------------------------------------------------------------ #
    # Contraintes
    # ------------------------------------------------------------------ #
    @api.constrains('subject')
    def _check_subject(self):
        for courrier in self:
            if not courrier.subject:
                raise ValidationError(_("Objet requis"))

    # ------------------------------------------------------------------ #
    # Outils internes
    # ------------------------------------------------------------------ #
    def _active_circuit_for_type(self):
        """Circuit actif rattaché au type du courrier (recordset vide sinon)."""
        Circuit = self.env['aite.workflow.circuit']
        if not self.type_id:
            return Circuit
        return Circuit.search([
            ('type_id', '=', self.type_id.id),
            ('active', '=', True),
        ], limit=1)

    @api.depends('sla_deadline', 'state')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for courrier in self:
            courrier.is_overdue = bool(
                courrier.sla_deadline
                and courrier.state not in ('ar', 'rj')
                and courrier.sla_deadline < now
            )

    def _search_is_overdue(self, operator, value):
        """Rend « En retard » filtrable en liste/recherche (champ non stocké)."""
        now = fields.Datetime.now()
        overdue = [
            ('sla_deadline', '!=', False),
            ('sla_deadline', '<', now),
            ('state', 'not in', ('ar', 'rj')),
        ]
        truthy = (operator == '=' and value) or (operator == '!=' and not value)
        if truthy:
            return overdue
        return ['|', '|',
                ('sla_deadline', '=', False),
                ('sla_deadline', '>=', now),
                ('state', 'in', ('ar', 'rj'))]

    @api.onchange('sender_partner_id')
    def _onchange_sender_partner_id(self):
        """Pré-remplit le nom et l'e-mail de l'expéditeur depuis le contact."""
        for courrier in self:
            if courrier.sender_partner_id:
                if not courrier.sender:
                    courrier.sender = courrier.sender_partner_id.display_name
                if not courrier.sender_email:
                    courrier.sender_email = courrier.sender_partner_id.email

    def _is_locked(self):
        """Le courrier est verrouillé (lecture seule) une fois archivé."""
        self.ensure_one()
        return self.state == 'ar'

    # ------------------------------------------------------------------ #
    # Notifications (activités Odoo + e-mail) à l'arrivée sur une étape
    # ------------------------------------------------------------------ #
    def _step_assignee_users(self, step):
        """Utilisateurs à notifier pour une étape : ``user_ids`` s'il est
        renseigné, sinon tous les membres des rôles (``role_ids``)."""
        if step.user_ids:
            return step.user_ids
        if step.role_ids:
            return self.env['res.users'].search([
                ('groups_id', 'in', step.role_ids.ids),
                ('share', '=', False),
            ])
        return self.env['res.users']

    def _notify_step_assignees(self, step):
        """Programme une activité « À faire » et notifie par message/e-mail les
        utilisateurs censés traiter l'étape courante."""
        self.ensure_one()
        if not step or step.is_final:
            return
        users = self._step_assignee_users(step)
        if not users:
            return
        deadline_date = self.sla_deadline.date() if self.sla_deadline else None
        # sudo : la notification ne doit pas dépendre des droits ORM de
        # l'utilisateur déclencheur (son identité est conservée, su=True).
        courrier = self.sudo()
        for user in users:
            courrier.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=deadline_date,
                summary=_("Courrier %s — étape « %s »") % (
                    self.reference or self.display_name, step.name),
                note=_("Le courrier « %s » attend votre traitement à l'étape "
                       "« %s ».") % (self.subject or '', step.name),
                user_id=user.id,
            )
        courrier.message_post(
            body=_("Courrier arrivé à l'étape « %s » — traitement attendu.") % step.name,
            partner_ids=users.partner_id.ids,
            subtype_xmlid='mail.mt_comment',
        )

    def _set_step_deadline(self, step):
        """Positionne l'échéance SLA d'après le SLA de l'étape (heures)."""
        self.ensure_one()
        if step and step.sla_hours:
            deadline = fields.Datetime.now() + timedelta(hours=step.sla_hours)
        else:
            deadline = False
        # Nouvelle étape = nouveau cycle SLA : les drapeaux de relance /
        # escalade sont réarmés.
        self.with_context(skip_courrier_audit=True).write({
            'sla_deadline': deadline,
            'sla_reminder_sent': False,
            'sla_escalated': False,
        })

    def _check_courrier_access(self, user=None):
        """Indique si ``user`` peut accéder au courrier.

        Logique centralisée (réutilisable, ex. WebDAV) et cohérente avec la
        règle d'enregistrement de confidentialité : un courrier confidentiel ou
        secret n'est visible que par un rôle habilité (manager/admin), le
        responsable, son créateur ou un membre du service destinataire.
        """
        self.ensure_one()
        user = user or self.env.user
        if user._is_superuser() or user.has_group('aite_courrier_base.group_manager'):
            return True
        if self.confidentiality_id.code not in ('CONF', 'SEC'):
            return True
        if self.responsible_id == user or self.create_uid == user:
            return True
        return user in self.department_id.member_ids.mapped('user_id')

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    def action_launch_circuit(self):
        """« Enregistrer et lancer le circuit » : sortie de brouillon."""
        for courrier in self:
            if courrier.state != 'draft':
                continue
            circuit = courrier._active_circuit_for_type()
            if not circuit:
                raise UserError(_(
                    "Aucun circuit actif n'est défini pour le type « %s ».",
                    courrier.type_id.display_name,
                ))
            initial_step = circuit.get_initial_step()
            if not initial_step:
                raise UserError(_(
                    "Le circuit « %s » ne définit pas d'étape initiale.",
                    circuit.display_name,
                ))
            reference = self.env['ir.sequence'].next_by_code('aite.courrier')
            courrier.with_context(skip_courrier_audit=True).write({
                'reference': reference,
                'circuit_id': circuit.id,
                'current_step_id': initial_step.id,
                'state': 'nw',
            })
            self.env['aite.courrier.step.history'].create({
                'courrier_id': courrier.id,
                'step_id': initial_step.id,
                'entered_date': fields.Datetime.now(),
                'user_id': self.env.user.id,
            })
            self.env['aite.courrier.audit.log']._log(
                self.env, _("Création courrier"), 'info', 'aite.courrier',
                courrier.id, courrier.reference,
                _("Lancement du circuit « %s ».") % circuit.display_name, 'ui',
            )
            courrier._set_step_deadline(initial_step)
            courrier._notify_step_assignees(initial_step)
            courrier._send_acknowledgement()
        return True

    def _send_acknowledgement(self):
        """Envoie l'accusé de réception automatique à l'expéditeur.

        Conditions : le type du courrier active l'accusé de réception
        (``send_acknowledgement``) et une adresse e-mail d'expéditeur est
        renseignée. Un échec d'envoi ne bloque JAMAIS le lancement du circuit :
        il est simplement tracé dans le journal d'audit (type ``err``).
        """
        template = self.env.ref(
            'aite_courrier_core.mail_template_courrier_ack',
            raise_if_not_found=False)
        for courrier in self:
            if not template or not courrier.type_id.send_acknowledgement \
                    or not courrier.sender_email:
                continue
            try:
                template.sudo().send_mail(
                    courrier.id,
                    email_values={'email_to': courrier.sender_email})
                self.env['aite.courrier.audit.log']._log(
                    self.env, _("Accusé de réception envoyé"), 'ok',
                    'aite.courrier', courrier.id, courrier.reference,
                    _("Destinataire : %s") % courrier.sender_email, 'system')
            except Exception as exc:  # noqa: BLE001 — l'envoi ne doit pas bloquer
                self.env['aite.courrier.audit.log']._log(
                    self.env, _("Échec accusé de réception"), 'err',
                    'aite.courrier', courrier.id, courrier.reference,
                    str(exc), 'system')
        return True

    # ------------------------------------------------------------------ #
    # SLA : relances et escalade hiérarchique (cron)
    # ------------------------------------------------------------------ #
    def _sla_escalation_users(self):
        """Destinataires de l'escalade : le manager du service destinataire,
        sinon l'ensemble des Managers Courrier (filet de sécurité)."""
        self.ensure_one()
        manager = self.department_id.manager_id.user_id
        if manager:
            return manager
        group = self.env.ref(
            'aite_courrier_base.group_manager', raise_if_not_found=False)
        if group:
            return self.env['res.users'].search([
                ('groups_id', 'in', group.ids), ('share', '=', False),
            ])
        return self.env['res.users']

    @api.model
    def _cron_check_sla_overdue(self):
        """Relance puis escalade les courriers en retard SLA (cron horaire).

        1. **Relance** : dès l'échéance dépassée, notifie UNE fois les
           habilités de l'étape courante (activité + message).
        2. **Escalade** : passé un délai supplémentaire (paramètre système
           ``aite_courrier.sla_escalation_hours``, 24 h par défaut), notifie
           UNE fois la hiérarchie (manager du service, sinon les Managers).
        Les drapeaux sont réarmés à chaque changement d'étape
        (cf. :meth:`_set_step_deadline`).
        """
        now = fields.Datetime.now()
        escalation_hours = int(self.env['ir.config_parameter'].sudo().get_param(
            'aite_courrier.sla_escalation_hours', 24))
        overdue = self.sudo().search([
            ('state', 'not in', ('draft', 'ar', 'rj')),
            ('sla_deadline', '!=', False),
            ('sla_deadline', '<', now),
        ])
        for courrier in overdue:
            step = courrier.current_step_id
            # --- 1. Relance des habilités de l'étape -----------------------
            if not courrier.sla_reminder_sent:
                users = courrier._step_assignee_users(step)
                if users:
                    courrier.message_post(
                        body=_("⏰ Relance SLA : l'échéance de l'étape "
                               "« %s » est dépassée depuis le %s.") % (
                            step.name,
                            fields.Datetime.context_timestamp(
                                courrier, courrier.sla_deadline
                            ).strftime("%d/%m/%Y %Hh%M")),
                        partner_ids=users.partner_id.ids,
                        subtype_xmlid='mail.mt_comment')
                courrier.with_context(skip_courrier_audit=True).write(
                    {'sla_reminder_sent': True})
                self.env['aite.courrier.audit.log']._log(
                    self.env, _("Relance SLA"), 'warn', 'aite.courrier',
                    courrier.id, courrier.reference,
                    _("Étape « %s » en retard — habilités relancés.") % step.name,
                    'system')
            # --- 2. Escalade hiérarchique ----------------------------------
            escalation_due = courrier.sla_deadline + timedelta(
                hours=escalation_hours)
            if not courrier.sla_escalated and escalation_due < now:
                managers = courrier._sla_escalation_users()
                for manager in managers:
                    courrier.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_("Escalade SLA — %s") % (
                            courrier.reference or courrier.display_name),
                        note=_("Le courrier « %s » est bloqué à l'étape "
                               "« %s » au-delà du délai d'escalade "
                               "(%d h après l'échéance SLA).") % (
                            courrier.subject or '', step.name,
                            escalation_hours),
                        user_id=manager.id)
                if managers:
                    courrier.message_post(
                        body=_("🔺 Escalade SLA : retard signalé à la "
                               "hiérarchie (%s).") % ', '.join(
                            managers.mapped('name')),
                        partner_ids=managers.partner_id.ids,
                        subtype_xmlid='mail.mt_comment')
                courrier.with_context(skip_courrier_audit=True).write(
                    {'sla_escalated': True})
                self.env['aite.courrier.audit.log']._log(
                    self.env, _("Escalade SLA"), 'warn', 'aite.courrier',
                    courrier.id, courrier.reference,
                    _("Étape « %s » — hiérarchie notifiée.") % step.name,
                    'system')
        return True

    # ------------------------------------------------------------------ #
    # Historique par expéditeur (vue 360° du tiers)
    # ------------------------------------------------------------------ #
    def action_view_sender_history(self):
        """Ouvre tous les courriers échangés avec le contact expéditeur."""
        self.ensure_one()
        if not self.sender_partner_id:
            raise UserError(_("Aucun contact expéditeur n'est renseigné."))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Courriers — %s") % self.sender_partner_id.display_name,
            'res_model': 'aite.courrier',
            'view_mode': 'list,form',
            'domain': [('sender_partner_id', '=', self.sender_partner_id.id)],
            'context': {'search_default_group_state': 1},
        }

    def _enter_step(self, step, transition=None, comment=False, user=None):
        """Fait entrer le courrier sur ``step`` (appelé par la validation).

        Clôt l'entrée d'historique courante, positionne l'étape, crée la
        nouvelle entrée d'historique et archive le courrier si l'étape est finale.
        """
        self.ensure_one()
        user = user or self.env.user
        now = fields.Datetime.now()
        open_history = self.step_history_ids.filtered(
            lambda h: h.step_id == self.current_step_id and not h.left_date)[:1]
        if open_history:
            open_history.write({
                'left_date': now,
                'comment': comment,
                'transition_label': transition.label if transition else False,
            })
        vals = {'current_step_id': step.id}
        if step.is_final:
            vals['state'] = 'ar'
        elif not step.is_initial and self.state == 'nw':
            # Le courrier a quitté l'étape d'entrée : il est en traitement.
            # Sans cela il restait « Nouveau » jusqu'à l'archivage, ce qui
            # faussait le tableau de bord et le suivi affiché au portail.
            vals['state'] = 'pr'
        self.with_context(skip_courrier_audit=True).write(vals)
        # L'entrée nouvellement créée ne porte PAS de commentaire : le commentaire
        # et la transition appartiennent à l'étape *quittée* (action effectuée),
        # renseignés ci-dessus sur ``open_history``. Les y dupliquer ici les
        # ferait écraser au passage suivant et brouillerait l'historique.
        self.env['aite.courrier.step.history'].create({
            'courrier_id': self.id,
            'step_id': step.id,
            'entered_date': now,
            'user_id': user.id,
        })
        self._set_step_deadline(step)
        self._notify_step_assignees(step)
        return True

    # ------------------------------------------------------------------ #
    # Surcharges ORM : verrouillage + audit
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        # Message explicite avant la contrainte NOT NULL de la base.
        for vals in vals_list:
            if not vals.get('subject'):
                raise ValidationError(_("Objet requis"))
        return super().create(vals_list)

    def write(self, vals):
        skip = self.env.context.get('skip_courrier_audit')
        touched_business = set(vals) & self._BUSINESS_FIELDS
        if not skip and touched_business:
            locked = self.filtered(lambda c: c._is_locked())
            if locked:
                raise UserError(_(
                    "Un courrier archivé est en lecture seule et ne peut plus "
                    "être modifié."
                ))
        res = super().write(vals)
        if not skip and touched_business:
            for courrier in self.filtered(lambda c: c.state != 'draft'):
                self.env['aite.courrier.audit.log']._log(
                    self.env, _("Modification courrier"), 'info', 'aite.courrier',
                    courrier.id, courrier.reference,
                    _("Champs modifiés : %s") % ', '.join(sorted(touched_business)),
                    'ui',
                )
        return res
