# -*- coding: utf-8 -*-
"""Tutoriel 01 — Enregistrer un courrier et lancer son circuit.

Sources : aite_courrier_core/views/aite_courrier_views.xml (« Enregistrer et
lancer le circuit », groupe « Aperçu du circuit »), models/aite_courrier.py
(champs, statuts, référence COUR-AAAA-NNNN), aite_courrier_workflow/data/
workflow_circuits.xml (Courrier entrant standard : Réception 4 h,
Qualification 8 h, Affectation 4 h, Traitement 48 h, Archivage 24 h) ;
recette SC01. Écran : scenarios/presentation.py, chapitre 1.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, youtube
from moteur import anneau, cacher, choisir, clic, etat, montrer, pause, saisir, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

AGENT = demo.PERSONNES['agent']
N1 = demo.NOUVEAU

TUTO = {
    'slug': 'tuto-01-enregistrer-un-courrier',
    'titre_page': 'AITE Courrier — Tutoriel 01 : enregistrer un courrier',
    'titre': 'Enregistrer un courrier',
    'serie': dict(COURRIER, numero=1),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Un courrier arrive. Qui s\'en *occupe,* et *quand ?*',
        'sous': 'Plis égarés, relances, délais inconnus : le courrier papier se perd entre deux bureaux.',
        'personnage': (AGENT[0], 'Agent courrier', AGENT[2]),
        'chaos': [('lettre', 'Pli reçu, sans référence'), ('alerte', 'Relance n° 3'), ('bulle', 'Tu as vu la lettre du fisc ?'),
                  ('note', 'Délai : ?'), ('dossier', 'Classeur « Arrivées »'), ('doc', 'Registre papier'),
                  ('bulle', 'Qui l\'a sur son bureau ?'), ('alerte', 'En retard')],
        'voix': "Un courrier arrive à l'accueil. Il passe de bureau en bureau, personne ne sait où il en est, "
                "et les relances s'accumulent. Ça vous parle ?",
    },
    'revelation': {'voix': "Avec Aïte Courrier, chaque pli devient un courrier suivi, dès la première minute."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Enregistrer un *courrier* en quelques clics',
        'pastilles': ['Référence unique', 'Circuit lancé automatiquement', 'Équipe prévenue'],
        'voix': "En quelques clics, le courrier reçoit sa référence unique, il part dans son circuit de traitement, "
                "et chaque personne concernée est prévenue. Voyons comment.",
    },
    'ecran': base.CH1['ecran'], 'vue_initiale': 'c1-liste',
    'etapes': [
        {'titre': 'Ouvrir la liste et créer',
         'texte': 'Entrants, internes, sortants : tout le courrier au même endroit, filtré en un clic.',
         'voix': "Tout le courrier de l'organisation est au même endroit. À gauche, on filtre par catégorie, entrant, "
                 "interne ou sortant, et par statut. Pour un nouveau pli, Carine clique sur Nouveau.",
         'gestes': [anneau('#c1-lat', d=1.8), bulle('#c1-lat', 'Catégorie et statut', d=2.4), survol('#c1-l3', decale=0.3),
                    pause(1.0), clic('#c1-nouveau'), aller('c1-form')]},
        {'titre': "Saisir l'essentiel",
         'texte': "Objet, expéditeur, adresse, type : quatre champs suffisent.",
         'voix': "Carine saisit l'objet du courrier, puis l'expéditeur et son adresse électronique, pour pouvoir lui "
                 "répondre. Enfin, elle choisit le type : courrier entrant, sortant, interne, facture ou devis. "
                 "Quatre champs suffisent, le reste suit.",
         'gestes': [zoom('#c1-exp', s=1.55, fy=0.42), clic('#c1-objet', fx=0.3), saisir('c1-objet', N1['objet'], d=1.5),
                    clic('#c1-exp', fx=0.3), saisir('c1-exp', N1['expediteur'], d=1.2),
                    clic('#c1-mail', fx=0.3), saisir('c1-mail', N1['courriel'], d=0.9),
                    clic('#c1-type', fx=0.3), choisir('c1-type', 'Courrier entrant'),
                    bulle('#c1-type', 'Le type choisit le circuit', d=2.2)]},
        {'titre': 'Le circuit, avant même d\'enregistrer',
         'texte': "Cinq étapes, chacune avec son délai en heures : tout le monde sait ce qui l'attend.",
         'voix': "Le type désigne le circuit : ici, le courrier entrant standard, en cinq étapes, de la réception à "
                 "l'archivage, chacune avec son délai en heures. L'aperçu s'affiche avant même l'enregistrement.",
         'gestes': [montrer('#c1-circuit', d=0.5), zoom('#c1-circuit', s=1.5, d=1.0), anneau('#c1-circuit', d=2.4),
                    bulle('#c1-s3', 'Traitement : 48 h', d=2.6, cote='gauche', fx=0.58)]},
        {'titre': 'Enregistrer et lancer le circuit',
         'texte': "Un clic : référence attribuée, étape Réception, activités envoyées à l'équipe.",
         'voix': "Un clic sur Enregistrer et lancer le circuit. La référence est attribuée automatiquement, le courrier "
                 "entre à l'étape Réception, et chaque personne concernée reçoit une activité à traiter. "
                 "Le courrier est lancé : plus rien ne se perd.",
         'gestes': [dezoom(d=0.8), clic('#c1-lancer'), cacher('#c1-circuit', d=0.3), texte('#c1-ref', N1['reference'], avec=True),
                    texte('#c1-titre', N1['reference'], avec=True), texte('#c1-msg0 .tx', 'Courrier créé', avec=True),
                    etat('#c1-statut', 'Nouveau', 'gris', avec=True, decale=0.1),
                    cacher('#c1-bande-a', d=0.2), montrer('#c1-bande-b', y=0, avec=True), montrer('#c1-sb', y=0, avec=True),
                    zoom('#c1-ref', s=1.6, fx=0.35, fy=0.35, d=0.8), bulle('#c1-ref', 'Référence unique', d=2.0),
                    dezoom(d=0.7), montrer('#c1-msg1', y=10), montrer('#c1-act0', y=10, decale=0.3),
                    montrer('#c1-act1', y=10, decale=0.3), anneau('#c1-chatter', d=1.6), anneau('#c1-sb', d=1.4)]},
    ],
    'benefices': {
        'titre': 'Plus aucun pli *perdu.*',
        'voix': "Le résultat : chaque courrier est tracé de bout en bout, chaque étape a son délai, et l'équipe est "
                "prévenue sans un seul appel.",
        'cartes': [('trace', N1['reference'], 'Tracé de bout en bout', "Une référence unique, l'historique de chaque étape, le journal d'audit."),
                   ('temps', '4 h · 48 h', 'Des délais clairs', "Chaque étape a son délai ; les retards remontent d'eux-mêmes."),
                   ('equipe', 'Activités', 'Une équipe prévenue', "Chaque personne concernée reçoit son activité, au bon moment.")],
    },
    'cta': {'titre': 'Votre courrier, enfin *sous* *contrôle.*', 'sous': 'AITE Courrier · le courrier et ses documents dans Odoo 18',
            'voix': "Aïte Courrier : votre courrier, enfin sous contrôle. Demandez votre démonstration sur Aïte Consulting point com."},
    'youtube': youtube('COMMENT ENREGISTRER UN COURRIER ET LANCER SON CIRCUIT AVEC AITE COURRIER (ODOO 18)',
                       "Un courrier arrive : en quelques clics, il reçoit sa référence unique, part dans son circuit de "
                       "traitement, et chaque personne concernée est prévenue. Tutoriel AITE Courrier, l'application de "
                       "gestion du courrier d'AITE Consulting pour Odoo 18.",
                       ['AITE Courrier', 'courrier entrant', 'circuit de traitement', 'référence courrier']),
}
