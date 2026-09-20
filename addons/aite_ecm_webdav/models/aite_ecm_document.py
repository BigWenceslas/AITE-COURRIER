# -*- coding: utf-8 -*-
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError

OFFICE_SCHEMES = {
    'ms-word': ('doc', 'docx', 'docm', 'dot', 'dotx', 'odt', 'rtf', 'txt'),
    'ms-excel': ('xls', 'xlsx', 'xlsm', 'xlt', 'ods', 'csv'),
    'ms-powerpoint': ('ppt', 'pptx', 'pptm', 'odp'),
}
OFFICE_LABELS = {'ms-word': "Word", 'ms-excel': "Excel", 'ms-powerpoint': "PowerPoint"}


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    webdav_url = fields.Char(string="Adresse WebDAV", compute='_compute_webdav_url')
    office_app = fields.Char(string="Application Office", compute='_compute_webdav_url')
    office_uri = fields.Char(string="Ouvrir dans Office", compute='_compute_webdav_url')

    @api.model
    def _webdav_base(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return "%s/webdav/aite_ecm" % base.rstrip('/')

    @api.depends('folder_id', 'name', 'reference', 'version_ids')
    def _compute_webdav_url(self):
        service = self.env['aite.ecm.webdav']
        base = self._webdav_base()
        for doc in self:
            if not doc.latest_version_id:
                doc.webdav_url = doc.office_uri = doc.office_app = False
                continue
            path = service.document_path(doc)
            url = "%s/%s" % (base, '/'.join(quote(p) for p in path.split('/')))
            doc.webdav_url = url
            ext = doc.latest_version_id.file_extension
            scheme = next((s for s, exts in OFFICE_SCHEMES.items() if ext in exts), False)
            doc.office_app = OFFICE_LABELS.get(scheme) if scheme else False
            doc.office_uri = "%s:ofe|u|%s" % (scheme, url) if scheme else False

    def action_open_in_office(self):
        """Ouvre le fichier dans Word / Excel / PowerPoint (édition sur le
        serveur, enregistrement → nouvelle version)."""
        self.ensure_one()
        if not self.office_uri:
            raise UserError(_("Ce format ne s'ouvre pas dans une application Office."))
        if not self._check_document_access('write'):
            uri = self.office_uri.replace(':ofe|', ':ofv|')     # lecture seule
        else:
            uri = self.office_uri
        return self._open_protocol_uri(uri)

    @api.model
    def _open_protocol_uri(self, uri):
        """Action ouvrant une URI de protocole applicatif.

        Volontairement pas un ``ir.actions.act_url`` : le client web normalise
        l'adresse, et une URI de protocole y perd ses barres verticales et son
        schéma imbriqué. Le navigateur la résout alors en chemin relatif
        d'Odoo — 404, sans jamais lancer Word. L'URI part donc telle quelle
        vers le navigateur (cf. ``static/src/open_uri.js``).
        """
        return {'type': 'ir.actions.client', 'tag': 'aite_ecm_open_uri',
                'params': {'uri': uri}}

    def _explorer_record(self):
        data = super()._explorer_record()
        data.update({'office_uri': self.office_uri or False,
                     'office_app': self.office_app or False,
                     'webdav_url': self.webdav_url or False})
        return data
