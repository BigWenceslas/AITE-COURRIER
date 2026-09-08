# -*- coding: utf-8 -*-
"""Contrôleur WebDAV : adaptateur HTTP au-dessus du service ``aite.courrier.webdav``.

Sert l'espace documentaire AITE Courrier en WebDAV directement depuis le
serveur Odoo (même port, même authentification). Implémente un sous-ensemble
utile de la RFC 4918 : OPTIONS, PROPFIND, GET/HEAD, PUT, DELETE, MKCOL, MOVE,
COPY, LOCK/UNLOCK, PROPPATCH.

Authentification : **HTTP Basic** vers un ``res.users`` Odoo ; toutes les
opérations s'exécutent ensuite avec les droits de cet utilisateur. Le serveur
est supposé mono-base (option ``--database`` / ``db_name``), ce qui correspond
au déploiement Docker fourni.

NB : la couche HTTP elle-même se valide sur une instance Odoo lancée (un client
WebDAV réel) ; la logique métier est, elle, couverte par les tests du service.
"""
import base64
import logging
import uuid
from datetime import timezone
from email.utils import formatdate
from urllib.parse import quote, unquote, urlparse
from xml.sax.saxutils import escape

import odoo
from odoo import http
from odoo.http import request, Response

from ..models.aite_courrier_webdav import ROOT_PATH, WebdavError, WebdavBadRequest

_logger = logging.getLogger(__name__)

WEBDAV_METHODS = [
    'OPTIONS', 'HEAD', 'GET', 'PUT', 'DELETE', 'PROPFIND', 'PROPPATCH',
    'MKCOL', 'MOVE', 'COPY', 'LOCK', 'UNLOCK',
]
ALLOW_HEADER = ', '.join(WEBDAV_METHODS)


class AiteCourrierWebdavController(http.Controller):

    # ------------------------------------------------------------------ #
    # Routage : un point d'entrée, dispatch par méthode HTTP
    # ------------------------------------------------------------------ #
    @http.route(
        ['/webdav/aite_courrier', '/webdav/aite_courrier/<path:subpath>'],
        type='http', auth='none', csrf=False, methods=WEBDAV_METHODS,
        save_session=False, sitemap=False)
    def dispatch(self, subpath='', **kwargs):
        method = request.httprequest.method
        # OPTIONS doit répondre sans authentification (découverte des capacités).
        if method == 'OPTIONS':
            return self._options()
        if not self._authenticate():
            return self._unauthorized()
        handler = getattr(self, '_handle_' + method.lower(), None)
        if handler is None:
            return Response(status=405, headers=[('Allow', ALLOW_HEADER)])
        try:
            return handler(subpath)
        except WebdavError as error:
            return Response(str(error) or error.label, status=error.status)
        except Exception:  # pragma: no cover - garde-fou
            _logger.exception("WebDAV : erreur inattendue sur %s %s", method, subpath)
            return Response("Internal Server Error", status=500)

    # ------------------------------------------------------------------ #
    # Authentification HTTP Basic -> res.users
    # ------------------------------------------------------------------ #
    def _unauthorized(self):
        return Response(
            "Authentification requise", status=401,
            headers=[('WWW-Authenticate', 'Basic realm="AITE Courrier WebDAV"')])

    def _resolve_db(self):
        if request.session.db:
            return request.session.db
        configured = (odoo.tools.config.get('db_name') or '').split(',')
        configured = [name.strip() for name in configured if name.strip()]
        if configured:
            return configured[0]
        available = http.db_list(force=True)
        return available[0] if len(available) == 1 else None

    def _authenticate(self):
        header = request.httprequest.headers.get('Authorization', '')
        if not header.startswith('Basic '):
            return False
        try:
            raw = base64.b64decode(header.split(' ', 1)[1]).decode('utf-8')
            login, _sep, password = raw.partition(':')
        except Exception:
            return False
        db = self._resolve_db()
        if not db:
            return False
        try:
            request.session.authenticate(
                db, {'login': login, 'password': password, 'type': 'password'})
        except Exception:
            return False
        uid = request.session.uid
        if not uid:
            return False
        request.update_env(user=uid)
        return True

    def _service(self):
        return request.env['aite.courrier.webdav']

    # ------------------------------------------------------------------ #
    # Helpers de formatage
    # ------------------------------------------------------------------ #
    def _href(self, resource_path):
        if resource_path:
            quoted = '/'.join(quote(part) for part in resource_path.split('/'))
            return '%s/%s' % (ROOT_PATH, quoted)
        return ROOT_PATH + '/'

    @staticmethod
    def _http_date(value):
        timestamp = value.replace(tzinfo=timezone.utc).timestamp()
        return formatdate(timestamp, usegmt=True)

    @staticmethod
    def _iso_date(value):
        return value.replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def _build_multistatus(self, resources):
        parts = ['<?xml version="1.0" encoding="utf-8"?>',
                 '<D:multistatus xmlns:D="DAV:">']
        for resource in resources:
            href = self._href(resource['path'])
            if resource['is_collection'] and not href.endswith('/'):
                href += '/'
            props = ['<D:displayname>%s</D:displayname>'
                     % escape(resource['name'] or '')]
            if resource['is_collection']:
                props.append('<D:resourcetype><D:collection/></D:resourcetype>')
            else:
                props.append('<D:resourcetype/>')
                props.append('<D:getcontentlength>%d</D:getcontentlength>'
                             % (resource['size'] or 0))
                if resource['content_type']:
                    props.append('<D:getcontenttype>%s</D:getcontenttype>'
                                 % escape(resource['content_type']))
            if resource.get('mtime'):
                props.append('<D:getlastmodified>%s</D:getlastmodified>'
                             % self._http_date(resource['mtime']))
            if resource.get('ctime'):
                props.append('<D:creationdate>%s</D:creationdate>'
                             % self._iso_date(resource['ctime']))
            if resource.get('locked'):
                props.append(
                    '<D:lockdiscovery><D:activelock>'
                    '<D:locktype><D:write/></D:locktype>'
                    '<D:lockscope><D:exclusive/></D:lockscope>'
                    '</D:activelock></D:lockdiscovery>')
            parts.append(
                '<D:response><D:href>%s</D:href><D:propstat><D:prop>%s</D:prop>'
                '<D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>'
                % (escape(href), ''.join(props)))
        parts.append('</D:multistatus>')
        return ''.join(parts)

    def _dest_to_subpath(self, destination):
        if not destination:
            return None
        path = unquote(urlparse(destination).path)
        if ROOT_PATH not in path:
            return None
        return path.split(ROOT_PATH, 1)[1].strip('/')

    # ------------------------------------------------------------------ #
    # Handlers par verbe
    # ------------------------------------------------------------------ #
    def _options(self):
        return Response(status=200, headers=[
            ('Allow', ALLOW_HEADER),
            ('DAV', '1, 2'),
            ('MS-Author-Via', 'DAV'),
            ('Content-Length', '0'),
        ])

    def _handle_propfind(self, subpath):
        raw_depth = request.httprequest.headers.get('Depth', '1')
        depth = 0 if raw_depth == '0' else 1
        resources = self._service().propfind(subpath, depth=depth)
        body = self._build_multistatus(resources)
        return Response(body, status=207,
                        content_type='application/xml; charset=utf-8')

    def _handle_get(self, subpath):
        segments = self._service()._split_path(subpath)
        if len(segments) < 2:
            return self._collection_index(subpath)
        data = self._service().read_file(subpath)
        headers = [
            ('Content-Type', data['content_type']),
            ('Content-Length', str(len(data['content']))),
            ('Content-Disposition', 'attachment; filename="%s"' % data['filename']),
        ]
        if data.get('mtime'):
            headers.append(('Last-Modified', self._http_date(data['mtime'])))
        return Response(data['content'], status=200, headers=headers)

    def _handle_head(self, subpath):
        response = self._handle_get(subpath)
        response.set_data(b'')
        return response

    def _collection_index(self, subpath):
        resources = self._service().propfind(subpath, depth=1)
        rows = []
        for resource in resources[1:]:
            href = self._href(resource['path'])
            if resource['is_collection'] and not href.endswith('/'):
                href += '/'
            rows.append('<li><a href="%s">%s</a></li>'
                        % (escape(href), escape(resource['name'])))
        title = escape(ROOT_PATH + ('/' + subpath if subpath else '/'))
        html = ('<html><head><meta charset="utf-8"/><title>%s</title></head>'
                '<body><h1>%s</h1><ul>%s</ul></body></html>'
                % (title, title, ''.join(rows)))
        return Response(html, content_type='text/html; charset=utf-8')

    def _handle_put(self, subpath):
        content = request.httprequest.get_data()
        result = self._service().put_file(subpath, content)
        return Response(status=201 if result['created'] else 204)

    def _handle_delete(self, subpath):
        self._service().delete_resource(subpath)
        return Response(status=204)

    def _handle_mkcol(self, subpath):
        # L'arborescence (racine, courriers) est gérée par l'application.
        return Response("Création de collection non autorisée", status=403)

    def _handle_move(self, subpath):
        destination = self._dest_to_subpath(
            request.httprequest.headers.get('Destination', ''))
        if destination is None:
            raise WebdavBadRequest()
        self._service().move_resource(subpath, destination)
        return Response(status=201)

    def _handle_copy(self, subpath):
        return Response("COPY non pris en charge", status=403)

    def _handle_lock(self, subpath):
        # Verrou consultatif : on émet un jeton sans le persister. La vraie
        # protection en écriture reste portée par ``is_locked`` (423 au PUT).
        token = 'opaquelocktoken:%s' % uuid.uuid4()
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<D:prop xmlns:D="DAV:"><D:lockdiscovery><D:activelock>'
                '<D:locktype><D:write/></D:locktype>'
                '<D:lockscope><D:exclusive/></D:lockscope>'
                '<D:depth>infinity</D:depth>'
                '<D:timeout>Second-3600</D:timeout>'
                '<D:locktoken><D:href>%s</D:href></D:locktoken>'
                '</D:activelock></D:lockdiscovery></D:prop>') % token
        return Response(body, status=200, content_type='application/xml; charset=utf-8',
                        headers=[('Lock-Token', '<%s>' % token)])

    def _handle_unlock(self, subpath):
        return Response(status=204)

    def _handle_proppatch(self, subpath):
        # Aucune propriété morte modifiable : on acquitte sans rien changer
        # (certains clients posent des timestamps après un PUT).
        href = self._href(self._service()._split_path(subpath) and subpath.strip('/'))
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<D:multistatus xmlns:D="DAV:"><D:response><D:href>%s</D:href>'
                '<D:propstat><D:prop/><D:status>HTTP/1.1 200 OK</D:status>'
                '</D:propstat></D:response></D:multistatus>') % escape(href)
        return Response(body, status=207, content_type='application/xml; charset=utf-8')
