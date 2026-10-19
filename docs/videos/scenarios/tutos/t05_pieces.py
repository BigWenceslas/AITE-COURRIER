# -*- coding: utf-8 -*-
"""Tutoriel 05 — Les pièces du courrier et leurs versions.

Sources : aite_courrier_ged/views (espace documentaire, « Prévisualiser »,
« Finaliser », onglet « Versions », ruban « Verrouillé », confidentialité
héritée), aite_courrier_ocr (colonne d'indexation, recherche plein texte) ;
aite_courrier_ged/models/aite_courrier_document.py (dossier par défaut du
type de courrier, ``default_folder_id`` ; verrouillage si finalisé, archivé ou
courrier archivé ; liste grisée si verrouillé) ; recette SC03. Écran :
présentation, chapitre 3, avec le groupe « Devis » déplié dans le module (un
clic sur un groupe le déplie, il n'ouvre pas de fiche).
"""

import demo
from scenarios import presentation as base
from ecrans import c_num, e, puce
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, animer, classe, clic, curseur, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

ASSIST = demo.PERSONNES['assistante']
CH = base.CH3

# Le groupe « Devis » déplié : ses premières pièces (fictives), la plus récente
# en tête ; une pièce verrouillée est grisée (decoration-muted="is_locked").
GABARIT = '28px 1fr 110px 90px 70px 100px 150px 70px'
PIECES = [("Devis D-2026-3468 — mise en place d'un ERP", 'COUR-2026-0107', '2', 'Secret', 'Brouillon', True),
          ('Devis D-2026-5120 — rénovation des bureaux', 'COUR-2026-0112', '1', 'Interne', 'Finalisé', True),
          ("Devis D-2026-7840 — mise en place d'un ERP", 'COUR-2026-0079', '1', 'Interne', 'Brouillon', True)]


def _ligne(i, nom, courrier, nb, conf, etat, gris):
    return ('<div class="ligne%s" id="t5-p%d" style="grid-template-columns:%s"><span class="cb"></span>'
            '<span class="ell" style="padding-left:14px">%s</span><span class="ell">%s</span><span class="ell">Devis</span>'
            '<span class="ell">pdf</span>%s<span class="ell">%s</span><span>%s</span></div>'
            % (' gris' if gris else '', i, GABARIT, e(nom), e(courrier), c_num(nb)[0], e(conf), puce(etat)))


ECRAN = CH['ecran']
_G0 = '<span class="ell"><b>▸</b> Devis (38)</span>'
assert _G0 in ECRAN
ECRAN = ECRAN.replace(_G0, '<span class="ell"><b id="t5-chev">▸</b> Devis (38)</span>', 1)
_FIN_G0 = ECRAN.index('<div class="ligne grp" id="c3-g1"')
ECRAN = (ECRAN[:_FIN_G0] + '<div id="t5-devis" style="height:0;overflow:hidden;opacity:0;visibility:hidden">%s</div>'
         % ''.join(_ligne(i, *p) for i, p in enumerate(PIECES)) + ECRAN[_FIN_G0:])

TUTO = {
    'slug': 'tuto-05-les-pieces-et-leurs-versions',
    'titre_page': 'AITE Courrier — Tutoriel 05 : les pièces et leurs versions',
    'titre': 'Les pièces et leurs versions',
    'serie': dict(COURRIER, numero=5),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Quelle est la *bonne* version de ce *devis ?*',
        'sous': 'Pièces jointes perdues dans les e-mails, fichiers « final_v3_def » : la bonne version introuvable.',
        'personnage': (ASSIST[0], 'Assistante', ASSIST[2]),
        'chaos': [('doc', 'devis_final_v3.pdf'), ('bulle', 'La dernière version ?'), ('doc', 'devis_final_DEF.pdf'),
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
    'ecran': ECRAN, 'vue_initiale': 'c3-liste',
    'etapes': [
        {'titre': "L'espace documentaire", 'texte': "Toutes les pièces des courriers, regroupées par dossier.",
         'voix': "L'espace documentaire réunit toutes les pièces jointes aux courriers, regroupées par dossier : les devis, "
                 "les factures, la direction. Chaque type de courrier peut avoir son dossier par défaut. Estelle déplie "
                 "les devis, et ouvre le plus récent.",
         'gestes': [anneau('#c3-g0', d=2.2), bulle('#c3-g0', 'Les pièces, par dossier', cote='droite', fx=0.35, d=2.2, avec=True),
                    anneau('#c3-g1', d=1.0), survol('#c3-g0'), clic('#c3-g0', fx=0.2), texte('#t5-chev', '▾', avec=True),
                    animer('#t5-devis', {'height': 0, 'autoAlpha': 0}, {'height': 93, 'autoAlpha': 1}, d=0.4, avec=True),
                    survol('#t5-p0', decale=0.3), classe('#c3-g0', retirer=['survol'], avec=True), clic('#t5-p0', fx=0.3), aller('c3-fiche')]},
        {'titre': 'Une confidentialité héritée', 'texte': "La pièce suit la confidentialité de son courrier : ici, Secret.",
         'voix': "La pièce hérite de la confidentialité de son courrier : ici, Secret. Elle n'est donc visible que des "
                 "personnes autorisées à voir ce courrier, partout dans l'application.",
         'gestes': [zoom('#c3-conf', s=1.7, fx=0.55, d=0.9), anneau('#c3-conf', d=1.6),
                    bulle('#c3-conf', 'Héritée du courrier', cote='dessous', d=2.4), dezoom(d=0.7)]},
        {'titre': 'Des versions empilées', 'texte': "La dernière en tête ; les précédentes restent consultables. Verrouillée, la pièce n'est plus modifiable.",
         'voix': "Ses versions s'empilent, la dernière en tête, chacune avec son fichier, sa taille et son auteur. Rien "
                 "n'est écrasé. La colonne Indexation suit l'extraction du texte, pour la recherche plein texte. "
                 "Et une pièce verrouillée ne se modifie plus.",
         'gestes': [zoom('#c3-versions', s=1.4, fx=0.68, d=0.9), anneau('#c3-versions', d=1.8),
                    bulle('#c3-v2', 'La dernière version en tête', cote='droite', fx=0.36, d=2.4), dezoom(d=0.7),
                    anneau('#c3-versions .tt span:last-child', d=1.8),
                    anneau('#c3-ruban', d=1.4), bulle('#c3-ruban', 'Verrouillée', cote='gauche', fx=0.15, d=2.0, avec=True)]},
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
