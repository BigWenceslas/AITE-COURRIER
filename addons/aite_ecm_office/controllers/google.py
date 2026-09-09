# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

from ..models.google_drive_client import GoogleDriveError, exchange_code

_logger = logging.getLogger(__name__)


class EcmGoogleController(http.Controller):

    @http.route('/ecm/google/callback', type='http', auth='user', methods=['GET'])
    def callback(self, code=None, state=None, error=None, **kw):
        user = request.env.user
        stored = user.sudo().ecm_google_state or ''
        if error or not code or not state or state != stored:
            return request.redirect('/odoo?google_error=1')
        client_id, secret, redirect = request.env['res.users']._google_oauth_config()
        try:
            tokens = exchange_code(client_id, secret, code, redirect)
        except GoogleDriveError as exc:
            _logger.warning("[google] %s", exc)
            return request.redirect('/odoo?google_error=1')
        user._google_store_tokens(tokens)
        user.sudo().write({'ecm_google_state': False})
        parts = state.split(':')
        if len(parts) == 3 and parts[1] and parts[2]:
            return request.redirect('/odoo/%s/%s' % (parts[1], parts[2]))
        return request.redirect('/odoo')
