# -*- coding: utf-8 -*-
"""Chatter tolérant à une messagerie non configurée.

Odoo refuse de publier un message quand il ne sait pas de quelle adresse
l'envoyer : si l'utilisateur qui agit n'a pas d'e-mail, ``message_post`` lève
« Unable to send message, please configure the sender's email address ».

Dans une administration, les comptes sont souvent créés avec un identifiant
technique (``cbi01``) sans adresse : une opération métier — poser un gel
juridique, lancer un circuit, déposer une version — ne doit pas échouer pour
cette raison. Ce mixin fournit une adresse d'expédition de repli (société,
puis paramètres ``mail.default.from`` / ``mail.catchall.domain``). Si aucune
n'est configurée, le message est publié sans adresse : il reste visible dans
le chatter, seule la notification par e-mail est omise.

Portée volontairement limitée aux modèles de la suite AITE : le comportement
standard d'Odoo n'est pas modifié pour les autres applications de la base.
"""
from odoo import api, models


class AiteChatterMixin(models.AbstractModel):
    _name = 'aite.chatter.mixin'
    _description = "Chatter tolérant (AITE)"

    @api.model
    def _aite_fallback_email_from(self):
        """Adresse d'expédition de repli, ou ``False``."""
        company = self.env.company.partner_id
        if company.email:
            return company.email_formatted
        Param = self.env['ir.config_parameter'].sudo()
        alias = Param.get_param('mail.default.from')
        domain = Param.get_param('mail.catchall.domain')
        if alias and domain:
            return '%s@%s' % (alias, domain)
        if alias and '@' in alias:
            return alias
        return False

    def _message_compute_author(self, author_id=None, email_from=None,
                                raise_on_email=True):
        author_id, computed = super()._message_compute_author(
            author_id, email_from, raise_on_email=False)
        if not computed:
            computed = self._aite_fallback_email_from()
        return author_id, computed
