# -*- coding: utf-8 -*-
"""Tutoriel 14 — Travailler sur un document : réservation, Office, versions, corbeille.

Sources :
- addons/aite_ecm_document/views/aite_ecm_document_views.xml : en-tête
  (« Réserver » en Brouillon, « Libérer », « Corbeille » et sa confirmation
  « Mettre ce document à la corbeille ? Il pourra être restauré avant purge
  automatique. », « Restaurer »), bandeau « Réservé par … jusqu'au … »,
  ruban « Corbeille », bouton statistique « Doublons », onglet « Relations »
  (« Relation », « Document cible », « Note » ; « Documents qui pointent vers
  celui-ci ») ;
- models/aite_ecm_document.py : réservation de aite_ecm.checkout_hours
  heures (48 par défaut), expirée d'elle-même ; écriture refusée à un autre
  que le titulaire ; libération par le titulaire ou un manager ; corbeille
  (audit « Mise à la corbeille »), restauration, purge quotidienne après
  aite_ecm.trash_retention_days jours (30 par défaut) ; doublons = autres
  documents actifs dont une version a la même empreinte SHA-256 ;
- models/res_config_settings.py : « Durée d'une réservation (h) » (48),
  « Rétention de la corbeille (jours) » (30) ; data/ir_cron_data.xml
  (« AITE ECM : purge de la corbeille », chaque jour) ;
- data/aite_ecm_data.xml : types de relations « est une annexe de »,
  « remplace » (inverse « est remplacé par »), « fait référence à »,
  « est une traduction de » ;
- addons/aite_ecm_webdav : « Ouvrir dans Office », « Adresse WebDAV » ;
  enregistrement depuis Office = nouvelle version, commentaire « Enregistré
  depuis le lecteur réseau », audit source WebDAV ; un verrou Office réserve
  le document ; refus si réservé par un autre ou finalisé.
Écran : scenarios/chapitres_ecm.py (CH_TRAVAIL), complété ici (commentaire de
version réel, bouton « Doublons », onglet « Relations »).
"""

import demo
from ecrans import ICONES, e, table
from scenarios import chapitres_ecm as ecm
from scenarios.tutos import ADRESSE, ECM, cta, etape, youtube
from moteur import anneau, animer, cacher, classe, clic, defiler, montrer, pause
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ASSIST, MANAGER = P['assistante'], P['manager']
CH = ecm.CH_TRAVAIL

_ecran = CH['ecran']
# le commentaire réel d'une version enregistrée depuis Office (aite_ecm_webdav)
_ecran = _ecran.replace('Enregistré depuis Word', 'Enregistré depuis le lecteur réseau', 1)
# le bouton « Doublons » : un autre document contient le même fichier
_ecran = _ecran.replace('<span class="stats"></span>',
                        '<span class="stats"><span class="stat" id="t14-doub"><span class="ic">%s</span>'
                        '<span><b>Doublons</b><i>1</i></span></span></span>' % ICONES['document'], 1)
# onglets adressables, et l'onglet « Relations »
_ecran = _ecran.replace('<span class="og actif">Versions</span><span class="og">Relations</span>',
                        '<span class="og actif" id="t14-og-v">Versions</span><span class="og" id="t14-og-r">Relations</span>', 1)
_rel = ('<div class="t14-rel masque" id="t14-rel">%s<div class="t14-sep">Documents qui pointent vers celui-ci</div>%s</div>' % (
    table([('Relation', '150px'), ('Document cible', '1fr'), ('Note', '1fr')],
          [{'id': 't14-l0', 'cellules': ['remplace', 'Contrat de maintenance — climatisation 2025', 'Contrat échu au 31/12/2025']},
           {'id': 't14-l1', 'cellules': ['fait référence à', 'Bail commercial — agence', '']}], identifiant='t14-liens', ajouter=False),
    table([('Document source', '1fr'), ('Relation', '150px'), ('Note', '1fr')],
          [{'id': 't14-l2', 'cellules': ['Avenant n° 2 — climatisation', 'a pour annexe', '']}], identifiant='t14-inv', ajouter=False)))
_ecran = _ecran.replace('<div class="o-table" id="c11-versions">', _rel + '<div class="o-table" id="c11-versions">', 1)
assert 't14-rel' in _ecran and 't14-doub' in _ecran and 't14-og-r' in _ecran and 'lecteur réseau' in _ecran

CSS = """
#app-11 .t14-rel { position: absolute; left: 16px; right: 16px; background: #fff; z-index: 2; }
#app-11 .t14-sep { margin: 12px 0 4px; padding-bottom: 4px; border-bottom: 1px solid #DEE2E6; font-size: 11.5px; font-weight: 700; }
#app-11 .o-cp .stats { margin-left: 160px; }
#c11-v3 { height: 0; overflow: hidden; }
#c11-doc .o-feuille { padding-bottom: 150px; }
#c11-doc .o-bande { position: relative; z-index: 4; background: #F8F9FA; }
"""

TUTO = {
    'slug': 'tuto-14-travailler-sur-un-document',
    'titre_page': 'AITE ECM — Tutoriel 14 : travailler sur un document',
    'titre': 'Travailler sur un document',
    'serie': dict(ECM, numero=14),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Qui a *écrasé* ma *version ?*',
        'sous': 'Deux personnes, un même contrat.',
        'personnage': (ASSIST[0], 'Assistante', ASSIST[2]),
        'chaos': [('doc', 'contrat_v2_modifié.docx'), ('alerte', 'Modifications perdues'), ('bulle', 'Tu travaillais dessus ?'),
                  ('note', 'Qui l\'a ouvert ?'), ('dossier', 'Corbeille vidée'), ('doc', 'contrat_v2_final.docx'),
                  ('bulle', 'Je l\'ai supprimé…'), ('alerte', 'Version écrasée')],
        'voix': "Deux personnes modifient le même contrat, chacune de son côté. À la fin, une version écrase l'autre, et un "
                "fichier supprimé ne revient plus.",
    },
    'revelation': {'voix': "Avec Aïte E C M, on réserve, on modifie dans Word, et rien ne se perd."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Modifier *sans* rien perdre',
        'pastilles': ['Réservation de 48 h', 'Word, version après version', 'Corbeille restaurable'],
        'voix': "Une réservation qui protège le document, Word branché sur la gestion documentaire, et une corbeille qui "
                "pardonne.",
    },
    'ecran': _ecran, 'vue_initiale': CH['vue_initiale'],
    'etapes': [
        etape(CH, 0, 'Réserver avant de modifier',
              "48 h par défaut, réglables ; pendant ce temps, personne d'autre ne peut modifier le document.",
              "Avant de modifier le contrat, Estelle le réserve. La réservation dure quarante-huit heures par défaut, une durée "
              "réglable dans les paramètres. Pendant ce temps, personne d'autre ne peut le modifier ; seule Estelle, ou un "
              "manager, peut le libérer.",
              inserer={5: [zoom('#c11-resa b', s=1.45, fx=0.3, fy=0.3, d=0.8)]},
              retirer=(6,),
              apres=[bulle('#c11-resa', 'Réservé pour 48 h', cote='dessous', fx=0.45, d=2.2), dezoom(d=0.6),
                     anneau('#c11-lib2', d=1.2)]),
        etape(CH, 1, 'Ouvrir dans Office',
              "Word s'ouvre sur le document ; chaque enregistrement crée une nouvelle version.",
              "Ouvrir dans Office lance Word sur le document, par le lecteur réseau WebDAV, dont l'adresse se copie aussi. "
              "Estelle modifie, puis enregistre : chaque enregistrement dans Word crée une nouvelle version dans le fonds, "
              "tracée au journal d'audit.",
              inserer={1: [anneau('#c11-off2', d=1.0)],
                       3: [animer('#c11-v3', {'height': 0, 'autoAlpha': 0}, {'height': 28, 'autoAlpha': 1}, d=0.5)]},
              retirer=(3,),
              apres=[bulle('#c11-v3', 'Nouvelle version : v3', cote='dessous', fx=0.3, d=2.4)]),
        etape(CH, 2, 'Libérer, et la corbeille sans risque',
              "Le titulaire ou un manager libère ; un document supprimé se restaure avant la purge (30 jours par défaut).",
              "Son travail fini, Estelle libère le document. Un document supprimé part d'abord à la corbeille, après "
              "confirmation. Il se restaure d'un clic, tant que la purge automatique n'est pas passée : trente jours par "
              "défaut, eux aussi réglables.",
              inserer={7: [zoom('#c11-conf', s=1.3, d=0.6)], 8: [pause(0.6)], 10: [dezoom(d=0.5)]},
              apres=[bulle('#c11-rest4', 'Restaurable 30 jours', cote='dessous', d=2.0), clic('#c11-rest4'),
                     cacher('#c11-ruban', d=0.3), cacher('#c11-b-d', d=0.2, avec=True), montrer('#c11-b-c', y=0, avec=True)]),
        {'titre': 'Relations et doublons',
         'texte': "Relier les documents entre eux (remplace, fait référence à…) ; le bouton Doublons repère le même fichier.",
         'voix': "Enfin, l'onglet Relations relie les documents entre eux : ce contrat remplace celui de l'an dernier, et "
                 "l'avenant y renvoie. Le bouton Doublons, lui, signale un autre document qui contient exactement le même "
                 "fichier.",
         'gestes': [clic('#t14-og-r'), classe('#t14-og-v', retirer=['actif'], avec=True), classe('#t14-og-r', ajouter=['actif'], avec=True),
                    cacher('#c11-versions', d=0.2), montrer('#t14-rel', y=10), defiler('#c11-doc .o-feuille', -130, d=0.7),
                    zoom('#t14-rel', s=1.2, fx=0.5, fy=0.5, d=0.8),
                    bulle('#t14-l0', 'Il remplace le contrat 2025', cote='droite', fx=0.47, d=2.2),
                    bulle('#t14-l2', "L'avenant y renvoie", cote='dessous', fx=0.3, d=2.0), dezoom(d=0.6),
                    clic('#t14-doub', d=0.7), bulle('#t14-doub', 'Même fichier, ailleurs', cote='dessous', d=2.2)]},
    ],
    'benefices': {
        'titre': 'Modifier, *sans* rien perdre.',
        'voix': "Une réservation qui évite les conflits, Word branché sur le fonds documentaire, chaque enregistrement "
                "versionné, et une corbeille qui laisse le temps de se raviser.",
        'cartes': [('cadenas', '48 h', 'Une réservation', "Personne d'autre ne modifie ; le titulaire ou un manager libère."),
                   ('doc', 'v1 · v2 · v3', 'Word versionné', "Chaque enregistrement dans Word crée une nouvelle version."),
                   ('temps', '30 jours', 'Une corbeille qui pardonne', "Un document supprimé se restaure avant la purge automatique.")],
    },
    'cta': cta('ecm', 'Vos documents, *sans* *conflit.*', "Aïte E C M : vos documents, sans conflit."),
    'youtube': youtube('COMMENT RÉSERVER, MODIFIER DANS WORD ET VERSIONNER UN DOCUMENT AVEC AITE ECM (ODOO 18)',
                       "Réserver un document avant de le modifier, l'ouvrir dans Word par le lecteur réseau WebDAV, versionner "
                       "chaque enregistrement, libérer, et restaurer depuis la corbeille avant la purge. Relations entre "
                       "documents et doublons. Tutoriel AITE ECM pour Odoo 18.",
                       ['AITE ECM', 'réservation document', 'WebDAV', 'Word Odoo', 'versions', 'corbeille']),
    'css': CSS,
}
