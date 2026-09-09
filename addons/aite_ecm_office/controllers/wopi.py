# -*- coding: utf-8 -*-
"""Contrôleur WOPI (transport uniquement — la logique est dans
``aite.ecm.office.token``) et page hôte de l'éditeur."""
import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class EcmWopiController(http.Controller):

    def _token(self, doc_id):
        token = request.params.get('access_token') or \
            request.httprequest.args.get('access_token')
        return request.env['aite.ecm.office.token'].sudo()._resolve(token, doc_id)

    @staticmethod
    def _json(data, status=200, headers=None):
        return Response(json.dumps(data), status=status,
                        headers=[('Content-Type', 'application/json')]
                        + list((headers or {}).items()))

    @staticmethod
    def _empty(status, headers=None):
        return Response('', status=status, headers=list((headers or {}).items()))

    # ------------------------------------------------------------------ #
    # CheckFileInfo / opérations de verrou
    # ------------------------------------------------------------------ #
    # ``readonly=False`` : WOPI pose et lève des verrous, enregistre le
    # contenu édité et rafraîchit les jetons — autant d'écritures.
    @http.route('/ecm/wopi/files/<int:doc_id>', type='http', auth='none',
                methods=['GET', 'POST'], csrf=False, save_session=False,
                readonly=False)
    def file_info(self, doc_id, **kw):
        token = self._token(doc_id)
        if token is None:
            return self._empty(401)
        method = request.httprequest.method
        if method == 'GET':
            return self._json(token.check_file_info())
        override = request.httprequest.headers.get('X-WOPI-Override', '')
        lock_id = request.httprequest.headers.get('X-WOPI-Lock')
        old_lock = request.httprequest.headers.get('X-WOPI-OldLock')
        if override in ('LOCK', 'REFRESH_LOCK'):
            code, headers = token.lock(lock_id, old_lock)
        elif override == 'UNLOCK':
            code, headers = token.unlock(lock_id)
        elif override == 'GET_LOCK':
            code, headers = token.get_lock()
        elif override in ('PUT_RELATIVE', 'RENAME_FILE', 'DELETE',
                          'PUT_USER_INFO'):
            code, headers = 501, {}
        else:
            code, headers = 400, {}
        return self._empty(code, headers)

    # ------------------------------------------------------------------ #
    # GetFile / PutFile
    # ------------------------------------------------------------------ #
    @http.route('/ecm/wopi/files/<int:doc_id>/contents', type='http',
                auth='none', methods=['GET', 'POST'], csrf=False,
                save_session=False, readonly=False)
    def file_contents(self, doc_id, **kw):
        token = self._token(doc_id)
        if token is None:
            return self._empty(401)
        if request.httprequest.method == 'GET':
            content, mimetype = token.get_file()
            return Response(content, status=200, headers=[
                ('Content-Type', mimetype),
                ('Content-Length', str(len(content)))])
        lock_id = request.httprequest.headers.get('X-WOPI-Lock')
        try:
            code, headers = token.put_file(request.httprequest.get_data(),
                                           lock_id)
        except Exception as exc:  # noqa: BLE001 — remonté à l'éditeur
            _logger.exception("[wopi] sauvegarde impossible")
            return self._json({'error': str(exc)}, 500)
        return self._empty(code, headers)

    # ------------------------------------------------------------------ #
    # Page hôte (iframe de l'éditeur)
    # ------------------------------------------------------------------ #
    @http.route('/ecm/office/edit/<int:doc_id>', type='http', auth='user',
                methods=['GET'])
    def editor(self, doc_id, mode='edit', **kw):
        doc = request.env['aite.ecm.document'].browse(doc_id).exists()
        if not doc:
            return request.not_found()
        doc.check_access('read')
        can_write = mode == 'edit' and doc._check_document_access('write')
        token = request.env['aite.ecm.office.token']._issue(
            doc, request.env.user, can_write)
        url = token._editor_url('edit' if can_write else 'view')
        return request.render('aite_ecm_office.wopi_host', {
            'doc': doc, 'editor_url': url, 'access_token': token.token,
            'access_token_ttl': int(token.expiry.timestamp() * 1000),
            'readonly': not can_write,
        })
