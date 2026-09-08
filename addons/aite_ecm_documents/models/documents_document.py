# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError


class DocumentsDocument(models.Model):
    """Adoption des fichiers déposés dans l'espace ECM de Documents."""

    _inherit = 'documents.document'

    def _ecm_document(self):
        self.ensure_one()
        if self.res_model == 'aite.ecm.document' and self.res_id:
            return self.env['aite.ecm.document'].sudo().browse(self.res_id).exists()
        return self.env['aite.ecm.document']

    def _ecm_adopt(self):
        """Fichier sans rattachement déposé sous l'espace ECM → document ECM
        (dossier, propriétaire, première version = la pièce déposée)."""
        Folder = self.env['aite.ecm.folder']
        for card in self:
            if card.type != 'binary' or not card.attachment_id \
                    or card.res_model or card.res_id:
                continue
            folder, inside = Folder._from_documents_folder(card.folder_id)
            if not inside:
                continue
            name = (card.name or card.attachment_id.name or _("Document"))
            if '.' in name:
                name = name.rsplit('.', 1)[0]
            owner = card.owner_id or self.env.user
            doc = self.env['aite.ecm.document'].with_user(owner).sudo().create({
                'name': name,
                'folder_id': folder.id or False,
                'owner_id': owner.id,
            })
            doc.sudo().write({'documents_document_id': card.id})
            # la pièce jointe est rattachée au document ECM (res_model/res_id
            # de la carte en découlent : champs liés à la pièce jointe)
            doc._documents_adopt_attachment(card.attachment_id, uploader=owner)
            if hasattr(card, 'message_post'):
                card.message_post(body=_(
                    "Document ECM créé : %s") % doc.reference)

    @api.model_create_multi
    def create(self, vals_list):
        cards = super().create(vals_list)
        if not self.env.context.get('ecm_skip_adopt'):
            cards.sudo()._ecm_adopt()
        return cards

    def write(self, vals):
        skip = self.env.context.get('ecm_skip_adopt')
        # le lien vers le document ECM est porté par la pièce jointe : on le
        # mémorise avant que la nouvelle pièce jointe ne l'efface
        before = {} if skip else {card.id: card._ecm_document() for card in self}
        res = super().write(vals)
        if skip:
            return res
        if vals.get('attachment_id'):
            for card in self:
                doc = before.get(card.id)
                if not doc or not card.attachment_id:
                    continue
                if card.attachment_id in doc.version_ids.mapped('attachment_id'):
                    continue
                if doc.is_locked:
                    raise UserError(_(
                        "Le document ECM %s est finalisé ou archivé : "
                        "remettez-le en brouillon avant de remplacer son "
                        "fichier.") % doc.reference)
                doc._documents_adopt_attachment(card.attachment_id,
                                                uploader=self.env.user)
        elif 'res_model' not in vals and 'res_id' not in vals:
            # dépôt dans l'espace ECM sur une carte créée vide (demande)
            self.filtered(lambda c: c.attachment_id and not c.res_model
                          )._ecm_adopt()
        if 'folder_id' in vals or 'name' in vals:
            for card in self:
                doc = card._ecm_document()
                if not doc:
                    continue
                dvals = {}
                if vals.get('name') and vals['name'] != doc.name:
                    dvals['name'] = vals['name'].rsplit('.', 1)[0] \
                        if '.' in vals['name'] else vals['name']
                if 'folder_id' in vals:
                    folder, inside = self.env['aite.ecm.folder'] \
                        ._from_documents_folder(card.folder_id)
                    if inside and folder != doc.folder_id:
                        dvals['folder_id'] = folder.id or False
                if dvals:
                    doc.with_context(documents_skip_sync=True).write(dvals)
        return res

    def unlink(self):
        if not self.env.context.get('ecm_skip_adopt'):
            managed = self.filtered(lambda c: c._ecm_document())
            if managed:
                raise UserError(_(
                    "Ces fichiers sont gérés par l'ECM (%s) : mettez le "
                    "document à la corbeille depuis sa fiche ECM, la carte "
                    "Documents suivra.") % ", ".join(
                        managed.mapped(lambda c: c._ecm_document().reference)))
        return super().unlink()
