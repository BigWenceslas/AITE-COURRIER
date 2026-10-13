# -*- coding: utf-8 -*-
"""Présentation d'AITE ECM : la gestion documentaire, la conservation et la preuve.

Reprend les chapitres ECM de la présentation complète (scenarios/presentation.py,
scénarios de recette SC04 à SC11, SC13, SC16, SC17) et ajoute « Travailler
sur un document » (scenarios/chapitres_ecm.py).
"""

from scenarios import presentation as base
from scenarios.chapitres_ecm import CH_TRAVAIL

CH_AUDIT = dict(base.CH9, titre='Traçabilité et contrôle', qui='Audit',
                sous="Chaque action sur le fonds laisse une trace : qui, quoi, quand, par quel canal.",
                roles=['Audit'], etapes=base.CH9['etapes'][:1],
                voix="la traçabilité. Chaque action sur le fonds documentaire laisse une trace.")

SCENARIO = {
    'slug': '00-ecm',
    'profil': 'ecm',
    'id': 'ecm',
    'marque': ('AITE', 'ECM'),
    'icone': 'aite_ecm.png',
    'titre_page': 'AITE ECM — présentation de la solution',
    'ouverture': {
        'sous': 'Documents · Conservation · Preuve · Odoo 18',
        'kicker': 'Présentation de la solution',
        'titre': 'Vos documents, *classés,* *prouvés,* *conservés.*',
        'mission': "Organiser tout le fonds documentaire, travailler à plusieurs sans rien perdre, prouver l'intégrité de chaque "
                   "version et conserver chaque document le temps qu'il faut.",
    },
    'cartes_intro': [
        {'kicker': 'En une minute', 'titre': 'Une plateforme documentaire complète',
         'sous': "Dans Odoo 18, AITE ECM partage les rôles, les circuits et le journal d'audit d'AITE Courrier.",
         'cartes': [('Organiser', 'Un fonds classé', "Documents typés avec leurs métadonnées, plan de classement, versions, étiquettes, recherche."),
                    ('Collaborer', 'Un travail partagé', "Réservation, ouverture dans Office, dossiers métier qui suivent leurs pièces, partages externes."),
                    ('Conserver et prouver', 'Une archive fiable', "Règles de conservation, gels juridiques, éliminations validées, sceaux chaînés, archives physiques.")],
         'voix_cle': 'ecm-intro-1',
         'voix': "Aïte E C M est la plateforme documentaire de la suite, dans Odoo dix-huit. Elle organise le fonds, permet de travailler "
                 "à plusieurs sans rien perdre, et conserve chaque document avec sa preuve."},
    ],
    'parcours': {
        'kicker': 'Le cycle de vie', 'titre': "De la création au sort final",
        'etapes': [('Brouillon', 'Création, versions, réservation', 'Utilité courante'),
                   ('Finalisé', 'Contenu arrêté', 'Utilité courante'),
                   ('Archivé', 'Classé, scellé', 'Archive intermédiaire'),
                   ('Échu', 'Durée de conservation atteinte', 'Sort final à appliquer'),
                   ('Sort final', 'Élimination validée ou conservation définitive', 'Bordereau')],
        'note': "Le document passe de <b>Brouillon</b> à <b>Finalisé</b> puis <b>Archivé</b> ; sa <b>règle de conservation</b> fixe "
                "ensuite la durée et le sort final, sous le contrôle d'un <b>gel juridique</b> s'il le faut.",
    },
    'roles': {
        'kicker': 'Les rôles', 'titre': 'Les mêmes rôles que le courrier',
        'sous': "Les droits suivent le rôle et le dossier de classement : chacun ne voit et ne modifie que ce qui le concerne.",
        'liste': [('Agent courrier', "Dépose les pièces reçues, consulte ses documents."), ('Assistant(e)', "Crée, classe et versionne les documents."),
                  ('Manager', "Valide éliminations et partages, pilote son service."), ('Comptabilité', "Tient les dossiers et pièces comptables."),
                  ('Signataire', "Vise et signe les documents qui le demandent."), ('Archiviste', "Classe, conserve, archive, élimine."),
                  ('Audit', "Consulte la preuve et le journal d'audit."), ('Administrateur', "Paramètre types, plan de classement et règles.")],
    },
    'sommaire_titre': 'Six chapitres, tout le fonds documentaire',
    'chapitres': [base.CH4, CH_TRAVAIL, base.CH7, base.CH5, base.CH6, CH_AUDIT],
    'cartes_fin': [
        base.SCENARIO['cartes_fin'][0],
        {'kicker': 'Et aussi', 'titre': 'Les modules complémentaires',
         'cartes': [('Le pont avec le courrier', 'Courrier et documents', "Les pièces des courriers deviennent des documents ECM, rangées dans le plan de classement."),
                    ('Nextcloud et édition en ligne', 'Le travail partagé', "Miroir Nextcloud, édition dans le navigateur avec Collabora ou OnlyOffice, ouverture dans Google Docs."),
                    ('Archivage électronique', 'La preuve à long terme', "Horodatage, attestation d'intégrité, copie de préservation PDF/A, export SEDA vers un service d'archives.")],
         'voix_cle': 'ecm-fin-2',
         'voix': "Des modules complémentaires vont plus loin : le pont avec le courrier, qui range ses pièces dans le fonds ; le miroir "
                 "Nextcloud et l'édition en ligne ; et l'archivage électronique, avec la copie de préservation P D F A et l'export SEDA."},
    ],
    'recette': {
        'kicker': 'Éprouvée', 'titre': 'Onze scénarios de recette ECM, tous conformes',
        'scenarios': [('SC04', 'Explorateur ECM'), ('SC05', 'Créer un document'), ('SC06', 'Conservation et gel'),
                      ('SC07', "Bordereau d'élimination"), ('SC08', 'Journal de preuve'), ('SC09', 'Archives physiques'),
                      ('SC10', 'Partages externes'), ('SC11', 'Dossiers métier'), ('SC13', "Journal d'audit"),
                      ('SC16', "Vérifier l'intégrité"), ('SC17', 'Nouvelle version')],
        'chiffres': [('11 / 11', 'scénarios ECM conformes'), ('18 / 18', "contrôles d'interfaces"),
                     ('349', 'tests automatisés, 0 échec')],
    },
    'retenir': {
        'regle': 'Chaque document est <b>classé</b>, chaque version <b>conservée</b>, chaque preuve <b>vérifiable</b>.',
        'cartes': [('Organiser', "Types, métadonnées, plan de classement, versions, réservation."),
                   ('Prouver', "Sceaux chaînés, horodatage, intégrité vérifiable, journal d'audit."),
                   ('Conserver', "Règles de conservation, gels juridiques, éliminations validées, archives physiques.")],
    },
    'fin': {'sous': 'Documents · Conservation · Preuve · Odoo 18', 'pied': 'AITE Consulting · www.aite-consulting.com'},
    'voix': {
        'ouverture': "Aïte E C M : vos documents classés, prouvés et conservés. Toute la gestion documentaire de votre organisation, "
                     "dans Odoo.",
        'parcours': "Chaque document suit un cycle de vie. Il naît brouillon, se versionne, puis il est finalisé et archivé. "
                    "Sa règle de conservation fixe ensuite combien de temps le garder, et ce qu'il devient à l'échéance : "
                    "élimination validée, ou conservation définitive.",
        'roles': "Aïte E C M partage les rôles du courrier, de l'agent à l'administrateur. Les droits suivent le rôle et le dossier "
                 "de classement : chacun ne voit et ne modifie que ce qui le concerne.",
        'sommaire': "Parcourons le fonds documentaire en six chapitres, sur les écrans de l'application.",
        'recette': "Tout ce que vous venez de voir a été éprouvé : onze scénarios de recette documentaire joués dans un vrai navigateur, "
                   "dix-huit contrôles d'interfaces, et trois cent quarante-neuf tests automatisés, sans un seul échec.",
        'retenir': "À retenir : avec Aïte E C M, chaque document est classé, chaque version conservée, et chaque preuve vérifiable.",
        'fin': "Aïte E C M, par Aïte Consulting. Merci de votre attention.",
    },
    'vignette': {'chapitre': 2, 'etape': 1, 'apres': 3.5},
}
