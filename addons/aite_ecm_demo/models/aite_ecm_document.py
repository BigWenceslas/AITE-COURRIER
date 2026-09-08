# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AiteEcmDocument(models.Model):
    """Point d'entrée de la tâche planifiée du jeu de données de test."""

    _inherit = 'aite.ecm.document'

    @api.model
    def _aite_demo_seed_batch(self):
        """Exécute un lot de génération ; se re-déclenche jusqu'à la fin."""
        from ..seed.generator import DemoSeeder
        seeder = DemoSeeder(self.env)
        if seeder.is_done or not seeder.state.get('profile'):
            cron = self.env.ref('aite_ecm_demo.ir_cron_seed',
                                raise_if_not_found=False)
            if cron:
                cron.sudo().write({'active': False})
            return True
        done = seeder.run_batch()
        cron = self.env.ref('aite_ecm_demo.ir_cron_seed',
                            raise_if_not_found=False)
        if cron:
            if done:
                cron.sudo().write({'active': False})
            else:
                cron.sudo()._trigger()
        return True
