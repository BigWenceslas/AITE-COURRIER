# -*- coding: utf-8 -*-
"""Tutoriel 10 — Le tableau de bord.

Sources : aite_courrier/static/src/xml (indicateurs « En cours », « En retard
(SLA) », « Reçus ce mois », « Archivés ce mois », « Taux de rejet », « Délai
moyen de traitement », « Charge par étape (en cours) », « Répartition par
catégorie »), menu « Tableau de bord » réservé aux managers et à l'audit ;
recette SC12. Écran : présentation, chapitre 10.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, etape, youtube
from moteur import anneau
from tutoriel import bulle, dezoom, zoom

MANAGER = demo.PERSONNES['manager']
CH = base.CH10

TUTO = {
    'slug': 'tuto-10-le-tableau-de-bord',
    'titre_page': 'AITE Courrier — Tutoriel 10 : le tableau de bord',
    'titre': 'Le tableau de bord',
    'serie': dict(COURRIER, numero=10),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Combien de courriers *attendent,* et *où ?*',
        'sous': 'Sans chiffres, impossible de savoir qui est débordé, ni quels dossiers dorment.',
        'personnage': (MANAGER[0], 'Manager', MANAGER[2]),
        'chaos': [('alerte', 'Retards ?'), ('bulle', 'On en a combien en cours ?'), ('doc', 'Tableau Excel à jour ?'),
                  ('note', 'Délai moyen : ?'), ('dossier', 'Piles de dossiers'), ('bulle', 'Qui est débordé ?'),
                  ('lettre', 'Courriers du mois'), ('alerte', 'Comité demain')],
        'voix': "Demain, comité de direction. Combien de courriers en cours ? Combien en retard ? Qui est débordé ? "
                "Sans chiffres fiables, impossible de répondre.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, votre activité se lit d'un coup d'œil."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Piloter d\'un *coup* *d\'œil*',
        'pastilles': ['Six indicateurs', 'Retards (SLA)', 'Charge par étape'],
        'voix': "Le tableau de bord rassemble six indicateurs clés, les retards sur les délais, et la charge de chaque "
                "étape du circuit.",
    },
    'ecran': CH['ecran'], 'vue_initiale': 'c10-tb',
    'etapes': [
        etape(CH, 0, "L'activité d'un coup d'œil", "En cours, en retard, reçus et archivés du mois, taux de rejet, délai moyen.",
              "Paul ouvre le tableau de bord. L'essentiel s'affiche d'un coup d'œil : les courriers en cours, ceux qui "
              "dépassent leur délai, les reçus et les archivés du mois, le taux de rejet et le délai moyen de traitement."),
        {'titre': 'Les retards remontent seuls', 'texte': "« En retard (SLA) » : les courriers qui ont dépassé le délai de leur étape.",
         'voix': "La tuile En retard compte les courriers qui ont dépassé le délai de leur étape. Ces retards remontent "
                 "seuls : une tâche planifiée relance, puis escalade les courriers en retard. Et le délai moyen mesure "
                 "le temps réel de traitement.",
         'gestes': [zoom('#c10-t1', s=1.8, d=0.9), anneau('#c10-t1', d=1.6), bulle('#c10-t1', 'Délai dépassé', cote='dessous', d=2.2),
                    dezoom(d=0.6), zoom('#c10-t5', s=1.8, d=0.8), anneau('#c10-t5', d=1.4),
                    bulle('#c10-t5', 'Temps réel de traitement', cote='dessous', d=2.2), dezoom(d=0.7)]},
        etape(CH, 1, 'Où le courrier attend', "La charge par étape montre où renforcer l'équipe.",
              "La charge par étape montre où les courriers attendent, et donc où renforcer l'équipe. À droite, la "
              "répartition entre courriers entrants, sortants et internes. Analyse détaillée ouvre l'analyse complète, "
              "en graphique ou en tableau croisé.",
              avant=[zoom('#c10-charge', s=1.45, d=0.8)], apres=[dezoom(d=0.7)]),
    ],
    'benefices': {
        'titre': 'Décider sur des *chiffres.*',
        'voix': "Les indicateurs sont à jour en permanence, les retards sautent aux yeux, et vous savez où renforcer "
                "votre équipe.",
        'cartes': [('cible', '6', 'Indicateurs clés', "En cours, retards, reçus, archivés, rejets, délai moyen."),
                   ('temps', 'SLA', 'Retards visibles', "Les dépassements de délai remontent d'eux-mêmes."),
                   ('equipe', 'Charge', 'Équipe bien dimensionnée', "Voir où le courrier attend, étape par étape.")],
    },
    'cta': cta('courrier', 'Pilotez votre *courrier.*', "Aïte Courrier : pilotez votre courrier."),
    'youtube': youtube('COMMENT PILOTER L\'ACTIVITÉ COURRIER AVEC LE TABLEAU DE BORD AITE COURRIER (ODOO 18)',
                       "Courriers en cours, retards sur les délais, taux de rejet, délai moyen, charge par étape : le tableau de "
                       "bord d'AITE Courrier pour piloter votre service courrier. Tutoriel pour Odoo 18.",
                       ['AITE Courrier', 'tableau de bord Odoo', 'indicateurs', 'SLA']),
}
