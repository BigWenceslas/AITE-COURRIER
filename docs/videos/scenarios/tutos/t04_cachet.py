# -*- coding: utf-8 -*-
"""Tutoriel 04 — Le cachet de traitement.

Sources : docs/produits/AITE_Courrier_cachet_de_traitement.md (ruban
« Traité », onglet « Cachet » : étape, intervenant, fonction, date ; sur le
portail, la fonction seule), aite_courrier_core/views/aite_courrier_views.xml
(ruban, onglet Cachet, filtre « Traités »), aite_courrier_validation (bandeau
« Circuit terminé — courrier archivé. »), portail (« Cachet de traitement ») ;
recette SC18 et SC15 ; aite_courrier_core/models/aite_courrier.py
(_enter_step, _compute_processed, _compute_visas) et
aite_courrier_step_history.py (actor_function). Écrans : présentation,
chapitres 2 et 8, avec le cachet recomposé ici (cinq visas, colonne
« Action », date avec les secondes comme dans Odoo), et la liste des
courriers avec le filtre « Traités » (filter_processed, domaine
is_processed ; liste grisée des archivés, decoration-muted), composée ici.
"""

import demo
from ecrans import bandeau, e, liste, panneau_lateral, panneau_liste, table, vue
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, cacher, classe, clic, montrer, pause, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ARCHI, AGENT, ASSIST, MANAGER = P['archiviste'], P['agent'], P['assistante'], P['manager']

# Le cachet du courrier clos, tel que le code le calcule : une ligne par étape
# franchie (visa_ids = step_history_ids), l'intervenant étant celui qui a fait
# entrer le courrier dans l'étape (_enter_step), la fonction le rôle de
# l'étape qu'il porte, à défaut les rôles de l'étape (actor_function), et
# « Action » la transition prise en quittant l'étape. Le circuit standard
# n'a pas de transition Réception → Archivage : les cinq étapes y passent.
VISAS = [('Réception', AGENT[0], 'Agent courrier', '05/10/2026 15:13:08', 'Qualifier'),
         ('Qualification', AGENT[0], 'Agent courrier', '06/10/2026 09:02:41', 'Affecter'),
         ('Affectation', ASSIST[0], 'Assistant(e)', '06/10/2026 11:40:17', 'Transmettre'),
         ('Traitement', MANAGER[0], 'Manager', '07/10/2026 10:05:33', 'Archiver'),
         ('Archivage', MANAGER[0], 'Archiviste', '11/10/2026 09:36:12', '')]


def _remplacer(html, avant, apres):
    assert html.count(avant) == 1, avant[:60]
    return html.replace(avant, apres, 1)


def _ecran_interne():
    # la vue de départ sera la liste des courriers composée plus bas
    html = _remplacer(base.CH2['ecran'], 'class="vue initiale avec-lateral" id="c2-liste"', 'class="vue avec-lateral" id="c2-liste"')
    debut = html.index('<div class="bandeau vert" id="c2-cachet-b">')
    fin = html.index('</div></div>', html.index('id="c2-v1"')) + len('</div></div>')
    cachet = (bandeau('✹ Courrier traité le 11/10/2026 09:36:12 — %d visa(s).' % len(VISAS), 'vert', 'c2-cachet-b')
              + table([('Étape', '96px'), ('Intervenant', '1fr'), ('Fonction', '96px'), ('Le', '132px'), ('Action', '84px')],
                      [{'id': 'c2-v%d' % i, 'cellules': list(l)} for i, l in enumerate(VISAS)],
                      identifiant='c2-cachet', ajouter=False))
    html = html[:debut] + cachet + html[fin:]
    # le fil du courrier clos : archivé le 11/10, pas « aujourd'hui » (13/10)
    clos = html.index('id="c2-clos"')
    sep = html.index('<div class="ch-sep">Aujourd\'hui</div>', clos)
    html = html[:sep] + '<div class="ch-sep">11 octobre 2026</div>' + html[sep + len('<div class="ch-sep">Aujourd\'hui</div>'):]
    # le dernier passage, Traitement → Archivage, fait par le manager
    return _remplacer(html, '<span class="av" style="background:%s">%s</span><div><div class="au">%s <i>09:36</i></div>'
                      '<div class="tx">Réception → ' % (ARCHI[2], ARCHI[1], ARCHI[0]),
                      '<span class="av" style="background:%s">%s</span><div><div class="au">%s <i>09:36</i></div>'
                      '<div class="tx">Traitement → ' % (MANAGER[2], MANAGER[1], MANAGER[0]))


def _portail():
    html = base.CH8['ecran'].replace('class="o-app portail" id="app-8"', 'class="o-app portail masque" id="app-8"', 1)
    lignes = ''.join('<div class="l"><b>%s</b><span>%s</span><span>%s</span></div>' % (e(n), e(f), le[:10])
                     for n, _, f, le, _ in VISAS)
    debut = html.index('<div class="l"><b>Réception</b>')
    fin = html.index('</div></div>', html.index('<div class="l"><b>Archivage</b>')) + len('</div>')
    return html[:debut] + lignes + html[fin:]


ENTONNOIR = '<svg viewBox="0 0 24 24" fill="#343A40"><path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/></svg>'
COUCHES = ('<svg viewBox="0 0 24 24" fill="#343A40"><path d="M12 3l10 5-10 5L2 8z"/>'
           '<path d="M4.6 11.7L12 15.4l7.4-3.7L22 13l-10 5L2 13z"/></svg>')
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'
# le menu Filtres / Regrouper par / Favoris (aite_courrier_core/views/aite_courrier_views.xml:153-178)
DD_FILTRES = ('<div class="masque" id="t4-ddf"%s><div class="col"><div class="h"><span class="t4-ico">%s</span> Filtres</div>'
              '<div class="f">Brouillons</div><div class="f" id="t4-f-traites">Traités</div><div class="f">En retard (SLA)</div>'
              '<div class="f">Mes courriers</div><div class="f">Reçus ce mois</div><div class="sep"></div>'
              '<div class="f">Entrants</div><div class="f">Sortants</div><div class="f">Internes</div><div class="sep"></div>'
              '<div class="f">Ajouter un filtre personnalisé</div></div>'
              '<div class="col"><div class="h"><span class="t4-ico">%s</span> Regrouper par</div><div class="f">Type</div>'
              '<div class="f">Statut</div><div class="f">Priorité</div><div class="f">Service</div><div class="sep"></div>'
              '<div class="f">Ajouter un groupe personnalisé ▾</div></div>'
              '<div class="col"><div class="h"><b class="etoile">★</b> Favoris</div>'
              '<div class="f">Enregistrer la recherche actuelle ▾</div></div></div>' % (ZONE, ENTONNOIR, COUCHES))
TRAITES = [l for l in base.LIGNES_COURRIERS if l[5] == 'Archivé']


def _listes():
    tous = vue('t4-tous', panneau_liste('Courriers', '1-80 / 151', nouveau=False)
               .replace('<span class="drop">▾</span>', '<span class="drop" id="t4-drop">▾</span>' + DD_FILTRES, 1)
               + base.lat_courriers(None)
               + liste(base.COL_COURRIERS, [base.ligne_courrier('t4-m%d' % i, *l) for i, l in enumerate(base.LIGNES_COURRIERS[:18])]))
    tous = tous.replace('class="vue"', 'class="vue initiale avec-lateral"', 1)
    lat = panneau_lateral([('▰ CATÉGORIE', [('Tous', '', True), ('Entrant', '4', False), ('Interne', '1', False),
                                           ('Sortant', '1', False)]), ('≡ STATUT', [('Archivé', '6', False)])])
    traites = vue('t4-traites', panneau_liste('Courriers', '1-6 / 6', facettes=[('◆', 'Traités')], nouveau=False)
                  .replace('<span class="k">◆</span>', '<span class="k t4-k">%s</span>' % ENTONNOIR, 1)
                  + lat + liste(base.COL_COURRIERS, [base.ligne_courrier('t4-r%d' % i, *l) for i, l in enumerate(TRAITES)]))
    return tous + traites.replace('class="vue"', 'class="vue avec-lateral"', 1)


ecran = _ecran_interne()
ecran = _remplacer(ecran, '<div class="o-contenu">', '<div class="o-contenu">' + _listes())
LIGNE_CLOS = 't4-r%d' % [l[0] for l in TRAITES].index(base.CLOS['reference'])
portail = _portail()

CSS = """
#app-2 .recherche { position: relative; }
#t4-ddf { position: absolute; right: -1px; top: 31px; z-index: 30; width: 560px; display: grid; grid-template-columns: 1.1fr 1fr 1fr;
  padding: 12px 0; background: #fff; border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 20px rgba(0,0,0,.16);
  color: #212529; font-size: 12px; }
#t4-ddf .col { padding: 0 12px; } #t4-ddf .col + .col { border-left: 1px solid #E9ECEF; }
#t4-ddf .h { display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 12.5px; margin: 0 0 6px 6px; }
#t4-ddf .t4-ico svg { width: 12px; height: 12px; display: block; }
#t4-ddf .etoile { color: #F0A020; font-weight: 400; }
#t4-ddf .f { padding: 3px 8px; white-space: nowrap; }
#t4-ddf .f.survol { background: #EEF3F6; }
#t4-ddf .sep { border-top: 1px solid #E9ECEF; margin: 5px 0; }
#app-2 .t4-k { display: inline-flex; align-items: center; } #app-2 .t4-k svg { width: 10px; height: 10px; display: block; }
"""

TUTO = {
    'slug': 'tuto-04-le-cachet-de-traitement',
    'titre_page': 'AITE Courrier — Tutoriel 04 : le cachet de traitement',
    'titre': 'Le cachet de traitement',
    'serie': dict(COURRIER, numero=4),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Ce courrier a-t-il *vraiment* été *traité ?*',
        'sous': 'Un tampon illisible, des visas oubliés : prouver qu\'un dossier est clos tient souvent du pari.',
        'personnage': (ARCHI[0], 'Archiviste', ARCHI[2]),
        'chaos': [('lettre', 'Dossier « clos » ?'), ('bulle', 'Qui a signé en dernier ?'), ('note', 'Tampon illisible'),
                  ('alerte', 'Visa manquant'), ('doc', 'Copie sans date'), ('bulle', 'Le client redemande'),
                  ('dossier', 'Archives'), ('alerte', 'Réclamation')],
        'voix': "Un client demande si son dossier a été traité. Le tampon est illisible, un visa manque, la date est "
                "introuvable. Comment le prouver ?",
    },
    'revelation': {'voix': "Avec Aïte Courrier, un courrier traité porte son cachet, comme un tampon officiel."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Un *cachet* qui prouve le traitement',
        'pastilles': ['Ruban « Traité »', 'Visas de chaque étape', 'Visible par le tiers'],
        'voix': "Au bout du circuit, chaque courrier reçoit son cachet : un ruban Traité, les visas de chaque étape, "
                "et la même preuve pour le tiers.",
    },
    'ecran': ecran + portail, 'vue_initiale': 't4-tous', 'css': CSS,
    'etapes': [
        {'titre': 'Retrouver les courriers traités', 'texte': "Le filtre « Traités » ne garde que les courriers arrivés au bout de leur circuit.",
         'voix': "Jules, l'archiviste, ouvre les filtres et choisit Traités : la liste ne garde que les courriers arrivés "
                 "au bout de leur circuit. Il ouvre la demande de devis pour travaux.",
         'gestes': [clic('#t4-drop', decale=0.3), montrer('#t4-ddf', y=-8, d=0.3), survol('#t4-f-traites', decale=0.2),
                    clic('#t4-f-traites', decale=0.1), cacher('#t4-ddf', d=0.15), aller('t4-traites'),
                    anneau('#t4-traites .facette', d=1.4), survol('#' + LIGNE_CLOS, decale=0.2),
                    clic('#' + LIGNE_CLOS, fx=0.35), aller('c2-clos')]},
        {'titre': 'Traité, au premier coup d\'œil', 'texte': "Courrier archivé, bandeau « Circuit terminé », ruban « Traité ».",
         'voix': "La barre d'étapes est au bout, sur l'Archivage. Le bandeau l'annonce : circuit terminé, courrier "
                 "archivé. Et le ruban Traité se voit au premier coup d'œil.",
         'gestes': [anneau('#c2-sb2', d=1.4, decale=0.4), anneau('#c2-clos .bandeau', d=1.6),
                    zoom('#c2-ruban', s=1.7, fx=0.62, fy=0.35, d=0.9), anneau('#c2-ruban', d=1.4),
                    bulle('#c2-ruban', 'Ruban « Traité »', cote='gauche', fx=0.1, d=2.2), dezoom(d=0.7)]},
        {'titre': 'Les visas de chaque étape', 'texte': "L'onglet Cachet : l'étape, l'intervenant, sa fonction et la date.",
         'voix': "L'onglet Cachet récapitule le traitement : la date de clôture, le nombre de visas, et pour chaque étape, "
                 "l'intervenant, sa fonction et la date. Tout est tiré de l'historique des étapes : rien n'est saisi à la main. "
                 "C'est la preuve, prête à être montrée.",
         'gestes': [clic('#c2-clos .og.actif', fx=0.5), zoom('#c2-cachet', s=1.5, d=0.9), anneau('#c2-cachet-b', d=1.6),
                    bulle('#c2-cachet', 'Nom, fonction, date', cote='dessous', d=2.4), anneau('#c2-cachet', d=1.8), dezoom(d=0.7),
                    anneau('#c2-clos .onglets .og:nth-child(2)', d=1.8),
                    bulle('#c2-clos .onglets .og:nth-child(3)', "Tiré de l'historique", cote='droite', d=2.2, avec=True)]},
        {'titre': 'Le tiers voit le même cachet', 'texte': "Sur son portail : « Demande traitée », les fonctions et les dates.",
         'voix': "Le tiers, lui, voit le même cachet sur son portail : demande traitée, avec la fonction de chaque "
                 "intervenant et la date de son visa. Les noms, eux, restent internes : seule la fonction est publiée.",
         'gestes': [texte('#pr-url', 'courrier.aite-demo.test/my/courriers/9'), cacher('#c8-compte', d=0.05),
                    montrer('#app-8', y=0, d=0.4), aller('c8-suivi'), pause(0.4), anneau('#c8-av', d=1.4),
                    zoom('#c8-cachet', s=1.7, d=0.9), anneau('#c8-cachet', d=1.6),
                    bulle('#c8-cachet', 'La fonction, pas le nom', cote='droite', d=2.4), dezoom(d=0.7)]},
    ],
    'benefices': {
        'titre': 'La preuve du traitement, *partagée.*',
        'voix': "Un courrier traité se reconnaît tout de suite, ses visas sont réunis au même endroit, et le tiers "
                "reçoit la même preuve, sans un appel.",
        'cartes': [('bouclier', 'Traité', 'Visible tout de suite', "Ruban et bandeau sur chaque courrier clos."),
                   ('trace', 'Visas', 'Une preuve complète', "L'étape, l'intervenant, sa fonction et la date de chaque visa."),
                   ('equipe', 'Portail', 'Le tiers rassuré', "Il voit le cachet de sa demande, sans appeler.")],
    },
    'cta': cta('courrier', 'Le traitement, *prouvé.*', "Aïte Courrier : le traitement, prouvé."),
    'youtube': youtube('COMMENT PROUVER QU\'UN COURRIER A ÉTÉ TRAITÉ : LE CACHET DE TRAITEMENT AITE COURRIER (ODOO 18)',
                       "Au bout de son circuit, chaque courrier reçoit un cachet de traitement : ruban « Traité », visas de "
                       "chaque étape, et la même preuve pour le tiers sur son portail. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'cachet de traitement', 'portail tiers', 'preuve de traitement']),
}
