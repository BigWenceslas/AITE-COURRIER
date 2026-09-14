# -*- coding: utf-8 -*-
import logging

from . import models
from . import seed
from . import wizard

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Enregistre le plan de génération, exécute un premier lot court (les
    premières données sont visibles dès la fin de l'installation), puis arme
    la tâche planifiée qui poursuit par lots en arrière-plan.

    Le premier lot est **sauté** si d'autres modules restent à installer :
    quand toute la suite s'installe en une commande, les modèles du courrier
    ne sont pas encore au registre au moment de ce crochet, et les courriers
    du jeu de données seraient tous ignorés. La tâche planifiée, elle,
    s'exécute sur un registre complet.
    """
    from .seed.generator import DemoSeeder, DEFAULT_PROFILE, PROFILES
    Param = env['ir.config_parameter'].sudo()
    profile = Param.get_param('aite_ecm_demo.profile', DEFAULT_PROFILE)
    if profile not in PROFILES:
        profile = DEFAULT_PROFILE
    seeder = DemoSeeder(env)
    seeder.setup(profile)
    pending = env['ir.module.module'].sudo().search_count(
        [('state', 'in', ('to install', 'to upgrade'))])
    if pending:
        _logger.info("[aite_ecm_demo] %d module(s) encore en cours "
                     "d'installation : la génération démarre en tâche de "
                     "fond, sur un registre complet.", pending)
        done = False
    else:
        budget = float(Param.get_param('aite_ecm_demo.install_seconds', 25))
        done = seeder.run_batch(budget=budget)
    cron = env.ref('aite_ecm_demo.ir_cron_seed', raise_if_not_found=False)
    if cron and not done:
        cron.sudo().write({'active': True})
        cron.sudo()._trigger()
        _logger.info("[aite_ecm_demo] la tâche planifiée poursuit la génération.")


def uninstall_hook(env):
    """Purge le jeu de données avant le nettoyage générique d'Odoo.

    Odoo supprime les enregistrements par identifiant externe, sans ordre
    métier : dossiers avant documents, tiers avant comptes. La purge du
    module connaît, elle, les dépendances — la lancer d'abord évite la
    cascade d'erreurs d'intégrité et garantit qu'il ne reste rien.
    """
    from .seed.generator import purge
    purge(env)
