# -*- coding: utf-8 -*-
import secrets

from odoo import _, fields, models
from odoo.exceptions import UserError

from .nextcloud_client import NextcloudError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nc_url = fields.Char(string="URL Nextcloud",
                         config_parameter='aite_ecm_nextcloud.url')
    nc_user = fields.Char(string="Compte de service",
                          config_parameter='aite_ecm_nextcloud.user')
    nc_password = fields.Char(string="Mot de passe d'application",
                              config_parameter='aite_ecm_nextcloud.password')
    nc_root = fields.Char(string="Dossier racine", default='AITE ECM',
                          config_parameter='aite_ecm_nextcloud.root')
    nc_mode = fields.Selection(
        selection=[('off', "Désactivé"),
                   ('push', "Miroir seul (Odoo → Nextcloud)"),
                   ('bidir', "Bidirectionnel (retour des modifications)")],
        string="Mode", default='off',
        config_parameter='aite_ecm_nextcloud.mode')
    nc_poll = fields.Boolean(string="Sondage périodique des modifications",
                             default=True,
                             config_parameter='aite_ecm_nextcloud.poll')
    nc_immediate = fields.Boolean(string="Envoi immédiat des versions",
                                  default=True,
                                  config_parameter='aite_ecm_nextcloud.immediate')
    nc_sync_courrier = fields.Boolean(
        string="Synchroniser aussi les pièces de courrier",
        config_parameter='aite_ecm_nextcloud.sync_courrier')
    nc_sync_confidential = fields.Boolean(
        string="Miroiter aussi les documents Confidentiel / Secret",
        config_parameter='aite_ecm_nextcloud.sync_confidential',
        help="Désactivé par défaut : le partage de dossiers Nextcloud est "
             "moins fin que les droits ECM.")
    nc_share_days = fields.Integer(
        string="Validité des liens publics (jours)", default=7,
        config_parameter='aite_ecm_nextcloud.share_days')
    nc_webhook_secret = fields.Char(
        string="Secret du webhook",
        config_parameter='aite_ecm_nextcloud.webhook_secret')
    nc_webhook_id = fields.Char(string="Webhook enregistré (ID)", readonly=True,
                                config_parameter='aite_ecm_nextcloud.webhook_id')

    def _nc_notify(self, title, message, kind='success'):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': title, 'message': message, 'type': kind,
                           'sticky': kind != 'success'}}

    def action_nc_test_connection(self):
        self.ensure_one()
        self.set_values()
        client = self.env['aite.ecm.document']._nc_client()
        try:
            client.ensure_dir('')
            info = client.stat('')
        except NextcloudError as exc:
            raise UserError(_("Connexion impossible : %s") % exc)
        return self._nc_notify(_("Nextcloud"), _(
            "Connexion réussie — dossier racine « %s » (id %s).")
            % (client.root, info and info.get('fileid')))

    def action_nc_register_webhook(self):
        self.ensure_one()
        if not self.nc_webhook_secret:
            self.nc_webhook_secret = secrets.token_urlsafe(24)
        self.set_values()
        client = self.env['aite.ecm.document']._nc_client()
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        target = "%s/ecm/nextcloud/webhook" % base_url.rstrip('/')
        try:
            webhook_id = client.register_webhook(target, self.nc_webhook_secret)
        except NextcloudError as exc:
            raise UserError(_(
                "Enregistrement du webhook impossible (%s). Vérifiez que "
                "l'app « Webhook Listeners » est activée sur Nextcloud (30+) "
                "et que le compte de service est administrateur.") % exc)
        self.env['ir.config_parameter'].sudo().set_param(
            'aite_ecm_nextcloud.webhook_id', webhook_id)
        self.nc_webhook_id = webhook_id
        return self._nc_notify(_("Nextcloud"), _(
            "Webhook enregistré (id %s) vers %s.") % (webhook_id, target))

    def action_nc_push_all(self):
        self.ensure_one()
        self.set_values()
        count = self.env['aite.ecm.document']._nc_push_all()
        if self.nc_sync_courrier and 'aite.courrier.document' in self.env:
            docs = self.env['aite.courrier.document'].sudo().search(
                [('version_ids', '!=', False),
                 ('nc_sync_state', 'in', ('none', 'error'))])
            docs._nc_schedule()
            count += len(docs)
        cron = self.env.ref('aite_ecm_nextcloud.ir_cron_nc_sync',
                            raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()
        return self._nc_notify(_("Nextcloud"), _(
            "%d document(s) planifié(s) pour envoi ; la tâche planifiée "
            "les traite par lots.") % count)
