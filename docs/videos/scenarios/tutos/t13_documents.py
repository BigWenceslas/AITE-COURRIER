# -*- coding: utf-8 -*-
"""Tutoriel 13 — Explorateur et document ECM.

Sources :
- addons/aite_ecm_document/views/aite_ecm_menus.xml (Documents › Explorateur,
  « Plan de classement ») ; action aite_ecm_document.action_aite_ecm_explorer_native ;
- gabarit OWL static/src/explorer/explorer.xml : boutons « Charger »,
  « Numériser » (« Photos (appareil photo sur mobile) assemblées en un PDF »),
  « Nouveau document », « Nouveau dossier », « Partager » (visible quand un
  document est inspecté) ; « Rechercher (titre, référence, fichier,
  contenu)… », « Plus récents » ; « Espace de travail », « Tous » ; fil
  « ECM › … », « … / … document(s) », « Effacer les filtres », « Tout
  sélectionner » ; cartes (référence · type, étiquettes, date, statut) ;
  inspecteur (« Fiche », « Aperçu », « Télécharger », « Nouvelle version »,
  « Réserver », « Lancer le circuit » — type à circuit actif, ici
  Procédure / instruction, aite_ecm_workflow —, « Finaliser » — brouillon
  avec fichier —, « Partager », « Corbeille » ; « Fichier », « Versions »,
  « Type », « Dossier », « Étiquettes », « Confidentialité »,
  « Propriétaire », « Modifié ») ;
- data/aite_ecm_data.xml : 7 dossiers livrés (Direction générale,
  Ressources humaines, Dossiers du personnel, Juridique et contrats, Finance
  et comptabilité, Achats et fournisseurs, Qualité et procédures) et 6 types
  (Contrat, Procédure / instruction, Facture fournisseur, Pièce du dossier du
  personnel, Procès-verbal / compte rendu, Document générique) ;
  data/ir_sequence_data.xml (référence DOC-AAAA-NNNNN) ;
- models/aite_ecm_document.py : « Titre », « Type », « Dossier de
  classement », statuts Brouillon / Finalisé / Archivé (Finalisé et Archivé
  verrouillent), MAX_FILE_SIZE = 100 Mo par fichier ; vue fiche : nouvelle
  version seulement en Brouillon (« Téléverser une nouvelle version »,
  « Ajouter la version ») ;
- models/aite_ecm_folder.py (« Chemin », « Lecture effective »,
  « Documents ») ; un dossier sans restriction propre hérite de son parent.
Écrans : explorateur reconstruit ici (modèle : base demo18, captures
t13_*), puis présentation, chapitre 4 (scenarios/presentation.py, CH4).
"""

import demo
from ecrans import ICONES, e, fenetre, vue
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, ECM, cta, etape, youtube
from moteur import anneau, classe, clic, curseur, montrer, pause, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ARCHI, MANAGER, ASSIST, COMPTA, AGENT = P['archiviste'], P['manager'], P['assistante'], P['compta'], P['agent']
CH = base.CH4
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'

CAMERA = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 4h6l1.6 2.4H21v13H3v-13h4.4zM12 9a4 4 0 100 8 4 4 0 000-8z"/></svg>')
DOSSIER = ('<svg viewBox="0 0 24 24" fill="none" stroke="#343A40" stroke-width="1.8" stroke-linejoin="round">'
           '<path d="M3 6h6l2 2h10v11H3z"/></svg>')
PDF = ('<svg viewBox="0 0 24 24" fill="none" stroke="#9AA0A6" stroke-width="1.4" stroke-linejoin="round"><path d="M14 2H5v20h14V7z"/>'
       '<path d="M14 2v5h5"/><path d="M8.5 17.5c2-3 3.5-6.5 3.2-8.5-.3-1.6-1.9-.8-1.2 1 .9 2.4 3.4 5 6 5.7 1.4.4 1.6-1 .2-1.1-2.6-.2-5.8.9-8.2 2.9z"/></svg>')
GRILLE = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="7" height="7"/><rect x="13" y="4" width="7" height="7"/><rect x="4" y="13" width="7" height="7"/><rect x="13" y="13" width="7" height="7"/></svg>'
LISTE = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="5" width="16" height="2.4"/><rect x="4" y="10.8" width="16" height="2.4"/><rect x="4" y="16.6" width="16" height="2.4"/></svg>'

# l'arborescence : (niveau, nom, nombre, ouvert)
ARBRE = [(0, 'Direction générale', 6), (1, 'Procès-verbaux', 6), (0, 'Ressources humaines', 7), (1, 'Dossiers du personnel', 4),
         (1, 'Recrutements', 1), (0, 'Juridique et contrats', 3), (1, 'Contrats fournisseurs', 2), (1, 'Contentieux', 0),
         (0, 'Finance et comptabilité', 16), (1, 'Factures fournisseurs 2026', 13), (1, 'Banques et assurances', 3),
         (0, 'Achats et fournisseurs', 5), (1, 'Agréments fournisseurs', 4), (1, "Appels d'offres", 1),
         (0, 'Qualité et procédures', 10), (1, 'Procédures en vigueur', 8), (0, 'Courrier', 177), (1, '2026', 177)]
I_QUAL = 14

# cartes : (référence, titre, type, étiquettes, statut, date)
TOUS = [
    ('DOC-2026-00359', 'Procédure de recette des documents', 'Procédure / instruction', [], 'Brouillon', '13/10/2026'),
    ('DOC-2026-00358', 'Attestation de non-redevance fiscale — Delta Équipements', 'Document générique', [('Fiscal', 'r')], 'Brouillon', '13/10/2026'),
    ('DOC-2026-00356', 'Registre de commerce — %s' % demo.TIERS, 'Document générique', [('Original papier', 'b')], 'Brouillon', '12/10/2026'),
    ('DOC-2026-00352', "Relevé d'identité bancaire — Delta Équipements", 'Document générique', [], 'Finalisé', '12/10/2026'),
    ('DOC-2026-00341', 'Contrat de maintenance — climatisation', 'Contrat', [('À renouveler', 'j')], 'Finalisé', '10/10/2026'),
    ('DOC-2026-00320', 'Procès-verbal du conseil — septembre', 'Procès-verbal / compte rendu', [], 'Finalisé', '08/10/2026'),
    ('DOC-2026-00311', 'Facture F-2026-6133 — télécommunications', 'Facture fournisseur', [('2026', 'j')], 'Finalisé', '07/10/2026'),
    ('DOC-2026-00298', "Note de service — horaires d'été", 'Document générique', [], 'Archivé', '06/10/2026'),
    ('DOC-2026-00255', 'Pièce de courrier — demande de devis', 'Pièce de courrier', [], 'Finalisé', '05/10/2026'),
]
QUAL = [
    ('DOC-2026-00359', 'Procédure de recette des documents', 'Procédure / instruction', [], 'Brouillon', '13/10/2026'),
    ('DOC-2026-00290', 'Cahier des charges — logiciel de paie', 'Document générique', [("Appel d'offres", 'r')], 'Finalisé', '02/10/2026'),
    ('DOC-2026-00286', "Procédure d'achat et de sélection des fournisseurs", 'Procédure / instruction', [], 'Finalisé', '01/10/2026'),
    ('DOC-2026-00279', 'Procédure de gestion des incidents', 'Procédure / instruction', [('Urgent', 'r')], 'Brouillon', '29/09/2026'),
    ('DOC-2026-00268', "Plan de continuité d'activité", 'Procédure / instruction', [], 'Finalisé', '24/09/2026'),
    ('DOC-2026-00262', 'Procédure de traitement des réclamations', 'Procédure / instruction', [], 'Archivé', '18/09/2026'),
]
STATUT = {'Brouillon': 'gris', 'Finalisé': 'vert', 'Archivé': 'noir'}


def carte(ident, ref, titre, typ, tags, statut, date):
    t = ''.join('<span class="t13-tag %s">%s</span>' % (c, e(n)) for n, c in tags)
    return ('<div class="t13-carte" id="%s"><div class="t13-vign">%s<span class="t13-chk" id="%s-chk"></span></div>'
            '<div class="t13-cc"><div class="t13-ct ell">%s</div><div class="t13-cs ell">%s · %s</div>'
            '<div class="t13-tags">%s</div><div class="t13-cp"><span>%s</span><span class="t13-st %s">%s</span></div></div></div>'
            % (ident, PDF, ident, e(titre), e(ref), e(typ), t, e(date), STATUT[statut], e(statut)))


def barre_outils(p):
    return ('<div class="t13-tb"><span class="t13-tbg" id="{p}-g"{z}>'
            '<span class="bt prim" id="{p}-charger"><span class="ic">{up}</span>Charger</span>'
            '<span class="bt second" id="{p}-num"><span class="ic">{cam}</span>Numériser</span>'
            '<span class="t13-lk" id="{p}-nd">Nouveau document</span><span class="t13-lk" id="{p}-nf">Nouveau dossier</span></span>'
            '<span class="t13-lk masque" id="{p}-part">Partager</span>'
            '<span class="t13-rech"><span class="t13-lp">{lp}</span><span class="ph">Rechercher (titre, référence, fichier, contenu)…</span></span>'
            '<span class="t13-tri">Plus récents ▾</span><span class="t13-vt"><i class="on">{gr}</i><i>{li}</i></span></div>'
            ).format(p=p, z=ZONE, up=ICONES['televerser'], cam=CAMERA, lp=ICONES['loupe'], gr=GRILLE, li=LISTE)


def arbre(prefixe, actif=None):
    h = ['<div class="t13-st-t">Espace de travail</div><div class="t13-it%s" id="%s-tous"><span>Tous</span></div>'
         % (' actif' if actif is None else '', prefixe)]
    for i, (niv, nom, n) in enumerate(ARBRE):
        fl = '<b>▾</b>' if niv == 0 and nom != 'Courrier' else ('<b>▾</b>' if nom == 'Courrier' else '<b></b>')
        if nom == '2026':
            fl = '<b>▸</b>'
        h.append('<div class="t13-it n%d%s" id="%s-f%d">%s<span class="t13-fi">%s</span><span class="ell">%s</span><i>%d</i></div>'
                 % (niv, ' actif' if actif == i else '', prefixe, i, fl if niv == 0 or nom == '2026' else '', DOSSIER, e(nom), n))
    return '<div class="t13-side" id="%s-arbre">%s</div>' % (prefixe, ''.join(h))


def ecran_explorateur():
    # « Tous »
    tous = vue('t13-tous', barre_outils('t13a')
               + arbre('t13a')
               + '<div class="t13-main"><div class="t13-fil"><span class="t13-bc">ECM</span><span class="t13-nb">60 / 257 document(s)</span>'
                 '<span class="t13-ts">☑ Tout sélectionner</span></div><div class="t13-grille" id="t13-grille-a">%s</div></div>'
               % ''.join(carte('t13a-c%d' % i, *c) for i, c in enumerate(TOUS)), initiale=True)
    # « Qualité et procédures », puis un document inspecté
    insp = ('<div class="t13-insp masque" id="t13-insp"%s><div class="t13-iv">%s</div>'
            '<div class="t13-it1">%s</div><div class="t13-is">%s · Brouillon</div>'
            '<div class="t13-ib" id="t13-ib"><span class="bt prim petit">Fiche</span><span class="bt second petit">Aperçu</span>'
            '<span class="bt second petit">Télécharger</span><span class="bt second petit">Nouvelle version</span>'
            '<span class="bt second petit">Réserver</span><span class="bt prim petit">Lancer le circuit</span>'
            '<span class="bt vert petit">Finaliser</span><span class="bt second petit" id="t13-ipart">Partager</span>'
            '<span class="bt t13-corb petit">Corbeille</span></div>'
            '<dl class="t13-dl" id="t13-dl"><dt>Fichier</dt><dd>Procedure_recette_documents.pdf <em>(212 Ko)</em></dd>'
            '<dt>Versions</dt><dd>1</dd><dt>Type</dt><dd>Procédure / instruction</dd>'
            '<dt>Dossier</dt><dd>Qualité et procédures</dd><dt>Étiquettes</dt><dd><em>—</em></dd>'
            '<dt>Confidentialité</dt><dd>Interne</dd><dt>Propriétaire</dt><dd>%s</dd><dt>Modifié</dt><dd>13/10/2026</dd></dl></div>'
            % (ZONE, PDF, e(QUAL[0][1]), QUAL[0][0], e(ARCHI[0])))
    qual = vue('t13-qual', barre_outils('t13b')
               + arbre('t13b', I_QUAL)
               + '<div class="t13-main" id="t13b-main"><div class="t13-fil"><span class="t13-bc">ECM › <b>Qualité et procédures</b></span>'
                 '<span class="t13-nb">10 / 10 document(s)</span><span class="t13-eff">Effacer les filtres</span>'
                 '<span class="t13-ts">☑ Tout sélectionner</span></div><div class="t13-grille" id="t13-grille-b">%s</div></div>%s'
               % (''.join(carte('t13b-c%d' % i, *c) for i, c in enumerate(QUAL)), insp))
    return fenetre('ECM', base.MENUS_ECM, [tous, qual], ARCHI[1], ARCHI[2], ident='app-13')


ECRAN4 = CH['ecran'].replace('<div class="o-app muk" id="app-4">', '<div class="o-app muk masque" id="app-4">', 1)
# une zone sur la colonne « Lecture effective » du plan de classement
ECRAN4 = ECRAN4.replace('<div class="vue" id="c4-plan" data-groupe="odoo">',
                        '<div class="vue" id="c4-plan" data-groupe="odoo"><div class="t13-zone" id="t13-le"%s></div>' % ZONE, 1)

# le bouton du champ binaire d'Odoo 18 en français : « Charger votre fichier » (web/i18n/fr.po, « Upload your file »)
ECRAN4 = ECRAN4.replace('Téléverser votre fichier', 'Charger votre fichier', 1)
assert 'Charger votre fichier' in ECRAN4

CSS = """
#app-13 .t13-tb { height: 44px; display: flex; align-items: center; gap: 6px; padding: 0 12px; background: #fff; border-bottom: 1px solid #DEE2E6; }
#app-13 .t13-tbg { display: inline-flex; align-items: center; gap: 6px; }
#app-13 .t13-tb .bt .ic svg { width: 12px; height: 12px; }
#app-13 .t13-lk { color: #528099; font-weight: 700; text-transform: uppercase; font-size: 12px; padding: 0 8px; letter-spacing: .01em; }
#app-13 .t13-rech { margin-left: auto; width: 250px; height: 28px; border: 1px solid #DEE2E6; border-radius: 4px; display: flex; align-items: center;
  gap: 6px; padding: 0 6px; color: #9AA0A6; font-size: 11px; overflow: hidden; white-space: nowrap; }
#app-13 .t13-lp svg { width: 12px; height: 12px; display: block; }
#app-13 .t13-tri { height: 28px; line-height: 26px; border: 1px solid #DEE2E6; border-radius: 4px; padding: 0 8px; font-size: 12px; }
#app-13 .t13-vt { display: inline-flex; } #app-13 .t13-vt i { width: 26px; height: 28px; display: inline-flex; align-items: center; justify-content: center;
  background: #E7E9ED; color: #343A40; } #app-13 .t13-vt i.on { background: #DCE8EF; box-shadow: inset 0 0 0 1px #5D8DA8; }
#app-13 .t13-vt svg { width: 12px; height: 12px; }
#app-13 .t13-side { position: absolute; left: 0; top: 44px; bottom: 0; width: 176px; background: #fff; border-right: 1px solid #DEE2E6;
  padding: 10px 0; overflow: hidden; }
#app-13 .t13-st-t { font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: #6C757D; padding: 0 8px 6px; }
#app-13 .t13-it { display: flex; align-items: center; gap: 3px; height: 21px; padding: 0 8px; font-size: 11.5px; color: #212529; }
#app-13 .t13-it.actif { background: #EEE8EC; font-weight: 600; box-shadow: inset 2px 0 0 #8E3A6E; }
#app-13 .t13-it b { width: 9px; font-size: 8px; color: #6C757D; font-weight: 400; flex: none; }
#app-13 .t13-it.n1 { padding-left: 26px; }
#app-13 .t13-it .t13-fi svg { width: 12px; height: 12px; display: block; }
#app-13 .t13-it .ell { flex: 1; }
#app-13 .t13-it i { font-style: normal; color: #6C757D; font-size: 10px; }
#app-13 .t13-main { position: absolute; left: 176px; right: 0; top: 44px; bottom: 0; padding: 10px 12px; overflow: hidden; }
#app-13 .t13-fil { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
#app-13 .t13-bc { font-size: 15px; } #app-13 .t13-bc b { font-weight: 500; }
#app-13 .t13-nb { font-size: 11px; color: #6C757D; } #app-13 .t13-eff { font-size: 11px; color: #528099; }
#app-13 .t13-ts { margin-left: auto; font-size: 11px; color: #528099; }
#app-13 .t13-grille { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
#app-13 .t13-carte { background: #fff; border: 1px solid #DEE2E6; border-radius: 6px; overflow: hidden; }
#app-13 .t13-carte.sel { box-shadow: 0 0 0 2px #8E3A6E; }
#app-13 .t13-carte.survol { box-shadow: 0 4px 12px rgba(0,0,0,.12); }
#app-13 .t13-vign { height: 88px; background: #F1F2F4; display: flex; align-items: center; justify-content: center; position: relative; }
#app-13 .t13-vign svg { width: 40px; height: 40px; }
#app-13 .t13-chk { position: absolute; right: 7px; top: 7px; width: 15px; height: 15px; border-radius: 50%; border: 1px solid #ADB5BD; background: #fff; }
#app-13 .t13-chk.on { background: #8E3A6E; border-color: #8E3A6E; box-shadow: inset 0 0 0 3px #fff; }
#app-13 .t13-cc { padding: 7px 9px 8px; }
#app-13 .t13-ct { font-size: 12px; font-weight: 600; }
#app-13 .t13-cs { font-size: 10.5px; color: #6C757D; margin-top: 2px; }
#app-13 .t13-tags { min-height: 16px; margin-top: 3px; display: flex; gap: 4px; }
#app-13 .t13-tag { font-size: 9.5px; padding: 1px 6px; border-radius: 8px; }
#app-13 .t13-tag.r { background: #FBE4E6; color: #B02A37; } #app-13 .t13-tag.j { background: #FFF3CD; color: #8A6400; }
#app-13 .t13-tag.b { background: #E7E9ED; color: #343A40; }
#app-13 .t13-cp { display: flex; justify-content: space-between; align-items: center; font-size: 10.5px; color: #6C757D; margin-top: 3px; }
#app-13 .t13-st { font-size: 9.5px; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
#app-13 .t13-st.gris { background: #E7E9ED; color: #212529; } #app-13 .t13-st.vert { background: #28A745; color: #fff; }
#app-13 .t13-st.noir { background: #212529; color: #fff; }
#app-13 .t13-main.insp { right: 250px; } #app-13 .t13-main.insp .t13-grille { grid-template-columns: repeat(2, 1fr); }
#app-13 .t13-insp { position: absolute; right: 0; top: 44px; bottom: 0; width: 250px; background: #fff; border-left: 1px solid #DEE2E6; padding: 12px; }
#app-13 .t13-iv { height: 92px; background: #F1F2F4; border-radius: 6px; display: flex; align-items: center; justify-content: center; }
#app-13 .t13-iv svg { width: 42px; height: 42px; }
#app-13 .t13-it1 { font-size: 13.5px; font-weight: 600; margin-top: 10px; line-height: 1.3; }
#app-13 .t13-is { font-size: 11px; color: #6C757D; margin: 3px 0 8px; }
#app-13 .t13-ib { display: flex; flex-wrap: wrap; gap: 4px; }
#app-13 .t13-ib .bt { height: 23px; font-size: 11px; padding: 0 7px; }
#app-13 .t13-corb { border: 1px solid #DC3545; color: #DC3545; background: #fff; }
#app-13 .t13-dl { margin: 12px 0 0; font-size: 11px; }
#app-13 .t13-dl dt { color: #6C757D; margin-top: 6px; } #app-13 .t13-dl dd { margin: 1px 0 0; } #app-13 .t13-dl em { font-style: normal; color: #6C757D; }
#app-4 .t13-zone { position: absolute; pointer-events: none; right: 92px; top: 84px; width: 216px; height: 260px; }
"""

TUTO = {
    'slug': 'tuto-13-explorateur-et-document-ecm',
    'titre_page': 'AITE ECM — Tutoriel 13 : explorateur et document ECM',
    'titre': 'Explorateur et document ECM',
    'serie': dict(ECM, numero=13),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Où est la *dernière* version de ce *document ?*',
        'sous': 'Dossiers partagés, pièces jointes, clés USB.',
        'personnage': (ARCHI[0], 'Archiviste', ARCHI[2]),
        'chaos': [('dossier', 'Dossier « Divers »'), ('doc', 'procedure_v3_final.docx'), ('bulle', "C'est laquelle, la bonne ?"),
                  ('note', 'Classé où ?'), ('lettre', 'Pièce jointe perdue'), ('alerte', 'Version écrasée'),
                  ('bulle', 'Sur ma clé USB'), ('doc', 'procedure_v4.docx')],
        'voix': "Une procédure existe en trois exemplaires, sur trois postes. Laquelle fait foi, et qui a le droit de "
                "la lire ?",
    },
    'revelation': {'voix': "Avec Aïte E C M, chaque document a sa place, sa référence et toutes ses versions."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Un fonds *classé,* typé, versionné',
        'pastilles': ["Un explorateur de documents", 'Un plan de classement', 'Des versions numérotées'],
        'voix': "Un explorateur pour parcourir le fonds, un plan de classement avec ses droits, et des versions numérotées.",
    },
    'ecran': ecran_explorateur() + ECRAN4, 'vue_initiale': 't13-tous',
    'etapes': [
        {'titre': "L'Explorateur ECM",
         'texte': "Documents › Explorateur : l'arborescence à gauche, les documents en cartes, le détail à droite.",
         'voix': "Jules, l'archiviste, ouvre l'Explorateur. À gauche, l'arborescence du plan de classement ; en haut, de quoi "
                 "charger des fichiers, numériser, créer un document ou un dossier. Il ouvre Qualité et procédures, et "
                 "sélectionne une procédure : ses informations s'affichent, avec ses actions, dont Partager.",
         'gestes': [curseur('#t13a-f2', fx=0.6, d=0.6, decale=0.3), bulle('#t13a-f2', 'Le plan de classement', cote='droite', d=2.0),
                    zoom('#t13a-g', s=1.45, fx=0.4, fy=0.22, d=0.8),
                    bulle('#t13a-num', 'Charger, numériser, créer', cote='dessous', d=2.2), dezoom(d=0.6),
                    survol('#t13a-f14', decale=0.2), clic('#t13a-f14', fx=0.4), aller('t13-qual'),
                    survol('#t13b-c0', decale=0.3), clic('#t13b-c0', fx=0.5, fy=0.3), classe('#t13b-c0', ajouter=['sel'], retirer=['survol'], avec=True),
                    classe('#t13b-c0-chk', ajouter=['on'], avec=True), classe('#t13b-main', ajouter=['insp'], avec=True),
                    montrer('#t13-insp', y=0, d=0.35),
                    montrer('#t13b-part', y=0, d=0.3, avec=True),
                    zoom('#t13-ib', s=1.5, fx=0.7, fy=0.45, d=0.8),
                    bulle('#t13-ib', 'Fiche, aperçu, partage…', cote='gauche', d=2.2), dezoom(d=0.6)]},
        etape(CH, 1, 'Liste et plan de classement',
              "La liste des documents, puis le plan de classement et ses droits de lecture effectifs.",
              "La liste des documents donne la même vue en colonnes : référence, type, dossier, statut. Le plan de classement, "
              "lui, montre les droits effectifs : le contentieux est réservé aux managers, et un sous-dossier sans règle propre "
              "hérite des droits de son parent.",
              avant=[montrer('#app-4', y=0, d=0.4), texte('#pr-url', ADRESSE % 'ecm'), anneau('#c4-l4', d=1.4, decale=0.3)],
              inserer={2: [zoom('#c4-le4', s=1.2, fx=0.62, fy=0.42, d=0.8)]},
              apres=[bulle('#c4-le4', 'Réservé aux managers', cote='gauche', d=2.2), dezoom(d=0.6)]),
        etape(CH, 2, 'Créer un document', "Titre, type et dossier de classement ; l'enregistrement attribue la référence.",
              "Pour créer un document, Jules saisit un titre, choisit le type, Procédure ou instruction, puis le dossier de "
              "classement. À l'enregistrement, la référence est attribuée automatiquement, et le document entre dans le "
              "fonds, en brouillon. Six types de documents et sept dossiers sont livrés, prêts à l'emploi.",
              apres=[bulle('#c4-ref', 'Référence attribuée', cote='droite', fx=0.55, d=2.0)]),
        etape(CH, 3, 'Déposer une version', "Chaque dépôt crée une version numérotée ; jusqu'à 100 Mo par fichier.",
              "Il dépose ensuite le fichier, avec un commentaire, puis clique sur Ajouter la version. Chaque dépôt crée une "
              "version numérotée, jusqu'à cent mégaoctets par fichier. Brouillon, Finalisé, Archivé : une fois finalisé, le "
              "document est verrouillé.",
              inserer={0: [zoom('#c4-ajout', s=1.35, fx=0.3, fy=0.35, d=0.7)]},
              apres=[bulle('#c4-ver1', 'Version v1 déposée', cote='droite', fx=0.6, d=1.8), dezoom(d=0.6),
                     anneau('#c4-sb', d=1.6)]),
    ],
    'benefices': {
        'titre': 'Chaque document à *sa* *place.*',
        'voix': "Un explorateur pour tout retrouver, un plan de classement qui porte les droits, et des versions qui ne "
                "s'écrasent plus jamais.",
        'cartes': [('cible', '7 dossiers', 'Un plan livré', "Sept dossiers et six types de documents, prêts à l'emploi."),
                   ('cadenas', 'Droits hérités', 'La bonne lecture', "Un sous-dossier sans règle propre hérite des droits de son parent."),
                   ('doc', 'DOC-2026-00360', 'Tout est versionné', "Une référence unique, des versions numérotées, jusqu'à 100 Mo.")],
    },
    'cta': cta('ecm', 'Vos documents, enfin *à* *leur* *place.*', "Aïte E C M : vos documents, enfin à leur place."),
    'youtube': youtube("COMMENT CLASSER ET VERSIONNER SES DOCUMENTS AVEC L'EXPLORATEUR AITE ECM (ODOO 18)",
                       "L'Explorateur ECM, le plan de classement et ses droits effectifs, la création d'un document avec sa "
                       "référence, et le dépôt de versions numérotées. Tutoriel AITE ECM, la gestion documentaire d'AITE "
                       "Consulting pour Odoo 18.",
                       ['AITE ECM', 'explorateur de documents', 'plan de classement', 'versions', 'GED Odoo']),
    'css': CSS,
}
