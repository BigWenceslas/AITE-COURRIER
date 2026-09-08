# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AiteCourrierDocumentVersion(models.Model):
    """Version immuable d'une pièce jointe d'un document.

    Chaque téléversement crée une nouvelle version ; les anciennes sont
    conservées. La suppression n'est possible que si le document n'est pas
    verrouillé, et reste tracée (audit conservé même après suppression du
    fichier).
    """

    _name = 'aite.courrier.document.version'
    _description = "Version de pièce jointe"
    _order = 'document_id, upload_date desc, id desc'

    document_id = fields.Many2one(
        comodel_name='aite.courrier.document', string="Document", required=True,
        ondelete='cascade', index=True,
    )
    version = fields.Char(string="Version", required=True)
    attachment_id = fields.Many2one(
        comodel_name='ir.attachment', string="Fichier", required=True,
        ondelete='restrict',
    )
    file_name = fields.Char(related='attachment_id.name', string="Nom du fichier")
    # Contenu de la pièce, exposé pour le téléchargement / l'aperçu depuis l'UI
    # (icône de téléchargement dans la liste des versions).
    file_data = fields.Binary(related='attachment_id.datas', string="Fichier")
    file_extension = fields.Char(
        string="Extension", compute='_compute_file_extension', store=True)
    file_size = fields.Integer(string="Taille (octets)")
    mime_type = fields.Char(string="Type MIME")
    uploaded_by = fields.Many2one(
        comodel_name='res.users', string="Téléversé par",
        default=lambda self: self.env.user)
    upload_date = fields.Datetime(string="Date", default=fields.Datetime.now)

    @api.depends('attachment_id.name')
    def _compute_file_extension(self):
        for version in self:
            name = version.attachment_id.name or ''
            version.file_extension = (
                name.rsplit('.', 1)[-1].lower() if '.' in name else False)

    def action_open_file(self):
        """Ouvre la pièce dans un nouvel onglet (aperçu natif du navigateur).

        ``download=false`` → le PDF s'affiche en ligne dans la visionneuse du
        navigateur ; les autres formats (DOCX/XLSX) se téléchargent. Méthode
        robuste, indépendante du widget ``pdf_viewer``."""
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("Aucun fichier à ouvrir pour cette version."))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=false' % self.attachment_id.id,
            'target': 'new',
        }

    def unlink(self):
        attachments = self.env['ir.attachment']
        for version in self:
            if version.document_id.is_locked:
                raise UserError(_(
                    "Suppression impossible : la version « %s » appartient à un "
                    "document verrouillé.", version.version))
            # Audit conservé même après suppression du fichier (journal immuable).
            self.env['aite.courrier.audit.log']._log(
                self.env, _("Suppression pièce jointe"), 'warn',
                'aite.courrier.document', version.document_id.id,
                version.document_id.name,
                _("%s — %s") % (version.version, version.attachment_id.name or ''),
                self.env.context.get('audit_source', 'ui'))
            attachments |= version.attachment_id
        res = super().unlink()
        attachments.sudo().unlink()
        return res
