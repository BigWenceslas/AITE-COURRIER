# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteEcmDocumentVersion(models.Model):
    """Version immuable d'un document ECM (v1, v2, …).

    Chaque version pointe vers son propre ``ir.attachment`` et porte
    l'**empreinte SHA-256** du contenu : base de la détection de doublons
    aujourd'hui, du journal de preuve (scellement) en v2.1.
    """

    _name = 'aite.ecm.document.version'
    _description = "Version de document ECM"
    _order = 'document_id, id desc'

    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document", required=True,
        ondelete='cascade', index=True)
    version = fields.Char(string="Version", required=True)
    attachment_id = fields.Many2one(
        comodel_name='ir.attachment', string="Fichier", required=True,
        ondelete='restrict')
    file_name = fields.Char(related='attachment_id.name',
                            string="Nom du fichier")
    file_data = fields.Binary(related='attachment_id.datas',
                              string="Fichier")
    file_extension = fields.Char(
        string="Extension", compute='_compute_file_extension', store=True)
    file_size = fields.Integer(string="Taille (octets)")
    mime_type = fields.Char(string="Type MIME")
    sha256 = fields.Char(string="Empreinte SHA-256", index=True,
                         readonly=True)
    uploaded_by = fields.Many2one(
        comodel_name='res.users', string="Téléversé par",
        default=lambda self: self.env.user)
    upload_date = fields.Datetime(string="Date",
                                  default=fields.Datetime.now)
    comment = fields.Char(string="Commentaire de version")

    @api.depends('attachment_id.name')
    def _compute_file_extension(self):
        for version in self:
            name = version.attachment_id.name or ''
            version.file_extension = (name.rsplit('.', 1)[-1].lower()
                                      if '.' in name else '')

    def action_open_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=false' % self.attachment_id.id,
            'target': 'new',
        }

    def action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % self.attachment_id.id,
            'target': 'self',
        }

    def unlink(self):
        for version in self:
            if version.document_id.is_locked:
                raise UserError(_(
                    "Impossible de supprimer une version d'un document "
                    "finalisé ou archivé (« %s »).", version.document_id.name))
        return super().unlink()
