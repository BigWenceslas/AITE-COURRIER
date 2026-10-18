# -*- coding: utf-8 -*-
"""Tutoriel 12 — Confidentialité et journal d'audit.

Sources : aite_courrier_base (journal d'audit en ajout seul, colonnes
« Date/heure », « Utilisateur », « Action », « Type », « Objet », « Source »,
« Détails » ; sources interface, système, API, WebDAV), niveaux de
confidentialité Public / Interne / Confidentiel / Secret et règles
d'enregistrement (fiche avant-vente) ; recette SC13 et SC14. Écran :
présentation, chapitre 9.
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, etape, youtube
from moteur import anneau
from tutoriel import bulle, dezoom, zoom

AUDIT = demo.PERSONNES['audit']
CH = base.CH9

TUTO = {
    'slug': 'tuto-12-confidentialite-et-journal-d-audit',
    'titre_page': "AITE Courrier — Tutoriel 12 : confidentialité et journal d'audit",
    'titre': "Confidentialité et audit",
    'serie': dict(COURRIER, numero=12),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Qui a *vu* ce courrier, et qui l\'a *modifié ?*',
        'sous': 'Un courrier confidentiel qui circule, une action contestée : sans trace, pas de preuve.',
        'personnage': (AUDIT[0], 'Audit', AUDIT[2]),
        'chaos': [('alerte', 'Fuite d\'information'), ('bulle', 'Qui a ouvert ce dossier ?'), ('lettre', 'Courrier confidentiel'),
                  ('note', 'Modifié par : ?'), ('doc', 'Photocopie'), ('bulle', 'Ce n\'est pas moi'),
                  ('dossier', 'Dossier RH'), ('alerte', 'Contrôle interne')],
        'voix': "Un courrier confidentiel a circulé. Qui l'a vu ? Qui l'a modifié ? Sans trace fiable, le contrôle "
                "interne n'a aucune réponse.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, chaque courrier est protégé, et chaque action laisse une trace."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Protéger, et *tout* *tracer*',
        'pastilles': ['4 niveaux de confidentialité', "Journal d'audit", 'Ajout seul'],
        'voix': "Quatre niveaux de confidentialité protègent les courriers, et le journal d'audit enregistre chaque "
                "action. Il ne fonctionne qu'en ajout : personne ne peut le modifier, ni l'effacer.",
    },
    'ecran': CH['ecran'], 'vue_initiale': 'c9-audit',
    'etapes': [
        etape(CH, 0, "Le journal d'audit", "Chaque action : l'auteur, l'objet, le type et la source.",
              "Sandrine, de l'audit, ouvre le journal. Chaque action y est tracée : création, transition, dépôt de "
              "version, accès par un lien de partage. On y lit l'auteur, l'objet et le résultat.",
              avant=[zoom('#c9-l1', s=1.4, fx=0.5, fy=0.3, d=0.8)], apres=[dezoom(d=0.6)]),
        {'titre': 'La source, et les refus', 'texte': "Interface, système, API ou lecteur réseau ; une tentative refusée est tracée.",
         'voix': "La colonne Source dit par où l'action est passée : l'interface, le système, l'A P I ou le lecteur "
                 "réseau. Et les refus y figurent aussi : une tentative non autorisée est enregistrée, en rouge.",
         'gestes': [zoom('#c9-l8', s=1.5, fx=0.55, d=0.8), anneau('#c9-l8', d=1.2), anneau('#c9-l9', d=1.2),
                    bulle('#c9-l9', 'Source : API, WebDAV…', cote='dessous', fx=0.62, d=2.2), dezoom(d=0.6),
                    zoom('#c9-l4', s=1.5, fx=0.55, d=0.8), anneau('#c9-l4', d=1.4),
                    bulle('#c9-l4', 'Tentative refusée', cote='dessous', fx=0.4, d=2.2), dezoom(d=0.7)]},
        etape(CH, 1, 'Le cloisonnement', "Un courrier secret n'apparaît qu'aux personnes autorisées.",
              "Le cloisonnement, maintenant. Un agent courrier cherche un courrier confidentiel destiné à un autre "
              "service. Le résultat est vide : un courrier confidentiel ou secret n'apparaît qu'à son responsable, à "
              "son service et aux managers, dans les listes comme dans les recherches."),
    ],
    'benefices': {
        'titre': 'Confidentiel, *et* *prouvé.*',
        'voix': "Les courriers sensibles restent entre les bonnes mains, chaque action est prouvée, et le journal ne "
                "peut pas être retouché.",
        'cartes': [('cadenas', '4 niveaux', 'Confidentialité', "Public, Interne, Confidentiel, Secret."),
                   ('trace', 'Tout', 'Chaque action tracée', "Auteur, objet, source, résultat, refus compris."),
                   ('bouclier', 'Ajout seul', 'Journal inaltérable', "Ni modification, ni suppression, administrateur compris.")],
    },
    'cta': cta('courrier', 'Protégé, *et* *tracé.*', "Aïte Courrier : protégé, et tracé."),
    'youtube': youtube("COMMENT PROTÉGER ET TRACER VOS COURRIERS : CONFIDENTIALITÉ ET JOURNAL D'AUDIT AITE COURRIER (ODOO 18)",
                       "Quatre niveaux de confidentialité, un journal d'audit en ajout seul qui trace chaque action et chaque "
                       "refus : la sécurité d'AITE Courrier. Tutoriel pour Odoo 18.",
                       ['AITE Courrier', "journal d'audit", 'confidentialité', 'sécurité Odoo']),
}
