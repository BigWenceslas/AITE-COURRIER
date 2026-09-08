# -*- coding: utf-8 -*-
import base64
import hashlib
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class AiteEcmDocument(models.Model):
    """Document d'entreprise : l'unité de base de l'ECM.

    Autonome (ou rattaché à n'importe quel enregistrement Odoo via
    ``res_model`` / ``res_id``), typé, décrit par des métadonnées, classé,
    versionné, verrouillable (check-out), reliable à d'autres documents,
    et gouverné par une règle d'accès **centralisée** :
    :meth:`_check_document_access`.
    """

    _name = 'aite.ecm.document'
    _description = "Document ECM"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    ALLOWED_EXTENSIONS = (
        'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
        'odt', 'ods', 'odp', 'txt', 'csv', 'rtf',
        'jpg', 'jpeg', 'png', 'tif', 'tiff', 'gif',
        'eml', 'msg', 'zip', 'xml', 'json',
    )
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 Mo
    MIME_BY_EXT = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet',
        'pptx': 'application/vnd.openxmlformats-officedocument.'
                'presentationml.presentation',
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
        'tif': 'image/tiff', 'tiff': 'image/tiff', 'gif': 'image/gif',
        'txt': 'text/plain', 'csv': 'text/csv', 'xml': 'application/xml',
        'json': 'application/json', 'zip': 'application/zip',
        'eml': 'message/rfc822', 'msg': 'application/vnd.ms-outlook',
    }
    # Champs figés une fois le document archivé.
    _CONTENT_FIELDS = {'name', 'type_id', 'folder_id', 'properties',
                       'confidentiality_id', 'res_model', 'res_id',
                       'description', 'tag_ids'}

    # ------------------------------------------------------------------ #
    # Identité, classement, rattachement
    # ------------------------------------------------------------------ #
    reference = fields.Char(
        string="Référence", readonly=True, copy=False, index=True,
        default=lambda self: _("Nouveau"))
    name = fields.Char(string="Titre", required=True, tracking=True)
    type_id = fields.Many2one(
        comodel_name='aite.ecm.document.type', string="Type",
        ondelete='restrict', tracking=True, index=True)
    properties = fields.Properties(
        string="Métadonnées", definition='type_id.metadata_definition',
        copy=True)
    folder_id = fields.Many2one(
        comodel_name='aite.ecm.folder', string="Dossier de classement",
        ondelete='restrict', tracking=True, index=True)
    tag_ids = fields.Many2many(
        comodel_name='aite.ecm.tag', relation='aite_ecm_document_tag_rel',
        column1='document_id', column2='tag_id', string="Étiquettes")
    confidentiality_id = fields.Many2one(
        comodel_name='aite.courrier.confidentiality',
        string="Confidentialité", ondelete='restrict', tracking=True,
        default=lambda self: self.env.ref(
            'aite_courrier_base.confidentiality_internal',
            raise_if_not_found=False))
    confidentiality_code = fields.Char(
        related='confidentiality_id.code', store=True, string="Code conf.")
    owner_id = fields.Many2one(
        comodel_name='res.users', string="Propriétaire", tracking=True,
        default=lambda self: self.env.user, index=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string="Société",
        default=lambda self: self.env.company)
    description = fields.Text(string="Description")
    shared_user_ids = fields.Many2many(
        comodel_name='res.users', relation='aite_ecm_document_reader_rel',
        column1='document_id', column2='user_id', string="Partagé en lecture avec",
        domain=[('share', '=', False)],
        help="Personnes autorisées à consulter ce document, même s'il est "
             "confidentiel ou dans un dossier qui leur est fermé.")
    editor_user_ids = fields.Many2many(
        comodel_name='res.users', relation='aite_ecm_document_editor_rel',
        column1='document_id', column2='user_id', string="Partagé en écriture avec",
        domain=[('share', '=', False)],
        help="Personnes autorisées à modifier ce document et à y ajouter "
             "des versions.")
    access_summary = fields.Text(
        string="Qui peut accéder", compute='_compute_access_summary')
    res_model = fields.Char(string="Modèle lié", index=True, copy=False)
    res_id = fields.Many2oneReference(
        string="ID lié", model_field='res_model', index=True, copy=False)
    res_display = fields.Char(
        string="Enregistrement lié", compute='_compute_res_display')

    # ------------------------------------------------------------------ #
    # Cycle de vie, corbeille
    # ------------------------------------------------------------------ #
    state = fields.Selection(
        selection=[('draft', "Brouillon"), ('final', "Finalisé"),
                   ('archived', "Archivé")],
        string="Statut", default='draft', required=True, tracking=True,
        index=True)
    is_locked = fields.Boolean(string="Verrouillé", compute='_compute_is_locked')
    active = fields.Boolean(string="Actif", default=True,
                            help="Décoché = document dans la corbeille.")
    trashed_date = fields.Datetime(string="Mis à la corbeille le",
                                   readonly=True, copy=False)
    trashed_uid = fields.Many2one(
        comodel_name='res.users', string="Mis à la corbeille par",
        readonly=True, copy=False)

    # ------------------------------------------------------------------ #
    # Versions
    # ------------------------------------------------------------------ #
    version_ids = fields.One2many(
        comodel_name='aite.ecm.document.version', inverse_name='document_id',
        string="Versions")
    version_count = fields.Integer(string="Nb versions",
                                   compute='_compute_versions')
    latest_version_id = fields.Many2one(
        comodel_name='aite.ecm.document.version',
        string="Dernière version", compute='_compute_versions')
    file_name = fields.Char(related='latest_version_id.file_name',
                            string="Fichier")
    file_extension = fields.Char(related='latest_version_id.file_extension',
                                 string="Extension")
    upload_file = fields.Binary(string="Nouvelle version", attachment=False)
    upload_filename = fields.Char(string="Nom du fichier")
    upload_comment = fields.Char(string="Commentaire")

    # ------------------------------------------------------------------ #
    # Check-out / check-in
    # ------------------------------------------------------------------ #
    checkout_user_id = fields.Many2one(
        comodel_name='res.users', string="Réservé par", readonly=True,
        copy=False, tracking=True)
    checkout_date = fields.Datetime(string="Réservé le", readonly=True,
                                    copy=False)
    checkout_expiry = fields.Datetime(string="Expiration de la réservation",
                                      readonly=True, copy=False)
    is_checked_out = fields.Boolean(compute='_compute_checkout')
    checked_out_by_me = fields.Boolean(compute='_compute_checkout')

    # ------------------------------------------------------------------ #
    # Relations, doublons, recherche
    # ------------------------------------------------------------------ #
    link_ids = fields.One2many(
        comodel_name='aite.ecm.document.link', inverse_name='document_id',
        string="Relations")
    reverse_link_ids = fields.One2many(
        comodel_name='aite.ecm.document.link', inverse_name='target_id',
        string="Relations entrantes")
    link_count = fields.Integer(compute='_compute_link_count')
    duplicate_ids = fields.Many2many(
        comodel_name='aite.ecm.document', string="Doublons",
        compute='_compute_duplicates')
    duplicate_count = fields.Integer(compute='_compute_duplicates')
    content_fulltext = fields.Char(
        string="Contenu des pièces", compute='_compute_content_fulltext',
        search='_search_content_fulltext')

    # ================================================================== #
    # Calculs
    # ================================================================== #
    @api.depends('res_model', 'res_id')
    def _compute_res_display(self):
        for doc in self:
            display = False
            if doc.res_model and doc.res_id and doc.res_model in self.env:
                record = self.env[doc.res_model].sudo().browse(doc.res_id)
                if record.exists():
                    model_name = self.env['ir.model'].sudo()._get(
                        doc.res_model).name
                    display = "%s : %s" % (model_name, record.display_name)
            doc.res_display = display

    @api.depends('folder_id.access_summary', 'confidentiality_code',
                 'owner_id', 'shared_user_ids', 'editor_user_ids')
    def _compute_access_summary(self):
        for doc in self:
            lines = []
            if doc.confidentiality_code in ('CONF', 'SEC'):
                lines.append(_("%s : réservé au propriétaire (%s), au créateur, "
                               "aux managers et aux personnes partagées.")
                             % (doc.confidentiality_id.name,
                                doc.owner_id.name or '—'))
            elif doc.folder_id:
                lines.append(doc.folder_id.access_summary)
            else:
                lines.append(_("Sans dossier : lecture et écriture ouvertes à "
                               "tous les rôles ECM."))
            if doc.shared_user_ids:
                lines.append(_("Lecture partagée avec : %s") % ", ".join(
                    doc.shared_user_ids.mapped('name')))
            if doc.editor_user_ids:
                lines.append(_("Écriture partagée avec : %s") % ", ".join(
                    doc.editor_user_ids.mapped('name')))
            doc.access_summary = "\n".join(lines)

    @api.depends('state')
    def _compute_is_locked(self):
        for doc in self:
            doc.is_locked = doc.state in ('final', 'archived')

    @api.depends('version_ids')
    def _compute_versions(self):
        for doc in self:
            versions = doc.version_ids.sorted(key=lambda v: v.id)
            doc.version_count = len(versions)
            doc.latest_version_id = versions[-1:] or False

    @api.depends('checkout_user_id', 'checkout_expiry')
    def _compute_checkout(self):
        now = fields.Datetime.now()
        for doc in self:
            active = bool(doc.checkout_user_id) and (
                not doc.checkout_expiry or doc.checkout_expiry > now)
            doc.is_checked_out = active
            doc.checked_out_by_me = active and (
                doc.checkout_user_id == self.env.user)

    @api.depends('link_ids', 'reverse_link_ids')
    def _compute_link_count(self):
        for doc in self:
            doc.link_count = len(doc.link_ids) + len(doc.reverse_link_ids)

    @api.depends('version_ids.sha256')
    def _compute_duplicates(self):
        Version = self.env['aite.ecm.document.version'].sudo()
        for doc in self:
            sha = doc.latest_version_id.sha256
            dups = self.env['aite.ecm.document']
            if sha:
                others = Version.search([('sha256', '=', sha),
                                         ('document_id', '!=', doc.id)])
                dups = others.mapped('document_id').filtered('active')
            doc.duplicate_ids = dups
            doc.duplicate_count = len(dups)

    def _compute_content_fulltext(self):
        for doc in self:
            doc.content_fulltext = False

    def _search_content_fulltext(self, operator, value):
        attachments = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'aite.ecm.document'),
            ('index_content', operator, value)])
        return [('id', 'in', attachments.mapped('res_id'))]

    # ================================================================== #
    # CRUD
    # ================================================================== #
    @api.model_create_multi
    def create(self, vals_list):
        Type = self.env['aite.ecm.document.type']
        for vals in vals_list:
            if not vals.get('reference') or vals['reference'] == _("Nouveau"):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'aite.ecm.document') or _("Nouveau")
            doc_type = Type.browse(vals['type_id']) if vals.get('type_id') \
                else Type
            if doc_type:
                if not vals.get('folder_id') and doc_type.default_folder_id:
                    vals['folder_id'] = doc_type.default_folder_id.id
                if not vals.get('confidentiality_id') \
                        and doc_type.default_confidentiality_id:
                    vals['confidentiality_id'] = \
                        doc_type.default_confidentiality_id.id
        docs = super().create(vals_list)
        for doc in docs:
            if doc.folder_id and not doc.folder_id.user_can(
                    self.env.user, 'write') and not self._is_manager():
                raise AccessError(_(
                    "Vous n'avez pas le droit d'écrire dans le dossier "
                    "« %s ».", doc.folder_id.complete_name))
            self._audit(doc, _("Création document"), 'info',
                        _("Type : %s") % (doc.type_id.name or '—'))
        return docs

    def write(self, vals):
        touched = set(vals) & self._CONTENT_FIELDS
        for doc in self:
            if touched and doc.state == 'archived':
                raise UserError(_(
                    "Le document « %s » est archivé : ses champs sont "
                    "figés.", doc.name))
            if touched and doc.is_checked_out and not doc.checked_out_by_me \
                    and not self._is_manager():
                raise UserError(_(
                    "Le document « %s » est réservé par %s.",
                    doc.name, doc.checkout_user_id.name))
            if 'folder_id' in vals and vals['folder_id']:
                folder = self.env['aite.ecm.folder'].browse(vals['folder_id'])
                if not folder.user_can(self.env.user, 'write') \
                        and not self._is_manager():
                    raise AccessError(_(
                        "Vous n'avez pas le droit d'écrire dans le dossier "
                        "« %s ».", folder.complete_name))
        return super().write(vals)

    def unlink(self):
        if not self._is_manager():
            raise AccessError(_(
                "Seul un manager peut supprimer définitivement un document ; "
                "utilisez la corbeille."))
        for doc in self:
            self._audit(doc, _("Suppression définitive"), 'warn', doc.reference)
        return super().unlink()

    # ================================================================== #
    # Accès centralisé
    # ================================================================== #
    def _is_manager(self, user=None):
        user = user or self.env.user
        return user._is_superuser() or user.has_group(
            'aite_courrier_base.group_manager') or user.has_group(
            'aite_courrier_base.group_admin')

    def _check_document_access(self, operation='read', user=None):
        """Règle d'accès unique (UI, API, partages, WebDAV à venir).

        1. Superutilisateur, Manager et Administrateur : accès total.
        2. Partage nominatif : lecteurs partagés (lecture), rédacteurs partagés
           (lecture et écriture) — quels que soient dossier et confidentialité.
        3. Confidentiel / Secret : propriétaire ou créateur uniquement.
        4. Droits du dossier de classement (lecture / écriture hérités).
        5. Écriture : refusée si verrouillé ou réservé par un autre.
        """
        self.ensure_one()
        user = user or self.env.user
        if self._is_manager(user):
            return True
        if operation != 'read' and (self.is_locked or (
                self.is_checked_out and self.checkout_user_id != user)):
            return False
        if user in self.editor_user_ids:
            return True
        if operation == 'read' and user in self.shared_user_ids:
            return True
        if self.confidentiality_code in ('CONF', 'SEC') and user not in (
                self.owner_id | self.create_uid):
            return False
        if self.folder_id and not self.folder_id.user_can(user, operation):
            return False
        if operation != 'read':
            if self.is_locked:
                return False
            if self.is_checked_out and self.checkout_user_id != user:
                return False
        return True

    # ================================================================== #
    # Versions
    # ================================================================== #
    def _next_version_label(self):
        self.ensure_one()
        return "v%d" % (len(self.version_ids) + 1)

    def add_version(self, filename, datas, comment=False):
        """Crée la version v(n+1) depuis un contenu base64.

        Contrôles : accès en écriture (verrou, réservation, dossier),
        extension autorisée (type ou liste standard), taille ; calcule
        l'empreinte SHA-256, signale les doublons et trace l'audit.
        """
        self.ensure_one()
        if not self._check_document_access('write'):
            raise AccessError(_(
                "Téléversement impossible : document verrouillé, réservé "
                "par un autre utilisateur ou accès refusé."))
        if not filename:
            raise ValidationError(_("Le nom du fichier est requis."))
        extension = filename.rsplit('.', 1)[-1].lower() \
            if '.' in filename else ''
        allowed = self.type_id._allowed_extensions() if self.type_id \
            else self.ALLOWED_EXTENSIONS
        if extension not in allowed:
            raise ValidationError(_(
                "Format non autorisé (« %s »). Formats acceptés : %s.",
                extension or filename,
                ', '.join(e.upper() for e in allowed)))
        try:
            raw = base64.b64decode(datas or b'')
        except Exception:
            raise ValidationError(_("Contenu de fichier invalide."))
        size = len(raw)
        if size > self.MAX_FILE_SIZE:
            raise ValidationError(_(
                "Fichier trop volumineux (%.1f Mo). Maximum : %d Mo.",
                size / 1024.0 / 1024.0, self.MAX_FILE_SIZE // (1024 * 1024)))
        sha = hashlib.sha256(raw).hexdigest()
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': datas,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': self.MIME_BY_EXT.get(extension),
        })
        version = self.env['aite.ecm.document.version'].create({
            'document_id': self.id,
            'version': self._next_version_label(),
            'attachment_id': attachment.id,
            'file_size': size,
            'mime_type': attachment.mimetype,
            'sha256': sha,
            'comment': comment or False,
            'uploaded_by': self.env.user.id,
            'upload_date': fields.Datetime.now(),
        })
        self._audit(self, _("Ajout de version"), 'info',
                    _("%s — %s (%.0f Ko) — sha256 %s…") % (
                        version.version, filename, size / 1024.0, sha[:12]))
        duplicates = self.env['aite.ecm.document.version'].sudo().search([
            ('sha256', '=', sha), ('document_id', '!=', self.id)])
        if duplicates:
            names = ', '.join(duplicates.mapped('document_id.reference'))
            self.message_post(body=_(
                "⚠ Contenu identique détecté dans : %s") % names)
        return version

    def action_upload_version(self):
        for doc in self:
            if not doc.upload_file:
                raise UserError(_("Sélectionnez d'abord un fichier."))
            doc.add_version(doc.upload_filename or _("document"),
                            doc.upload_file, doc.upload_comment)
            doc.write({'upload_file': False, 'upload_filename': False,
                       'upload_comment': False})
        return True

    def action_preview_latest(self):
        self.ensure_one()
        if not self.latest_version_id:
            raise UserError(_("Aucune version à afficher."))
        return self.latest_version_id.action_open_file()

    # ================================================================== #
    # Cycle de vie
    # ================================================================== #
    def action_mark_final(self):
        for doc in self:
            if not doc.latest_version_id:
                raise UserError(_("Impossible de finaliser sans version."))
            if doc.is_checked_out:
                raise UserError(_("Libérez d'abord la réservation."))
            doc.write({'state': 'final'})
            self._audit(doc, _("Document finalisé"), 'ok', doc.reference)
        return True

    def action_mark_archived(self):
        for doc in self:
            doc.write({'state': 'archived'})
            self._audit(doc, _("Document archivé"), 'ok', doc.reference)
        return True

    def action_reset_draft(self):
        if not self._is_manager():
            raise AccessError(_(
                "Seul un manager peut remettre un document en brouillon."))
        for doc in self:
            doc.write({'state': 'draft'})
            self._audit(doc, _("Retour en brouillon"), 'warn', doc.reference)
        return True

    # ================================================================== #
    # Check-out / check-in
    # ================================================================== #
    def _checkout_hours(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'aite_ecm.checkout_hours', 48))

    def action_checkout(self):
        for doc in self:
            if doc.is_locked:
                raise UserError(_("Un document verrouillé ne se réserve pas."))
            if doc.is_checked_out and not doc.checked_out_by_me:
                raise UserError(_(
                    "Déjà réservé par %s jusqu'au %s.",
                    doc.checkout_user_id.name,
                    fields.Datetime.context_timestamp(
                        doc, doc.checkout_expiry).strftime("%d/%m/%Y %Hh%M")
                    if doc.checkout_expiry else '—'))
            if not doc._check_document_access('write'):
                raise AccessError(_("Accès en écriture refusé."))
            now = fields.Datetime.now()
            doc.write({
                'checkout_user_id': self.env.user.id,
                'checkout_date': now,
                'checkout_expiry': now + timedelta(
                    hours=doc._checkout_hours()),
            })
            self._audit(doc, _("Réservation (check-out)"), 'info',
                        doc.reference)
        return True

    def action_checkin(self):
        for doc in self:
            if doc.checkout_user_id and doc.checkout_user_id != self.env.user \
                    and not self._is_manager():
                raise UserError(_(
                    "Seul %s (ou un manager) peut libérer ce document.",
                    doc.checkout_user_id.name))
            doc.write({'checkout_user_id': False, 'checkout_date': False,
                       'checkout_expiry': False})
            self._audit(doc, _("Libération (check-in)"), 'info',
                        doc.reference)
        return True

    # ================================================================== #
    # Corbeille
    # ================================================================== #
    def action_trash(self):
        for doc in self:
            if not doc._check_document_access('write'):
                raise AccessError(_("Accès en écriture refusé."))
            if doc.state == 'archived' and not self._is_manager():
                raise UserError(_(
                    "Un document archivé ne peut être mis à la corbeille "
                    "que par un manager."))
            doc.write({'active': False, 'trashed_date': fields.Datetime.now(),
                       'trashed_uid': self.env.user.id})
            self._audit(doc, _("Mise à la corbeille"), 'warn', doc.reference)
        return True

    def action_restore(self):
        for doc in self:
            doc.write({'active': True, 'trashed_date': False,
                       'trashed_uid': False})
            self._audit(doc, _("Restauration"), 'ok', doc.reference)
        return True

    @api.model
    def _cron_purge_trash(self):
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'aite_ecm.trash_retention_days', 30))
        limit = fields.Datetime.now() - timedelta(days=days)
        expired = self.with_context(active_test=False).sudo().search([
            ('active', '=', False), ('trashed_date', '<', limit)])
        for doc in expired:
            self._audit(doc, _("Purge de la corbeille"), 'warn',
                        doc.reference, source='system')
        expired.sudo().unlink()
        return True

    # ================================================================== #
    # Navigation
    # ================================================================== #
    def action_open_linked_record(self):
        self.ensure_one()
        if not (self.res_model and self.res_id):
            raise UserError(_("Aucun enregistrement lié."))
        return {'type': 'ir.actions.act_window', 'res_model': self.res_model,
                'res_id': self.res_id, 'view_mode': 'form'}

    def action_view_duplicates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Doublons de %s") % self.reference,
            'res_model': 'aite.ecm.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.duplicate_ids.ids)],
        }

    # ================================================================== #
    # Audit
    # ================================================================== #
    def _audit(self, doc, action, action_type, detail, source=None):
        self.env['aite.courrier.audit.log']._log(
            self.env, action, action_type, 'aite.ecm.document', doc.id,
            doc.reference or doc.name, detail,
            source or self.env.context.get('audit_source', 'ui'))
