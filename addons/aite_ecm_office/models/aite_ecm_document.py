# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
from datetime import timedelta
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .google_drive_client import (EDIT_URL, GOOGLE_MIME, GoogleDriveClient,
                                  GoogleDriveError)

_logger = logging.getLogger(__name__)

OFFICE_SCHEMES = {
    'word': ('ms-word', ('doc', 'docx', 'rtf', 'odt', 'txt')),
    'excel': ('ms-excel', ('xls', 'xlsx', 'csv', 'ods')),
    'powerpoint': ('ms-powerpoint', ('ppt', 'pptx', 'odp')),
}
OFFICE_EXTENSIONS = sum((exts for _s, exts in OFFICE_SCHEMES.values()), ())


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    # ------------------------------------------------------------------ #
    # LibreOffice (l'ouverture dans Word/Excel/PowerPoint et l'adresse WebDAV
    # sont fournies par aite_ecm_webdav ; on ajoute ici LibreOffice)
    # ------------------------------------------------------------------ #
    libreoffice_uri = fields.Char(string="Ouvrir dans LibreOffice",
                                  compute='_compute_libreoffice_uri')

    @api.depends('webdav_url', 'latest_version_id')
    def _compute_libreoffice_uri(self):
        for doc in self:
            ext = (doc.latest_version_id.file_extension or '').lower()
            doc.libreoffice_uri = (
                "vnd.libreoffice.command:ofe|u|%s" % doc.webdav_url
                if doc.webdav_url and ext in OFFICE_EXTENSIONS else False)

    def _office_check(self):
        self.ensure_one()
        if not self.latest_version_id:
            raise UserError(_("Ce document n'a pas encore de fichier."))
        if not self.office_uri and not self.libreoffice_uri:
            raise UserError(_(
                "Ce format (%s) ne s'ouvre pas dans une suite bureautique.",
                self.latest_version_id.file_extension or '?'))
        if self.is_locked:
            raise UserError(_(
                "Document finalisé ou archivé : ouvrez-le en lecture seule "
                "depuis l'aperçu, ou remettez-le en brouillon."))
        if self.is_checked_out and not self.checked_out_by_me:
            raise UserError(_("Réservé par %s.", self.checkout_user_id.name))
        return True

    def action_open_libreoffice(self):
        self._office_check()
        self._audit(self, _("Ouverture dans LibreOffice"), 'info',
                    self.webdav_url or '')
        return {'type': 'ir.actions.act_url', 'url': self.libreoffice_uri,
                'target': 'self'}

    # ------------------------------------------------------------------ #
    # Édition dans le navigateur (WOPI : Collabora Online / OnlyOffice)
    # ------------------------------------------------------------------ #
    wopi_available = fields.Boolean(string="Édition en ligne possible",
                                    compute='_compute_wopi_available')

    @api.depends('latest_version_id')
    def _compute_wopi_available(self):
        from .aite_ecm_office_token import WOPI_APPS
        server = self.env['aite.ecm.office.token']._server_url()
        for doc in self:
            ext = (doc.latest_version_id.file_extension or '').lower()
            doc.wopi_available = bool(server and ext in WOPI_APPS)

    def _office_online_url(self, mode='edit'):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return "%s/ecm/office/edit/%d?mode=%s" % (base.rstrip('/'), self.id, mode)

    def action_office_edit_online(self):
        self.ensure_one()
        if not self.latest_version_id:
            raise UserError(_("Ce document n'a pas encore de fichier."))
        if not self.wopi_available:
            raise UserError(_(
                "Édition en ligne indisponible : serveur non configuré ou "
                "format non pris en charge (%s).",
                self.latest_version_id.file_extension or '?'))
        if self.is_locked:
            return self.action_office_view_online()
        if self.is_checked_out and not self.checked_out_by_me:
            raise UserError(_("Réservé par %s.", self.checkout_user_id.name))
        self._audit(self, _("Édition en ligne"), 'info',
                    self.latest_version_id.file_name or '')
        return {'type': 'ir.actions.act_url', 'url': self._office_online_url('edit'),
                'target': 'new'}

    def action_office_view_online(self):
        self.ensure_one()
        if not self.wopi_available:
            raise UserError(_("Aperçu en ligne indisponible pour ce format."))
        return {'type': 'ir.actions.act_url', 'url': self._office_online_url('view'),
                'target': 'new'}

    # ------------------------------------------------------------------ #
    # Google Docs (Drive)
    # ------------------------------------------------------------------ #
    gdrive_file_id = fields.Char(string="Fichier Google Drive", readonly=True,
                                 copy=False, index=True)
    gdrive_mimetype = fields.Char(readonly=True, copy=False)
    gdrive_url = fields.Char(string="Éditer dans Google", readonly=True, copy=False)
    gdrive_modified = fields.Char(readonly=True, copy=False)
    gdrive_user_id = fields.Many2one(
        comodel_name='res.users', string="Édité sur Google par", readonly=True,
        copy=False)
    gdrive_sync_date = fields.Datetime(readonly=True, copy=False)
    gdrive_error = fields.Text(readonly=True, copy=False)
    google_configured = fields.Boolean(compute='_compute_google_configured')

    def _compute_google_configured(self):
        configured = bool(self.env['res.users']._google_oauth_config()[0])
        for doc in self:
            doc.google_configured = configured

    def _gdrive_client(self, user=None):
        user = user or self.env.user
        token = user._google_access_token()
        if not token:
            return None
        return GoogleDriveClient(token)

    def action_open_google(self):
        """Dépose la dernière version dans Drive (dossier « AITE ECM »),
        convertie au format Google, et ouvre l'éditeur."""
        self.ensure_one()
        if not self.latest_version_id:
            raise UserError(_("Ce document n'a pas encore de fichier."))
        ext = (self.latest_version_id.file_extension or '').lower()
        if ext not in GOOGLE_MIME:
            raise UserError(_("Ce format (%s) ne s'ouvre pas dans Google Docs.", ext))
        if self.is_locked:
            raise UserError(_("Document finalisé ou archivé."))
        if self.is_checked_out and not self.checked_out_by_me:
            raise UserError(_("Réservé par %s.", self.checkout_user_id.name))
        client = self._gdrive_client()
        if client is None:
            return self.env['res.users']._google_authorize_action(
                return_model=self._name, return_id=self.id)
        if self.gdrive_file_id and self.gdrive_url:
            try:
                meta = client.metadata(self.gdrive_file_id)
                if not meta.get('trashed'):
                    return {'type': 'ir.actions.act_url', 'url': self.gdrive_url,
                            'target': 'new'}
            except GoogleDriveError:
                pass
        version = self.latest_version_id
        raw = base64.b64decode(version.attachment_id.sudo().datas or b'')
        try:
            folder_id = client.ensure_folder("AITE ECM")
            meta = client.upload(
                "%s - %s" % (self.reference, self.name), raw,
                version.mime_type or 'application/octet-stream', folder_id,
                convert_to=GOOGLE_MIME[ext])
        except GoogleDriveError as exc:
            raise UserError(str(exc))
        url = EDIT_URL.get(meta.get('mimeType'), meta.get('webViewLink'))
        url = url % meta['id'] if '%s' in url else url
        self.sudo().write({
            'gdrive_file_id': meta['id'], 'gdrive_mimetype': meta.get('mimeType'),
            'gdrive_url': url, 'gdrive_modified': meta.get('modifiedTime'),
            'gdrive_user_id': self.env.user.id,
            'gdrive_sync_date': fields.Datetime.now(), 'gdrive_error': False})
        if not self.is_checked_out:
            try:
                self.action_checkout()
            except UserError:
                pass
        self._audit(self, _("Ouverture dans Google Docs"), 'info', url)
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def _gdrive_pull(self, client=None, force=False):
        """Rapatrie la copie Google en nouvelle version si elle a changé."""
        self.ensure_one()
        if not self.gdrive_file_id:
            return False
        user = self.gdrive_user_id or self.env.user
        client = client or self._gdrive_client(user)
        if client is None:
            self.sudo().write({'gdrive_error': _(
                "Autorisation Google de %s expirée.") % user.name})
            return False
        meta = client.metadata(self.gdrive_file_id)
        if meta.get('trashed'):
            self.sudo().write({'gdrive_error': _("Copie Google supprimée."),
                               'gdrive_file_id': False, 'gdrive_url': False})
            return False
        if not force and meta.get('modifiedTime') == self.gdrive_modified:
            return False
        content, mimetype, ext = client.download(self.gdrive_file_id,
                                                 meta.get('mimeType'))
        latest = self.latest_version_id
        if latest and latest.sha256 == hashlib.sha256(content).hexdigest():
            self.sudo().write({'gdrive_modified': meta.get('modifiedTime')})
            return False
        if self.is_locked:
            self.sudo().write({'gdrive_error': _(
                "Modifié sur Google mais le document est finalisé/archivé.")})
            return False
        base = (latest.file_name or self.name).rsplit('.', 1)[0] \
            if latest else self.name
        filename = "%s.%s" % (base, ext or latest.file_extension or 'bin')
        self.with_user(user).sudo().with_context(
            audit_source='api', gdrive_skip=True).add_version(
            filename, base64.b64encode(content), _("Enregistré dans Google Docs"))
        self.sudo().write({'gdrive_modified': meta.get('modifiedTime'),
                           'gdrive_sync_date': fields.Datetime.now(),
                           'gdrive_error': False})
        self._audit(self, _("Version importée depuis Google Docs"), 'ok',
                    _("par %s") % user.name)
        return True

    def action_google_pull(self):
        for doc in self:
            try:
                created = doc._gdrive_pull(force=False)
            except GoogleDriveError as exc:
                raise UserError(str(exc))
            doc.message_post(body=_("Google Docs : %s") % (
                _("nouvelle version importée.") if created
                else _("aucune modification.")))
        return True

    def action_google_finish(self):
        """Rapatrie puis supprime la copie Drive et libère la réservation."""
        for doc in self.filtered('gdrive_file_id'):
            client = doc._gdrive_client(doc.gdrive_user_id or self.env.user)
            try:
                doc._gdrive_pull(client=client)
                if client:
                    client.delete(doc.gdrive_file_id)
            except GoogleDriveError as exc:
                raise UserError(str(exc))
            doc.sudo().write({'gdrive_file_id': False, 'gdrive_url': False,
                              'gdrive_mimetype': False, 'gdrive_modified': False,
                              'gdrive_error': False})
            if doc.is_checked_out and doc.checked_out_by_me:
                doc.action_checkin()
            doc._audit(doc, _("Édition Google terminée"), 'ok', '')
        return True

    # ------------------------------------------------------------------ #
    # Explorateur
    # ------------------------------------------------------------------ #
    def _explorer_record(self):
        rec = super()._explorer_record()
        rec.update({
            'libreoffice_uri': self.libreoffice_uri or False,
            'wopi_available': self.wopi_available,
            'wopi_edit_url': self._office_online_url('edit') if self.wopi_available else False,
            'gdrive_file_id': self.gdrive_file_id or False,
            'gdrive_url': self.gdrive_url or False,
        })
        return rec

    @api.model
    def explorer_meta(self):
        meta = super().explorer_meta()
        meta['google_configured'] = bool(
            self.env['res.users']._google_oauth_config()[0])
        meta['wopi_configured'] = bool(
            self.env['aite.ecm.office.token']._server_url())
        return meta

    @api.model
    def _cron_google_sync(self):
        docs = self.sudo().search([('gdrive_file_id', '!=', False)])
        for doc in docs:
            try:
                with self.env.cr.savepoint():
                    doc._gdrive_pull()
            except Exception as exc:  # noqa: BLE001
                doc.sudo().write({'gdrive_error': str(exc)[:500]})
                _logger.warning("[google] %s : %s", doc.reference, exc)
        return True
