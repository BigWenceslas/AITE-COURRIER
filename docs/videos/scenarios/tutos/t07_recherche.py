# -*- coding: utf-8 -*-
"""Tutoriel 07 — Recherche plein texte (OCR) : retrouver un courrier par le
contenu de ses pièces.

Sources :
- aite_courrier_ocr/views/aite_courrier_views.xml:10-12 (champ de recherche
  « Contenu des pièces (plein texte) », placé après « Responsable ») ;
- aite_courrier_ocr/models/aite_courrier.py:10-30 (``document_fulltext`` :
  interroge le texte extrait de toutes les versions des pièces, en sudo, puis
  rend des ids : les règles d'accès du courrier s'appliquent ensuite) ;
- aite_courrier_ocr/models/aite_courrier_document_version.py:60-69 (état
  « Indexation » : Non concerné, En attente, Indexé, Erreur), :80-86 (mise en
  file « En attente » à la création d'une version PDF ou image), :88-91
  (``action_reprocess_ocr`` : remet en file), :97 (lots de 20), :147-166
  (couche texte pypdf d'abord, OCR Tesseract en repli sous 40 caractères),
  :169-183 (``aite_courrier.ocr_max_pages``, 10 par défaut), :186-196 (OCR
  des images) ;
- aite_courrier_ocr/views/aite_courrier_document_views.xml:10-19 (colonne
  ``ocr_state`` en badge vert / orange / rouge après « Date » ; bouton
  « Réindexer », info-bulle « Relancer l'extraction plein texte », masqué
  pour « En attente » et « Non concerné ») ;
- aite_courrier_ocr/data/ir_cron_data.xml:6-13 (« AITE Courrier : indexation
  plein texte (OCR) », toutes les 10 minutes) ;
- aite_courrier_ged/views/aite_courrier_document_views.xml:30-92 (fiche de la
  pièce : « Prévisualiser », « Finaliser », états, champs, « Téléverser une
  nouvelle version », bouton du champ binaire « Charger votre fichier »
  (Odoo, relevé dans la base), textes d'aide, onglet « Versions », colonnes
  des versions) ; models/aite_courrier_document.py:100-132 (« Confidentialité
  (héritée) », « Verrouillé », « Nombre de versions », « Fichier à
  téléverser ») ; models/aite_courrier_document_version.py:23-40 (« Version »,
  « Nom du fichier », « Extension », « Taille (octets) », « Téléversé par »,
  « Date ») ; aite_courrier_ecm/views/aite_courrier_ecm_views.xml:69 (onglet
  « ECM ») ;
- aite_courrier_ged/views/aite_courrier_views.xml:11-25 (onglet
  « Documents » du courrier, « Prévisualiser ») ; aite_courrier_ged/security/
  ir.model.access.csv:26-33 (seuls l'agent courrier et l'administrateur
  modifient une version : « Réindexer » leur est réservé, vérifié dans la
  base : « Erreur d'accès » pour l'assistante) ;
- aite_courrier_core/views/aite_courrier_views.xml:144-152 (champs de
  recherche, dans l'ordre), aite_courrier_validation/views/
  aite_courrier_views.xml:15-23 et aite_courrier_reponse/views/
  aite_courrier_views.xml:12-14 (« Commenter », « Répondre ») ;
- docs/TUTORIEL_CAPTURE_OCR.md §B.1 à B.5 (cron toutes les 10 minutes,
  Tesseract facultatif, 10 pages par défaut, « Réindexer », confidentialité
  respectée) ; docs/produits/AITE_Courrier_fiche_avant_vente_technique.md:41.
Écrans : composés d'après la base de démonstration (thème MuK, compte
assistante) : menu de recherche « Rechercher … pour: … », facette, fiche du
courrier en lecture, pièce ouverte dans la fenêtre « Ouvrir : Documents »
(pied « Fermer »), info-bulle noire du bouton. Liste reprise de la
présentation, chapitre 1.
"""

import demo
from ecrans import (assistant, bande, bouton, bouton_stat, c_html, c_num, case, champ, chatter, e, fenetre,
                    feuille, grille2, liste, message, onglets, panneau_fiche, panneau_lateral, panneau_liste, puce,
                    sec_titre, statusbar, table, v, vue, ICONES)
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, cacher, classe, clic, curseur, fermer, montrer, ouvrir, pause, saisir, vue as aller
from tutoriel import ECHELLE, bulle, dezoom, zoom

ASSIST = demo.PERSONNES['assistante']
AGENT = demo.PERSONNES['agent']
MANAGER = demo.PERSONNES['manager']
MOT = 'résiliation'
REF = 'COUR-2026-0048'
OBJET = 'Contrat de maintenance — proposition de renouvellement'
FOURN = demo.FOURNISSEUR
COURRIEL = demo.EN_COURS['courriel']
PIECE = 'Conditions générales de maintenance'

RESULTATS = [
    (REF, OBJET, 'Courrier entrant', 'Juridique', 'Traitement', 'En traitement', 'gris', '29/09/2026'),
    ('COUR-2026-0012', 'Avenant au bail commercial — agence', 'Courrier entrant', 'Direction générale', 'Archivage',
     'Archivé', 'gris', '17/09/2026', 'gris'),
]

# Les champs du menu de recherche, dans l'ordre de la vue (core + OCR) ;
# True : champ relationnel, avec sa flèche de sous-menu.
CHAMPS = [('Référence / Objet', False), ('Type', True), ('Service destinataire', True), ('Responsable', True),
          ('Contenu des pièces (plein texte)', False), ('Contact expéditeur', True), ('Expéditeur (texte)', False)]

LIEN_EXT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
            'stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v6H4V6h6"/></svg>')
RAFRAICHIR = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" '
              'stroke-linejoin="round"><path d="M20 11a8 8 0 00-14.3-4.6L4 8"/><path d="M4 3v5h5"/>'
              '<path d="M4 13a8 8 0 0014.3 4.6L20 16"/><path d="M20 21v-5h-5"/></svg>')


def bulle_g(sel, texte, largeur, s, d=2.4, **kw):
    """Une bulle à gauche de ``sel`` (``largeur`` et ``s`` : conservés pour les appels existants)."""
    return bulle(sel, texte, cote='gauche', d=d, **kw)


# ------------------------------------------------------------- l'écran --
def _menu_recherche():
    items = ''.join('<div class="t7-ai%s" id="t7-a%d"><span class="t7-car%s"></span>Rechercher <b>%s</b> pour: <b><i>%s</i></b></div>'
                    % (' sel' if i == 0 else '', i, ' on' if rel else '', e(nom), e(MOT)) for i, (nom, rel) in enumerate(CHAMPS))
    return ('<div class="t7-auto masque" id="t7-auto">%s<div class="t7-ai t7-perso">Ajouter un filtre personnalisé</div></div>'
            % items)


def _liste():
    lst = vue('t7-liste', panneau_liste('Courriers', '1-80 / 151', nouveau=False, recherche_id='t7-rech') + base.lat_courriers(None)
              + liste(base.COL_COURRIERS, [base.ligne_courrier('t7-l%d' % i, *l) for i, l in enumerate(base.LIGNES_COURRIERS)]),
              initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    # le menu déroulant s'ouvre sous la barre de recherche
    return lst.replace('<span class="drop">▾</span>', '<span class="drop">▾</span>' + _menu_recherche(), 1)


def _resultats():
    lat = panneau_lateral([('▰ CATÉGORIE', [('Tous', '', True), ('Entrant', '2', False)]),
                           ('≡ STATUT', [('Archivé', '1', False), ('En traitement', '1', False)])])
    return vue('t7-res', panneau_liste('Courriers', '1-2 / 2', facettes=[('Contenu des pièces (plein texte)', MOT)], nouveau=False)
               + lat + liste(base.COL_COURRIERS, [base.ligne_courrier('t7-r%d' % i, *l) for i, l in enumerate(RESULTATS)])
               ).replace('class="vue"', 'class="vue avec-lateral"', 1)


def _fiche():
    stats = bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '2')
    prev = '<span class="lien t7-prev">%s Prévisualiser</span>' % ICONES['oeil']
    docs = table([('Nom', '1fr'), ('Dossier', '62px'), ('Étiquettes', '66px'), ('Extension', '62px'), ('Nombre de versions', '62px'),
                  ('État', '70px'), ('Verrouillé', '22px'), ('', '92px')],
                 [{'id': 't7-d%d' % i, 'cellules': [n, '', '', 'pdf', c_num(nb), c_html('<span>%s</span>' % puce('Brouillon')),
                                                    c_html(case(False)), c_html(prev)]}
                  for i, (n, nb) in enumerate([('Lettre — proposition de renouvellement', '1'), (PIECE, '2')])],
                 identifiant='t7-docs', ajouter=False)
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v">%s</div>' % REF
             + grille2([champ('Objet', v(OBJET)), champ('Contact expéditeur', v(FOURN, True), aide=True),
                        champ('Expéditeur', v(FOURN)), champ('E-mail expéditeur', v(COURRIEL, True), aide=True),
                        champ('Type', v('Courrier entrant', True)), champ('Service destinataire', v('Juridique', True))],
                       [champ('Statut', puce('En traitement', 'gris'), aide=True), champ('Priorité', v('Normale', True)),
                        champ('Confidentialité', v('Interne', True)), champ('Date de réception', v('29/09/2026')),
                        champ('Responsable', v(MANAGER[0], True))])
             + onglets(['Documents', 'Historique'], 0) + docs)
    ch = chatter([message(AGENT[0], AGENT[2], 'Courrier arrivé à l\'étape « Réception » — traitement attendu.', '08:52'),
                  message(MANAGER[0], MANAGER[2], 'Affectation → <span class="lien">Traitement</span> (Étape courante)', '09:41')],
                 identifiant='t7-chatter', suivre='')
    return vue('t7-fiche', panneau_fiche('Courriers', REF, '1 / 2', nouveau=False, boutons_stat=stats)
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande([bouton('t7-com', 'Commenter', 'second'), bouton('t7-rep', 'Répondre', 'second', 'retour')],
                         statusbar(base.ETAPES, 3, 't7-sb'), 't7-bande'), feuille(corps), ch))


def _piece():
    """La pièce, ouverte depuis l'onglet Documents : fenêtre « Ouvrir : Documents »."""
    ouvrir_v = c_html('<span class="lien t7-btn">%s Ouvrir</span>' % LIEN_EXT)
    tip = '<span class="t7-tip masque" id="t7-tip"><i></i>Relancer l\'extraction plein texte</span>'
    reindexer = c_html('<span class="lien t7-btn t7-rx" id="t7-rx">%s Réindexer%s</span>' % (RAFRAICHIR, tip))
    colonnes = [('Version', '46px'), ('Nom du fichier', '1fr'), ('', '58px'), ('Télécharger', '66px'), ('Extension', '62px'),
                ('Taille (octets)', '66px'), ('Téléversé par', '84px'), ('Date', '122px'), ('Indexation', '80px'), ('', '86px')]
    versions = table(colonnes, [
        {'id': 't7-v2', 'cellules': ['v2', 'Conditions_generales_maintenance_v2.pdf', ouvrir_v, '212.48 Kb',
                                     c_html('<span class="ell t7-ext">pdf</span>'), c_num('217 579'), AGENT[0],
                                     '13/10/2026 10:24:05', c_html('<span>%s</span>' % puce('En attente', 'jaune', 't7-v2-ix')), '']},
        {'id': 't7-v1', 'cellules': ['v1', 'Conditions_generales_maintenance.pdf', ouvrir_v, '208.11 Kb',
                                     c_html('<span class="ell t7-ext" id="t7-v1-ext">pdf</span>'), c_num('213 107'), AGENT[0],
                                     '29/09/2026 10:12:40', c_html('<span>%s</span>' % puce('Indexé', 'vert', 't7-v1-ix')), reindexer]},
    ], identifiant='t7-versions', ajouter=False)
    tete = ('<div class="t7-dh">%s%s<span class="t7-sbz">%s</span></div>'
            % (bouton('t7-prev', 'Prévisualiser', 'second', 'oeil'), bouton('t7-fin', 'Finaliser', 'prim'),
               statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 't7-dsb')))
    corps = ('<div id="t7-piece">' + tete + '<div class="t7-titre">%s</div>' % e(PIECE)
             + grille2([champ('Courrier', v(REF, True)), champ('Dossier', ''), champ('Étiquettes', '')],
                       [champ('Confidentialité (héritée)', v('Interne', True)), champ('Nombre de versions', v('2')),
                        champ('Verrouillé', case(False), aide=True)])
             + sec_titre('Téléverser une nouvelle version')
             + champ('Fichier à téléverser', '<span class="bt prim t7-charger">Charger votre fichier</span>')
             + '<div class="t7-aide">Formats acceptés : PDF, DOCX, XLSX, images (JPG, PNG, TIFF), e-mails (EML, MSG) — 50 Mo maximum.</div>'
             + '<div class="t7-aide">Cliquez <b>Prévisualiser</b> (en-tête) pour ouvrir la dernière version dans un onglet — le PDF '
               's\'affiche directement. Chaque version est aussi téléchargeable ou ouvrable ci-dessous.</div>'
             + onglets(['Versions', 'ECM'], 0) + versions + '<div class="t7-vide"></div></div>')
    return assistant('t7-dlg', 'Ouvrir : Documents', corps, [('t7-fermer', 'Fermer', 'prim')], haut=52, largeur=960)


def ecran():
    return fenetre('Courrier', ['Courriers', 'Espace documentaire'], [_liste(), _resultats(), _fiche()],
                   ASSIST[1], ASSIST[2], calques=_piece(), ident='app-7')


CSS = """
#app-7 .recherche { position: relative; }
#t7-auto { position: absolute; left: -1px; top: 31px; width: 452px; z-index: 30; background: #fff; border: 1px solid #DEE2E6;
  border-radius: 4px; box-shadow: 0 10px 26px rgba(0,0,0,.16); padding: 5px 0; font-size: 12.5px; color: #212529; }
#t7-auto .t7-ai { display: flex; align-items: center; height: 25px; padding: 0 10px 0 6px; white-space: nowrap; }
#t7-auto .t7-ai b { font-weight: 600; margin: 0 4px; } #t7-auto .t7-ai b i { font-style: italic; }
#t7-auto .t7-ai.sel { background: #E9ECEF; }
#t7-auto .t7-car { width: 14px; flex: none; }
#t7-auto .t7-car.on::before { content: ''; display: inline-block; border-left: 5px solid #495057; border-top: 4px solid transparent;
  border-bottom: 4px solid transparent; margin-left: 3px; }
#t7-auto .t7-perso { padding-left: 20px; color: #528099; }
#t7-res .facette, #t7-res .facette .k { white-space: nowrap; flex: none; }
#t7-chatter .ch-bts .bt { padding: 0 6px; font-size: 11px; }
#t7-docs .t7-prev, #t7-dlg .t7-btn { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
#t7-docs .t7-prev svg { width: 12px; height: 12px; }
#t7-dlg .t7-btn svg { width: 11px; height: 11px; display: block; }
#t7-dlg .mc { padding: 12px 16px 6px; }
#t7-dlg .mt { padding: 12px 16px; }
#t7-dlg .mp { padding: 10px 16px; }
#t7-dlg .t7-dh { display: flex; align-items: center; gap: 4px; }
#t7-dlg .t7-sbz { margin-left: auto; }
#t7-dlg .t7-titre { font-size: 22px; margin: 8px 0 8px; }
#t7-dlg .champ { min-height: 24px; padding: 2px 0; }
#t7-dlg .sec-t { margin: 8px 0 4px; }
#t7-dlg .t7-charger { font-size: 11.5px; padding: 3px 9px; }
#t7-dlg .t7-aide { color: #6C757D; font-size: 11.5px; line-height: 1.45; margin: 3px 0; }
#t7-dlg .onglets { margin-top: 6px; }
#t7-dlg .o-table .tt, #t7-dlg .o-table .tl { font-size: 11.5px; column-gap: 7px; }
#t7-dlg .o-table .num { text-align: right; }
#t7-dlg .t7-rx { position: relative; overflow: visible; }
#t7-dlg .t7-vide { height: 40px; }
#t7-tip { position: absolute; right: 2px; top: 31px; z-index: 5; background: #000; color: #fff; font-size: 11px; padding: 4px 8px;
  border-radius: 3px; white-space: nowrap; }
#t7-tip i { position: absolute; right: 30px; top: -5px; border-left: 5px solid transparent; border-right: 5px solid transparent;
  border-bottom: 5px solid #000; }
#t7-versions .tl > span { min-width: 0; }
"""

TUTO = {
    'slug': 'tuto-07-recherche-plein-texte',
    'titre_page': 'AITE Courrier — Tutoriel 07 : recherche plein texte (OCR)',
    'titre': 'Recherche plein texte (OCR)',
    'serie': dict(COURRIER, numero=7),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Cette clause, elle était dans *quel* *courrier ?*',
        'sous': 'Objet vague, scans sans titre, annexes empilées : le bon courrier se cache dans ses pièces.',
        'personnage': (ASSIST[0], 'Assistante', ASSIST[2]),
        'chaos': [('doc', 'scan_0042.pdf'), ('bulle', 'Tu te rappelles la date ?'), ('lettre', 'Objet : « Divers »'),
                  ('alerte', 'Introuvable'), ('dossier', 'Classeur 2026'), ('note', 'Mot-clé : résiliation'),
                  ('bulle', 'Dans une annexe ?'), ('doc', 'scan (3).pdf')],
        'voix': "Un fournisseur cite une clause de résiliation. Elle figurait dans un courrier, mais lequel ? "
                "L'objet n'en dit rien : la clause dort dans une pièce jointe.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, on retrouve un courrier par ce que disent ses pièces."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Chercher dans le *contenu* des *pièces*',
        'pastilles': ['Texte des PDF extrait', 'OCR des scans (Tesseract)', 'Indexation en tâche de fond'],
        'voix': "Le texte des P D F est extrait automatiquement, les numérisations peuvent passer à l'O C R, et tout "
                "s'indexe en tâche de fond, sans faire attendre personne. Voyons comment.",
    },
    'ecran': ecran(), 'vue_initiale': 't7-liste',
    'css': CSS,
    'etapes': [
        {'titre': 'Chercher dans le contenu',
         'texte': "Un mot dans la barre de recherche, puis « Contenu des pièces (plein texte) ».",
         'voix': "Estelle tape le mot qu'elle cherche, résiliation, dans la barre de recherche des courriers. Par défaut, "
                 "la recherche porte sur la référence et l'objet : elle choisit plutôt Contenu des pièces, plein texte.",
         'gestes': [zoom('#t7-rech', s=1.55, fx=0.55, fy=0.15, d=0.9), clic('#t7-rech-q', fx=0.15), saisir('t7-rech-q', MOT, d=0.9),
                    montrer('#t7-auto', y=6, d=0.25), anneau('#t7-a0', d=1.4), pause(0.8),
                    classe('#t7-a0', retirer=['sel']), classe('#t7-a4', ajouter=['sel'], avec=True),
                    curseur('#t7-a4', fx=0.35, avec=True, d=0.6),
                    bulle_g('#t7-a4', 'Le texte des pièces', 450, 1.55, d=2.2), pause(1.6),
                    clic('#t7-a4', fx=0.35, deplacer=False), cacher('#t7-auto', d=0.15), aller('t7-res'),
                    anneau('#t7-res .facette', d=1.2)]},
        {'titre': 'Le courrier retrouvé',
         'texte': "Le mot n'est ni dans l'objet ni dans l'expéditeur : il est dans une pièce du courrier.",
         'voix': "Deux courriers remontent, alors que le mot n'est ni dans leur objet, ni dans leur expéditeur. Et seuls "
                 "les courriers qu'Estelle a le droit de voir s'affichent. Elle ouvre le contrat de maintenance, puis sa "
                 "pièce : les conditions générales.",
         'gestes': [dezoom(d=0.7), anneau('#t7-r0', d=1.0), anneau('#t7-r1', d=1.0),
                    bulle('#t7-r1 > span:nth-child(3)', "Le mot n'est pas dans l'objet", cote='dessous', fx=0.3, d=2.4),
                    pause(1.4), clic('#t7-r0', fx=0.35), aller('t7-fiche'), pause(0.4), anneau('#t7-docs', d=1.2),
                    clic('#t7-d1', fx=0.2), ouvrir('t7-dlg')]},
        {'titre': "L'état d'indexation",
         'texte': "Colonne Indexation : « Indexé » quand le texte est extrait, « En attente » jusqu'au prochain passage.",
         'voix': "La colonne Indexation suit chaque version de la pièce. La version 1 est indexée : son texte est extrait. "
                 "La version 2, déposée il y a quelques minutes, est en attente : une tâche planifiée passe toutes les "
                 "dix minutes, en arrière-plan. Personne n'attend.",
         'gestes': [zoom('#t7-versions', s=1.12, fx=0.5, fy=0.62, d=0.9), anneau('#t7-versions .tt > span:nth-child(9)', d=1.4),
                    anneau('#t7-v1-ix', d=1.2), bulle('#t7-v1-ix', 'Texte extrait', cote='dessous', d=2.4), pause(1.6),
                    anneau('#t7-v2 > span:nth-child(8)', d=1.2), anneau('#t7-v2-ix', d=1.2),
                    bulle_g('#t7-v2-ix', 'Au prochain passage', 66, 1.2, d=2.8), pause(2.4)]},
        {'titre': "Couche texte, OCR et relance",
         'texte': "PDF lu directement ; OCR Tesseract en repli, s'il est installé. « Réindexer » remet en file.",
         'voix': "Le texte des P D F est lu directement. Pour une numérisation, l'O C R Tesseract prend le relais s'il est "
                 "installé : dix pages par défaut, un réglage modifiable. Et le bouton Réindexer, pour l'agent courrier "
                 "ou l'administrateur, remet une version en file d'attente.",
         'gestes': [anneau('#t7-v1-ext', d=1.0), bulle('#t7-v1-ext', 'Couche texte du PDF', cote='dessous', d=2.2), pause(1.2),
                    bulle_g('#t7-versions .tt > span:nth-child(9)', 'Scan : OCR, si Tesseract', 80, 1.2, d=2.6), pause(2.4),
                    curseur('#t7-rx', fx=0.76, fy=0.1, d=0.6), montrer('#t7-tip', y=4, d=0.2), anneau('#t7-rx', d=1.2),
                    bulle_g('#t7-tip', 'Agent ou administrateur', 168, 1.2, d=2.4), pause(1.6),
                    cacher('#t7-tip', d=0.2), dezoom(d=0.7), clic('#t7-fermer'), fermer('t7-dlg')]},
    ],
    'benefices': {
        'titre': 'Retrouvé par son *contenu.*',
        'voix': "Un mot suffit pour retrouver un courrier, l'indexation travaille en tâche de fond, et chacun ne voit "
                "que les courriers auxquels il a droit.",
        'cartes': [('cible', 'Plein texte', 'Un mot suffit', "Le texte de toutes les versions de toutes les pièces est interrogé."),
                   ('temps', '10 min', 'En tâche de fond', "Une tâche planifiée indexe les nouvelles versions, sans attente."),
                   ('bouclier', "Règles d'accès", 'Confidentialité suivie', "Un courrier confidentiel ne remonte que pour qui peut le voir.")],
    },
    'cta': cta('courrier', 'Le bon courrier, *en* *un* *mot.*', "Aïte Courrier : le bon courrier, en un mot."),
    'youtube': youtube('COMMENT RETROUVER UN COURRIER PAR LE CONTENU DE SES PIÈCES AVEC AITE COURRIER (ODOO 18)',
                       "Recherche plein texte et OCR : AITE Courrier extrait le texte des PDF et, si Tesseract est installé, "
                       "celui des numérisations, en tâche de fond. Un mot tapé dans la recherche « Contenu des pièces » "
                       "retrouve le courrier, dans le respect des règles de confidentialité. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'recherche plein texte', 'OCR', 'Tesseract', 'indexation PDF']),
}
