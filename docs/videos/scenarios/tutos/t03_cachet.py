# -*- coding: utf-8 -*-
"""Tutoriel 03 — Le cachet de traitement.

Sources : docs/produits/AITE_Courrier_cachet_de_traitement.md (ruban
« Traité », onglet « Cachet » : étape, intervenant, fonction, date ; sur le
portail, la fonction seule), aite_courrier_core/views/aite_courrier_views.xml
(ruban, onglet Cachet, filtre « Traités »), aite_courrier_validation (bandeau
« Circuit terminé — courrier archivé. »), portail (« Cachet de traitement ») ;
recette SC18 et SC15. Écrans : présentation, chapitres 2 et 8.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, initiale, youtube
from moteur import anneau, cacher, montrer, pause, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

ARCHI = demo.PERSONNES['archiviste']
ecran = initiale(base.CH2['ecran'], 'c2-clos', 'c2-liste')
portail = base.CH8['ecran'].replace('class="o-app portail" id="app-8"', 'class="o-app portail masque" id="app-8"', 1)

TUTO = {
    'slug': 'tuto-03-le-cachet-de-traitement',
    'titre_page': 'AITE Courrier — Tutoriel 03 : le cachet de traitement',
    'titre': 'Le cachet de traitement',
    'serie': dict(COURRIER, numero=3),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Ce courrier a-t-il *vraiment* été *traité ?*',
        'sous': 'Un tampon illisible, des visas oubliés : prouver qu\'un dossier est clos tient souvent du pari.',
        'personnage': (ARCHI[0], 'Archiviste', ARCHI[2]),
        'chaos': [('lettre', 'Dossier « clos » ?'), ('bulle', 'Qui a signé en dernier ?'), ('note', 'Tampon illisible'),
                  ('alerte', 'Visa manquant'), ('doc', 'Copie sans date'), ('bulle', 'Le client redemande'),
                  ('dossier', 'Archives'), ('alerte', 'Réclamation')],
        'voix': "Un client demande si son dossier a été traité. Le tampon est illisible, un visa manque, la date est "
                "introuvable. Comment le prouver ?",
    },
    'revelation': {'voix': "Avec Aïte Courrier, un courrier traité porte son cachet, comme un tampon officiel."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Un *cachet* qui prouve le traitement',
        'pastilles': ['Ruban « Traité »', 'Visas de chaque étape', 'Visible par le tiers'],
        'voix': "Au bout du circuit, le courrier reçoit son cachet de traitement : un ruban Traité, les visas de chaque "
                "étape, et la même preuve pour le tiers, sur son portail.",
    },
    'ecran': ecran + portail, 'vue_initiale': 'c2-clos',
    'etapes': [
        {'titre': 'Traité, au premier coup d\'œil', 'texte': "Courrier archivé, bandeau « Circuit terminé », ruban « Traité ».",
         'voix': "Jules, l'archiviste, ouvre un courrier arrivé au bout de son circuit. Le bandeau l'annonce : circuit "
                 "terminé, courrier archivé. Et le ruban Traité se voit au premier coup d'œil.",
         'gestes': [anneau('#c2-sb2', d=1.4, decale=0.4), anneau('#c2-clos .bandeau', d=1.6),
                    zoom('#c2-ruban', s=1.7, fx=0.62, fy=0.35, d=0.9), anneau('#c2-ruban', d=1.4),
                    bulle('#c2-ruban', 'Ruban « Traité »', cote='gauche', fx=0.1, d=2.2), dezoom(d=0.7)]},
        {'titre': 'Les visas de chaque étape', 'texte': "L'onglet Cachet : l'étape, l'intervenant, sa fonction et la date.",
         'voix': "L'onglet Cachet récapitule le traitement : la date de clôture, le nombre de visas, et pour chaque étape, "
                 "l'intervenant, sa fonction et la date. C'est la preuve, prête à être montrée.",
         'gestes': [zoom('#c2-cachet', s=1.5, d=0.9), anneau('#c2-cachet-b', d=1.6),
                    bulle('#c2-cachet', 'Nom, fonction, date', cote='dessous', d=2.4), anneau('#c2-cachet', d=1.8), dezoom(d=0.7)]},
        {'titre': 'Le tiers voit le même cachet', 'texte': "Sur son portail : « Demande traitée », les fonctions et les dates.",
         'voix': "Le tiers, lui, voit le même cachet sur son portail : demande traitée, avec la fonction de chaque "
                 "intervenant et la date de son visa. Ses noms restent internes : seule la fonction est publiée.",
         'gestes': [texte('#pr-url', 'courrier.aite-demo.test/my/courriers'), cacher('#c8-compte', d=0.05),
                    montrer('#app-8', y=0, d=0.4), aller('c8-suivi'), pause(0.4), anneau('#c8-av', d=1.4),
                    zoom('#c8-cachet', s=1.7, d=0.9), anneau('#c8-cachet', d=1.6),
                    bulle('#c8-cachet', 'La fonction, pas le nom', cote='droite', d=2.4), dezoom(d=0.7)]},
    ],
    'benefices': {
        'titre': 'La preuve du traitement, *partagée.*',
        'voix': "Un courrier traité se reconnaît tout de suite, ses visas sont réunis au même endroit, et le tiers "
                "reçoit la même preuve, sans un appel.",
        'cartes': [('bouclier', 'Traité', 'Visible tout de suite', "Ruban et bandeau sur chaque courrier clos."),
                   ('trace', 'Visas', 'Une preuve complète', "L'étape, l'intervenant, sa fonction et la date de chaque visa."),
                   ('equipe', 'Portail', 'Le tiers rassuré', "Il voit le cachet de sa demande, sans appeler.")],
    },
    'cta': cta('courrier', 'Le traitement, *prouvé.*', "Aïte Courrier : le traitement, prouvé."),
    'youtube': youtube('COMMENT PROUVER QU\'UN COURRIER A ÉTÉ TRAITÉ : LE CACHET DE TRAITEMENT AITE COURRIER (ODOO 18)',
                       "Au bout de son circuit, chaque courrier reçoit un cachet de traitement : ruban « Traité », visas de "
                       "chaque étape, et la même preuve pour le tiers sur son portail. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'cachet de traitement', 'portail tiers', 'preuve de traitement']),
}
