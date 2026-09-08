# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

try:
    from odoo.tools.mail import parse_contact_from_email
except ImportError:  # repli très défensif selon la révision d'Odoo
    parse_contact_from_email = None

from odoo.tools import email_split


class AiteCourrier(models.Model):
    """Capture e-mail : la passerelle mail d'Odoo crée le courrier.

    Le modèle héritant déjà de ``mail.thread``, il suffit d'implémenter
    :meth:`message_new` (e-mail adressé à l'alias → nouveau courrier) ; les
    réponses ultérieures au même fil (``message_update``) alimentent le
    chatter du courrier existant. Les pièces jointes des e-mails sont
    converties en documents GED versionnés via
    :meth:`_message_post_after_hook`.
    """

    _inherit = 'aite.courrier'

    # En dessous de cette taille, une image jointe est considérée comme une
    # signature/un logo d'e-mail et n'est pas archivée dans la GED.
    MIN_IMAGE_CAPTURE_SIZE = 8 * 1024  # 8 Ko
    _IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'tif', 'tiff')

    # ------------------------------------------------------------------ #
    # Passerelle entrante
    # ------------------------------------------------------------------ #
    @api.model
    def _capture_default_type(self):
        """Type appliqué aux courriers créés par e-mail.

        Priorité au type explicitement marqué « capture e-mail », sinon le
        premier type de catégorie « Entrant » (référentiel livré en standard).
        """
        Type = self.env['aite.courrier.type']
        return Type.search([('mail_capture_default', '=', True)], limit=1) \
            or Type.search([('category', '=', 'entrant')], limit=1)

    @api.model
    def _parse_sender(self, email_from):
        """Extrait (nom, e-mail) de l'en-tête ``From``."""
        if parse_contact_from_email:
            name, email = parse_contact_from_email(email_from or '')
        else:
            emails = email_split(email_from or '')
            email = emails[0] if emails else ''
            name = (email_from or '').replace('<%s>' % email, '').strip(' "\'')
        return name or email, email

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """E-mail reçu sur l'alias → courrier en brouillon pré-qualifié."""
        values = dict(custom_values or {})
        email_from = msg_dict.get('email_from') or ''
        name, email = self._parse_sender(email_from)
        default_type = self._capture_default_type()
        values.setdefault('subject',
                          msg_dict.get('subject') or _("Courrier sans objet"))
        values.setdefault('sender', name or email_from)
        if email:
            values.setdefault('sender_email', email)
        if msg_dict.get('author_id'):
            values.setdefault('sender_partner_id', msg_dict['author_id'])
        if default_type and not values.get('type_id'):
            values['type_id'] = default_type.id
        values.setdefault('date_received', fields.Date.context_today(self))
        courrier = super().message_new(msg_dict, custom_values=values)
        self.env['aite.courrier.audit.log']._log(
            self.env, _("Courrier créé par e-mail"), 'info', 'aite.courrier',
            courrier.id, courrier.display_name,
            _("De : %s — Objet : %s") % (email_from,
                                         msg_dict.get('subject') or ''),
            'system')
        return courrier

    # ------------------------------------------------------------------ #
    # Pièces jointes des e-mails → documents GED versionnés
    # ------------------------------------------------------------------ #
    def _message_post_after_hook(self, message, msg_vals):
        res = super()._message_post_after_hook(message, msg_vals)
        # Uniquement les messages de type e-mail (passerelle entrante et
        # réponses au fil) ; les commentaires internes ne sont pas archivés.
        if message.message_type in ('email', 'email_outgoing') \
                and message.attachment_ids:
            self._capture_attachments_to_ged(message.attachment_ids)
        return res

    def _capture_attachments_to_ged(self, attachments):
        """Convertit les pièces d'un e-mail en documents versionnés.

        Filtres : extensions autorisées par la GED, taille minimale pour les
        images (élimine signatures et logos), pièces déjà versionnées
        ignorées. Une pièce en échec (ex. > 50 Mo) est tracée en audit sans
        bloquer le traitement de l'e-mail.
        """
        self.ensure_one()
        Document = self.env['aite.courrier.document'].sudo()
        allowed = Document.ALLOWED_EXTENSIONS
        for attachment in attachments:
            filename = attachment.name or ''
            extension = (filename.rsplit('.', 1)[-1].lower()
                         if '.' in filename else '')
            if extension not in allowed:
                continue
            if extension in self._IMAGE_EXTENSIONS \
                    and (attachment.file_size or 0) < self.MIN_IMAGE_CAPTURE_SIZE:
                continue
            # Déjà versionnée (ex. e-mail sortant d'une pièce GED) : ignorer.
            if attachment.res_model == 'aite.courrier.document':
                continue
            try:
                document = Document.create({
                    'name': filename,
                    'courrier_id': self.id,
                })
                document.with_context(audit_source='system').add_version(
                    filename, attachment.datas)
            except Exception as exc:  # noqa: BLE001 — ne pas bloquer l'e-mail
                self.env['aite.courrier.audit.log']._log(
                    self.env, _("Échec capture pièce jointe"), 'err',
                    'aite.courrier', self.id,
                    self.reference or self.display_name,
                    _("%s : %s") % (filename, exc), 'system')
        return True
