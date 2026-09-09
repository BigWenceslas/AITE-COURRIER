# -*- coding: utf-8 -*-
"""Hôte WOPI : édition des documents ECM dans le navigateur avec
Collabora Online ou OnlyOffice (auto-hébergés).

* un **jeton** par (document, utilisateur), limité dans le temps ;
* ``CheckFileInfo`` / ``GetFile`` / ``PutFile`` / ``Lock`` implémentés ici,
  le contrôleur ne faisant que transporter les requêtes ;
* verrou WOPI = **réservation ECM** ; sauvegarde = **nouvelle version** ;
* découverte du serveur (``/hosting/discovery``) mise en cache.
"""
import base64
import logging
import secrets
import xml.etree.ElementTree as ET
from datetime import timedelta
from urllib.parse import quote, urlencode

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PARAM_URL = 'aite_ecm_office.wopi_server_url'
PARAM_HOURS = 'aite_ecm_office.wopi_token_hours'
PARAM_DISCOVERY = 'aite_ecm_office.wopi_discovery_cache'
PARAM_DISCOVERY_DATE = 'aite_ecm_office.wopi_discovery_date'
# extension → application WOPI (nom utilisé dans la découverte)
WOPI_APPS = {
    'docx': 'writer', 'doc': 'writer', 'odt': 'writer', 'rtf': 'writer',
    'txt': 'writer',
    'xlsx': 'calc', 'xls': 'calc', 'ods': 'calc', 'csv': 'calc',
    'pptx': 'impress', 'ppt': 'impress', 'odp': 'impress',
    'pdf': 'draw',
}


class AiteEcmOfficeToken(models.Model):
    _name = 'aite.ecm.office.token'
    _description = "Jeton d'édition en ligne (WOPI)"
    _order = 'id desc'

    token = fields.Char(required=True, index=True,
                        default=lambda self: secrets.token_urlsafe(32))
    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', required=True, ondelete='cascade',
        index=True)
    user_id = fields.Many2one(comodel_name='res.users', required=True,
                              ondelete='cascade')
    can_write = fields.Boolean(default=False)
    expiry = fields.Datetime(required=True)
    lock_id = fields.Char(string="Verrou WOPI")

    # ================================================================== #
    # Configuration et découverte
    # ================================================================== #
    @api.model
    def _server_url(self):
        return (self.env['ir.config_parameter'].sudo().get_param(PARAM_URL)
                or '').strip().rstrip('/')

    @api.model
    def _token_hours(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            PARAM_HOURS, 8) or 8)

    @api.model
    def _discovery(self, force=False):
        """Charge et met en cache (24 h) le XML de découverte du serveur."""
        Param = self.env['ir.config_parameter'].sudo()
        server = self._server_url()
        if not server:
            raise UserError(_(
                "Aucun serveur d'édition en ligne configuré (ECM › "
                "Configuration › Paramètres › Édition Office)."))
        cached = Param.get_param(PARAM_DISCOVERY)
        stamp = Param.get_param(PARAM_DISCOVERY_DATE)
        fresh = stamp and fields.Datetime.from_string(stamp) > \
            fields.Datetime.now() - timedelta(hours=24)
        if cached and fresh and not force:
            return cached
        import requests
        try:
            resp = requests.get(server + '/hosting/discovery', timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise UserError(_("Serveur d'édition injoignable : %s") % exc)
        Param.set_param(PARAM_DISCOVERY, resp.text)
        Param.set_param(PARAM_DISCOVERY_DATE,
                        fields.Datetime.to_string(fields.Datetime.now()))
        return resp.text

    @api.model
    def _editor_urlsrc(self, extension, mode='edit'):
        """URL d'action (edit/view) du serveur pour une extension."""
        root = ET.fromstring(self._discovery())
        ext = (extension or '').lower()
        wanted_app = WOPI_APPS.get(ext)
        fallback = None
        for app in root.iter('app'):
            for action in app.iter('action'):
                if action.get('ext', '').lower() != ext:
                    continue
                name = action.get('name')
                urlsrc = action.get('urlsrc')
                if name == mode:
                    return urlsrc
                if name in ('view', 'edit') and not fallback:
                    fallback = urlsrc
        if fallback:
            return fallback
        raise UserError(_(
            "Le serveur d'édition ne prend pas en charge le format « %s »%s.",
            ext, '' if wanted_app else _(" (format inconnu)")))

    @api.model
    def _clean_urlsrc(self, urlsrc):
        """Retire les paramètres facultatifs « <ui=UI_LLCC&> » de la découverte."""
        if '<' in urlsrc:
            urlsrc = urlsrc.split('<', 1)[0]
        return urlsrc.rstrip('?&')

    # ================================================================== #
    # Jetons
    # ================================================================== #
    @api.model
    def _issue(self, document, user, can_write):
        expiry = fields.Datetime.now() + timedelta(hours=self._token_hours())
        existing = self.sudo().search([
            ('document_id', '=', document.id), ('user_id', '=', user.id),
            ('expiry', '>', fields.Datetime.now())], limit=1)
        if existing:
            existing.write({'can_write': can_write, 'expiry': expiry})
            return existing
        return self.sudo().create({'document_id': document.id,
                                   'user_id': user.id, 'can_write': can_write,
                                   'expiry': expiry})

    @api.model
    def _resolve(self, token, document_id):
        """Jeton valide pour ce document, ou None."""
        rec = self.sudo().search([('token', '=', token or ''),
                                  ('document_id', '=', int(document_id))],
                                 limit=1)
        if not rec or rec.expiry < fields.Datetime.now():
            return None
        return rec

    @api.model
    def _cron_purge(self):
        self.sudo().search([('expiry', '<', fields.Datetime.now()
                             - timedelta(days=1))]).unlink()
        return True

    # ================================================================== #
    # Opérations WOPI (appelées par le contrôleur)
    # ================================================================== #
    def _doc(self):
        self.ensure_one()
        return self.document_id.with_user(self.user_id).sudo()

    def check_file_info(self):
        """Réponse de ``CheckFileInfo``."""
        self.ensure_one()
        doc = self._doc()
        version = doc.latest_version_id
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        can_write = bool(self.can_write and not doc.is_locked and (
            not doc.is_checked_out or doc.checkout_user_id == self.user_id))
        return {
            'BaseFileName': version.file_name or "%s.%s" % (
                doc.name, version.file_extension or 'bin'),
            'OwnerId': str(doc.owner_id.id or doc.create_uid.id),
            'Size': int(version.file_size or 0),
            'UserId': str(self.user_id.id),
            'UserFriendlyName': self.user_id.name,
            'Version': str(version.id),
            'LastModifiedTime': (version.upload_date or doc.write_date
                                 ).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'UserCanWrite': can_write,
            'ReadOnly': not can_write,
            'UserCanNotWriteRelative': True,
            'SupportsUpdate': True,
            'SupportsLocks': True,
            'SupportsGetLock': True,
            'SupportsExtendedLockLength': True,
            'SupportsRename': False,
            'DisablePrint': False,
            'DisableExport': False,
            'HidePrintOption': False,
            'PostMessageOrigin': base,
            'BreadcrumbBrandName': 'AITE ECM',
            'BreadcrumbBrandUrl': base,
            'BreadcrumbFolderName': doc.folder_id.complete_name or 'ECM',
            'BreadcrumbDocName': doc.name,
            'EnableOwnerTermination': False,
            'IsAnonymousUser': False,
        }

    def get_file(self):
        self.ensure_one()
        version = self._doc().latest_version_id
        return base64.b64decode(version.attachment_id.sudo().datas or b''), \
            version.mime_type or 'application/octet-stream'

    def put_file(self, content, lock_id=None):
        """Sauvegarde depuis l'éditeur → nouvelle version ; retourne
        (code HTTP, en-têtes)."""
        self.ensure_one()
        doc = self._doc()
        if not self.can_write:
            return 401, {}
        if doc.is_locked:
            return 409, {'X-WOPI-Lock': self.lock_id or '',
                         'X-WOPI-LockFailureReason': 'document verrouillé'}
        if lock_id and self.lock_id and lock_id != self.lock_id:
            return 409, {'X-WOPI-Lock': self.lock_id}
        if doc.is_checked_out and doc.checkout_user_id != self.user_id:
            return 409, {'X-WOPI-Lock': self.lock_id or '',
                         'X-WOPI-LockFailureReason': 'réservé par %s'
                         % doc.checkout_user_id.name}
        version = doc.latest_version_id
        filename = version.file_name or "%s.%s" % (doc.name,
                                                    version.file_extension)
        doc.with_context(audit_source='ui').add_version(
            filename, base64.b64encode(content or b''),
            _("Enregistré depuis l'éditeur en ligne"))
        return 200, {'X-WOPI-ItemVersion': str(doc.latest_version_id.id)}

    def lock(self, lock_id, old_lock=None):
        """LOCK / REFRESH_LOCK / UNLOCK_AND_RELOCK → (code, en-têtes)."""
        self.ensure_one()
        doc = self._doc()
        if doc.is_locked:
            return 409, {'X-WOPI-Lock': self.lock_id or '',
                         'X-WOPI-LockFailureReason': 'document verrouillé'}
        if doc.is_checked_out and doc.checkout_user_id != self.user_id:
            return 409, {'X-WOPI-Lock': self.lock_id or '',
                         'X-WOPI-LockFailureReason': 'réservé par %s'
                         % doc.checkout_user_id.name}
        if self.lock_id and self.lock_id not in (lock_id, old_lock):
            return 409, {'X-WOPI-Lock': self.lock_id}
        if not doc.is_checked_out:
            doc.with_context(audit_source='ui').action_checkout()
        self.sudo().write({'lock_id': lock_id,
                           'expiry': fields.Datetime.now()
                           + timedelta(hours=self._token_hours())})
        return 200, {'X-WOPI-ItemVersion': str(doc.latest_version_id.id)}

    def unlock(self, lock_id):
        self.ensure_one()
        doc = self._doc()
        if self.lock_id and lock_id != self.lock_id:
            return 409, {'X-WOPI-Lock': self.lock_id}
        self.sudo().write({'lock_id': False})
        if doc.is_checked_out and doc.checkout_user_id == self.user_id:
            doc.with_context(audit_source='ui').action_checkin()
        return 200, {}

    def get_lock(self):
        self.ensure_one()
        return 200, {'X-WOPI-Lock': self.lock_id or ''}

    # ================================================================== #
    # Page d'édition
    # ================================================================== #
    def _editor_url(self, mode='edit'):
        """URL du client WOPI (iframe) pour ce jeton."""
        self.ensure_one()
        doc = self._doc()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        wopisrc = "%s/ecm/wopi/files/%d" % (base.rstrip('/'), doc.id)
        urlsrc = self._clean_urlsrc(self._editor_urlsrc(
            doc.latest_version_id.file_extension, mode))
        sep = '&' if '?' in urlsrc else '?'
        params = {'WOPISrc': wopisrc, 'lang': (self.user_id.lang or 'fr_FR')
                  .replace('_', '-')}
        return "%s%s%s" % (urlsrc, sep, urlencode(params, quote_via=quote))
