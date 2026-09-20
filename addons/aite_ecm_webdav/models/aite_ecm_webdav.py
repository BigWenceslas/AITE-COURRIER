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


def _is_unfiled(folder):
    """``True`` pour le repère « sans classement ».

    Le plan de classement manipule indifféremment un ``aite.ecm.folder`` ou
    la chaîne ``UNFILED`` ; comparer un enregistrement à une chaîne avec
    ``==`` déclenche un avertissement Odoo et renvoie toujours ``False``.
    """
    return isinstance(folder, str) and folder == UNFILED
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
        if _is_unfiled(folder):
            domain.append(('folder_id', '=', False))
        elif folder:
            domain.append(('folder_id', '=', folder.id))
        else:
            return self.env['aite.ecm.document']
        return self.env['aite.ecm.document'].search(domain, order='reference')

    @api.model
    def _document_by_filename(self, folder, filename):
        docs = self._documents_in(folder)
        exact = docs.filtered(lambda d: self._document_filename(d) == filename)[:1]
        if exact:
            return exact
        # repli : la référence en tête du nom (fichier réenregistré sous un
        # autre nom par Office)
        ref = filename.split(' - ', 1)[0].strip()
        by_reference = docs.filtered(lambda d: d.reference == ref)[:1]
        if by_reference:
            return by_reference
        # repli : le titre seul. L'ECM republie « RÉFÉRENCE - Titre.ext », mais
        # un client qui vient de déposer « Titre.ext » le redemande sous ce
        # nom-là — sans quoi l'Explorateur Windows ne retrouve pas le fichier
        # qu'il vient de créer.
        title = filename.rsplit('.', 1)[0] if '.' in filename else filename
        return docs.filtered(lambda d: d.name == title)[:1]

    @api.model
    def _folder_path(self, folder):
        if _is_unfiled(folder):
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
    def _descriptor(self, path, name, is_collection, doc=None, folder=None):
        version = doc.latest_version_id if doc else None
        if doc:
            mtime, ctime = version.upload_date or doc.write_date, doc.create_date
        elif folder:
            mtime, ctime = folder.write_date, folder.create_date
        else:
            # Racine et « Sans classement » : le client WebDAV de Windows
            # refuse d'ouvrir une collection sans date de modification. On
            # sert l'instant, comme le fait le lecteur du courrier.
            mtime, ctime = fields.Datetime.now(), None
        return {
            'path': path, 'name': name, 'is_collection': is_collection,
            'size': version.file_size if version else 0,
            'content_type': version.mime_type if version else None,
            'mtime': mtime,
            'ctime': ctime,
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
        record = folder if folder and not _is_unfiled(folder) else None
        resources = [self._descriptor(base, name, True, folder=record)]
        if depth < 1:
            return resources
        Folder = self.env['aite.ecm.folder']
        if folder is False:
            children = Folder.search([('parent_id', '=', False)])
            for child in children:
                seg = self._folder_segment(child)
                resources.append(self._descriptor(seg, seg, True, folder=child))
            resources.append(self._descriptor(UNFILED, UNFILED, True))
            return resources
        if not _is_unfiled(folder):
            for child in Folder.search([('parent_id', '=', folder.id)]):
                seg = self._folder_segment(child)
                resources.append(self._descriptor("%s/%s" % (base, seg), seg, True,
                                                  folder=child))
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
            if folder and not _is_unfiled(folder):
                vals['folder_id'] = folder.id
            # Création et première version dans un même savepoint : le
            # contrôleur convertit l'erreur en réponse HTTP (409), la
            # transaction est donc validée. Sans ce savepoint, un format
            # refusé laisserait derrière lui un document sans version —
            # invisible du lecteur réseau, mais bien présent en base.
            with self.env.cr.savepoint():
                doc = self.env['aite.ecm.document'].with_context(
                    audit_source='webdav').create(vals)
                doc.with_context(audit_source='webdav').add_version(
                    filename, datas)
            return doc, True
        except AccessError as exc:
            raise WebdavForbidden(str(exc))
        except (UserError, ValidationError) as exc:
            raise WebdavConflict(str(exc))

    def lock(self, path):
        """LOCK Office/WebDAV → réservation ECM.

        Un verrou posé sur un nom **encore libre** (ressource « lock-null » de
        la RFC 4918) n'est pas une anomalie : c'est ainsi que l'Explorateur
        Windows crée un fichier — il verrouille le nom, dépose le contenu,
        puis libère. Refuser ce verrou, c'est refuser toute création depuis le
        lecteur réseau. On vérifie donc seulement que le dossier existe et
        qu'on a le droit d'y écrire ; rien n'est créé ici, c'est le PUT qui
        créera le document. Retourne un enregistrement vide dans ce cas, ce
        qui vaut au contrôleur un 201 plutôt qu'un 200.
        """
        try:
            _folder, doc = self._resolve_file(path)
        except WebdavNotFound:
            return self._lock_free_name(path)
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

    @api.model
    def _lock_free_name(self, path):
        """Verrou sur un nom libre : contrôle le dossier d'accueil."""
        segments = self._split(path)
        if len(segments) < 2:
            raise WebdavForbidden()
        folder = self._folder_by_segments(segments[:-1])   # 404 si inconnu
        if folder and not _is_unfiled(folder) \
                and not folder.user_can(self.env.user, 'write') \
                and not self.env['aite.ecm.document']._is_manager():
            raise WebdavForbidden(
                _("Écriture refusée dans le dossier « %s ».", folder.name))
        return self.env['aite.ecm.document']

    def unlock(self, path):
        try:
            _folder, doc = self._resolve_file(path)
        except WebdavNotFound:
            # Libération d'un nom resté libre (création abandonnée) : rien à
            # faire, et surtout pas une erreur.
            return self.env['aite.ecm.document']
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
        target_id = False if not target or _is_unfiled(target) else target.id
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
        if _is_unfiled(parent):
            raise WebdavForbidden()
        try:
            return self.env['aite.ecm.folder'].create({
                'name': segments[-1], 'parent_id': parent.id if parent else False})
        except AccessError as exc:
            raise WebdavForbidden(str(exc))
