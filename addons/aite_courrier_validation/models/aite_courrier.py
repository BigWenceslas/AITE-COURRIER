# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AiteCourrier(models.Model):
    """Exécution des transitions du workflow sur le courrier.

    Toutes les actions vérifient l'habilitation **côté serveur**
    (``can_user_act`` du Sprint 02) avant d'agir. Le contrôle de rôle/users
    pilote l'action ; la modification du courrier elle-même est faite en
    ``sudo`` (l'utilisateur opérationnel n'a pas forcément le droit ORM
    d'écrire le courrier), tout en conservant son identité dans l'audit.
    """

    _inherit = 'aite.courrier'

    available_transition_ids = fields.Many2many(
        comodel_name='aite.workflow.transition',
        string="Actions disponibles",
        compute='_compute_available_transitions',
    )
    can_act = fields.Boolean(
        string="Peut agir", compute='_compute_available_transitions')

    @api.depends('current_step_id', 'state')
    def _compute_available_transitions(self):
        for courrier in self:
            can_act = courrier._user_can_act(self.env.user)
            courrier.can_act = can_act
            if can_act and courrier.current_step_id:
                courrier.available_transition_ids = \
                    courrier.current_step_id.outgoing_transition_ids
            else:
                courrier.available_transition_ids = False

    # ------------------------------------------------------------------ #
    # Habilitation
    # ------------------------------------------------------------------ #
    def _user_can_act(self, user):
        """Vrai si ``user`` peut agir sur l'étape courante.

        Le superutilisateur (scripts, OdooBot) court-circuite le contrôle ;
        sinon on applique la règle role_ids/user_ids de l'étape courante.
        Un courrier archivé ou rejeté n'autorise aucune action.
        """
        self.ensure_one()
        if self.state in ('ar', 'rj') or not self.current_step_id:
            return False
        if user._is_superuser():
            return True
        return self.current_step_id.can_user_act(user)

    # ------------------------------------------------------------------ #
    # Traçage / notification
    # ------------------------------------------------------------------ #
    def _audit_action(self, action, action_type, detail=False):
        self.ensure_one()
        self.env['aite.courrier.audit.log']._log(
            self.env, action, action_type, 'aite.courrier', self.id,
            self.reference or self.display_name, detail or '', 'ui')

    def _notify_action(self, action_label, comment, user):
        """Poste un message signé et horodaté (JJ/MM HHhMM) dans l'historique."""
        self.ensure_one()
        local_dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        stamp = local_dt.strftime("%d/%m %Hh%M")
        body = Markup("<p><b>%s</b><br/><span class='text-muted'>%s &middot; "
                      "%s</span></p>") % (action_label, user.name, stamp)
        if comment:
            body += Markup("<p>%s</p>") % comment
        self.sudo().message_post(body=body, author_id=user.partner_id.id)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _as_transition(self, transition):
        if isinstance(transition, int):
            return self.env['aite.workflow.transition'].browse(transition)
        return transition

    def do_transition(self, transition, comment=False):
        """VALIDER (forward) ou RETOURNER (backward) via une transition sortante.

        Vérifie l'habilitation et l'éventuel commentaire obligatoire, déplace le
        courrier (``_enter_step``), notifie et trace l'audit (``ok`` en avant,
        ``warn`` en arrière). L'arrivée sur une étape finale archive le courrier
        (géré par ``_enter_step``).
        """
        self.ensure_one()
        transition = self._as_transition(transition)
        user = self.env.user
        if self.state in ('ar', 'rj'):
            raise UserError(_(
                "Aucune action n'est possible : le courrier est « %s ».",
                dict(self._fields['state'].selection).get(self.state, self.state)))
        if not self.current_step_id or \
                transition not in self.current_step_id.outgoing_transition_ids:
            raise UserError(_(
                "Cette transition n'est pas disponible depuis l'étape courante."))
        if not self._user_can_act(user):
            self._audit_action(_("Tentative non autorisée"), 'err',
                               _("Action « %s » refusée.") % transition.label)
            raise AccessError(_(
                "Vous n'êtes pas autorisé à effectuer cette action sur cette "
                "étape."))
        if transition.comment_required and not (comment and comment.strip()):
            self._audit_action(_("Action bloquée"), 'err',
                               _("Commentaire manquant pour « %s ».") % transition.label)
            raise UserError(_("Commentaire obligatoire pour cette action"))
        target = transition.step_to_id
        self.sudo()._enter_step(target, transition, comment, user)
        self._notify_action("%s — %s" % (transition.label, target.name),
                            comment, user)
        self._audit_action(
            transition.label, 'ok' if transition.direction == 'forward' else 'warn',
            _("Vers l'étape « %s ».") % target.name)
        return True

    def action_reject(self, comment=False):
        """REJETER : passe le courrier en état rejeté (rj), sans l'archiver.

        Un commentaire (motif) est obligatoire. L'étape courante est conservée
        (repère du point de rejet) et le courrier reste consultable.
        """
        self.ensure_one()
        user = self.env.user
        if self.state in ('ar', 'rj'):
            raise UserError(_("Le courrier est déjà clôturé."))
        if not self._user_can_act(user):
            self._audit_action(_("Tentative non autorisée"), 'err',
                               _("Rejet refusé."))
            raise AccessError(_("Vous n'êtes pas autorisé à rejeter ce courrier."))
        if not (comment and comment.strip()):
            self._audit_action(_("Action bloquée"), 'err', _("Rejet sans motif."))
            raise UserError(_("Commentaire obligatoire pour cette action"))
        self.sudo().with_context(skip_courrier_audit=True).write({'state': 'rj'})
        self._notify_action(_("Rejeté"), comment, user)
        self._audit_action(_("Rejet"), 'warn', comment)
        return True

    def action_post_comment(self, body):
        """COMMENTER : ajoute un message à l'historique sans changer l'étape."""
        self.ensure_one()
        if not (body and body.strip()):
            raise UserError(_("Le commentaire ne peut pas être vide."))
        self._notify_action(_("Commentaire"), body, self.env.user)
        self._audit_action(_("Commentaire"), 'info', body)
        return True

    # ------------------------------------------------------------------ #
    # Ouverture de l'assistant (UI)
    # ------------------------------------------------------------------ #
    def _open_action_wizard(self, kind):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Action sur le courrier"),
            'res_model': 'aite.courrier.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_courrier_id': self.id, 'default_kind': kind},
        }

    def action_wizard_validate(self):
        return self._open_action_wizard('validate')

    def action_wizard_reject(self):
        return self._open_action_wizard('reject')

    def action_wizard_comment(self):
        return self._open_action_wizard('comment')
