# -*- coding: utf-8 -*-
"""Tutoriel 09 — Le portail des tiers.

Sources : aite_courrier_portal/views/portal_templates.xml (« Mes courriers »,
« Nouvelle demande », « Objet », « Nature de la demande », « Votre message »,
« Pièces jointes », « Envoyer la demande », « Avancement », « Cachet de
traitement », « Pièces du dossier ») ; recette SC15. Écran : présentation,
chapitre 8.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import COURRIER, cta, etape, youtube
from moteur import anneau
from tutoriel import bulle, dezoom, zoom

CH = base.CH8

TUTO = {
    'slug': 'tuto-09-le-portail-des-tiers',
    'titre_page': 'AITE Courrier — Tutoriel 09 : le portail des tiers',
    'titre': 'Le portail des tiers',
    'serie': dict(COURRIER, numero=9),
    'adresse': 'courrier.aite-demo.test/my/courriers',
    'accroche': {
        'question': '« Où en est *ma* *demande ?* »',
        'sous': 'Appels, relances, déplacements : vos partenaires veulent savoir, et vos équipes répondent au téléphone.',
        'personnage': (demo.TIERS, 'Tiers externe', '#2E8CB2'),
        'chaos': [('bulle', 'Vous avez bien reçu mon courrier ?'), ('alerte', '5e appel'), ('lettre', 'Dépôt au guichet'),
                  ('note', 'Rappeler le client'), ('bulle', 'C\'est traité quand ?'), ('doc', 'Accusé perdu'),
                  ('dossier', 'Pièces à redéposer'), ('alerte', 'Réclamation')],
        'voix': "Vos partenaires déposent leurs courriers au guichet, puis appellent pour savoir où en est leur demande. "
                "Et vos équipes passent leurs journées au téléphone.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, vos partenaires déposent et suivent leurs demandes en ligne."},
    'apercu': {
        'kicker': 'AITE Courrier · Portail', 'titre': 'Déposer et *suivre* en ligne',
        'pastilles': ['Dépôt avec pièces jointes', 'Suivi étape par étape', 'Cachet de traitement'],
        'voix': "Sur le portail, le tiers dépose sa demande avec ses pièces jointes, suit son avancement étape par étape, "
                "et voit le cachet de traitement, une fois sa demande traitée.",
    },
    'ecran': CH['ecran'], 'vue_initiale': 'c8-compte',
    'etapes': [
        etape(CH, 0, 'Son espace, ses courriers', "Mes courriers : toutes ses demandes, avec un statut écrit pour lui.",
              "Depuis son espace personnel, le tiers ouvre Mes courriers. Il y retrouve toutes ses demandes, avec un statut "
              "rédigé pour lui : reçue, en traitement, traitée.",
              apres=[bulle('#c8-l1', 'Un statut clair', cote='dessous', fx=0.75, d=2.2)]),
        etape(CH, 1, 'Déposer une demande', "Objet, nature, message et pièces jointes, puis Envoyer la demande.",
              "Il dépose une nouvelle demande : l'objet, la nature, son message, et ses pièces jointes, plusieurs à la "
              "fois. À l'envoi, la demande arrive directement dans le courrier entrant de l'organisation, et un message "
              "lui confirme la réception.",
              inserer={2: [zoom('#c8-objet', s=1.4, fy=0.45, d=0.8)], 10: [dezoom(d=0.6)]},
              apres=[bulle('#c8-ok', 'Réception confirmée', cote='dessous', d=2.2)]),
        etape(CH, 2, "Suivre, jusqu'au cachet", "L'avancement étape par étape, puis le cachet de traitement.",
              "Il suit ensuite l'avancement, étape par étape. Une fois sa demande traitée, il voit le cachet de traitement, "
              "avec la fonction de chaque intervenant et la date de son visa, et télécharge les pièces du dossier.",
              apres=[zoom('#c8-cachet', s=1.7, d=0.9), bulle('#c8-cachet', 'Demande traitée', cote='droite', d=2.2), dezoom(d=0.7)]),
    ],
    'benefices': {
        'titre': 'Moins d\'appels, des partenaires *rassurés.*',
        'voix': "Le dépôt se fait en ligne, à toute heure, le suivi est transparent, et la preuve du traitement est "
                "remise sans un appel.",
        'cartes': [('eclair', '24 h / 24', 'Dépôt en ligne', "La demande arrive directement dans le courrier entrant."),
                   ('trace', 'Avancement', 'Suivi transparent', "Le tiers voit chaque étape de sa demande."),
                   ('bouclier', 'Cachet', 'Preuve remise', "Le cachet de traitement, visible sur le portail.")],
    },
    'cta': cta('courrier', 'Vos partenaires, *mieux* *servis.*', "Aïte Courrier : vos partenaires, mieux servis."),
    'youtube': youtube('COMMENT VOS PARTENAIRES DÉPOSENT ET SUIVENT LEURS COURRIERS EN LIGNE : LE PORTAIL AITE COURRIER (ODOO 18)',
                       "Le portail des tiers d'AITE Courrier : dépôt de demandes avec pièces jointes, suivi étape par étape et "
                       "cachet de traitement, sans un appel. Tutoriel pour Odoo 18.",
                       ['AITE Courrier', 'portail Odoo', 'portail client', 'suivi de demande']),
}
