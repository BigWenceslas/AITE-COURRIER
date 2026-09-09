# -*- coding: utf-8 -*-
import base64

from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools.mail import plaintext2html

from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    pager as portal_pager,
)

# Libellés publics des statuts : le vocabulaire interne (brouillon, rejeté…)
# n'est pas exposé tel quel aux tiers.
PORTAL_STATE_LABELS = {
    'draft': "Reçue",
    'nw': "Enregistrée",
    'pr': "En traitement",
    'rj': "Clôturée sans suite",
    'ar': "Traitée",
}


class CourrierCustomerPortal(CustomerPortal):
    """Portail « Mes courriers » : liste, suivi, dépôt de demandes."""

    _COURRIER_PER_PAGE = 20

    # ------------------------------------------------------------------ #
    # Aides
    # ------------------------------------------------------------------ #
    def _courrier_domain(self):
        partner = request.env.user.partner_id
        return [
            '|',
            ('sender_partner_id', '=', partner.id),
            ('sender_partner_id', '=', partner.commercial_partner_id.id),
        ]

    def _portal_entrant_types(self):
        return request.env['aite.courrier.type'].sudo().search([
            ('category', '=', 'entrant'), ('active', '=', True),
        ])

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'courrier_count' in counters:
            try:
                values['courrier_count'] = request.env['aite.courrier'] \
                    .search_count(self._courrier_domain())
            except AccessError:
                values['courrier_count'] = 0
        return values

    # ------------------------------------------------------------------ #
    # Liste
    # ------------------------------------------------------------------ #
    @http.route(['/my/courriers', '/my/courriers/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_courriers(self, page=1, **kw):
        Courrier = request.env['aite.courrier']
        domain = self._courrier_domain()
        courrier_count = Courrier.search_count(domain)
        pager = portal_pager(
            url='/my/courriers',
            total=courrier_count,
            page=page,
            step=self._COURRIER_PER_PAGE,
        )
        courriers = Courrier.search(
            domain, order='date_received desc, id desc',
            limit=self._COURRIER_PER_PAGE, offset=pager['offset'])
        return request.render(
            'aite_courrier_portal.portal_my_courriers', {
                'courriers': courriers,
                'pager': pager,
                'page_name': 'courrier',
                'state_labels': PORTAL_STATE_LABELS,
                'default_url': '/my/courriers',
            })

    # ------------------------------------------------------------------ #
    # Détail (suivi d'avancement)
    # ------------------------------------------------------------------ #
    @http.route(['/my/courriers/<int:courrier_id>'],
                type='http', auth='user', website=True)
    def portal_courrier_detail(self, courrier_id, **kw):
        try:
            # Vérifie les droits AVEC l'utilisateur portail (ACL + règle
            # d'enregistrement), puis renvoie l'enregistrement en sudo pour
            # lire les relations (type, étapes) sans élargir les ACL.
            courrier_sudo = self._document_check_access(
                'aite.courrier', courrier_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        # Parcours du circuit : étapes triées, étape courante en évidence.
        steps = courrier_sudo.circuit_id.step_ids.sorted(
            key=lambda s: (s.sequence, s.id))
        # Pièces téléchargeables via jeton d'accès (pas d'ACL attachement).
        documents = []
        for document in courrier_sudo.document_ids:
            version = document.latest_version_id
            if not version or not version.attachment_id:
                continue
            attachment = version.attachment_id.sudo()
            token = attachment.generate_access_token()[0]
            documents.append({
                'name': document.name,
                'filename': version.file_name,
                'url': '/web/content/%d?access_token=%s&download=true' % (
                    attachment.id, token),
            })
        return request.render(
            'aite_courrier_portal.portal_courrier_detail', {
                'courrier': courrier_sudo,
                'steps': steps,
                'documents': documents,
                'page_name': 'courrier_detail',
                'state_labels': PORTAL_STATE_LABELS,
                'submitted': kw.get('submitted'),
            })

    # ------------------------------------------------------------------ #
    # Dépôt d'une demande
    # ------------------------------------------------------------------ #
    @http.route(['/my/courriers/new'], type='http', auth='user',
                website=True, methods=['GET', 'POST'])
    def portal_courrier_new(self, **post):
        types = self._portal_entrant_types()
        errors = {}
        if request.httprequest.method == 'POST':
            subject = (post.get('subject') or '').strip()
            type_id = int(post.get('type_id') or 0)
            if not subject:
                errors['subject'] = _("L'objet est obligatoire.")
            if type_id not in types.ids:
                errors['type_id'] = _("Choisissez la nature de la demande.")
            if not errors:
                courrier = self._portal_create_courrier(
                    subject, type_id, post.get('description') or '')
                self._portal_attach_files(courrier)
                return request.redirect(
                    '/my/courriers/%d?submitted=1' % courrier.id)
        return request.render(
            'aite_courrier_portal.portal_courrier_new', {
                'types': types,
                'errors': errors,
                'default': post,
                'page_name': 'courrier_new',
            })

    def _portal_create_courrier(self, subject, type_id, description):
        """Crée le courrier (sudo) au nom du tiers connecté + trace l'audit."""
        partner = request.env.user.partner_id
        courrier = request.env['aite.courrier'].sudo().create({
            'subject': subject,
            'type_id': type_id,
            'sender': partner.display_name,
            'sender_partner_id': partner.id,
            'sender_email': partner.email,
            'date_received': fields.Date.context_today(
                request.env['aite.courrier']),
        })
        if description.strip():
            courrier.message_post(
                body=plaintext2html(description),
                author_id=partner.id,
                message_type='comment')
        request.env['aite.courrier.audit.log'].sudo()._log(
            request.env, _("Demande déposée via le portail"), 'info',
            'aite.courrier', courrier.id, courrier.display_name,
            _("Tiers : %s — Objet : %s") % (partner.display_name, subject),
            'system')
        return courrier

    def _portal_attach_files(self, courrier):
        """Convertit les fichiers téléversés en documents GED versionnés.

        Mêmes garde-fous que la capture e-mail : formats de la GED, taille
        contrôlée par ``add_version`` ; un fichier refusé est tracé en audit
        sans faire échouer le dépôt.
        """
        Document = request.env['aite.courrier.document'].sudo()
        allowed = Document.ALLOWED_EXTENSIONS
        for storage in request.httprequest.files.getlist('attachments'):
            filename = storage.filename or ''
            extension = (filename.rsplit('.', 1)[-1].lower()
                         if '.' in filename else '')
            if not filename or extension not in allowed:
                continue
            try:
                document = Document.create({
                    'name': filename,
                    'courrier_id': courrier.id,
                })
                document.with_context(audit_source='system').add_version(
                    filename, base64.b64encode(storage.read()))
            except Exception as exc:  # noqa: BLE001 — dépôt jamais bloqué
                request.env['aite.courrier.audit.log'].sudo()._log(
                    request.env, _("Pièce portail refusée"), 'warn',
                    'aite.courrier', courrier.id, courrier.display_name,
                    _("%s : %s") % (filename, exc), 'system')
        return True
