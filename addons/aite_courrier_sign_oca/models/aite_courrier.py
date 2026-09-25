# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

# Zone de signature, en POURCENTAGE de la page (sign_oca), y compté depuis le
# haut : équivalent des fractions 0.66 / 0.88 / 0.22 / 0.06 du module Sign.
SIGNATURE_BOX = {'position_x': 66, 'position_y': 88, 'width': 22, 'height': 6}
PENDING_STATES = ('1_draft', '0_sent')


class AiteCourrier(models.Model):
    """Signature électronique du courrier via le module OCA ``sign_oca``.

    * :meth:`action_request_signature` soumet la dernière version PDF au
      responsable du courrier (zone de signature pré-positionnée) ;
    * :meth:`do_transition` est gardée : une étape « Signature requise »
      n'autorise aucune transition en avant tant qu'aucune demande n'a été
      signée **pendant le passage en cours sur l'étape** — un retour sur
      l'étape, ou une seconde étape à signer, exige une nouvelle signature ;
    * à la signature, le PDF signé est versé en nouvelle version GED.
    """

    _inherit = 'aite.courrier'

    sign_oca_request_ids = fields.One2many(
        comodel_name='sign.oca.request', inverse_name='courrier_id',
        string="Demandes de signature",
    )
    # compute_sudo : la garde et le compteur ne dépendent pas des droits
    # Signature de l'utilisateur qui ouvre le courrier.
    sign_request_count = fields.Integer(
        string="Signatures", compute='_compute_sign_requests',
        compute_sudo=True)
    has_completed_signature = fields.Boolean(
        string="Signature complétée", compute='_compute_sign_requests',
        compute_sudo=True,
        help="Une demande de signature a été signée pendant le passage en "
             "cours sur l'étape courante.")
    current_step_require_signature = fields.Boolean(
        related='current_step_id.require_signature', string="Étape à signer")

    @api.depends('sign_oca_request_ids.state',
                 'sign_oca_request_ids.courrier_step_history_id',
                 'current_step_id', 'step_history_ids.left_date')
    def _compute_sign_requests(self):
        all_requests = self._sign_oca_requests()
        for courrier in self:
            requests = all_requests.filtered(
                lambda r: r.courrier_id == courrier._origin)
            visit = courrier._sign_oca_current_visit()
            courrier.sign_request_count = len(requests)
            courrier.has_completed_signature = bool(visit) and any(
                r.state == '2_signed' and r.courrier_step_history_id == visit
                for r in requests)

    def _sign_oca_requests(self, domain=None):
        """Demandes des courriers, cherchées en sudo.

        Pas sign_oca_request_ids : le cache est partagé entre environnements
        et peut contenir la liste lue avec les droits de l'utilisateur, sans
        les demandes qu'il ne voit pas — la garde se tromperait.
        """
        return self.env['sign.oca.request'].sudo().search(
            [('courrier_id', 'in', self._origin.ids)] + (domain or []))

    def _sign_oca_current_visit(self):
        """Entrée d'historique du passage en cours sur l'étape courante
        (cherchée en sudo, comme dans _sign_oca_requests)."""
        self.ensure_one()
        History = self.env['aite.courrier.step.history'].sudo()
        if not (self._origin.id and self.current_step_id):
            return History
        return History.search([
            ('courrier_id', '=', self._origin.id),
            ('step_id', '=', self.current_step_id.id),
            ('left_date', '=', False),
        ], order='entered_date desc, id desc', limit=1)

    # ------------------------------------------------------------------ #
    # Demande de signature
    # ------------------------------------------------------------------ #
    def _signature_source_version(self):
        """Dernière version PDF parmi les documents du courrier."""
        self.ensure_one()
        versions = self.document_ids.mapped('latest_version_id').filtered(
            lambda v: v.file_extension == 'pdf')
        return versions.sorted(
            key=lambda v: (v.upload_date or fields.Datetime.now(), v.id))[-1:]

    def _sign_oca_role(self):
        return self.env.ref('sign_oca.sign_role_employee',
                            raise_if_not_found=False) \
            or self.env['sign.oca.role'].sudo().search([], limit=1)

    def _sign_oca_signature_field(self):
        return self.env.ref('sign_oca.sign_field_signature',
                            raise_if_not_found=False) \
            or self.env['sign.oca.field'].sudo().search(
                [('field_type', '=', 'signature')], limit=1)

    def action_request_signature(self):
        """Soumet la dernière version PDF à la signature du responsable.

        Réservé à qui peut agir sur l'étape courante, si elle est « Signature
        requise ». Une demande encore en attente pour ce courrier est annulée
        et remplacée (changement de responsable, e-mail perdu…).
        """
        self.ensure_one()
        if self.state in ('draft', 'ar', 'rj') \
                or not self.current_step_id.require_signature:
            raise UserError(_(
                "La signature ne se demande que sur une étape « Signature "
                "requise » d'un courrier en cours."))
        if not self._user_can_act(self.env.user):
            self._audit_action(_("Tentative non autorisée"), 'err',
                               _("Demande de signature refusée."))
            raise AccessError(_(
                "Vous n'êtes pas autorisé à demander la signature sur cette "
                "étape."))
        if self.has_completed_signature:
            raise UserError(_("La signature de cette étape est déjà obtenue."))
        version = self._signature_source_version()
        if not version:
            raise UserError(_(
                "Aucune version PDF n'est disponible : la signature "
                "électronique porte sur un document PDF du courrier."))
        signer = self.responsible_id or self.env.user
        if not signer.partner_id.email:
            raise UserError(_(
                "Le signataire « %s » n'a pas d'adresse e-mail : elle est "
                "nécessaire pour lui envoyer le lien de signature.",
                signer.name))
        role = self._sign_oca_role()
        field = self._sign_oca_signature_field()
        if not role or not field:
            raise UserError(_(
                "Paramétrage Signature incomplet : aucun rôle ou aucun type "
                "de champ « signature » n'est défini."))
        replaced = self._sign_oca_requests([('state', 'in', PENDING_STATES)])
        for pending in replaced:
            pending.cancel()  # un à un : cancel() journalise par demande
        request = self.env['sign.oca.request'].sudo().create({
            'name': _("Signature — %s") % (self.reference or self.subject),
            # sign_oca garde SA copie (réécrite à chaque signature) : la
            # version GED d'origine reste intacte.
            'data': version.attachment_id.sudo().datas,
            'filename': version.file_name or 'document.pdf',
            'record_ref': '%s,%s' % (self._name, self.id),
            'courrier_id': self.id,
            'courrier_step_history_id': self._sign_oca_current_visit().id,
            'courrier_document_id': version.document_id.id,
            'user_id': self.env.user.id,
            'signer_ids': [Command.create({
                'partner_id': signer.partner_id.id,
                'role_id': role.id,
            })],
        })
        request.add_item(dict(SIGNATURE_BOX, field_id=field.id,
                              role_id=role.id, required=True, page=1))
        # sign_oca n'envoie rien à la création : l'envoi est explicite.
        request.action_send()
        body = _("Demande de signature envoyée à %s (document « %s »).") % (
            signer.name, version.file_name or '')
        if replaced:
            body += " " + _("Demande précédente annulée : %s.") % ", ".join(
                replaced.mapped('name'))
        # sudo : assistants et managers n'ont que la lecture du courrier,
        # insuffisante pour publier (même choix que _notify_action).
        self.sudo().message_post(body=body,
                                 author_id=self.env.user.partner_id.id)
        self._audit_action(
            _("Demande de signature"), 'info',
            _("Signataire : %s — %s") % (signer.name, version.file_name or ''))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Demande de signature"),
            'res_model': 'sign.oca.request',
            'res_id': request.id,
            'view_mode': 'form',
        }

    def action_view_sign_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Signatures — %s") % (self.reference or self.subject),
            'res_model': 'sign.oca.request',
            'view_mode': 'list,form',
            'domain': [('courrier_id', '=', self.id)],
            'context': {'create': False},
        }

    # ------------------------------------------------------------------ #
    # Fin de signature (appelé par sign.oca.request._check_signed, en sudo)
    # ------------------------------------------------------------------ #
    def _sign_oca_on_request_signed(self, request):
        self.ensure_one()
        filename = request.filename or 'document.pdf'
        base = filename[:-4] if filename.lower().endswith('.pdf') else filename
        signed_name = "%s_signe.pdf" % base
        signers = self.env['sign.oca.request.signer'].sudo().search(
            [('request_id', '=', request.id)])  # cf. _sign_oca_requests
        detail = _("Demande « %s » signée par %s.") % (
            request.name, ", ".join(signers.mapped('partner_id.name')))
        document = request.courrier_document_id
        if document:
            try:
                # Contrôles GED (confidentialité, verrou) faits au nom du
                # demandeur, pas du signataire anonyme du portail.
                version = document.with_user(request.user_id).sudo() \
                    .with_context(audit_source='system') \
                    .add_version(signed_name, request.data)
                detail += " " + _("PDF signé versé en %s.") % version.version
            except (AccessError, UserError, ValidationError) as err:
                _logger.info("PDF signé non versé en GED (%s) : %s",
                             request.name, err)
                document = False
        attachment_ids = []
        if not document:
            detail += " " + _("PDF signé joint à l'historique.")
            attachment_ids = self.env['ir.attachment'].create({
                'name': signed_name, 'datas': request.data,
                'res_model': self._name, 'res_id': self.id,
                'mimetype': 'application/pdf',
            }).ids
        self.message_post(body=detail, attachment_ids=attachment_ids,
                          author_id=self.env.ref('base.partner_root').id)
        self.env['aite.courrier.audit.log']._log(
            self.env, _("Signature complétée"), 'ok', 'aite.courrier',
            self.id, self.reference or self.display_name, detail, 'system')

    # ------------------------------------------------------------------ #
    # Garde serveur : étape « Signature requise »
    # ------------------------------------------------------------------ #
    def do_transition(self, transition, comment=False):
        self.ensure_one()
        transition = self._as_transition(transition)
        # Transition indisponible ou utilisateur non habilité : le refus
        # standard (et son audit) revient à super().
        if transition.direction == 'forward' \
                and self.current_step_id.require_signature \
                and transition in self.current_step_id.outgoing_transition_ids \
                and self._user_can_act(self.env.user) \
                and not self.has_completed_signature:
            # Écrit hors de la transaction annulée par l'erreur qui suit
            # (entrée 'err' du journal d'audit).
            self._audit_action(
                _("Action bloquée"), 'err',
                _("Étape « %s » : signature électronique manquante.")
                % self.current_step_id.name)
            raise UserError(_(
                "Cette étape exige une signature électronique : aucune "
                "demande n'a été signée depuis l'arrivée du courrier sur "
                "l'étape. Utilisez « Demander la signature » puis attendez "
                "la signature."))
        res = super().do_transition(transition, comment=comment)
        self._sign_oca_cancel_stale_requests()
        return res

    def _sign_oca_cancel_stale_requests(self):
        """Annule les demandes restées en attente d'un passage terminé :
        signées plus tard, elles ne lèveraient plus aucune garde."""
        stale = self._sign_oca_requests([
            ('state', 'in', PENDING_STATES),
            ('courrier_step_history_id.left_date', '!=', False)])
        if stale:
            for pending in stale:
                pending.cancel()
            self.sudo().message_post(
                body=_("Demande de signature annulée, le courrier ayant "
                       "quitté l'étape : %s.") % ", ".join(stale.mapped('name')),
                author_id=self.env.ref('base.partner_root').id)
