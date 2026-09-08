# -*- coding: utf-8 -*-
"""Génère (ou reprend) le jeu de données de façon synchrone, lot par lot avec
commit — pour une base où la suite est déjà installée, ou pour choisir un
profil plus volumineux.

Usage :  ./odoo-bin shell -d <base> < addons/aite_ecm_demo/scripts/seed_demo.py
Profil : modifiez PROFILE ci-dessous ('leger', 'standard' ou 'complet').
"""
from odoo.addons.aite_ecm_demo.seed.generator import DemoSeeder  # noqa: E402

PROFILE = 'leger'

seeder = DemoSeeder(env, log=print)  # noqa: F821 (env fourni par le shell)
if seeder.is_done and env['ir.config_parameter'].sudo().get_param(  # noqa: F821
        'aite_ecm_demo.seeded'):
    print("Un jeu de données existe déjà : purgez-le d'abord "
          "(scripts/purge_demo.py) pour en générer un autre.")
else:
    seeder.run_all(profile=None if seeder.state.get('profile') and
                   not seeder.is_done else PROFILE, commit=True)
    print("Terminé.")
