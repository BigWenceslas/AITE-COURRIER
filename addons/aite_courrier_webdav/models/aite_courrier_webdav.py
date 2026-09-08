# -*- coding: utf-8 -*-
"""Service WebDAV de l'espace documentaire AITE Courrier.

Toute la logique métier du WebDAV vit ici (résolution de chemin, listage,
lecture / écriture / suppression), ce qui la rend **testable** sans serveur
HTTP. Le contrôleur ``controllers/webdav.py`` n'est qu'un adaptateur qui
traduit les verbes WebDAV en appels à ce service et formate les réponses HTTP.

Toutes les opérations s'appuient sur les points d'accroche déjà prévus côté
GED (cf. ``aite_courrier_ged/docs/WEBDAV_READINESS.md``) et s'exécutent avec
les droits de ``self.env.user`` (l'utilisateur authentifié en HTTP Basic).
"""
import base64

from odoo import api, models, fields
from odoo.exceptions import AccessError, ValidationError

#: Préfixe d'URL sous lequel le contrôleur expose l'arborescence.
ROOT_PATH = '/webdav/aite_courrier'


# --------------------------------------------------------------------------- #
# Erreurs traduites en codes HTTP par le contrôleur
# --------------------------------------------------------------------------- #
class WebdavError(Exception):
    """Erreur WebDAV portant le code HTTP à renvoyer."""
    status = 500
    label = "Internal Server Error"

    def __init__(self, message=''):
        super().__init__(message or self.label)


class WebdavNotFound(WebdavError):
    status = 404
    label = "Not Found"


class WebdavForbidden(WebdavError):
    status = 403
    label = "Forbidden"


class WebdavLocked(WebdavError):
    status = 423
    label = "Locked"


class WebdavConflict(WebdavError):
    status = 409
    label = "Conflict"


class WebdavBadRequest(WebdavError):
    status = 400
    label = "Bad Request"


class AiteCourrierWebdav(models.AbstractModel):
    """Service (sans table) exposant la GED en WebDAV.

    Niveaux de l'arborescence ::

        /                       -> racine (collection de courriers)
        /<référence>            -> collection des documents d'un courrier
        /<référence>/<fichier>  -> un document (sa dernière version)
    """

    _name = 'aite.courrier.webdav'
    _description = "Service WebDAV AITE Courrier"

    # ------------------------------------------------------------------ #
    # Helpers de chemin
    # ------------------------------------------------------------------ #
    @api.model
    def _split_path(self, path):
        """Découpe un chemin en segments non vides."""
        return [segment for segment in (path or '').split('/') if segment]

    @api.model
    def _document_filename(self, document):
        """Nom de fichier exposé pour un document (nom + extension)."""
        extension = document.file_extension
        name = document.name or ('document-%d' % document.id)
        if extension and not name.lower().endswith('.' + extension.lower()):
            return '%s.%s' % (name, extension)
        return name

    # ------------------------------------------------------------------ #
    # Résolution / contrôle d'accès
    # ------------------------------------------------------------------ #
    @api.model
    def _accessible_courriers(self):
        """Courriers déjà enregistrés (avec référence) visibles par l'utilisateur."""
        courriers = self.env['aite.courrier'].search([('reference', '!=', False)])
        return courriers.filtered(
            lambda c: c._check_courrier_access(self.env.user))

    @api.model
    def _courrier_by_reference(self, reference):
        courrier = self.env['aite.courrier'].search(
            [('reference', '=', reference)], limit=1)
        if not courrier:
            raise WebdavNotFound()
        if not courrier._check_courrier_access(self.env.user):
            raise WebdavForbidden()
        return courrier

    @api.model
    def _readable_documents(self, courrier):
        return courrier.document_ids.filtered(
            lambda d: d._check_document_access('read', self.env.user))

    @api.model
    def _document_by_filename(self, courrier, filename):
        target = (filename or '').lower()
        for document in courrier.document_ids:
            if self._document_filename(document).lower() == target:
                return document
        return self.env['aite.courrier.document']

    # ------------------------------------------------------------------ #
    # Descripteurs de ressource (consommés par le contrôleur pour PROPFIND)
    # ------------------------------------------------------------------ #
    @api.model
    def _root_descriptor(self):
        return {
            'name': 'aite_courrier', 'path': '', 'is_collection': True,
            'size': 0, 'content_type': None,
            'ctime': False, 'mtime': fields.Datetime.now(), 'locked': False,
        }

    @api.model
    def _courrier_descriptor(self, courrier):
        return {
            'name': courrier.reference, 'path': courrier.reference,
            'is_collection': True, 'size': 0, 'content_type': None,
            'ctime': courrier.create_date, 'mtime': courrier.write_date,
            'locked': courrier.state == 'ar',
        }

    @api.model
    def _document_descriptor(self, courrier, document):
        version = document.latest_version_id
        filename = self._document_filename(document)
        return {
            'name': filename,
            'path': '%s/%s' % (courrier.reference, filename),
            'is_collection': False,
            'size': version.file_size or 0,
            'content_type': version.mime_type or 'application/octet-stream',
            'ctime': document.create_date, 'mtime': document.write_date,
            'locked': document.is_locked,
        }

    # ------------------------------------------------------------------ #
    # PROPFIND : lister une ressource (et ses enfants si depth >= 1)
    # ------------------------------------------------------------------ #
    @api.model
    def propfind(self, path, depth=1):
        segments = self._split_path(path)
        if len(segments) == 0:
            resources = [self._root_descriptor()]
            if depth >= 1:
                resources += [self._courrier_descriptor(c)
                              for c in self._accessible_courriers()]
            return resources
        if len(segments) == 1:
            courrier = self._courrier_by_reference(segments[0])
            resources = [self._courrier_descriptor(courrier)]
            if depth >= 1:
                resources += [self._document_descriptor(courrier, d)
                              for d in self._readable_documents(courrier)]
            return resources
        if len(segments) == 2:
            courrier = self._courrier_by_reference(segments[0])
            document = self._document_by_filename(courrier, segments[1])
            if not document:
                raise WebdavNotFound()
            if not document._check_document_access('read', self.env.user):
                raise WebdavForbidden()
            return [self._document_descriptor(courrier, document)]
        raise WebdavNotFound()

    # ------------------------------------------------------------------ #
    # GET : contenu de la dernière version d'un document
    # ------------------------------------------------------------------ #
    @api.model
    def read_file(self, path):
        segments = self._split_path(path)
        if len(segments) != 2:
            raise WebdavForbidden()
        courrier = self._courrier_by_reference(segments[0])
        document = self._document_by_filename(courrier, segments[1])
        if not document:
            raise WebdavNotFound()
        if not document._check_document_access('read', self.env.user):
            raise WebdavForbidden()
        version = document.latest_version_id
        if version and version.attachment_id.datas:
            content = base64.b64decode(version.attachment_id.datas)
        else:
            content = b''
        return {
            'filename': self._document_filename(document),
            'content': content,
            'content_type': (version.mime_type if version else None)
            or 'application/octet-stream',
            'mtime': document.write_date,
        }

    # ------------------------------------------------------------------ #
    # PUT : déposer un fichier -> nouvelle version (création si nécessaire)
    # ------------------------------------------------------------------ #
    @api.model
    def put_file(self, path, content):
        segments = self._split_path(path)
        if len(segments) != 2:
            raise WebdavForbidden()
        courrier = self._courrier_by_reference(segments[0])
        filename = segments[1]
        document = self._document_by_filename(courrier, filename)
        created = False
        if not document:
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            document = self.env['aite.courrier.document'].with_context(
                audit_source='webdav').create({
                    'name': base_name, 'courrier_id': courrier.id})
            created = True
        if document.is_locked:
            if created:
                document.unlink()
            raise WebdavLocked()
        datas = base64.b64encode(content or b'').decode()
        try:
            document.with_context(audit_source='webdav').add_version(filename, datas)
        except AccessError:
            if created:
                document.unlink()
            raise WebdavForbidden()
        except ValidationError as error:
            if created:
                document.unlink()
            raise WebdavConflict(str(error))
        return {'created': created}

    # ------------------------------------------------------------------ #
    # DELETE : supprimer un document (refusé si verrouillé)
    # ------------------------------------------------------------------ #
    @api.model
    def delete_resource(self, path):
        segments = self._split_path(path)
        if len(segments) != 2:
            # On ne supprime ni la racine ni un courrier via WebDAV.
            raise WebdavForbidden()
        courrier = self._courrier_by_reference(segments[0])
        document = self._document_by_filename(courrier, segments[1])
        if not document:
            raise WebdavNotFound()
        if not document._check_document_access('write', self.env.user):
            if document.is_locked:
                raise WebdavLocked()
            raise WebdavForbidden()
        document.with_context(audit_source='webdav').unlink()
        return True

    # ------------------------------------------------------------------ #
    # MOVE : renommage d'un document au sein du même courrier
    # ------------------------------------------------------------------ #
    @api.model
    def move_resource(self, source, destination):
        source_segments = self._split_path(source)
        dest_segments = self._split_path(destination)
        if len(source_segments) != 2 or len(dest_segments) != 2:
            raise WebdavForbidden()
        if source_segments[0] != dest_segments[0]:
            # Déplacement entre courriers non pris en charge.
            raise WebdavForbidden()
        courrier = self._courrier_by_reference(source_segments[0])
        document = self._document_by_filename(courrier, source_segments[1])
        if not document:
            raise WebdavNotFound()
        if not document._check_document_access('write', self.env.user):
            if document.is_locked:
                raise WebdavLocked()
            raise WebdavForbidden()
        new_name = dest_segments[1]
        base_name = new_name.rsplit('.', 1)[0] if '.' in new_name else new_name
        document.write({'name': base_name})
        return True
