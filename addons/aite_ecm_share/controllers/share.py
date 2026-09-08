# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class EcmShareController(http.Controller):
    """Accès public par jeton : page d'accueil du lien puis fichier."""

    def _share(self, token):
        share = request.env['aite.ecm.share'].sudo().search(
            [('token', '=', token)], limit=1)
        return share if share and share._check_valid() else None

    @http.route(['/ecm/share/<string:token>'], type='http', auth='public',
                website=False, sitemap=False)
    def share_landing(self, token, **kw):
        share = self._share(token)
        if not share:
            return request.render('aite_ecm_share.share_invalid', {},
                                  status=404)
        return request.render('aite_ecm_share.share_landing', {
            'share': share,
            'document': share.document_id,
            'version': share.document_id.latest_version_id,
        })

    @http.route(['/ecm/share/<string:token>/file'], type='http',
                auth='public', website=False, sitemap=False)
    def share_file(self, token, **kw):
        share = self._share(token)
        if not share:
            return request.render('aite_ecm_share.share_invalid', {},
                                  status=404)
        filename, raw, mimetype = share._served_content()
        share._register_access()
        if share.view_only and mimetype != 'application/pdf':
            return request.render('aite_ecm_share.share_invalid', {
                'reason': "Ce document n'est consultable qu'en PDF."},
                status=403)
        headers = [
            ('Content-Type', mimetype),
            ('Content-Length', str(len(raw))),
            ('Content-Disposition', 'inline' if share.view_only
             else http.content_disposition(filename)),
            ('X-Content-Type-Options', 'nosniff'),
            ('Cache-Control', 'no-store'),
        ]
        return request.make_response(raw, headers=headers)
