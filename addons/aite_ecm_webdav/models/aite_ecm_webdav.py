# -*- coding: utf-8 -*-
"""Service WebDAV du plan de classement ECM.

Arborescence exposée : ``/<dossier>/<sous-dossier>/<REF - Titre.ext>`` plus un
dossier « Sans classement ». Toutes les opérations passent par l'ORM sous
l'identité de l'utilisateur authentifié : règles d'accès ECM, verrous et audit
s'appliquent exactement comme dans l'application.
"""
import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

UNFILED = "Sans classement"
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class WebdavError(Exception):
    status = 500

    def __init__(self, message=''):
        super().__init__(message)
        self.message = message


class WebdavNotFound(WebdavError):
    status = 404


class WebdavForbidden(WebdavError):
    status = 403


class WebdavLocked(WebdavError):
    status = 423


class WebdavConflict(WebdavError):
    status = 409


class WebdavBadRequest(WebdavError):
    status = 400


class WebdavUnsupportedMedia(WebdavError):
    status = 415


def sanitize(name):
    return _FORBIDDEN.sub('_', (name or '').strip()).strip('. ') or 'sans_nom'


class AiteEcmWebdav(models.AbstractModel):
    _name = 'aite.ecm.webdav'
    _description = "Service WebDAV ECM"

    # ------------------------------------------------------------------ #
    # Chemins
    # ------------------------------------------------------------------ #
    @api.model
    def _split(self, path):
        return [s for s in (path or '').split('/') if s]

    @api.model
    def _folder_segment(self, folder):
        return sanitize(folder.name)

    @api.model
    def _document_filename(self, document):
        version = document.latest_version_id
        ext = version.file_extension or ''
        base = "%s - %s" % (document.reference or document.id,
                            sanitize(document.name)[:80])
        return "%s.%s" % (base, ext) if ext else base

    @api.model
    def _folder_by_segments(self, segments):
        """Dossier ECM désigné par des segments ; ``False`` = racine,
        ``UNFILED`` = sans classement ; lève 404 si inconnu."""
        if not segments:
            return False
        if segments == [UNFILED]:
            return UNFILED
        Folder = self.env['aite.ecm.folder']
        current = Folder
        for seg in segments:
            domain = [('parent_id', '=', current.id if current else False)]
            match = Folder.search(domain).filtered(
                lambda f: self._folder_segment(f) == seg)[:1]
            if not match:
                raise WebdavNotFound()
            current = match
        return current

    @api.model
    def _documents_in(self, folder):
        domain = [('version_ids', '!=', False)]
        if folder == UNFILED:
            domain.append(('folder_id', '=', False))
        elif folder:
            domain.append(('folder_id', '=', folder.id))
        else:
            return self.env['aite.ecm.document']
        return self.env['aite.ecm.document'].search(domain, order='reference')

    @api.model
    def _document_by_filename(self, folder, filename):
        """Document désigné par un nom de fichier dans ``folder``.

        Quatre clés sont acceptées, de la plus précise à la plus tolérante.
        Le serveur expose ``RÉFÉRENCE - Titre.ext`` alors que le client
        manipule le nom qu'il a lui-même écrit : sans ces replis, un fichier
        déposé ou renommé devenait introuvable et un nouveau document était
        créé à chaque enregistrement.

        1. le nom **exposé** par le serveur ;
        2. le **titre** du document suivi de son extension — c'est le nom que
           le client vient d'employer lors d'un dépôt ou d'un renommage ;
        3. le nom **réel du fichier** de la dernière version ;
        4. la référence en tête du nom, lorsque le fichier a été réenregistré
           sous un autre titre par Office.
        """
        docs = self._documents_in(folder)
        exact = docs.filtered(lambda d: self._document_filename(d) == filename)[:1]
        if exact:
            return exact
        stem = filename.rsplit('.', 1)[0] if '.' in filename else filename
        by_title = docs.filtered(
            lambda d: sanitize(d.name)[:80] == stem)[:1]
        if by_title:
            return by_title
        by_file = docs.filtered(
            lambda d: (d.latest_version_id.file_name or '') == filename)[:1]
        if by_file:
            return by_file
        ref = filename.split(' - ', 1)[0].strip()
        return docs.filtered(lambda d: d.reference == ref)[:1]

    @api.model
    def _folder_path(self, folder):
        if folder == UNFILED:
            return UNFILED
        parts = []
        while folder:
            parts.insert(0, self._folder_segment(folder))
            folder = folder.parent_id
        return '/'.join(parts)

    @api.model
    def document_path(self, document):
        """Chemin WebDAV (relatif à la racine) d'un document."""
        folder = document.folder_id or UNFILED
        return "%s/%s" % (self._folder_path(folder),
                          self._document_filename(document))

    # ------------------------------------------------------------------ #
    # Descripteurs
    # ------------------------------------------------------------------ #
    def _descriptor(self, path, name, is_collection, doc=None):
        version = doc.latest_version_id if doc else None
        return {
            'path': path, 'name': name, 'is_collection': is_collection,
            'size': version.file_size if version else 0,
            'content_type': version.mime_type if version else None,
            'mtime': (version.upload_date or doc.write_date) if doc else None,
            'ctime': doc.create_date if doc else None,
            'etag': ('"%s"' % (version.sha256 or version.id)) if version else None,
            'locked': bool(doc and (doc.is_checked_out or doc.is_locked)),
        }

    def propfind(self, path, depth=1):
        segments = self._split(path)
        if segments and segments[-1] and '.' in segments[-1] and len(segments) >= 1:
            # tentative de fichier
            try:
                folder = self._folder_by_segments(segments[:-1]) if len(segments) > 1 \
                    else False
            except WebdavNotFound:
                folder = None
            if folder is not None and folder is not False:
                doc = self._document_by_filename(folder, segments[-1])
                if doc:
                    return [self._descriptor('/'.join(segments),
                                             self._document_filename(doc), False, doc)]
        folder = self._folder_by_segments(segments)
        base = '/'.join(segments)
        name = segments[-1] if segments else 'aite_ecm'
        resources = [self._descriptor(base, name, True)]
        if depth < 1:
            return resources
        Folder = self.env['aite.ecm.folder']
        if folder is False:
            children = Folder.search([('parent_id', '=', False)])
            for child in children:
                seg = self._folder_segment(child)
                resources.append(self._descriptor(seg, seg, True))
            resources.append(self._descriptor(UNFILED, UNFILED, True))
            return resources
        if folder != UNFILED:
            for child in Folder.search([('parent_id', '=', folder.id)]):
                seg = self._folder_segment(child)
                resources.append(self._descriptor("%s/%s" % (base, seg), seg, True))
        for doc in self._documents_in(folder):
            fname = self._document_filename(doc)
            resources.append(self._descriptor("%s/%s" % (base, fname), fname, False, doc))
        return resources

    # ------------------------------------------------------------------ #
    # Fichiers
    # ------------------------------------------------------------------ #
    def _resolve_file(self, path):
        segments = self._split(path)
        if len(segments) < 2:
            raise WebdavNotFound()
        folder = self._folder_by_segments(segments[:-1])
        doc = self._document_by_filename(folder, segments[-1])
        if not doc:
            raise WebdavNotFound()
        return folder, doc

    def read_file(self, path):
        _folder, doc = self._resolve_file(path)
        version = doc.latest_version_id
        raw = base64.b64decode(version.attachment_id.datas or b'')
        return doc, raw, version.mime_type or 'application/octet-stream'

    def put_file(self, path, content):
        """Enregistrement (Office, copie de fichier) → nouvelle version ;
        fichier inconnu dans un dossier → nouveau document."""
        segments = self._split(path)
        if len(segments) < 2:
            raise WebdavForbidden()
        folder = self._folder_by_segments(segments[:-1])
        filename = segments[-1]
        if filename.startswith(('~$', '.~lock', '._')) or filename.endswith('.tmp'):
            raise WebdavForbidden()      # fichiers temporaires d'Office
        doc = self._document_by_filename(folder, filename)
        datas = base64.b64encode(content)
        try:
            if doc:
                if doc.is_checked_out and not doc.checked_out_by_me:
                    raise WebdavLocked(_("Réservé par %s") % doc.checkout_user_id.name)
                if doc.is_locked:
                    raise WebdavLocked(_("Document finalisé ou archivé"))
                doc.with_context(audit_source='webdav').add_version(
                    filename, datas, _("Enregistré depuis le lecteur réseau"))
                return doc, False
            title = filename.rsplit('.', 1)[0] if '.' in filename else filename
            vals = {'name': title}
            if folder and folder != UNFILED:
                vals['folder_id'] = folder.id
            doc = self.env['aite.ecm.document'].with_context(
                audit_source='webdav').create(vals)
            doc.with_context(audit_source='webdav').add_version(filename, datas)
            return doc, True
        except AccessError as exc:
            raise WebdavForbidden(str(exc))
        except (UserError, ValidationError) as exc:
            raise WebdavConflict(str(exc))

    def lock(self, path):
        """LOCK Office/WebDAV → réservation ECM."""
        _folder, doc = self._resolve_file(path)
        if doc.is_locked:
            raise WebdavLocked(_("Document finalisé ou archivé"))
        if doc.is_checked_out and not doc.checked_out_by_me:
            raise WebdavLocked(_("Réservé par %s") % doc.checkout_user_id.name)
        if not doc.is_checked_out:
            try:
                doc.with_context(audit_source='webdav').action_checkout()
            except (AccessError, UserError) as exc:
                raise WebdavForbidden(str(exc))
        return doc

    def unlock(self, path):
        _folder, doc = self._resolve_file(path)
        if doc.is_checked_out and doc.checked_out_by_me:
            doc.with_context(audit_source='webdav').action_checkin()
        return doc

    def delete(self, path):
        _folder, doc = self._resolve_file(path)
        try:
            doc.with_context(audit_source='webdav').action_trash()
        except (AccessError, UserError) as exc:
            raise WebdavForbidden(str(exc))

    def move(self, source, destination):
        _folder, doc = self._resolve_file(source)
        dest = self._split(destination)
        if len(dest) < 2:
            raise WebdavConflict()
        target = self._folder_by_segments(dest[:-1])
        new_name = dest[-1]
        if new_name.startswith('~$') or new_name.endswith('.tmp'):
            raise WebdavForbidden()
        vals = {}
        title = new_name.rsplit('.', 1)[0] if '.' in new_name else new_name
        if title.startswith(doc.reference + ' - '):
            title = title[len(doc.reference) + 3:]
        if title and title != doc.name:
            vals['name'] = title
        target_id = False if target in (False, UNFILED) else target.id
        if target_id != doc.folder_id.id:
            vals['folder_id'] = target_id
        if vals:
            try:
                doc.with_context(audit_source='webdav').write(vals)
            except (AccessError, UserError) as exc:
                raise WebdavForbidden(str(exc))
        return doc

    def mkcol(self, path):
        segments = self._split(path)
        if not segments:
            raise WebdavConflict()
        parent = self._folder_by_segments(segments[:-1])
        if parent == UNFILED:
            raise WebdavForbidden()
        try:
            return self.env['aite.ecm.folder'].create({
                'name': segments[-1], 'parent_id': parent.id if parent else False})
        except AccessError as exc:
            raise WebdavForbidden(str(exc))
