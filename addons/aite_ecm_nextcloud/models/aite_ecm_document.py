# -*- coding: utf-8 -*-
from odoo import _, api, models

from .nextcloud_client import sanitize


class AiteEcmDocument(models.Model):
    """Document ECM miroité dans Nextcloud sous le plan de classement."""

    _name = 'aite.ecm.document'
    _inherit = ['aite.ecm.document', 'aite.ecm.nextcloud.mixin']

    def _nc_model_enabled(self):
        """Les documents Confidentiel / Secret restent dans Odoo, sauf option
        explicite : le partage de dossiers Nextcloud est moins fin que les
        droits ECM."""
        self.ensure_one()
        if self.confidentiality_code in ('CONF', 'SEC'):
            return self._nc_params()['sync_confidential']
        return True

    def _nc_target_dir(self):
        self.ensure_one()
        if self.folder_id:
            segments = [sanitize(s.strip()) for s in
                        self.folder_id.complete_name.split(' / ')]
        else:
            segments = [_("Sans classement")]
        segments.append("%s - %s" % (self.reference or self.id,
                                     sanitize(self.name, 60)))
        return '/'.join(segments)

    def _nc_pull_user(self):
        """La version importée est attribuée à l'utilisateur qui a réservé
        le document (session d'édition), sinon au propriétaire."""
        self.ensure_one()
        if self.is_checked_out and self.checkout_user_id:
            return self.checkout_user_id
        return self.owner_id or self.create_uid

    def add_version(self, filename, datas, comment=False):
        version = super().add_version(filename, datas, comment)
        if not self.env.context.get('nc_skip_push') and self._nc_schedule():
            if self._nc_params()['immediate']:
                self._nc_try_push()
        return version

    def write(self, vals):
        res = super().write(vals)
        if ({'name', 'folder_id'} & set(vals)) and not self.env.context.get(
                'nc_skip_push'):
            self.filtered('nc_path')._nc_schedule()
        if 'active' in vals and not vals['active']:
            # corbeille : le miroir reste en place jusqu'à la purge
            pass
        return res

    def unlink(self):
        """Suppression définitive : le miroir Nextcloud est retiré."""
        paths = [(d.nc_path, d.nc_share_id) for d in self if d.nc_path]
        res = super().unlink()
        if paths and self._nc_active():
            try:
                client = self._nc_client()
                for path, share_id in paths:
                    if share_id:
                        client.delete_share(share_id)
                    client.delete(path.rsplit('/', 1)[0])
            except Exception:  # noqa: BLE001 — nettoyage best effort
                pass
        return res

    @api.model
    def _nc_push_all(self):
        """Envoi initial du fonds (bouton des paramètres)."""
        docs = self.sudo().search([('version_ids', '!=', False),
                                   ('nc_sync_state', 'in', ('none', 'error'))])
        docs._nc_schedule()
        return len(docs)
