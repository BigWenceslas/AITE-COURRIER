# -*- coding: utf-8 -*-
"""Tutoriel 12 — Confidentialité et journal d'audit.

Sources : aite_courrier_base (journal d'audit en ajout seul, colonnes
« Date/heure », « Utilisateur », « Action », « Type », « Objet », « Source »,
« Détails » ; sources interface, système, API, WebDAV), niveaux de
confidentialité Public / Interne / Confidentiel / Secret et règles
d'enregistrement (fiche avant-vente) ; recette SC13 et SC14. Écran :
présentation, chapitre 9, corrigé ici d'après le code et la base :
- l'action du portail s'intitule « Demande déposée via le portail », détail
  « Tiers : … — Objet : … » (aite_courrier_portal/controllers/portal.py) ;
- l'accès par lien de partage est fait par l'utilisateur public d'Odoo,
  « Public user » (relevé dans la base, aite_ecm_share/models/aite_ecm_share.py) ;
- « Ajout de version » : « vN — fichier (N Ko) — sha256 … »
  (aite_ecm_document/models/aite_ecm_document.py) ;
- « Archiver » (Traitement → Archivage) n'est permis qu'au rôle de l'étape
  Traitement, Manager (workflow_circuits.xml, can_user_act) : l'archiviste ne
  peut pas l'avoir fait ;
- source « API » ajoutée par aite_ecm_api (selection_add).
Confidentialité : règle « Courrier : confidentialité (opérationnels) »
(aite_courrier_core/security/aite_courrier_security.xml) : Confidentiel et
Secret visibles du responsable, du créateur, des membres du service
destinataire ; accès complet des managers (et de l'administrateur). Menu
« Audit › Journal d'audit » réservé au rôle Audit (l'administrateur
l'implique). Le journal ne trace pas les simples consultations d'un courrier
(aucune entrée « lecture ») : l'accroche demande donc qui *peut* le voir.
Journal : write/unlink refusés hors superutilisateur technique
(aite_courrier_base/models/aite_courrier_audit_log.py).
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, etape, youtube
from moteur import anneau, saisir
from tutoriel import bulle, dezoom, zoom

AUDIT = demo.PERSONNES['audit']
CH = base.CH9
MANAGER = demo.PERSONNES['manager']
ARCHI = demo.PERSONNES['archiviste']


def _ecran():
    import re
    h = CH['ecran']

    def ligne(k, avant, apres):
        nonlocal h
        m = re.search(r'<div class="ligne" id="c9-l%d".*?</div>' % k, h)
        assert m and m.group(0).count(avant) == 1, (k, avant)
        h = h[:m.start()] + m.group(0).replace(avant, apres) + h[m.end():]

    for k in (3, 10):
        ligne(k, '>Demande déposée<', '>Demande déposée via le portail<')
    ligne(10, 'Tiers : %s<' % demo.TIERS, "Tiers : %s — Objet : Réclamation sur la facture d'août<" % demo.TIERS)
    ligne(7, '>Utilisateur public<', '>Public user<')
    ligne(8, 'recette_v2.pdf — sha256', 'recette_v2.pdf (24 Ko) — sha256')
    ligne(9, 'Attestation ANR.pdf — sha256', 'Attestation ANR.pdf (31 Ko) — sha256')
    for k in (6, 15):
        ligne(k, '>%s<' % ARCHI[0], '>%s<' % MANAGER[0])
    return h

TUTO = {
    'slug': 'tuto-12-confidentialite-et-journal-d-audit',
    'titre_page': "AITE Courrier — Tutoriel 12 : confidentialité et journal d'audit",
    'titre': "Confidentialité et audit",
    'serie': dict(COURRIER, numero=12),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Qui *peut* voir ce courrier, et qui l\'a *modifié ?*',
        'sous': 'Un courrier confidentiel qui circule, une action contestée\u00a0: sans trace, pas de preuve.',
        'personnage': (AUDIT[0], 'Audit', AUDIT[2]),
        'chaos': [('alerte', 'Fuite d\'information'), ('bulle', 'Qui y a accès ?'), ('lettre', 'Courrier confidentiel'),
                  ('doc', 'Photocopie'), ('note', 'Modifié par : ?'), ('bulle', 'Ce n\'est pas moi'),
                  ('dossier', 'Dossier RH'), ('alerte', 'Contrôle interne')],
        'voix': "Un courrier confidentiel a circulé. Qui pouvait le voir ? Qui l'a modifié ? Sans trace fiable, le contrôle "
                "interne n'a aucune réponse.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, chaque courrier est protégé, et chaque action laisse une trace."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Protéger, et *tout* *tracer*',
        'pastilles': ['4 niveaux de confidentialité', "Journal d'audit", 'Ajout seul'],
        'voix': "Quatre niveaux de confidentialité protègent les courriers, et le journal d'audit enregistre chaque "
                "action. Il ne fonctionne qu'en ajout : personne ne peut le modifier, ni l'effacer.",
    },
    'ecran': _ecran(), 'vue_initiale': 'c9-audit',
    'etapes': [
        # Les anneaux visent des cellules, pas des lignes entières : zoomée,
        # une ligne du journal déborde de la fenêtre, et son anneau aussi.
        {'titre': "Le journal d'audit", 'texte': "Chaque action : l'auteur, l'objet, le type et la source.",
         'voix': "Sandrine, de l'audit, ouvre le journal. Chaque action y est tracée : création, transition, dépôt de "
                 "version, accès par un lien de partage. On y lit l'auteur, l'objet et le résultat.",
         'gestes': [zoom('#c9-l1', s=1.4, fx=0.5, fy=0.3, d=0.8),
                    anneau('#c9-l0 > span:nth-child(4)', d=0.9), anneau('#c9-l1 > span:nth-child(4)', d=0.9),
                    anneau('#c9-l8 > span:nth-child(4)', d=0.9), anneau('#c9-l7 > span:nth-child(4)', d=0.9),
                    anneau('#c9-l1 > span:nth-child(3)', d=0.9), anneau('#c9-l1 > span:nth-child(6)', d=0.9),
                    anneau('#c9-l1 > span:nth-child(5)', d=0.9), dezoom(d=0.6)]},
        {'titre': 'La source, et les refus', 'texte': "Interface, système, API ou lecteur réseau ; une tentative refusée est tracée.",
         'voix': "La colonne Source dit par où l'action est passée : l'interface, le système, l'A P I ou le lecteur "
                 "réseau. Et les refus y figurent aussi : une tentative non autorisée est enregistrée, en rouge.",
         'gestes': [zoom('#c9-l8', s=1.5, fx=0.55, d=0.8), anneau('#c9-l7 > span:nth-child(7)', d=0.8),
                    anneau('#c9-l8 > span:nth-child(7)', d=0.8), anneau('#c9-l9 > span:nth-child(7)', d=0.8),
                    bulle('#c9-l9 > span:nth-child(7)', 'Source : API, WebDAV…', cote='dessous', d=2.2), dezoom(d=0.6),
                    zoom('#c9-l4', s=1.5, fx=0.55, d=0.8), anneau('#c9-l4 > span:nth-child(4)', d=0.8),
                    anneau('#c9-l4 > span:nth-child(5)', d=0.8),
                    bulle('#c9-l4 > span:nth-child(5)', 'Tentative refusée', cote='dessous', d=2.2), dezoom(d=0.7)]},
        etape(CH, 1, 'Le cloisonnement', "Un courrier secret n'apparaît qu'aux personnes autorisées.",
              "Le cloisonnement, maintenant. Un agent courrier cherche, par sa référence, un courrier confidentiel destiné "
              "à un autre service. Le résultat est vide : un courrier confidentiel ou secret n'apparaît qu'à son "
              "responsable, à son créateur, au service destinataire et aux managers, dans les listes comme dans les "
              "recherches.",
              retirer=(2,), inserer={2: [saisir('c9-rech-q', 'COUR-2026-0042', d=0.8)]}),
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
