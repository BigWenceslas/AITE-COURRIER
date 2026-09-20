# -*- coding: utf-8 -*-
"""Serveur WebDAV du plan de classement ECM (classe 1 + verrous)."""
import base64
import logging
import uuid
from datetime import timezone
from email.utils import formatdate
from urllib.parse import quote, unquote, urlparse
from xml.sax.saxutils import escape

import odoo
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from werkzeug.wrappers import Response
from odoo.addons.aite_courrier_base.tools import webdav_auth

from ..models.aite_ecm_webdav import WebdavError, WebdavNotFound

_logger = logging.getLogger(__name__)
ROOT_PATH = '/webdav/aite_ecm'
ALLOW = 'OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND, PROPPATCH, MKCOL, MOVE, LOCK, UNLOCK'


class AiteEcmWebdavController(http.Controller):

    # ``readonly=False`` : pour une route ``auth='none'`` Odoo 18 ouvre par
    # défaut un curseur en lecture seule. Or WebDAV écrit dès la connexion
    # (dernière connexion de l'utilisateur) puis à chaque PUT / MOVE / LOCK :
    # sans cette précision, chaque requête est jouée deux fois (essai en
    # lecture seule, puis reprise en écriture).
    @http.route([ROOT_PATH, ROOT_PATH + '/<path:subpath>'], type='http',
                auth='none', csrf=False, methods=None, save_session=False,
                readonly=False)
    def dispatch(self, subpath='', **kwargs):
        method = request.httprequest.method.upper()
        if method == 'OPTIONS':
            return self._options()
        if not self._authenticate():
            return self._unauthorized()
        handler = getattr(self, '_handle_' + method.lower(), None)
        if not handler:
            return Response(status=405, headers=[('Allow', ALLOW)])
        try:
            return handler(unquote(subpath).strip('/'))
        except WebdavError as exc:
            return Response(exc.message or '', status=exc.status,
                            content_type='text/plain; charset=utf-8')
        except AccessError as exc:
            # Utilisateur authentifié mais sans droit sur l'ECM : c'est un
            # refus (403), pas une panne du serveur.
            return Response(str(exc), status=403,
                            content_type='text/plain; charset=utf-8')
        except Exception:  # noqa: BLE001
            _logger.exception("WebDAV ECM : erreur sur %s %s", method, subpath)
            return Response(status=500)

    # ------------------------------------------------------------------ #
    # Authentification (Basic, comme le lecteur réseau Windows/macOS)
    # ------------------------------------------------------------------ #
    def _unauthorized(self):
        return Response(status=401, headers=[
            ('WWW-Authenticate', 'Basic realm="AITE ECM"')])

    def _resolve_db(self):
        """Base à ouvrir pour une requête WebDAV.

        Un client réel (l'Explorateur Windows, le Finder, un montage
        ``davfs``) se présente sans cookie : ``request.db`` est vide au
        moment du Basic. On retombe donc sur la base configurée
        (``--database`` / ``db_name``), puis sur la base unique de
        l'instance.
        """
        if request.db or request.session.db:
            return request.db or request.session.db
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
        except Exception:  # noqa: BLE001
            return False
        db = self._resolve_db()
        if not db:
            return False
        # Mot de passe ou clé d'API, avec cache : un client WebDAV présente
        # ses identifiants à chaque requête (cf. aite_courrier_base.tools).
        uid = webdav_auth.authenticate(request, db, login, password)
        if not uid:
            return False
        request.update_env(user=uid)
        return True

    def _service(self):
        return request.env['aite.ecm.webdav']

    # ------------------------------------------------------------------ #
    # Formatage
    # ------------------------------------------------------------------ #
    @staticmethod
    def _http_date(value):
        """Date HTTP (RFC 7231) à partir d'un ``datetime`` Odoo.

        Odoo stocke des datetimes **naïfs exprimés en UTC** :
        ``email.utils.format_datetime(..., usegmt=True)`` les refuse. On
        rattache donc explicitement le fuseau UTC avant le formatage.
        """
        return formatdate(value.replace(tzinfo=timezone.utc).timestamp(),
                          usegmt=True)

    def _href(self, path):
        if path:
            return ROOT_PATH + '/' + '/'.join(quote(p) for p in path.split('/'))
        return ROOT_PATH + '/'

    def _multistatus(self, resources):
        parts = ['<?xml version="1.0" encoding="utf-8"?>',
                 '<D:multistatus xmlns:D="DAV:">']
        for res in resources:
            href = self._href(res['path'])
            if res['is_collection'] and not href.endswith('/'):
                href += '/'
            props = ['<D:displayname>%s</D:displayname>' % escape(res['name'] or '')]
            if res['is_collection']:
                props.append('<D:resourcetype><D:collection/></D:resourcetype>')
            else:
                props.append('<D:resourcetype/>')
                props.append('<D:getcontentlength>%d</D:getcontentlength>' % (res['size'] or 0))
                if res.get('content_type'):
                    props.append('<D:getcontenttype>%s</D:getcontenttype>'
                                 % escape(res['content_type']))
                if res.get('etag'):
                    props.append('<D:getetag>%s</D:getetag>' % escape(res['etag']))
            if res.get('mtime'):
                props.append('<D:getlastmodified>%s</D:getlastmodified>'
                             % self._http_date(res['mtime']))
            if res.get('ctime'):
                props.append('<D:creationdate>%sZ</D:creationdate>'
                             % res['ctime'].replace(microsecond=0).isoformat())
            props.append('<D:supportedlock><D:lockentry><D:lockscope><D:exclusive/>'
                         '</D:lockscope><D:locktype><D:write/></D:locktype>'
                         '</D:lockentry></D:supportedlock>')
            if res.get('locked'):
                props.append('<D:lockdiscovery><D:activelock><D:locktype><D:write/>'
                             '</D:locktype><D:lockscope><D:exclusive/></D:lockscope>'
                             '</D:activelock></D:lockdiscovery>')
            parts.append('<D:response><D:href>%s</D:href><D:propstat><D:prop>%s</D:prop>'
                         '<D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>'
                         % (escape(href), ''.join(props)))
        parts.append('</D:multistatus>')
        return Response(''.join(parts), status=207,
                        content_type='application/xml; charset=utf-8')

    def _dest_to_subpath(self, destination):
        path = unquote(urlparse(destination or '').path)
        if ROOT_PATH not in path:
            return None
        return path.split(ROOT_PATH, 1)[1].strip('/')

    # ------------------------------------------------------------------ #
    # Verbes
    # ------------------------------------------------------------------ #
    def _options(self):
        return Response(status=200, headers=[
            ('DAV', '1, 2'), ('MS-Author-Via', 'DAV'), ('Allow', ALLOW),
            ('Content-Length', '0')])

    def _handle_propfind(self, subpath):
        depth = request.httprequest.headers.get('Depth', '1')
        depth = 0 if depth == '0' else 1
        return self._multistatus(self._service().propfind(subpath, depth=depth))

    def _handle_proppatch(self, subpath):
        # propriétés mortes non gérées : on acquitte (Office en pose parfois)
        self._service().propfind(subpath, depth=0)
        body = ('<?xml version="1.0" encoding="utf-8"?><D:multistatus xmlns:D="DAV:">'
                '<D:response><D:href>%s</D:href><D:propstat><D:prop/>'
                '<D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>'
                '</D:multistatus>' % escape(self._href(subpath)))
        return Response(body, status=207, content_type='application/xml; charset=utf-8')

    def _handle_get(self, subpath):
        try:
            doc, raw, mimetype = self._service().read_file(subpath)
        except WebdavNotFound:
            resources = self._service().propfind(subpath, depth=1)
            items = ''.join('<li><a href="%s">%s%s</a></li>' % (
                escape(self._href(r['path'])) + ('/' if r['is_collection'] else ''),
                escape(r['name']), '/' if r['is_collection'] else '')
                for r in resources[1:])
            return Response('<html><body><h3>AITE ECM — %s</h3><ul>%s</ul></body></html>'
                            % (escape(subpath or 'racine'), items),
                            content_type='text/html; charset=utf-8')
        version = doc.latest_version_id
        return Response(raw, status=200, headers=[
            ('Content-Type', mimetype), ('Content-Length', str(len(raw))),
            ('ETag', '"%s"' % (version.sha256 or version.id)),
            ('Last-Modified',
             self._http_date(version.upload_date or doc.write_date))])

    def _handle_head(self, subpath):
        """Mêmes en-têtes que GET, sans le corps.

        ``set_data`` recalcule ``Content-Length`` : lui passer un corps vide
        annonçait donc **0 octet**. Un client qui interroge la taille avant de
        charger — Word le fait systématiquement — en conclut que le fichier
        est vide, et ouvre une fenêtre sans document.
        """
        response = self._handle_get(subpath)
        length = response.headers.get('Content-Length')
        if length is None:
            length = str(len(response.get_data()))
        response.automatically_set_content_length = False
        response.set_data(b'')
        response.headers['Content-Length'] = length
        return response

    def _handle_put(self, subpath):
        content = request.httprequest.get_data()
        doc, created = self._service().put_file(subpath, content)
        version = doc.latest_version_id
        return Response(status=201 if created else 204,
                        headers=[('ETag', '"%s"' % (version.sha256 or version.id))])

    def _handle_delete(self, subpath):
        self._service().delete(subpath)
        return Response(status=204)

    def _handle_mkcol(self, subpath):
        self._service().mkcol(subpath)
        return Response(status=201)

    def _handle_move(self, subpath):
        dest = self._dest_to_subpath(request.httprequest.headers.get('Destination'))
        if dest is None:
            return Response(status=400)
        self._service().move(subpath, dest)
        return Response(status=201)

    def _handle_copy(self, subpath):
        return Response(status=403)

    def _handle_lock(self, subpath):
        # Un enregistrement vide = verrou sur un nom encore libre : la RFC
        # 4918 veut alors 201 Created.
        doc = self._service().lock(subpath)
        token = 'opaquelocktoken:%s' % uuid.uuid4()
        timeout = request.httprequest.headers.get('Timeout', 'Second-3600')
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<D:prop xmlns:D="DAV:"><D:lockdiscovery><D:activelock>'
                '<D:locktype><D:write/></D:locktype>'
                '<D:lockscope><D:exclusive/></D:lockscope>'
                '<D:depth>0</D:depth><D:timeout>%s</D:timeout>'
                '<D:locktoken><D:href>%s</D:href></D:locktoken>'
                '</D:activelock></D:lockdiscovery></D:prop>') % (escape(timeout), token)
        return Response(body, status=200 if doc else 201,
                        content_type='application/xml; charset=utf-8',
                        headers=[('Lock-Token', '<%s>' % token)])

    def _handle_unlock(self, subpath):
        self._service().unlock(subpath)
        return Response(status=204)
