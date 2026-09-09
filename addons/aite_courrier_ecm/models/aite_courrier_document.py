# -*- coding: utf-8 -*-
"""Miroir ECM des pièces de courrier.

Chaque ``aite.courrier.document`` possède un ``aite.ecm.document`` jumeau,
rattaché au courrier (``res_model='aite.courrier'``). Les **pièces jointes ne
sont pas dupliquées** : chaque version ECM pointe vers l'``ir.attachment`` de
la version courrier correspondante.
"""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AiteCourrierDocument(models.Model):
    _inherit = 'aite.courrier.document'

    ecm_document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document ECM",
        readonly=True, copy=False, index=True, ondelete='set null')

    # ------------------------------------------------------------------ #
    # Classement : Courrier / <année> / <référence>
    # ------------------------------------------------------------------ #
    def _ecm_folder(self):
        """Dossier ECM du courrier (créé au besoin)."""
        self.ensure_one()
        Folder = self.env['aite.ecm.folder'].sudo()
        root = self.env.ref('aite_courrier_ecm.folder_courrier',
                            raise_if_not_found=False)
        if not root:
            return Folder
        courrier = self.courrier_id
        date = courrier.date_received or fields.Date.context_today(self)
        year = str(getattr(date, 'year', fields.Date.today().year))
        year_folder = Folder.search([('name', '=', year),
                                     ('parent_id', '=', root.id)], limit=1)
        if not year_folder:
            year_folder = Folder.create({'name': year, 'parent_id': root.id})
        ref = courrier.reference or _("Brouillon %s") % courrier.id
        folder = Folder.search([('name', '=', ref),
                                ('parent_id', '=', year_folder.id)], limit=1)
        if not folder:
            folder = Folder.create({'name': ref, 'parent_id': year_folder.id,
                                    'description': courrier.subject or ''})
        return folder

    def _ecm_values(self):
        self.ensure_one()
        courrier = self.courrier_id
        dtype = self.env.ref('aite_courrier_ecm.type_courrier',
                             raise_if_not_found=False)
        vals = {
            'name': self.name,
            'type_id': dtype.id if dtype else False,
            'folder_id': self._ecm_folder().id or False,
            'confidentiality_id': courrier.confidentiality_id.id or False,
            'owner_id': (courrier.responsible_id or self.create_uid).id,
            'res_model': 'aite.courrier',
            'res_id': courrier.id,
            'description': courrier.subject or '',
        }
        if dtype:
            vals['properties'] = {
                'cour_reference': courrier.reference or '',
                'cour_type': courrier.type_id.name or '',
                'cour_expediteur': courrier.sender or '',
                'cour_date': fields.Date.to_string(courrier.date_received)
                if courrier.date_received else False,
            }
        return vals

    # ------------------------------------------------------------------ #
    # Synchronisation
    # ------------------------------------------------------------------ #
    def _ecm_sync(self):
        """Crée ou met à jour le jumeau ECM, versions comprises."""
        Document = self.env['aite.ecm.document'].sudo()
        Version = self.env['aite.ecm.document.version'].sudo()
        for piece in self:
            if not piece.courrier_id:
                continue
            ecm = piece.ecm_document_id
            vals = piece._ecm_values()
            if not ecm:
                ecm = Document.with_context(ecm_from_courrier=True).create(vals)
                piece.sudo().write({'ecm_document_id': ecm.id})
            else:
                ecm.with_context(ecm_from_courrier=True,
                                 documents_skip_sync=True).write(vals)
            # versions manquantes : même pièce jointe, pas de copie du fichier
            known = set(ecm.version_ids.mapped('attachment_id').ids)
            for version in piece.version_ids.sorted('id'):
                if version.attachment_id.id in known:
                    continue
                Version.create({
                    'document_id': ecm.id,
                    'version': version.version,
                    'attachment_id': version.attachment_id.id,
                    'file_size': version.file_size,
                    'mime_type': version.mime_type,
                    'sha256': getattr(version, 'sha256', False) or False,
                    'uploaded_by': version.uploaded_by.id,
                    'upload_date': version.upload_date,
                    'comment': _("Pièce de courrier %s")
                    % (piece.courrier_id.reference or ''),
                })
            # état : une pièce verrouillée l'est aussi côté ECM
            target = 'archived' if piece.courrier_id.state == 'ar' else (
                'final' if piece.state in ('final', 'archived') else 'draft')
            if ecm.state != target and ecm.version_ids:
                ecm.with_context(ecm_from_courrier=True).sudo().write(
                    {'state': target})
        return True

    def _ecm_try_sync(self):
        for piece in self:
            try:
                with self.env.cr.savepoint():
                    piece._ecm_sync()
            except Exception as exc:  # noqa: BLE001 — le courrier prime
                _logger.warning("[courrier→ecm] %s : %s", piece.display_name, exc)

    # ------------------------------------------------------------------ #
    # Crochets
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        pieces = super().create(vals_list)
        pieces._ecm_try_sync()
        return pieces

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('ecm_from_courrier') and (
                {'name', 'state', 'folder_id', 'confidentiality_id'} & set(vals)):
            self._ecm_try_sync()
        return res

    def add_version(self, filename, datas):
        version = super().add_version(filename, datas)
        self._ecm_try_sync()
        return version

    def unlink(self):
        mirrors = self.mapped('ecm_document_id')
        res = super().unlink()
        for ecm in mirrors:
            if ecm.exists() and ecm.active:
                try:
                    ecm.sudo().with_context(ecm_from_courrier=True).action_trash()
                except Exception:  # noqa: BLE001
                    pass
        return res

    # ------------------------------------------------------------------ #
    # Reprise
    # ------------------------------------------------------------------ #
    @api.model
    def _ecm_mirror_all(self, limit=None):
        pieces = self.sudo().search([('ecm_document_id', '=', False)],
                                    limit=limit)
        pieces._ecm_try_sync()
        return len(pieces)

    @api.model
    def _cron_ecm_mirror(self):
        """Filet de sécurité : reflète les pièces qui auraient échappé au
        miroir (imports, corrections en base)."""
        return self._ecm_mirror_all(limit=200)


class AiteEcmDocument(models.Model):
    """Le document ECM issu d'un courrier renvoie vers celui-ci et n'est pas
    modifiable indépendamment (le courrier reste la source)."""

    _inherit = 'aite.ecm.document'

    courrier_piece_id = fields.Many2one(
        comodel_name='aite.courrier.document', string="Pièce de courrier",
        compute='_compute_courrier_piece', store=True)

    @api.depends('res_model', 'res_id')
    def _compute_courrier_piece(self):
        Piece = self.env['aite.courrier.document'].sudo()
        for doc in self:
            doc.courrier_piece_id = Piece.search(
                [('ecm_document_id', '=', doc.id)], limit=1) if doc.id else False

    def add_version(self, filename, datas, comment=False):
        """Une version ajoutée côté ECM est répercutée sur la pièce de
        courrier (source unique)."""
        version = super().add_version(filename, datas, comment)
        if not self.env.context.get('ecm_from_courrier'):
            for doc in self.filtered('courrier_piece_id'):
                piece = doc.courrier_piece_id.sudo()
                if version.attachment_id.id not in \
                        piece.version_ids.mapped('attachment_id').ids:
                    self.env['aite.courrier.document.version'].sudo().create({
                        'document_id': piece.id,
                        'version': version.version,
                        'attachment_id': version.attachment_id.id,
                        'file_size': version.file_size,
                        'mime_type': version.mime_type,
                        'uploaded_by': version.uploaded_by.id,
                        'upload_date': version.upload_date,
                    })
        return version

    def action_open_courrier(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'aite.courrier',
                'res_id': self.res_id, 'view_mode': 'form'}
