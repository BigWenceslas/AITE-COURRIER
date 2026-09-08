# -*- coding: utf-8 -*-
"""Client Nextcloud minimal (WebDAV + OCS) fondé sur ``requests``.

* WebDAV authentifié : ``/remote.php/dav/files/<utilisateur>/…`` — PROPFIND,
  MKCOL, PUT, GET, MOVE, DELETE ; identifiant de fichier (``oc:fileid``) et
  ETag exploités pour la détection des modifications.
* OCS : création / suppression de liens publics (API de partage) et
  enregistrement de webhooks (app *Webhook Listeners*, Nextcloud 30+).

Aucune dépendance au-delà de ``requests`` (livré avec Odoo).
"""
import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote

import requests

_logger = logging.getLogger(__name__)

NS = {'d': 'DAV:', 'oc': 'http://owncloud.org/ns', 'nc': 'http://nextcloud.org/ns'}
PROPFIND_BODY = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
    '<d:prop><d:getetag/><d:getlastmodified/><d:getcontenttype/>'
    '<d:resourcetype/><oc:fileid/><oc:size/></d:prop></d:propfind>')
EVENT_NODE_WRITTEN = 'OCP\\Files\\Events\\Node\\NodeWrittenEvent'
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class NextcloudError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def sanitize(name, limit=120):
    """Nom de fichier/dossier sûr pour Nextcloud et les clients Windows."""
    name = _FORBIDDEN.sub('_', (name or '').strip()).strip('. ')
    name = re.sub(r'\s+', ' ', name)
    return (name or 'sans_nom')[:limit]


class NextcloudClient:

    def __init__(self, base_url, user, password, root='AITE ECM', timeout=60):
        self.base = (base_url or '').rstrip('/')
        self.user = user
        self.auth = (user, password)
        self.root = (root or '').strip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({'OCS-APIRequest': 'true'})

    # ------------------------------------------------------------------ #
    # Chemins
    # ------------------------------------------------------------------ #
    def full_path(self, path=''):
        """Chemin complet (depuis la racine de l'utilisateur) d'un chemin
        relatif au dossier racine du connecteur."""
        parts = [p for p in (self.root, (path or '').strip('/')) if p]
        return '/'.join(parts)

    def dav_url(self, path=''):
        return "%s/remote.php/dav/files/%s/%s" % (
            self.base, quote(self.user, safe=''), quote(self.full_path(path)))

    def file_url(self, file_id):
        return "%s/f/%s" % (self.base, file_id)

    # ------------------------------------------------------------------ #
    # Transport
    # ------------------------------------------------------------------ #
    def _request(self, method, url, ok=(200, 201, 204, 207), **kw):
        kw.setdefault('timeout', self.timeout)
        try:
            resp = self.session.request(method, url, **kw)
        except requests.RequestException as exc:
            raise NextcloudError("Nextcloud injoignable : %s" % exc)
        if resp.status_code not in ok:
            raise NextcloudError(
                "Nextcloud %s %s → HTTP %s" % (method, url, resp.status_code),
                resp.status_code)
        return resp

    # ------------------------------------------------------------------ #
    # WebDAV
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_multistatus(text):
        items = []
        root = ET.fromstring(text)
        for response in root.findall('d:response', NS):
            href = response.findtext('d:href', default='', namespaces=NS)
            prop = None
            for propstat in response.findall('d:propstat', NS):
                status = propstat.findtext('d:status', default='', namespaces=NS)
                if '200' in status:
                    prop = propstat.find('d:prop', NS)
                    break
            if prop is None:
                continue
            etag = (prop.findtext('d:getetag', default='', namespaces=NS)
                    or '').strip('"')
            items.append({
                'href': unquote(href),
                'name': unquote(href.rstrip('/').rsplit('/', 1)[-1]),
                'etag': etag,
                'fileid': prop.findtext('oc:fileid', default='', namespaces=NS),
                'size': int(prop.findtext('oc:size', default='0',
                                          namespaces=NS) or 0),
                'modified': prop.findtext('d:getlastmodified', default='',
                                          namespaces=NS),
                'is_dir': prop.find('d:resourcetype/d:collection', NS) is not None,
            })
        return items

    def stat(self, path=''):
        """Propriétés d'un fichier/dossier, ou None s'il n'existe pas."""
        resp = self._request('PROPFIND', self.dav_url(path), ok=(207, 404),
                             headers={'Depth': '0'}, data=PROPFIND_BODY)
        if resp.status_code == 404:
            return None
        items = self._parse_multistatus(resp.text)
        return items[0] if items else None

    def listdir(self, path=''):
        """Contenu direct d'un dossier (le dossier lui-même exclu)."""
        resp = self._request('PROPFIND', self.dav_url(path), ok=(207, 404),
                             headers={'Depth': '1'}, data=PROPFIND_BODY)
        if resp.status_code == 404:
            return []
        items = self._parse_multistatus(resp.text)
        return items[1:] if items else []

    def mkcol(self, path):
        self._request('MKCOL', self.dav_url(path), ok=(201, 405))

    def ensure_dir(self, path):
        """Crée l'arborescence manquante (y compris la racine)."""
        parts = [p for p in (path or '').strip('/').split('/') if p]
        if self.stat('') is None:
            self._request('MKCOL', self.dav_url(''), ok=(201, 405))
        current = ''
        for part in parts:
            current = "%s/%s" % (current, part) if current else part
            if self.stat(current) is None:
                self.mkcol(current)

    def upload(self, path, data):
        """PUT ; retourne (fileid, etag)."""
        resp = self._request('PUT', self.dav_url(path), ok=(200, 201, 204),
                             data=data,
                             headers={'Content-Type': 'application/octet-stream'})
        fileid = resp.headers.get('OC-FileId') or ''
        etag = (resp.headers.get('OC-ETag') or resp.headers.get('ETag')
                or '').strip('"')
        if not fileid or not etag:
            info = self.stat(path) or {}
            fileid, etag = info.get('fileid', fileid), info.get('etag', etag)
        return fileid, etag

    def download(self, path):
        return self._request('GET', self.dav_url(path)).content

    def delete(self, path):
        self._request('DELETE', self.dav_url(path), ok=(204, 404))

    def move(self, src, dst):
        self._request('MOVE', self.dav_url(src), ok=(201, 204),
                      headers={'Destination': self.dav_url(dst),
                               'Overwrite': 'T'})

    # ------------------------------------------------------------------ #
    # OCS : partage
    # ------------------------------------------------------------------ #
    def _ocs(self, method, endpoint, **kw):
        url = "%s/ocs/v2.php/%s" % (self.base, endpoint.lstrip('/'))
        kw.setdefault('params', {})
        kw['params']['format'] = 'json'
        resp = self._request(method, url, ok=(200, 201), **kw)
        try:
            return resp.json().get('ocs', {}).get('data', {})
        except ValueError:
            raise NextcloudError("Réponse OCS illisible.")

    def create_public_link(self, path, password=None, expire_date=None,
                           label=None, permissions=1):
        data = {'shareType': 3, 'path': '/' + self.full_path(path),
                'permissions': permissions}
        if password:
            data['password'] = password
        if expire_date:
            data['expireDate'] = expire_date  # AAAA-MM-JJ
        if label:
            data['label'] = label
        share = self._ocs('POST', 'apps/files_sharing/api/v1/shares', data=data)
        return {'id': str(share.get('id', '')), 'url': share.get('url', '')}

    def delete_share(self, share_id):
        try:
            self._ocs('DELETE', 'apps/files_sharing/api/v1/shares/%s' % share_id)
        except NextcloudError as exc:
            if exc.status != 404:
                raise

    # ------------------------------------------------------------------ #
    # OCS : webhooks (Nextcloud 30+)
    # ------------------------------------------------------------------ #
    def register_webhook(self, target_url, secret, event=EVENT_NODE_WRITTEN):
        payload = {'httpMethod': 'POST', 'uri': target_url, 'event': event,
                   'authMethod': 'header',
                   'authData': {'X-AITE-Secret': secret}}
        data = self._ocs('POST', 'apps/webhooks/api/v1/webhooks', json=payload)
        return str(data.get('id', ''))

    def list_webhooks(self):
        data = self._ocs('GET', 'apps/webhooks/api/v1/webhooks')
        return data if isinstance(data, list) else []

    def delete_webhook(self, webhook_id):
        try:
            self._ocs('DELETE', 'apps/webhooks/api/v1/webhooks/%s' % webhook_id)
        except NextcloudError as exc:
            if exc.status != 404:
                raise
