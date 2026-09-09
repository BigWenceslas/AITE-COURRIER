# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ecm_google_client_id = fields.Char(
        string="Client OAuth Google — ID",
        config_parameter='aite_ecm_office.google_client_id')
    ecm_google_client_secret = fields.Char(
        string="Client OAuth Google — secret",
        config_parameter='aite_ecm_office.google_client_secret')
    ecm_google_redirect = fields.Char(
        string="URI de redirection à déclarer", compute='_compute_ecm_google_redirect')
    ecm_webdav_url = fields.Char(string="Adresse WebDAV de l'ECM",
                                 compute='_compute_ecm_google_redirect')
    ecm_wopi_server_url = fields.Char(
        string="Serveur d'édition en ligne (Collabora / OnlyOffice)",
        config_parameter='aite_ecm_office.wopi_server_url',
        help="URL publique du serveur WOPI, ex. https://office.exemple.cm")
    ecm_wopi_token_hours = fields.Integer(
        string="Durée d'une session d'édition (h)", default=8,
        config_parameter='aite_ecm_office.wopi_token_hours')

    def action_ecm_wopi_test(self):
        self.ensure_one()
        self.set_values()
        Token = self.env['aite.ecm.office.token']
        xml = Token._discovery(force=True)
        import xml.etree.ElementTree as ET
        exts = sorted({a.get('ext') for a in ET.fromstring(xml).iter('action')
                       if a.get('ext')})
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': "Édition en ligne", 'type': 'success',
                           'message': "Serveur joignable — %d formats : %s"
                           % (len(exts), ', '.join(exts[:20]))}}

    def _compute_ecm_google_redirect(self):
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                or '').rstrip('/')
        for rec in self:
            rec.ecm_google_redirect = base + '/ecm/google/callback'
            rec.ecm_webdav_url = base + '/webdav/aite_ecm/'
