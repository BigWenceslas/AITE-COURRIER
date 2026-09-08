# -*- coding: utf-8 -*-
from odoo import _, models

from odoo.addons.aite_ecm_nextcloud.models.nextcloud_client import sanitize


class AiteCourrierDocument(models.Model):
    """Pièce de courrier miroitée (option « synchroniser le courrier »)."""

    _name = 'aite.courrier.document'
    _inherit = ['aite.courrier.document', 'aite.ecm.nextcloud.mixin']

    def _nc_model_enabled(self):
        return self._nc_params()['sync_courrier']

    def _nc_target_dir(self):
        self.ensure_one()
        courrier = self.courrier_id
        year = courrier.date_received.year if courrier.date_received \
            else courrier.create_date.year
        ref = courrier.reference or _("Brouillon %d") % courrier.id
        return "%s/%s/%s - %s" % (_("Courrier"), year, ref,
                                  sanitize(courrier.subject or '', 60))

    def _nc_reference(self):
        self.ensure_one()
        return "%s / %s" % (self.courrier_id.reference or self.courrier_id.id,
                            self.name)

    def _nc_pull_user(self):
        self.ensure_one()
        return self.courrier_id.responsible_id or self.create_uid

    def add_version(self, filename, datas):
        version = super().add_version(filename, datas)
        if not self.env.context.get('nc_skip_push') and self._nc_schedule():
            if self._nc_params()['immediate']:
                self._nc_try_push()
        return version
