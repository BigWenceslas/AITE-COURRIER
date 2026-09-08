# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..seed.generator import DemoSeeder, PROFILES, purge


class AiteEcmDemoWizard(models.TransientModel):
    """Tableau de bord du jeu de données de test (ECM › Configuration)."""

    _name = 'aite.ecm.demo.wizard'
    _description = "Jeu de données de test — pilotage"

    profile = fields.Selection(
        selection=[('leger', "Léger (150 courriers, 60 documents, 40 dossiers)"),
                   ('standard', "Standard (300 courriers, 120 documents, 100 dossiers)"),
                   ('complet', "Complet (500 courriers, 200 documents, 200 dossiers)")],
        string="Profil", default='leger', required=True)
    status = fields.Text(string="État", readonly=True)
    last_error = fields.Text(string="Dernière erreur", readonly=True)
    cron_active = fields.Boolean(string="Tâche planifiée active", readonly=True)
    seeded = fields.Char(string="Terminé le", readonly=True)
    has_plan = fields.Boolean(readonly=True)
    is_done = fields.Boolean(readonly=True)

    # ------------------------------------------------------------------ #
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update(self._snapshot())
        return res

    def _snapshot(self):
        seeder = DemoSeeder(self.env)
        cron = self.env.ref('aite_ecm_demo.ir_cron_seed',
                            raise_if_not_found=False)
        state = seeder.state
        return {
            'profile': state.get('profile') or self.env[
                'ir.config_parameter'].sudo().get_param(
                'aite_ecm_demo.profile', 'leger'),
            'status': seeder.summary(),
            'last_error': state.get('last_error_detail') or False,
            'cron_active': bool(cron and cron.sudo().active),
            'seeded': self.env['ir.config_parameter'].sudo().get_param(
                'aite_ecm_demo.seeded') or False,
            'has_plan': bool(state.get('profile')),
            'is_done': seeder.is_done,
        }

    def _reopen(self):
        self.ensure_one()
        self.write(self._snapshot())
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new',
                'name': _("Jeu de données de test")}

    def _cron(self):
        return self.env.ref('aite_ecm_demo.ir_cron_seed',
                            raise_if_not_found=False)

    # ------------------------------------------------------------------ #
    def action_start(self):
        """Nouveau plan avec le profil choisi, premier lot immédiat."""
        self.ensure_one()
        seeder = DemoSeeder(self.env)
        if seeder.state.get('profile') and not seeder.is_done:
            raise UserError(_(
                "Une génération est en cours : utilisez « Générer un lot » "
                "ou « Tout générer », ou purgez d'abord."))
        if self.env['ir.config_parameter'].sudo().get_param(
                'aite_ecm_demo.seeded'):
            raise UserError(_(
                "Un jeu de données existe déjà : purgez-le avant d'en "
                "générer un autre."))
        seeder.setup(self.profile)
        done = seeder.run_batch(budget=30)
        cron = self._cron()
        if cron and not done:
            cron.sudo().write({'active': True})
            cron.sudo()._trigger()
        return self._reopen()

    def action_run_batch(self):
        """Un lot de 30 secondes, tout de suite (sans tâche planifiée)."""
        self.ensure_one()
        seeder = DemoSeeder(self.env)
        if not seeder.state.get('profile'):
            raise UserError(_("Aucun plan : cliquez d'abord « Démarrer »."))
        done = seeder.run_batch(budget=30)
        cron = self._cron()
        if cron and done:
            cron.sudo().write({'active': False})
        return self._reopen()

    def action_run_all(self):
        """Déroule tous les lots restants dans cette requête (plusieurs
        minutes possibles — réservé aux instances sans limite de temps)."""
        self.ensure_one()
        seeder = DemoSeeder(self.env)
        if not seeder.state.get('profile'):
            raise UserError(_("Aucun plan : cliquez d'abord « Démarrer »."))
        guard = 0
        while not seeder.run_batch(budget=30) and guard < 200:
            guard += 1
            seeder._loaded = False
            if seeder.state.get('last_error') == 'chargement du contexte':
                break
        cron = self._cron()
        if cron and seeder.is_done:
            cron.sudo().write({'active': False})
        return self._reopen()

    def action_trigger_cron(self):
        self.ensure_one()
        cron = self._cron()
        if not cron:
            raise UserError(_("Tâche planifiée introuvable."))
        cron.sudo().write({'active': True})
        cron.sudo()._trigger()
        return self._reopen()

    def action_purge(self):
        self.ensure_one()
        purge(self.env)
        cron = self._cron()
        if cron:
            cron.sudo().write({'active': False})
        return self._reopen()
