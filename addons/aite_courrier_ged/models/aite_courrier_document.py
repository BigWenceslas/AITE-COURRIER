# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class AiteCourrierDocument(models.Model):
    """Document rattaché à un courrier : conteneur de versions de pièces jointes.

    La confidentialité est HÉRITÉE du courrier (champ related stocké) et un
    document dont la version est finale/archivée — ou dont le courrier est
    archivé — est verrouillé (``is_locked``) : ses versions ne sont plus
    modifiables. Ces deux notions, avec :meth:`_check_document_access`, sont les
    points d'accroche prévus pour le futur provider WebDAV (cf.
    docs/WEBDAV_READINESS.md).
    """

    _name = 'aite.courrier.document'
    _description = "Document de courrier"
    _order = 'create_date desc, id desc'

    # Extensions et taille autorisées (attributs de classe : surchargeables/
    # patchables, notamment en test). Benchmark GEC : au-delà de la bureautique,
    # accepter les images (courrier photographié / scanné en image) et les
    # e-mails archivés (EML/MSG).
    ALLOWED_EXTENSIONS = (
        'pdf', 'docx', 'xlsx',
        'jpg', 'jpeg', 'png', 'tif', 'tiff',
        'eml', 'msg',
    )
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo
    MIME_BY_EXT = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'tif': 'image/tiff',
        'tiff': 'image/tiff',
        'eml': 'message/rfc822',
        'msg': 'application/vnd.ms-outlook',
    }

    name = fields.Char(string="Nom", required=True)
    courrier_id = fields.Many2one(
        comodel_name='aite.courrier', string="Courrier", required=True,
        ondelete='cascade', index=True,
    )
    folder_id = fields.Many2one(
        comodel_name='aite.courrier.folder', string="Dossier", ondelete='restrict',
    )
    tag_ids = fields.Many2many(
        comodel_name='aite.courrier.document.tag',
        relation='aite_courrier_document_tag_rel',
        column1='document_id', column2='tag_id', string="Étiquettes",
    )
    # Confidentialité HÉRITÉE du courrier : related stocké, recalculé si la
    # confidentialité du courrier change.
    confidentiality_id = fields.Many2one(
        comodel_name='aite.courrier.confidentiality',
        string="Confidentialité (héritée)",
        related='courrier_id.confidentiality_id', store=True, readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', "Brouillon"),
            ('final', "Finalisé"),
            ('archived', "Archivé"),
        ],
        string="État", default='draft', required=True,
    )
    is_locked = fields.Boolean(
        string="Verrouillé", compute='_compute_is_locked', store=True,
        help="Vrai si le document est finalisé/archivé ou si son courrier est "
             "archivé : les versions ne sont alors plus modifiables.",
    )
    version_ids = fields.One2many(
        comodel_name='aite.courrier.document.version', inverse_name='document_id',
        string="Versions",
    )
    version_count = fields.Integer(
        string="Nombre de versions", compute='_compute_versions', store=True)
    latest_version_id = fields.Many2one(
        comodel_name='aite.courrier.document.version', string="Dernière version",
        compute='_compute_versions', store=True)
    file_extension = fields.Char(
        string="Extension", compute='_compute_versions', store=True)

    # Zone de téléversement (transient à l'écran ; non stockée durablement).
    upload_file = fields.Binary(string="Fichier à téléverser")
    upload_filename = fields.Char(string="Nom du fichier")

    # ------------------------------------------------------------------ #
    # Création : auto-classement
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-classement : à défaut de dossier explicite, applique le dossier
        par défaut du type de courrier (``type_id.default_folder_id``)."""
        for vals in vals_list:
            if not vals.get('folder_id') and vals.get('courrier_id'):
                courrier = self.env['aite.courrier'].browse(vals['courrier_id'])
                default_folder = courrier.type_id.default_folder_id
                if default_folder:
                    vals['folder_id'] = default_folder.id
        return super().create(vals_list)

    # ------------------------------------------------------------------ #
    # Calculs
    # ------------------------------------------------------------------ #
    @api.depends('state', 'courrier_id.state')
    def _compute_is_locked(self):
        for document in self:
            document.is_locked = (
                document.state in ('final', 'archived')
                or document.courrier_id.state == 'ar'
            )

    @api.depends('version_ids', 'version_ids.upload_date')
    def _compute_versions(self):
        for document in self:
            versions = document.version_ids.sorted(
                key=lambda v: (v.upload_date or fields.Datetime.now(), v.id))
            document.version_count = len(versions)
            document.latest_version_id = versions[-1:].id
            document.file_extension = versions[-1:].file_extension or False

    # ------------------------------------------------------------------ #
    # Contrat d'accès central (UI + futur WebDAV)
    # ------------------------------------------------------------------ #
    def _check_document_access(self, operation='read', user=None):
        """Contrat d'accès centralisé du document.

        Utilisé par l'UI et **conçu pour être appelé tel quel par le futur
        provider WebDAV** (``aite_courrier_webdav``). Renvoie un booléen et ne
        lève pas : c'est l'appelant qui décide d'émettre une erreur / un 403.

        Règles :
          * ``read`` : autorisé si l'utilisateur a accès au courrier rattaché,
            c'est-à-dire selon la confidentialité héritée — délégué à
            ``aite.courrier._check_courrier_access`` (logique unique côté core).
          * ``write`` / ``unlink`` : mêmes règles de confidentialité que la
            lecture, ET refusé si le document est verrouillé (``is_locked``) :
            les versions finales/archivées sont en lecture seule.
        """
        self.ensure_one()
        user = user or self.env.user
        if not self.courrier_id._check_courrier_access(user):
            return False
        if operation in ('write', 'unlink') and self.is_locked:
            return False
        return True

    # ------------------------------------------------------------------ #
    # Versioning
    # ------------------------------------------------------------------ #
    def _next_version_label(self):
        self.ensure_one()
        numbers = [
            int(v.version[1:]) for v in self.version_ids
            if v.version[:1] == 'v' and v.version[1:].isdigit()
        ]
        return 'v%d' % ((max(numbers) if numbers else 0) + 1)

    def add_version(self, filename, datas):
        """Crée une nouvelle version v(n+1) à partir d'un contenu encodé base64.

        Contrôle l'extension (cf. ALLOWED_EXTENSIONS) et la taille (≤ 50 Mo), conserve
        les versions précédentes, et trace un audit « Ajout pièce jointe ».
        """
        self.ensure_one()
        if not self._check_document_access('write'):
            raise AccessError(_(
                "Téléversement impossible : document verrouillé ou accès refusé."))
        if not filename:
            raise ValidationError(_("Le nom du fichier est requis."))
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(_(
                "Format de fichier non autorisé (« %s »). "
                "Formats acceptés : %s.",
                extension or filename,
                ', '.join(ext.upper() for ext in self.ALLOWED_EXTENSIONS)))
        try:
            raw = base64.b64decode(datas or b'')
        except Exception:
            raise ValidationError(_("Contenu de fichier invalide."))
        size = len(raw)
        if size > self.MAX_FILE_SIZE:
            raise ValidationError(_(
                "Fichier trop volumineux (%.1f Mo). Taille maximale : %d Mo.",
                size / 1024.0 / 1024.0, self.MAX_FILE_SIZE // (1024 * 1024)))
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': datas,
            'res_model': 'aite.courrier.document',
            'res_id': self.id,
            'mimetype': self.MIME_BY_EXT.get(extension),
        })
        version = self.env['aite.courrier.document.version'].create({
            'document_id': self.id,
            'version': self._next_version_label(),
            'attachment_id': attachment.id,
            'file_size': size,
            'mime_type': attachment.mimetype,
            'uploaded_by': self.env.user.id,
            'upload_date': fields.Datetime.now(),
        })
        self.env['aite.courrier.audit.log']._log(
            self.env, _("Ajout pièce jointe"), 'info', 'aite.courrier.document',
            self.id, self.name,
            _("%s — %s (%.0f Ko)") % (version.version, filename, size / 1024.0),
            self.env.context.get('audit_source', 'ui'))
        return version

    def action_upload_version(self):
        """Bouton UI : crée une version depuis la zone de téléversement."""
        for document in self:
            if document.upload_file:
                document.add_version(document.upload_filename, document.upload_file)
                document.write({'upload_file': False, 'upload_filename': False})
        return True

    def action_preview_latest(self):
        """Ouvre/prévisualise la dernière version dans un nouvel onglet."""
        self.ensure_one()
        if not self.latest_version_id:
            raise ValidationError(_("Ce document n'a aucune version à prévisualiser."))
        return self.latest_version_id.action_open_file()

    def action_mark_final(self):
        self.write({'state': 'final'})
        return True

    def action_mark_archived(self):
        self.write({'state': 'archived'})
        return True

    def action_reset_draft(self):
        self.write({'state': 'draft'})
        return True
