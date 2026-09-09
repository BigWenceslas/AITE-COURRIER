# -*- coding: utf-8 -*-
"""Client minimal Google OAuth 2 + Drive API v3 (``requests``)."""
import json
import logging
from urllib.parse import urlencode

import requests

_logger = logging.getLogger(__name__)

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
DRIVE = 'https://www.googleapis.com/drive/v3'
UPLOAD = 'https://www.googleapis.com/upload/drive/v3'
SCOPE = 'https://www.googleapis.com/auth/drive.file'
GOOGLE_MIME = {
    'docx': 'application/vnd.google-apps.document',
    'doc': 'application/vnd.google-apps.document',
    'odt': 'application/vnd.google-apps.document',
    'xlsx': 'application/vnd.google-apps.spreadsheet',
    'xls': 'application/vnd.google-apps.spreadsheet',
    'ods': 'application/vnd.google-apps.spreadsheet',
    'csv': 'application/vnd.google-apps.spreadsheet',
    'pptx': 'application/vnd.google-apps.presentation',
    'ppt': 'application/vnd.google-apps.presentation',
    'odp': 'application/vnd.google-apps.presentation',
}
EXPORT_MIME = {
    'application/vnd.google-apps.document': (
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx'),
    'application/vnd.google-apps.spreadsheet': (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx'),
    'application/vnd.google-apps.presentation': (
        'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'pptx'),
}
EDIT_URL = {
    'application/vnd.google-apps.document': 'https://docs.google.com/document/d/%s/edit',
    'application/vnd.google-apps.spreadsheet': 'https://docs.google.com/spreadsheets/d/%s/edit',
    'application/vnd.google-apps.presentation': 'https://docs.google.com/presentation/d/%s/edit',
}


class GoogleDriveError(Exception):
    pass


def auth_url(client_id, redirect_uri, state):
    return AUTH_URL + '?' + urlencode({
        'client_id': client_id, 'redirect_uri': redirect_uri,
        'response_type': 'code', 'scope': SCOPE, 'access_type': 'offline',
        'prompt': 'consent', 'state': state})


def exchange_code(client_id, client_secret, code, redirect_uri):
    resp = requests.post(TOKEN_URL, data={
        'code': code, 'client_id': client_id, 'client_secret': client_secret,
        'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'},
        timeout=30)
    if resp.status_code != 200:
        raise GoogleDriveError("Échange du code OAuth refusé : %s" % resp.text[:200])
    return resp.json()


def refresh_token(client_id, client_secret, token):
    resp = requests.post(TOKEN_URL, data={
        'refresh_token': token, 'client_id': client_id,
        'client_secret': client_secret, 'grant_type': 'refresh_token'},
        timeout=30)
    if resp.status_code != 200:
        raise GoogleDriveError("Rafraîchissement du jeton refusé : %s" % resp.text[:200])
    return resp.json()


class GoogleDriveClient:

    def __init__(self, access_token, timeout=60):
        self.session = requests.Session()
        self.session.headers['Authorization'] = 'Bearer %s' % access_token
        self.timeout = timeout

    def _request(self, method, url, ok=(200,), **kw):
        kw.setdefault('timeout', self.timeout)
        try:
            resp = self.session.request(method, url, **kw)
        except requests.RequestException as exc:
            raise GoogleDriveError("Google Drive injoignable : %s" % exc)
        if resp.status_code not in ok:
            raise GoogleDriveError("Google Drive %s %s → HTTP %s %s" % (
                method, url.split('?')[0], resp.status_code, resp.text[:200]))
        return resp

    def ensure_folder(self, name):
        resp = self._request('GET', DRIVE + '/files', params={
            'q': "name = '%s' and mimeType = 'application/vnd.google-apps.folder' "
                 "and trashed = false" % name.replace("'", "\\'"),
            'fields': 'files(id)'})
        files = resp.json().get('files', [])
        if files:
            return files[0]['id']
        resp = self._request('POST', DRIVE + '/files', json={
            'name': name, 'mimeType': 'application/vnd.google-apps.folder'})
        return resp.json()['id']

    def upload(self, name, content, mimetype, folder_id=None, convert_to=None):
        """Téléversement multipart ; ``convert_to`` = type Google natif
        (Docs / Sheets / Slides) pour éditer dans l'éditeur Google."""
        metadata = {'name': name}
        if folder_id:
            metadata['parents'] = [folder_id]
        if convert_to:
            metadata['mimeType'] = convert_to
        boundary = 'aite_ecm_boundary'
        body = (
            ('--%s\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n%s\r\n'
             % (boundary, json.dumps(metadata))).encode('utf-8')
            + ('--%s\r\nContent-Type: %s\r\n\r\n' % (boundary, mimetype)).encode('utf-8')
            + content + ('\r\n--%s--' % boundary).encode('utf-8'))
        resp = self._request('POST', UPLOAD + '/files', params={
            'uploadType': 'multipart',
            'fields': 'id,mimeType,modifiedTime,webViewLink'},
            data=body, headers={'Content-Type': 'multipart/related; boundary=%s'
                                % boundary})
        return resp.json()

    def metadata(self, file_id):
        resp = self._request('GET', DRIVE + '/files/%s' % file_id, params={
            'fields': 'id,name,mimeType,modifiedTime,md5Checksum,trashed,webViewLink'})
        return resp.json()

    def download(self, file_id, mimetype):
        """Contenu du fichier : export pour un type Google natif, sinon
        téléchargement direct."""
        if mimetype in EXPORT_MIME:
            export_mime, ext = EXPORT_MIME[mimetype]
            resp = self._request('GET', DRIVE + '/files/%s/export' % file_id,
                                 params={'mimeType': export_mime})
            return resp.content, export_mime, ext
        resp = self._request('GET', DRIVE + '/files/%s' % file_id,
                             params={'alt': 'media'})
        return resp.content, mimetype, None

    def delete(self, file_id):
        self._request('DELETE', DRIVE + '/files/%s' % file_id, ok=(204, 404))

    def share_with(self, file_id, email, role='writer'):
        self._request('POST', DRIVE + '/files/%s/permissions' % file_id,
                      params={'sendNotificationEmail': 'false'},
                      json={'type': 'user', 'role': role, 'emailAddress': email})
