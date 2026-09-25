# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.sign_oca.controllers.main import PortalSign


class AitePortalSign(PortalSign):

    @http.route()
    def portal_download_signed(self, request_id, **kw):
        """sign_oca sert ici n'importe quelle demande à tout utilisateur
        connecté (sudo sans contrôle) : on exige un droit de lecture ou la
        qualité de signataire (même critère que la liste « Mes signatures »
        du portail)."""
        sign_request = request.env['sign.oca.request'].browse(request_id)
        try:
            sign_request.check_access('read')
        except (AccessError, MissingError):
            is_signer = request.env['sign.oca.request.signer'].sudo() \
                .search_count([
                    ('request_id', '=', request_id),
                    ('partner_id', 'child_of', request.env.user.partner_id.id),
                ])
            if not is_signer:
                raise request.not_found()
        return super().portal_download_signed(request_id, **kw)
