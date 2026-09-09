# -*- coding: utf-8 -*-
"""Serveur WebDAV du plan de classement ECM (classe 1 + verrous)."""
import base64
import logging
import uuid
from datetime import timezone
from email.utils import format_datetime
from urllib.parse import quote, unquote, urlparse
from xml.sax.saxutils import escape

from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response

from ..models.aite_ecm_webdav import (
    WebdavError, WebdavNotFound, WebdavUnsupportedMedia,
)

_logger = logging.getLogger(__name__)
ROOT_PATH = '/webdav/aite_ecm'
ALLOW = 'OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND, PROPPATCH, MKCOL, MOVE, LOCK, UNLOCK'


def http_date(value):
    """Date HTTP (RFC 1123) à partir d'un datetime Odoo, qui est *naïf* et
    exprimé en UTC : ``format_datetime(..., usegmt=True)`` exige un datetime
    portant explicitement le fuseau UTC."""
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return format_datetime(value.astimezone(timezone.utc), usegmt=True)


class AiteEcmWebdavController(http.Controller):

    # ``readonly=False`` : Odoo 18 sert les méthodes de lecture sur un curseur
    # en lecture seule, alors que l'authentification HTTP Basic écrit (journal de
    # connexion, session). Sans cela, toute requête WebDAV échoue en 401 avec
    # « Opening a read/write test cursor from a readonly one » dès qu'un réplica
    # de lecture est configuré — et systématiquement en test.
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
        except Exception:  # noqa: BLE001
            _logger.exception("WebDAV ECM : erreur sur %s %s", method, subpath)
            return Response(status=500)

    # ------------------------------------------------------------------ #
    # Authentification (Basic, comme le lecteur réseau Windows/macOS)
    # ------------------------------------------------------------------ #
    def _unauthorized(self):
        return Response(status=401, headers=[
            ('WWW-Authenticate', 'Basic realm="AITE ECM"')])

    def _authenticate(self):
        header = request.httprequest.headers.get('Authorization', '')
        if not header.startswith('Basic '):
            return False
        try:
            raw = base64.b64decode(header.split(' ', 1)[1]).decode('utf-8')
            login, _sep, password = raw.partition(':')
        except Exception:  # noqa: BLE001
            return False
        db = request.db or request.session.db
        if not db:
            return False
        try:
            request.session.authenticate(
                db, {'login': login, 'password': password, 'type': 'password'})
        except Exception:  # noqa: BLE001
            return False
        if not request.session.uid:
            return False
        request.update_env(user=request.session.uid)
        return True

    def _service(self):
        return request.env['aite.ecm.webdav']

    @staticmethod
    def _request_body():
        """Corps brut d'un ``PUT``.

        Un client annonçant un type de formulaire (``x-www-form-urlencoded``,
        ``multipart/form-data``) voit son corps consommé par l'analyseur de
        formulaires : ``get_data()`` renvoie alors des octets vides et le
        fichier serait enregistré vide, **sans erreur**. On préfère refuser la
        requête plutôt que de détruire silencieusement le contenu.
        """
        content = request.httprequest.get_data()
        if content:
            return content
        declared = request.httprequest.headers.get('Content-Length')
        if declared and declared.isdigit() and int(declared) > 0:
            raise WebdavUnsupportedMedia(
                "Corps de requête illisible : envoyez le fichier tel quel, "
                "avec un en-tête Content-Type binaire "
                "(application/octet-stream ou le type du document), et non un "
                "type de formulaire.")
        return content

    # ------------------------------------------------------------------ #
    # Formatage
    # ------------------------------------------------------------------ #
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
                             % http_date(res['mtime']))
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
            ('Last-Modified', http_date(version.upload_date or doc.write_date))])

    def _handle_head(self, subpath):
        # RFC 7231 : ``HEAD`` doit annoncer les mêmes en-têtes que ``GET``,
        # ``Content-Length`` compris. Vider le corps le remet à zéro : on le
        # restaure, sans quoi les clients WebDAV croient le fichier vide.
        resp = self._handle_get(subpath)
        length = resp.headers.get('Content-Length')
        resp.set_data(b'')
        if length is not None:
            # werkzeug recalcule ``Content-Length`` d'après le corps au moment
            # de l'envoi : il faut désactiver ce recalcul pour conserver la
            # taille réelle du fichier.
            resp.automatically_set_content_length = False
            resp.headers['Content-Length'] = length
        return resp

    def _handle_put(self, subpath):
        content = self._request_body()
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
        self._service().lock(subpath)
        token = 'opaquelocktoken:%s' % uuid.uuid4()
        timeout = request.httprequest.headers.get('Timeout', 'Second-3600')
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<D:prop xmlns:D="DAV:"><D:lockdiscovery><D:activelock>'
                '<D:locktype><D:write/></D:locktype>'
                '<D:lockscope><D:exclusive/></D:lockscope>'
                '<D:depth>0</D:depth><D:timeout>%s</D:timeout>'
                '<D:locktoken><D:href>%s</D:href></D:locktoken>'
                '</D:activelock></D:lockdiscovery></D:prop>') % (escape(timeout), token)
        return Response(body, status=200, content_type='application/xml; charset=utf-8',
                        headers=[('Lock-Token', '<%s>' % token)])

    def _handle_unlock(self, subpath):
        self._service().unlock(subpath)
        return Response(status=204)
