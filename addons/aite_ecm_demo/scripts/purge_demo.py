# -*- coding: utf-8 -*-
"""Supprime le jeu de données (courriers, documents, dossiers, tiers…).

Usage :  ./odoo-bin shell -d <base> < addons/aite_ecm_demo/scripts/purge_demo.py
Équivalent : désinstaller le module aite_ecm_demo.
"""
from odoo.addons.aite_ecm_demo.seed.generator import purge  # noqa: E402

purge(env, log=print)  # noqa: F821
env.cr.commit()  # noqa: F821
