# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class NextcloudWebhookController(http.Controller):
    """Réception des événements fichiers de Nextcloud (Webhook Listeners)."""

    @http.route('/ecm/nextcloud/webhook', type='http', auth='none',
                methods=['POST'], csrf=False, save_session=False)
    def webhook(self, **kw):
        env = request.env(su=True)
        secret = env['ir.config_parameter'].get_param(
            'aite_ecm_nextcloud.webhook_secret')
        given = request.httprequest.headers.get('X-AITE-Secret')
        if not secret or given != secret:
            return request.make_json_response({'error': 'forbidden'}, 403)
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True)
                                 or '{}')
        except ValueError:
            return request.make_json_response({'error': 'bad json'}, 400)
        event = payload.get('event') or {}
        node = event.get('node') or {}
        file_id = str(node.get('id') or '')
        path = node.get('path') or ''
        marked = 0
        Mixin = env['aite.ecm.document']
        for model in Mixin._nc_models():
            Model = env[model]
            domain = [('nc_file_id', '=', file_id)] if file_id else []
            if not domain and path:
                domain = [('nc_path', '!=', False),
                          ('nc_path', '=ilike', '%' + path.rsplit('/', 1)[-1])]
            if not domain:
                continue
            records = Model.search(domain)
            records.filtered(
                lambda r: r.nc_sync_state != 'todo')._nc_mark('pull')
            marked += len(records)
        if marked:
            cron = env.ref('aite_ecm_nextcloud.ir_cron_nc_sync',
                           raise_if_not_found=False)
            if cron:
                cron._trigger()
        _logger.info("[nextcloud] webhook %s : %d document(s) à importer",
                     event.get('class', '?'), marked)
        return request.make_json_response({'ok': True, 'marked': marked})
