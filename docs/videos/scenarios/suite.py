# -*- coding: utf-8 -*-
"""La suite AITE réunie : AITE Courrier et AITE ECM dans une seule vidéo.

Les dix chapitres de la présentation du courrier (scenarios/presentation.py),
plus « Travailler sur un document » (scenarios/chapitres_ecm.py), placé après
la gestion documentaire. Les dix-huit scénarios de recette y sont couverts.
"""

from scenarios import presentation as base
from scenarios.chapitres_ecm import CH_TRAVAIL
from scenarios.ecm import SCENARIO as ECM

S = base.SCENARIO

SCENARIO = dict(S)
SCENARIO.update({
    'slug': '00-suite',
    'profil': 'suite',
    'id': 'suite',
    'marque': ('AITE', 'Courrier & ECM'),
    'titre_page': 'Suite AITE — Courrier et ECM',
    'ouverture': dict(S['ouverture'], sous='Courrier · GED · Conservation · Preuve · Odoo 18',
                      kicker='La suite AITE',
                      titre='Le courrier et les documents, *une seule suite.*',
                      mission="Enregistrer et faire circuler le courrier, organiser tout le fonds documentaire, prouver et "
                              "conserver : deux applications, mêmes rôles, mêmes circuits, même journal d'audit."),
    'cartes_intro': [dict(S['cartes_intro'][0], voix_cle='suite-intro-1')],
    'sommaire_titre': 'Onze chapitres, toute la suite',
    'chapitres': [base.CH1, base.CH2, base.CH3, base.CH4, CH_TRAVAIL, base.CH5, base.CH6, base.CH7, base.CH8, base.CH9, base.CH10],
    'cartes_fin': [S['cartes_fin'][0], S['cartes_fin'][1], ECM['cartes_fin'][1]],
    'fin': {'sous': 'Courrier · GED · Conservation · Preuve · Odoo 18', 'pied': 'AITE Consulting · www.aite-consulting.com'},
    'voix': dict(S['voix'],
                 ouverture="La suite Aïte, Courrier et E C M : le courrier et les documents de votre organisation, dans une seule "
                           "suite. Enregistrer, faire circuler, organiser, prouver et conserver.",
                 sommaire="Suivons maintenant toute la suite, en onze chapitres, sur les écrans de l'application.",
                 retenir="À retenir : avec la suite Aïte, chaque courrier a un circuit, chaque document une histoire, et chaque action une trace.",
                 fin="La suite Aïte, Courrier et E C M, par Aïte Consulting. Merci de votre attention."),
    'vignette': {'chapitre': 5, 'etape': 1, 'apres': 3.5},
})
