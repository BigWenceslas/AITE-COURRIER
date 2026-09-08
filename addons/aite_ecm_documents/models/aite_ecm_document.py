# -*- coding: utf-8 -*-
import base64
import hashlib

from odoo import _, api, fields, models


class AiteEcmDocument(models.Model):
    """Une carte Documents par document ECM, maintenue à jour (le mixin
    ``documents.mixin`` est ajouté ici, hors du socle Community)."""

    _name = 'aite.ecm.document'
    _inherit = ['aite.ecm.document', 'documents.mixin']

    documents_document_id = fields.Many2one(
        comodel_name='documents.document', string="Carte Documents",
        readonly=True, copy=False, index=True, ondelete='set null')
    documents_thumbnail = fields.Binary(
        related='documents_document_id.thumbnail', string="Vignette")

    # ------------------------------------------------------------------ #
    # documents.mixin : dossier, propriétaire, une seule carte par document
    # ------------------------------------------------------------------ #
    def _get_document_folder(self):
        if self.folder_id:
            return self.folder_id.sudo()._get_or_create_documents_folder()
        return self.env['aite.ecm.folder']._documents_root() \
            or self.env['documents.document']

    def _get_document_owner(self):
        return self.owner_id

    def _check_create_documents(self):
        """La carte n'est créée automatiquement que pour la première pièce ;
        les versions suivantes mettent à jour cette carte."""
        self.ensure_one()
        return not self.documents_document_id and super()._check_create_documents()

    def _get_document_tags(self):
        return self._documents_tags()

    def _documents_tags(self):
        """Étiquettes Documents homonymes des étiquettes ECM (créées au
        besoin, schéma 17 avec facette ou 18 sans facette)."""
        Tag = self.env['documents.tag'].sudo()
        tags = Tag.browse()
        for ecm_tag in self.tag_ids:
            tag = Tag.search([('name', '=', ecm_tag.name)], limit=1)
            if not tag:
                vals = {'name': ecm_tag.name}
                if 'color' in Tag._fields:
                    vals['color'] = ecm_tag.color
                if 'facet_id' in Tag._fields:          # Odoo ≤ 17
                    Facet = self.env['documents.facet'].sudo()
                    facet = Facet.search([('name', '=', 'ECM')], limit=1)
                    if not facet:
                        fvals = {'name': 'ECM'}
                        if 'folder_id' in Facet._fields:
                            root = self.env['aite.ecm.folder']._documents_root()
                            fvals['folder_id'] = root.id if root else False
                        facet = Facet.create(fvals)
                    vals['facet_id'] = facet.id
                tag = Tag.create(vals)
            tags |= tag
        return tags

    def _documents_card_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'folder_id': self._get_document_folder().id or False,
            'tag_ids': [(6, 0, self._documents_tags().ids)],
            'owner_id': self.owner_id.id or False,
            'res_model': self._name,
            'res_id': self.id,
        }

    def _documents_find_card(self):
        self.ensure_one()
        if self.documents_document_id:
            return self.documents_document_id
        Card = self.env['documents.document'].sudo()
        card = Card.search([('res_model', '=', self._name),
                            ('res_id', '=', self.id)], order='id', limit=1)
        if card:
            self.sudo().write({'documents_document_id': card.id})
        return card

    def _documents_sync_card(self):
        """Aligne la carte (titre, dossier, étiquettes, dernière version).
        Les cartes surnuméraires héritées (une par version avant ce module)
        sont archivées, jamais supprimées : leurs pièces jointes restent des
        versions ECM."""
        Card = self.env['documents.document'].sudo()
        for doc in self:
            latest = doc.latest_version_id
            cards = Card.with_context(active_test=False).search(
                [('res_model', '=', self._name), ('res_id', '=', doc.id)],
                order='id')
            card = doc.documents_document_id
            if not card:
                card = cards.filtered(
                    lambda c: latest and c.attachment_id == latest.attachment_id
                )[:1] or cards[:1]
                if card:
                    doc.sudo().write({'documents_document_id': card.id})
            if not card:
                continue
            vals = doc._documents_card_vals()
            if latest and card.attachment_id != latest.attachment_id:
                vals['attachment_id'] = latest.attachment_id.id
            if 'active' in Card._fields:
                vals['active'] = doc.active
            card.with_context(ecm_skip_adopt=True).write(vals)
            extra = cards - card
            if extra and 'active' in Card._fields:
                extra.with_context(ecm_skip_adopt=True).write({'active': False})

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    def add_version(self, filename, datas, comment=False):
        version = super().add_version(filename, datas, comment)
        self._documents_sync_card()
        return version

    def write(self, vals):
        res = super().write(vals)
        if {'name', 'folder_id', 'tag_ids', 'owner_id', 'active'} & set(vals) \
                and not self.env.context.get('documents_skip_sync'):
            self.filtered('documents_document_id')._documents_sync_card()
        return res

    def _documents_adopt_attachment(self, attachment, uploader=None):
        """Crée une version ECM à partir d'une pièce jointe déposée dans
        Documents (sans dupliquer le fichier)."""
        self.ensure_one()
        raw = base64.b64decode(attachment.sudo().datas or b'')
        if self.latest_version_id and self.latest_version_id.sha256 == \
                hashlib.sha256(raw).hexdigest():
            return self.latest_version_id
        attachment.sudo().write({'res_model': self._name, 'res_id': self.id})
        version = self.env['aite.ecm.document.version'].sudo().create({
            'document_id': self.id,
            'version': self._next_version_label(),
            'attachment_id': attachment.id,
            'file_size': len(raw),
            'mime_type': attachment.mimetype,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'comment': _("Déposé dans Documents"),
            'uploaded_by': (uploader or self.env.user).id,
            'upload_date': fields.Datetime.now(),
        })
        self._audit(self, _("Version déposée via Documents"), 'info',
                    "%s — %s" % (version.version, attachment.name))
        return version

    def action_open_explorer(self):
        """Ouvre l'explorateur Documents sur le dossier du document."""
        self.ensure_one()
        card = self._documents_find_card()
        folder = card.folder_id if card else self._get_document_folder()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_documents.action_aite_ecm_explorer')
        ctx = dict(self.env.context)
        if folder:
            ctx.update({'searchpanel_default_folder_id': folder.id,
                        'documents_default_folder_id': folder.id})
        if card:
            action['domain'] = [('id', '=', card.id)]
        action['context'] = ctx
        return action

    @api.model
    def _documents_rebuild_cards(self):
        """Rattache les cartes existantes et fusionne les doublons (une carte
        par version avant ce module)."""
        docs = self.sudo().search([('version_ids', '!=', False)])
        for doc in docs:
            doc._documents_sync_card()
        return len(docs)
