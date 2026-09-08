# -*- coding: utf-8 -*-
import base64
import io
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:  # pypdf est livré avec Odoo (odoo.tools.pdf) ; import direct sécurisé
    from pypdf import PdfReader, PdfWriter
except ImportError:  # pragma: no cover
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        PdfReader = PdfWriter = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:  # pragma: no cover
    rl_canvas = None


class AiteEcmShare(models.Model):
    """Lien de partage externe d'un document ECM."""

    _name = 'aite.ecm.share'
    _description = "Partage externe ECM"
    _order = 'id desc'

    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document", required=True,
        ondelete='cascade', index=True)
    name = fields.Char(string="Libellé", required=True,
                       default=lambda self: _("Partage"))
    token = fields.Char(
        string="Jeton", required=True, index=True, copy=False, readonly=True,
        default=lambda self: secrets.token_urlsafe(24))
    active = fields.Boolean(string="Actif", default=True)
    expiry_date = fields.Datetime(string="Expire le")
    max_downloads = fields.Integer(
        string="Téléchargements max.", default=0,
        help="0 = illimité.")
    download_count = fields.Integer(string="Accès", readonly=True,
                                    copy=False)
    last_access = fields.Datetime(string="Dernier accès", readonly=True,
                                  copy=False)
    view_only = fields.Boolean(
        string="Consultation seule",
        help="Le PDF s'affiche dans le navigateur sans téléchargement.")
    watermark = fields.Boolean(
        string="Filigrane", default=True,
        help="Incruste une mention (date, jeton) dans le PDF servi.")
    watermark_text = fields.Char(
        string="Texte du filigrane",
        default=lambda self: _("Diffusion contrôlée — AITE ECM"))
    recipient = fields.Char(string="Destinataire (info)")
    url = fields.Char(string="Lien", compute='_compute_url')
    is_valid = fields.Boolean(string="Valide", compute='_compute_is_valid')

    @api.depends('token')
    def _compute_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', '')
        for share in self:
            share.url = "%s/ecm/share/%s" % (base, share.token)

    @api.depends('active', 'expiry_date', 'max_downloads', 'download_count')
    def _compute_is_valid(self):
        now = fields.Datetime.now()
        for share in self:
            share.is_valid = share._check_valid(now)

    def _check_valid(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if not self.active or not self.document_id.active:
            return False
        if self.expiry_date and self.expiry_date < now:
            return False
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        return True

    @api.model_create_multi
    def create(self, vals_list):
        shares = super().create(vals_list)
        for share in shares:
            if share.document_id.confidentiality_code in ('CONF', 'SEC'):
                share.watermark = True
            self.env['aite.courrier.audit.log']._log(
                self.env, _("Création d'un lien de partage"), 'info',
                'aite.ecm.document', share.document_id.id,
                share.document_id.reference,
                _("Lien %s — expire %s") % (
                    share.token[:8], share.expiry_date or _("jamais")), 'ui')
        return shares

    def action_deactivate(self):
        self.write({'active': False})
        return True

    # ------------------------------------------------------------------ #
    # Service du fichier (appelé par le contrôleur public)
    # ------------------------------------------------------------------ #
    def _register_access(self):
        self.ensure_one()
        self.sudo().write({'download_count': self.download_count + 1,
                           'last_access': fields.Datetime.now()})
        self.env['aite.courrier.audit.log']._log(
            self.env, _("Accès par lien de partage"), 'info',
            'aite.ecm.document', self.document_id.id,
            self.document_id.reference,
            _("Lien %s — accès n°%d") % (self.token[:8],
                                          self.download_count), 'system')

    def _served_content(self):
        """(nom de fichier, octets, mimetype) de la dernière version,
        filigranée si demandé et si PDF."""
        self.ensure_one()
        version = self.document_id.latest_version_id
        if not version:
            raise UserError(_("Ce document n'a pas encore de fichier."))
        raw = base64.b64decode(version.attachment_id.sudo().datas or b'')
        mimetype = version.mime_type or 'application/octet-stream'
        if self.watermark and version.file_extension == 'pdf':
            raw = self._watermark_pdf(raw, "%s · %s · %s" % (
                self.watermark_text or '',
                fields.Date.context_today(self).strftime('%d/%m/%Y'),
                self.token[:8]))
        return version.file_name, raw, mimetype

    @api.model
    def _watermark_pdf(self, raw, text):
        """Incruste ``text`` en diagonale sur chaque page (pypdf + reportlab).
        Repli sans modification si les bibliothèques manquent."""
        if not (PdfReader and PdfWriter and rl_canvas):
            _logger.warning("Filigrane indisponible (pypdf/reportlab).")
            return raw
        try:
            reader = PdfReader(io.BytesIO(raw))
            writer = PdfWriter()
            for page in reader.pages:
                width = float(page.mediabox.width) or A4[0]
                height = float(page.mediabox.height) or A4[1]
                buf = io.BytesIO()
                c = rl_canvas.Canvas(buf, pagesize=(width, height))
                c.saveState()
                c.setFillColorRGB(0.45, 0.2, 0.4)
                try:
                    c.setFillAlpha(0.18)
                except Exception:
                    pass
                c.setFont("Helvetica-Bold", 28)
                c.translate(width / 2, height / 2)
                c.rotate(35)
                c.drawCentredString(0, 0, text)
                c.setFont("Helvetica", 9)
                c.drawCentredString(0, -22, text)
                c.restoreState()
                c.save()
                buf.seek(0)
                overlay = PdfReader(buf).pages[0]
                page.merge_page(overlay)
                writer.add_page(page)
            out = io.BytesIO()
            writer.write(out)
            return out.getvalue()
        except Exception as exc:  # PDF chiffré / corrompu : servir tel quel
            _logger.warning("Filigrane impossible : %s", exc)
            return raw


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    share_ids = fields.One2many(
        comodel_name='aite.ecm.share', inverse_name='document_id',
        string="Partages")
    share_count = fields.Integer(compute='_compute_share_count')

    @api.depends('share_ids')
    def _compute_share_count(self):
        for doc in self:
            doc.share_count = len(doc.share_ids)

    def action_create_share(self):
        self.ensure_one()
        if not self.latest_version_id:
            raise UserError(_("Ajoutez d'abord un fichier au document."))
        share = self.env['aite.ecm.share'].create({
            'document_id': self.id,
            'name': _("Partage — %s") % self.reference,
            'expiry_date': fields.Datetime.now() + timedelta(days=7),
        })
        return {'type': 'ir.actions.act_window',
                'res_model': 'aite.ecm.share', 'res_id': share.id,
                'view_mode': 'form', 'target': 'new'}

    def action_view_shares(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'name': _("Partages — %s") % self.reference,
                'res_model': 'aite.ecm.share', 'view_mode': 'list,form',
                'domain': [('document_id', '=', self.id)],
                'context': {'default_document_id': self.id}}
