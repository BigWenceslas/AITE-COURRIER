# -*- coding: utf-8 -*-
import logging

from . import models
from . import seed
from . import wizard

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Enregistre le plan de génération, exécute un premier lot court (les
    premières données sont visibles dès la fin de l'installation), puis arme
    la tâche planifiée qui poursuit par lots en arrière-plan."""
    from .seed.generator import DemoSeeder, DEFAULT_PROFILE, PROFILES
    Param = env['ir.config_parameter'].sudo()
    profile = Param.get_param('aite_ecm_demo.profile', DEFAULT_PROFILE)
    if profile not in PROFILES:
        profile = DEFAULT_PROFILE
    seeder = DemoSeeder(env)
    seeder.setup(profile)
    budget = float(Param.get_param('aite_ecm_demo.install_seconds', 25))
    done = seeder.run_batch(budget=budget)
    cron = env.ref('aite_ecm_demo.ir_cron_seed', raise_if_not_found=False)
    if cron and not done:
        cron.sudo().write({'active': True})
        cron.sudo()._trigger()
        _logger.info("[aite_ecm_demo] la tâche planifiée poursuit la génération.")
