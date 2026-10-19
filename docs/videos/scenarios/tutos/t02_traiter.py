# -*- coding: utf-8 -*-
"""Tutoriel 02 — Traiter un courrier : faire avancer le circuit.

Sources : aite_courrier_validation (boutons « Traiter », « Rejeter »,
« Commenter » ; assistant « Action sur le courrier » ; habilitation vérifiée
côté serveur, refus tracé au journal d'audit), onglet « Historique »
(aite_courrier_core) ; recette SC02. Écran : présentation, chapitre 2.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, etape, youtube
from moteur import anneau
from tutoriel import bulle, dezoom, zoom

MANAGER = demo.PERSONNES['manager']
CH = base.CH2

TUTO = {
    'slug': 'tuto-02-traiter-un-courrier',
    'titre_page': 'AITE Courrier — Tutoriel 02 : traiter un courrier',
    'titre': 'Traiter un courrier',
    'serie': dict(COURRIER, numero=2),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Qui doit *traiter* ce dossier, et qui l\'a *validé ?*',
        'sous': 'Validations orales, notes volantes, parapheurs : impossible de savoir où en est une décision.',
        'personnage': (MANAGER[0], 'Manager', MANAGER[2]),
        'chaos': [('lettre', 'Dossier en attente'), ('bulle', 'C\'est validé, ou pas ?'), ('alerte', 'Délai dépassé'),
                  ('note', 'Visa : ?'), ('doc', 'Note manuscrite'), ('bulle', 'Je ne l\'ai jamais reçu'),
                  ('dossier', 'Parapheur'), ('alerte', 'Relance n° 2')],
        'voix': "Un dossier attend une décision. Qui doit le traiter ? A-t-il été validé, et par qui ? Entre les notes "
                "volantes et les parapheurs, la décision se perd.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, chaque décision suit un circuit clair, et laisse sa trace."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Faire avancer le *circuit,* en un geste',
        'pastilles': ['Traiter', 'Rejeter avec motif', 'Historique complet'],
        'voix': "Traiter, rejeter ou commenter : chaque geste fait avancer le courrier dans son circuit, par la bonne "
                "personne, et tout est gardé dans l'historique.",
    },
    'ecran': CH['ecran'], 'vue_initiale': 'c2-liste',
    'etapes': [
        etape(CH, 0, 'Sa file de travail', "Le filtre « En traitement » ne garde que les courriers en circulation.",
              "Paul, le manager du service, filtre les courriers en traitement : c'est sa file de travail. Il ouvre la "
              "demande d'agrément fournisseur. La barre d'étapes montre où elle en est : à l'Affectation.",
              inserer={4: [zoom('#c2-sb', s=1.6, fx=0.62, fy=0.25)]},
              apres=[bulle('#c2-sb-2', 'Étape courante', cote='dessous', d=2.0)]),
        etape(CH, 1, 'Traiter, en un seul geste', "Traiter ouvre l'action : une transition, un commentaire, puis Confirmer.",
              "Un clic sur Traiter ouvre l'action sur le courrier. Paul choisit la transition, Transmettre, et laisse "
              "un commentaire. Il confirme : le courrier passe à l'étape Traitement. Seuls les rôles habilités à "
              "l'étape peuvent le faire avancer, et un refus est tracé au journal d'audit.",
              avant=[dezoom(d=0.7)], inserer={2: [zoom('#c2-as', s=1.35, d=0.7)], 9: [dezoom(d=0.6)]},
              apres=[bulle('#c2-sb-3', 'Nouvelle étape', cote='dessous', d=2.0)]),
        etape(CH, 2, 'Un historique complet', "Pour chaque étape : l'entrée, la sortie, l'intervenant, la transition et le commentaire.",
              "L'onglet Historique garde la trace de chaque étape franchie : la date d'entrée, la date de sortie, "
              "l'intervenant, la transition choisie et son commentaire. Plus besoin de chercher qui a fait quoi.",
              inserer={5: [zoom('#c2-histo', s=1.45, d=0.8)]},
              apres=[bulle('#c2-histo', 'Qui, quand, quelle décision', cote='dessous', fx=0.5, d=2.2), dezoom(d=0.6)]),
        {'titre': 'Rejeter ou commenter', 'texte': "Un rejet exige son motif ; un commentaire informe sans changer d'étape.",
         'voix': "Deux autres gestes complètent le circuit. Rejeter arrête le courrier, et le motif est alors obligatoire. "
                 "Commenter ajoute une note au courrier, sans le faire changer d'étape.",
         'gestes': [zoom('#c2-rej', s=1.6, fx=0.4, fy=0.3, d=0.8), anneau('#c2-rej', d=2.4),
                    bulle('#c2-rej', 'Motif obligatoire', cote='dessous', d=2.4, avec=True), anneau('#c2-com', d=2.6),
                    bulle('#c2-com', "Une note, sans changer d'étape", cote='dessous', d=2.6, avec=True), dezoom(d=0.7)]},
    ],
    'benefices': {
        'titre': 'Des décisions *tracées,* sans effort.',
        'voix': "Le bon geste est fait par la bonne personne, chaque étape est tracée, et même les refus sont gardés "
                "au journal d'audit.",
        'cartes': [('equipe', 'Habilitations', 'La bonne personne', "Seuls les rôles habilités à l'étape font avancer le courrier."),
                   ('trace', 'Historique', 'Chaque étape tracée', "Entrée, sortie, intervenant, transition et commentaire."),
                   ('bouclier', 'Audit', 'Les refus aussi', "Une tentative non autorisée est tracée au journal d'audit.")],
    },
    'cta': cta('courrier', 'Chaque décision a sa *trace.*', "Aïte Courrier : chaque décision a sa trace."),
    'youtube': youtube('COMMENT TRAITER UN COURRIER ET FAIRE AVANCER SON CIRCUIT AVEC AITE COURRIER (ODOO 18)',
                       "Traiter, rejeter, commenter : le manager fait avancer le courrier d'étape en étape, et l'historique "
                       "garde la trace de chaque décision. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'circuit de validation', 'workflow Odoo', 'validation courrier']),
}
