# -*- coding: utf-8 -*-
"""Tutoriel 04 — Les pièces du courrier et leurs versions.

Sources : aite_courrier_ged/views (espace documentaire, « Prévisualiser »,
« Finaliser », onglet « Versions », ruban « Verrouillé », confidentialité
héritée), aite_courrier_ocr (colonne d'indexation, recherche plein texte) ;
recette SC03. Écran : présentation, chapitre 3.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, etape, youtube
from moteur import anneau, curseur
from tutoriel import bulle, dezoom, zoom

ASSIST = demo.PERSONNES['assistante']
CH = base.CH3

TUTO = {
    'slug': 'tuto-04-les-pieces-et-leurs-versions',
    'titre_page': 'AITE Courrier — Tutoriel 04 : les pièces et leurs versions',
    'titre': 'Les pièces et leurs versions',
    'serie': dict(COURRIER, numero=4),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Quelle est la *bonne* version de ce *devis ?*',
        'sous': 'Pièces jointes perdues dans les e-mails, fichiers « final_v3_def » : la bonne version introuvable.',
        'personnage': (ASSIST[0], 'Assistante', ASSIST[2]),
        'chaos': [('doc', 'devis_final_v3.pdf'), ('bulle', 'Tu as la dernière version ?'), ('doc', 'devis_final_DEF.pdf'),
                  ('alerte', 'Fichier écrasé'), ('lettre', 'Pièce jointe perdue'), ('note', 'Qui l\'a modifié ?'),
                  ('dossier', 'Dossier partagé'), ('bulle', 'C\'est confidentiel, non ?')],
        'voix': "Le devis final, version trois, ou version définitive ? Entre les pièces jointes et les dossiers "
                "partagés, plus personne ne sait quelle est la bonne version.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, chaque pièce garde toutes ses versions, au bon endroit."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Chaque *pièce,* toutes ses *versions*',
        'pastilles': ['Classées par dossier', 'Confidentialité héritée', 'Rien ne s\'écrase'],
        'voix': "Les pièces des courriers sont rangées par dossier, elles héritent de la confidentialité de leur courrier, "
                "et leurs versions s'empilent : rien n'est jamais écrasé.",
    },
    'ecran': CH['ecran'], 'vue_initiale': 'c3-liste',
    'etapes': [
        etape(CH, 0, "L'espace documentaire", "Toutes les pièces des courriers, regroupées par dossier.",
              "L'espace documentaire réunit toutes les pièces jointes aux courriers, regroupées par dossier : les devis, "
              "les factures, la direction. Le dossier se choisit tout seul, selon le type du courrier. Estelle ouvre un devis.",
              avant=[bulle('#c3-g0', 'Un dossier par type de pièce', cote='droite', fx=0.35, d=2.2)]),
        {'titre': 'Une confidentialité héritée', 'texte': "La pièce suit la confidentialité de son courrier : ici, Secret.",
         'voix': "La pièce hérite de la confidentialité de son courrier : ici, Secret. Elle n'est donc visible que des "
                 "personnes autorisées à voir ce courrier, partout dans l'application.",
         'gestes': [zoom('#c3-conf', s=1.7, fx=0.55, d=0.9), anneau('#c3-conf', d=1.6),
                    bulle('#c3-conf', 'Héritée du courrier', cote='dessous', d=2.4), dezoom(d=0.7)]},
        {'titre': 'Des versions empilées', 'texte': "La dernière en tête ; les précédentes restent consultables. Verrouillée, la pièce ne bouge plus.",
         'voix': "Ses versions s'empilent, la dernière en tête, chacune avec son fichier, sa taille et son auteur. Rien "
                 "n'est écrasé. La colonne Indexation suit l'extraction du texte, pour la recherche plein texte. "
                 "Et une pièce verrouillée ne se modifie plus.",
         'gestes': [zoom('#c3-versions', s=1.4, d=0.9), anneau('#c3-versions', d=1.8),
                    bulle('#c3-v2', 'La dernière version en tête', cote='dessous', fx=0.3, d=2.4), dezoom(d=0.7),
                    anneau('#c3-ruban', d=1.4), bulle('#c3-ruban', 'Verrouillée', cote='gauche', fx=0.15, d=2.0)]},
        {'titre': 'Prévisualiser en un clic', 'texte': "Prévisualiser ouvre la dernière version : le PDF s'affiche directement.",
         'voix': "Enfin, Prévisualiser ouvre la dernière version dans un onglet : le PDF s'affiche directement, sans "
                 "téléchargement. Chaque version reste aussi téléchargeable.",
         'gestes': [curseur('#c3-prev'), anneau('#c3-prev', d=1.4), bulle('#c3-prev', 'Le PDF, sans téléchargement', cote='dessous', d=2.4)]},
    ],
    'benefices': {
        'titre': 'La bonne version, *toujours.*',
        'voix': "La bonne version est toujours en tête, l'historique est complet, et la confidentialité du courrier "
                "protège aussi ses pièces.",
        'cartes': [('doc', 'v1 · v2 · v3', 'Toutes les versions', "Empilées, jamais écrasées, chacune avec son auteur."),
                   ('cadenas', 'Héritée', 'Confidentialité suivie', "Une pièce Secret reste Secret, partout."),
                   ('eclair', 'Un clic', 'Prévisualiser', "Le PDF s'ouvre directement, sans téléchargement.")],
    },
    'cta': cta('courrier', 'La bonne *version,* toujours.', "Aïte Courrier : la bonne version, toujours."),
    'youtube': youtube('COMMENT GÉRER LES PIÈCES ET LES VERSIONS DE VOS COURRIERS AVEC AITE COURRIER (ODOO 18)',
                       "L'espace documentaire d'AITE Courrier : les pièces classées par dossier, la confidentialité héritée du "
                       "courrier, les versions empilées sans jamais rien écraser. Tutoriel pour Odoo 18.",
                       ['AITE Courrier', 'GED Odoo', 'versions de documents', 'pièces jointes']),
}
