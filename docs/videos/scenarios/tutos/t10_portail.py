# -*- coding: utf-8 -*-
"""Tutoriel 10 — Le portail des tiers.

Sources : aite_courrier_portal/views/portal_templates.xml (« Mes courriers »,
« Nouvelle demande », « Objet », « Nature de la demande », « Votre message »,
« Pièces jointes », « Envoyer la demande », « Avancement », « Cachet de
traitement », « Pièces du dossier », « Demande reçue », alerte « Votre
demande a été reçue et sera prochainement prise en charge par nos équipes. »
quand le courrier n'a pas encore de circuit) ; controllers/portal.py
(PORTAL_STATE_LABELS : Reçue, En traitement, Traitée ; dépôt = courrier créé
en brouillon, d'un type « entrant ») ; aite_courrier_core/models/
aite_courrier.py (visa_lines : une ligne par étape franchie, fonction et date,
jamais le nom) et aite_courrier_step_history.py (actor_function : rôle tenu
par l'intervenant parmi ceux de l'étape) ; circuit « Courrier entrant
standard » (aite_courrier_workflow/data/workflow_circuits.xml) ; carte Odoo
« Connexion & Sécurité » (portal, i18n fr) ; recette SC15. Écran :
présentation, chapitre 8, complété ici (cachet des cinq étapes, alerte de la
demande reçue).
"""

import demo
from scenarios import presentation as base
from scenarios.tutos import COURRIER, cta, etape, youtube
from moteur import anneau, pause, texte
from tutoriel import bulle, dezoom, zoom

CH = base.CH8
URL = 'courrier.aite-demo.test/my%s'


def _ecran():
    """L'écran du chapitre 8, rendu fidèle : libellé Odoo de la carte de
    sécurité, cachet complet (une ligne par étape franchie du circuit
    standard), alerte de la demande reçue, encore sans circuit."""
    h = CH['ecran']
    for avant, apres in [
        ('<b>Connexion et sécurité</b>', '<b>Connexion &amp; Sécurité</b>'),
        ('<div class="l"><b>Archivage</b><span>Archiviste</span>',
         '<div class="l"><b>Qualification</b><span>Agent courrier</span><span>06/10/2026</span></div>'
         '<div class="l"><b>Affectation</b><span>Assistant(e)</span><span>06/10/2026</span></div>'
         '<div class="l"><b>Traitement</b><span>Manager</span><span>08/10/2026</span></div>'
         '<div class="l"><b>Archivage</b><span>Archiviste</span>'),
        ('<b>Nature :</b> Courrier entrant</div></div>',
         '<b>Nature :</b> Courrier entrant<div class="t10-info">Votre demande a été reçue et sera prochainement prise '
         'en charge par nos équipes.</div></div></div>'),
    ]:
        assert h.count(avant) == 1, avant
        h = h.replace(avant, apres, 1)
    return h


CSS = """
#c8-cachet { width: 268px; }
#c8-cachet div.l { grid-template-columns: 82px 1fr auto; }
#app-8 .t10-info { margin-top: 12px; padding: 10px 14px; border: 1px solid #D3D6D8; border-radius: 4px; background: #E2E3E5;
  color: #41464B; font-size: 12px; }
"""

TUTO = {
    'slug': 'tuto-10-le-portail-des-tiers',
    'titre_page': 'AITE Courrier — Tutoriel 10 : le portail des tiers',
    'titre': 'Le portail des tiers',
    'serie': dict(COURRIER, numero=10),
    'adresse': URL % '',
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
    'ecran': _ecran(), 'vue_initiale': 'c8-compte', 'css': CSS,
    'etapes': [
        etape(CH, 0, 'Son espace, ses courriers', "Mes courriers : toutes ses demandes, avec un statut écrit pour lui.",
              "Depuis son espace personnel, le tiers ouvre Mes courriers. Il y retrouve toutes ses demandes, avec un statut "
              "rédigé pour lui : reçue, en traitement, traitée.",
              inserer={3: [texte('#pr-url', URL % '/courriers', avec=True)]},
              apres=[bulle('#c8-l1', 'Un statut clair', cote='dessous', fx=0.75, d=2.2)]),
        etape(CH, 1, 'Déposer une demande', "Objet, nature, message et pièces jointes, puis Envoyer la demande.",
              "Il dépose une nouvelle demande : l'objet, la nature, son message, et ses pièces jointes, plusieurs à la "
              "fois. À l'envoi, la demande arrive directement dans le courrier entrant de l'organisation. Un message "
              "lui confirme la réception ; sa référence lui sera communiquée dès la prise en charge.",
              inserer={2: [texte('#pr-url', URL % '/courriers/new', avec=True), zoom('#c8-objet', s=1.35, fx=0.62, fy=0.45, d=0.8)],
                       10: [dezoom(d=0.6)], 12: [texte('#pr-url', URL % '/courriers/142?submitted=1', avec=True)]},
              retirer=(12,),  # l'anneau sur le bandeau : la bulle le désigne déjà
              apres=[bulle('#c8-ok', 'Réception confirmée', cote='dessous', d=2.2), pause(1.2)]),
        etape(CH, 2, "Suivre, jusqu'au cachet", "L'avancement étape par étape, puis le cachet de traitement.",
              "Il suit ensuite l'avancement, étape par étape. Une fois sa demande traitée, il voit le cachet de traitement, "
              "avec la fonction de chaque intervenant et la date de son visa, et télécharge les pièces du dossier.",
              inserer={1: [texte('#pr-url', URL % '/courriers/9', avec=True)]},
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
