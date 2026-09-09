# -*- coding: utf-8 -*-
"""Jetons OAuth Google par utilisateur (portée drive.file)."""
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .google_drive_client import GoogleDriveError, auth_url, refresh_token


class ResUsers(models.Model):
    _inherit = 'res.users'

    ecm_google_refresh_token = fields.Char(copy=False, groups='base.group_system')
    ecm_google_access_token = fields.Char(copy=False, groups='base.group_system')
    ecm_google_token_expiry = fields.Datetime(copy=False, groups='base.group_system')
    ecm_google_state = fields.Char(copy=False, groups='base.group_system')
    ecm_google_linked = fields.Boolean(
        string="Google Docs autorisé", compute='_compute_ecm_google_linked')

    def _compute_ecm_google_linked(self):
        for user in self:
            user.ecm_google_linked = bool(user.sudo().ecm_google_refresh_token)

    @api.model
    def _google_oauth_config(self):
        get = self.env['ir.config_parameter'].sudo().get_param
        client_id = (get('aite_ecm_office.google_client_id') or '').strip()
        secret = get('aite_ecm_office.google_client_secret') or ''
        redirect = "%s/ecm/google/callback" % (
            get('web.base.url') or '').rstrip('/')
        return client_id, secret, redirect

    def _google_authorize_action(self, return_model=None, return_id=None):
        """Action de redirection vers le consentement Google."""
        self.ensure_one()
        client_id, _secret, redirect = self._google_oauth_config()
        if not client_id:
            raise UserError(_(
                "Google Docs n'est pas configuré : renseignez le client OAuth "
                "dans ECM › Configuration › Paramètres."))
        state = "%s:%s:%s" % (secrets.token_urlsafe(16), return_model or '',
                              return_id or '')
        self.sudo().write({'ecm_google_state': state})
        return {'type': 'ir.actions.act_url', 'target': 'self',
                'url': auth_url(client_id, redirect, state)}

    def _google_store_tokens(self, tokens):
        self.ensure_one()
        vals = {'ecm_google_access_token': tokens.get('access_token'),
                'ecm_google_token_expiry': fields.Datetime.now() + timedelta(
                    seconds=int(tokens.get('expires_in', 3600)) - 60)}
        if tokens.get('refresh_token'):
            vals['ecm_google_refresh_token'] = tokens['refresh_token']
        self.sudo().write(vals)

    def _google_access_token(self):
        """Jeton d'accès valide (rafraîchi au besoin) ou False."""
        self.ensure_one()
        me = self.sudo()
        if not me.ecm_google_refresh_token:
            return False
        if me.ecm_google_access_token and me.ecm_google_token_expiry \
                and me.ecm_google_token_expiry > fields.Datetime.now():
            return me.ecm_google_access_token
        client_id, secret, _redirect = self._google_oauth_config()
        try:
            tokens = refresh_token(client_id, secret, me.ecm_google_refresh_token)
        except GoogleDriveError:
            me.write({'ecm_google_refresh_token': False,
                      'ecm_google_access_token': False})
            return False
        self._google_store_tokens(tokens)
        return me.ecm_google_access_token

    def action_google_unlink(self):
        for user in self:
            user.sudo().write({'ecm_google_refresh_token': False,
                               'ecm_google_access_token': False,
                               'ecm_google_token_expiry': False})
        return True
