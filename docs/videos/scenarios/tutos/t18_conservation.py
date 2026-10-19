# -*- coding: utf-8 -*-
"""Tutoriel 18 — Conservation et gels juridiques.

Sources (addons/aite_ecm_records) :
- data/aite_ecm_records_data.xml : les cinq règles livrées (OHADA-10
  « Pièces comptables — 10 ans (OHADA) » 10 années, Finalisation,
  Élimination, base légale « Acte uniforme OHADA relatif au droit
  comptable… » ; CONTRAT-10 ; RH-5 ; PV-PERM ; PROC-3) ;
- models/aite_ecm_retention.py:24-35 (points de départ et sorts finaux),
  :46-83 (champs de la règle : « Priorité », « Libellé », « Code », « Base
  légale », « Types de documents », « Dossiers de classement », « Niveaux de
  confidentialité », « Durée », « Unité », « Point de départ », « Sort
  final »), :136-142 action_apply_now (notification « Conservation » —
  « %d document(s) réévalué(s). »), :145-223 gel juridique (états
  « Brouillon » / « Actif » / « Levé », « Seul un manager peut poser un
  gel. », message « Gel posé sur %d document(s). », levée : motif
  obligatoire) ;
- models/aite_ecm_document.py:14-21 (« Cycle de vie archivistique » :
  « Échue — sort final à appliquer », « Archive intermédiaire »…), :153-195
  (précision « Échue le %s — sort final : %s », gel → archive
  intermédiaire, « Gel juridique : %s »), :251-278 (« Conserver
  définitivement », « Prolonger d'un an » : affichés sur la fiche, mais non
  démontrés — le recalcul quotidien (:214-218, cron) et « Recalculer tout le
  fonds » repartent de la règle et réécrivent échéance et cycle : la vidéo
  ne promet donc pas que ces décisions durent), :325-360 (écriture, corbeille et suppression
  refusées sous gel : « Gel juridique actif (%s) : impossible de mettre
  « %s » à la corbeille. ») ;
- views/aite_ecm_retention_views.xml (liste, fiche, encadré « La règle
  applicable… », bouton « Recalculer tout le fonds ») ;
  views/aite_ecm_document_views.xml (bandeau « Durée de conservation
  échue (…) — sort final : … », bandeau « Gel juridique actif — … Ce
  document ne peut être ni modifié, ni mis à la corbeille, ni détruit. »,
  onglet « Conservation », groupes « Politique appliquée » et « Conservation
  physique et données », action « Documents échus » groupée par « Règle de
  conservation ») ; views/aite_ecm_legal_hold_views.xml (« Poser le gel »
  et sa confirmation, « Lever le gel », « Documents gelés », « Référence du
  dossier (litige, audit) », « À la demande de », « Responsable », « Posé
  le », « Motif », « Motif de la levée », onglet « Périmètre », « Dossiers
  gelés ») ; views/aite_ecm_records_menus.xml (menu « Conservation » ;
  « Règles de conservation » sous Configuration) ;
- data/ir_cron_data.xml (« AITE ECM : politique de conservation »,
  quotidienne) ;
- aite_ecm_document/views/aite_ecm_document_views.xml:25-27 (« Corbeille »
  et sa confirmation) ; aite_ecm_document/views/aite_ecm_menus.xml:26-28
  (Configuration réservée aux managers et administrateurs : c'est donc le
  manager qui ouvre les règles).
Titres de boîtes « Confirmation » et « Opération invalide », bouton « Envoyer message » du
fil de discussion : Odoo 18.
Modèle visuel : base demo18 (MuK), captures t18_*.
"""

import demo
from ecrans import (ICONES, assistant, bande, bandeau, bouton, bouton_stat, c_html, c_lien, c_puce, case, champ, chatter, e,
                    fenetre, feuille, grille2, liste, message, onglets, panneau_fiche, panneau_lateral, panneau_liste, puce,
                    sec_titre, statusbar, table, v, vue)
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import anneau, cacher, classe, clic, curseur, etat, fermer, montrer, ouvrir, pause, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ARCHI, MANAGER = P['archiviste'], P['manager']
MENUS = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse']
MENUS_CONFIG = MENUS + ['Configuration']
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'

# Les règles livrées (aite_ecm_records_data.xml), dans l'ordre de priorité.
REGLES = [('OHADA-10', 'Pièces comptables — 10 ans (OHADA)', '10', 'Finalisation', 'Élimination', 'rouge'),
          ('CONTRAT-10', 'Contrats — 10 ans après la fin du contrat', '10', 'Date portée par une métadonnée', 'Revue avant décision', 'gris'),
          ('RH-5', 'Dossiers du personnel — 5 ans après le départ', '5', 'Archivage', 'Revue avant décision', 'gris'),
          ('PV-PERM', 'Procès-verbaux et actes de gouvernance — définitif', '1', 'Finalisation', 'Conservation définitive', 'vert'),
          ('PROC-3', 'Procédures — 3 ans après remplacement', '3', 'Archivage', 'Revue avant décision', 'gris')]

# La facture échue (fictive) : finalisée le 21/10/2015, échue le 21/10/2025.
FACT = {'reference': 'DOC-2015-00412', 'titre': 'Facture F-2015-0412 — %s' % demo.FOURNISSEUR, 'depart': '21/10/2015',
        'echeance': '21/10/2025', 'iso': '2025-10-21',
        'fichier': 'Facture_F-2015-0412.pdf', 'boite': 'Factures fournisseurs 2015'}
FACT2 = {'reference': 'DOC-2014-00931', 'titre': 'Facture F-2014-0931 — %s' % demo.FOURNISSEUR, 'echeance': '03/06/2024'}
GEL = {'nom': 'Contrôle fiscal 2026', 'ref': 'CF-2026-07', 'demande': 'Direction financière', 'date': '13/10/2026',
       'motif': 'Vérification de comptabilité annoncée sur les exercices 2023 à 2025.', 'docs': '38'}

POIGNEE = '<span class="t18-poi">⋮⋮</span>'


def tags(*noms):
    return '<span class="t18-tags">%s</span>' % ''.join('<span class="t18-tag">%s</span>' % e(n) for n in noms)


def menu_deroulant(ident, items):
    """Le menu déroulant d'Odoo sous un menu de la barre du haut."""
    return '<div class="t18-dd masque" id="%s"%s>%s</div>' % (ident, ZONE, ''.join(
        '<div class="it" id="%s-%d">%s</div>' % (ident, i, e(m)) for i, m in enumerate(items)))


def poser_menu(html, app, n, dd):
    """Accroche un menu déroulant sous le menu n° ``n`` de la fenêtre ``app``."""
    ancre = '<span class="menu" id="%s-m%d">' % (app, n)
    debut = html.index(ancre)
    fin = html.index('</span>', debut)
    return (html[:debut] + '<span class="menu t18-menu" id="%s-m%d">' % (app, n) + html[debut + len(ancre):fin] + dd
            + html[fin:])


def masquer_app(html, ident):
    return html.replace('<div class="o-app muk" id="%s">' % ident, '<div class="o-app muk masque" id="%s">' % ident, 1)


def notification(ident, titre, texte_html):
    return ('<div class="t18-notif masque" id="%s"%s><b>%s</b><span>%s</span><i>×</i></div>'
            % (ident, ZONE, e(titre), texte_html))


def boite(ident, titre, texte_html, boutons, haut=250, largeur=560):
    return assistant(ident, titre, '<div class="t18-msg">%s</div>' % texte_html, boutons, haut=haut, largeur=largeur)


# ---------------------------------------------------------- le manager --
def ecran_manager():
    lignes = [{'id': 't18-r%d' % i, 'cellules': [c_html(POIGNEE), c, l, c_html('<span class="num">%s</span>' % d), 'années', p,
                                                c_puce(s, g, 't18-sf%d' % i)]}
              for i, (c, l, d, p, s, g) in enumerate(REGLES)]
    regles = vue('t18-regles', panneau_liste('Règles de conservation', '1-5 / 5', ident='t18r')
                 + liste([('', '14px'), ('Code', '96px'), ('Libellé', '1fr'), ('Durée', '46px'), ('Unité', '56px'),
                          ('Point de départ', '196px'), ('Sort final', '150px')], lignes, ident='t18-lst')
                 + '<div class="t18-zone" id="t18-sorts"%s></div>' % ZONE, initiale=True)
    gauche = [sec_titre('Périmètre'), champ('Code', v('OHADA-10')), champ('Priorité', v('10'), aide=True),
              champ('Types de documents', tags('Facture fournisseur')),
              champ('Dossiers de classement', tags('Finance et comptabilité'), aide=True),
              champ('Niveaux de confidentialité', '')]
    droite = ['<div id="t18-duree">', sec_titre('Durée et sort final'),
              champ('Durée', '<span class="t18-dv">10</span><span class="t18-du">années</span>', 't18-d1'),
              champ('Point de départ', v('Finalisation'), 't18-d2'), champ('Sort final', v('Élimination'), 't18-d3'), '</div>']
    corps = ('<div class="titre-doc t18-h1">Pièces comptables — 10 ans (OHADA)</div>' + grille2(gauche, droite)
             + sec_titre('Base légale')
             + '<div class="t18-texte" id="t18-base">Acte uniforme OHADA relatif au droit comptable : conservation des pièces '
               'justificatives pendant 10 ans.</div>'
             + sec_titre('Commentaire') + '<div class="t18-texte t18-vide"></div>'
             + '<div class="bandeau t18-info">La règle applicable à un document est la <b>première</b> (par priorité) dont le '
               'périmètre correspond. L\'échéance se calcule à partir du point de départ ; le recalcul est quotidien, ou '
               'immédiat avec le bouton ci-dessous.</div>'
             + bouton('t18-recalc', 'Recalculer tout le fonds', 'second'))
    regle = vue('t18-regle', panneau_fiche('Règles de conservation', 'Pièces comptables — 10 ans (OHADA)', '1 / 5',
                                           boutons_stat=bouton_stat('Documents', '12'))
                + '<div class="o-corps"><div class="o-gauche t18-sans-bande">%s</div></div>' % feuille(corps)
                + notification('t18-toast', 'Conservation', '257 document(s) réévalué(s).'))
    # le gel juridique, en brouillon puis actif
    perim = ('<div class="champ t18-perim-d" id="t18-dossiers"><span class="l">Dossiers gelés<sup>?</sup></span><span class="v">%s</span></div>'
             % tags('Finance et comptabilité')
             + table([('Référence', '110px'), ('Titre', '1fr'), ('Dossier de classement', '170px'), ('Cycle de vie archivistique', '150px')],
                     [{'id': 't18-p0', 'cellules': ['DOC-2026-00341', 'Contrat de maintenance — climatisation',
                                                    'Juridique et contrats', 'Utilité courante']}], identifiant='t18-perim'))
    gel_corps = ('<div class="titre-doc t18-h1">%s</div>' % GEL['nom']
                 + grille2([champ('Référence du dossier (litige, audit)', v(GEL['ref'])), champ('À la demande de', v(GEL['demande'])),
                            champ('Responsable', v(MANAGER[0]))],
                           [champ('Posé le', v('', identifiant='t18-pose'), 't18-pose-c')])
                 + sec_titre('Motif') + '<div class="t18-texte" id="t18-motif">%s</div>' % e(GEL['motif'])
                 + '<div class="masque" id="t18-levee">%s<div class="t18-texte t18-vide"></div></div>' % sec_titre('Motif de la levée')
                 + onglets(['Périmètre']) + perim)
    ch = chatter([message(MANAGER[0], MANAGER[2], 'Gel posé sur %s document(s).' % GEL['docs'], '10:42', 't18-gmsg', masque=True)],
                 identifiant='t18-gch', suivre='Suivre').replace('Envoyer un message', 'Envoyer message', 1)
    gel = vue('t18-gel', panneau_fiche('Gels juridiques', GEL['nom'], '1 / 1',
                                       boutons_stat=bouton_stat('Documents gelés', GEL['docs'], 'cadenas'))
              + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                  bande([bouton('t18-poser', 'Poser le gel', 'prim')], statusbar(['Brouillon', 'Actif', 'Levé'], 0, 't18-gsb'),
                        't18-gb', [bouton('t18-lever', 'Lever le gel', 'orange')]),
                  feuille(gel_corps), ch))
    conf = boite('t18-gconf', 'Confirmation', 'Les documents visés deviendront non modifiables et non destructibles. Confirmer ?',
                 [('t18-gok', 'Ok', 'prim'), ('t18-gnon', 'Annuler', 'second')])
    dd = menu_deroulant('t18-ddc', ['Types de documents', 'Étiquettes', 'Types de relations', 'Types de dossiers',
                                    'Règles de conservation'])
    html = fenetre('ECM', MENUS_CONFIG, [regles, regle, gel], MANAGER[1], MANAGER[2], calques=conf, ident='app-18m')
    return poser_menu(html, 'app-18m', 6, dd)


# ------------------------------------------------------- l'archiviste --
COL_DOCS = [('Référence', '112px'), ('Titre', '1fr'), ('Type', '120px'), ('Dossier de classement', '150px'),
            ('Propriétaire', '104px'), ('Vers.', '36px'), ('Statut', '70px')]


def onglet_conservation(prefixe, regle_cycle, precision, echeance, gel=''):
    gauche = [sec_titre('Politique appliquée'),
              champ('Règle de conservation', v('Pièces comptables — 10 ans (OHADA)', True), aide=True),
              champ('Règle imposée', '', aide=True),
              champ('Départ de la conservation', v(FACT['depart'])),
              champ('Échéance de conservation', v(echeance, identifiant=prefixe + '-ech'), prefixe + '-ech-c'),
              champ('Sort final', v('Élimination')),
              champ('Cycle de vie archivistique', puce(regle_cycle[0], regle_cycle[1], prefixe + '-cycle'), prefixe + '-cycle-c'),
              champ('Précision', v(precision, identifiant=prefixe + '-prec'), prefixe + '-prec-c')]
    droite = [sec_titre('Conservation physique et données'),
              champ("Boîte d'archives physique", v(FACT['boite'])),
              champ('Original papier conservé', case(True), aide=True),
              champ('Contient des données personnelles', case(False), aide=True),
              champ('Gels juridiques', gel)]
    return ('<div class="t18-cons" id="%s-cons">%s</div>' % (prefixe, grille2(gauche, droite))
            + '<div class="t18-bts">%s%s</div>' % (
                bouton(prefixe + '-garder', 'Conserver définitivement', 'second', 'sceau'),
                bouton(prefixe + '-prol', "Prolonger d'un an", 'second', 'horloge')))


def fiche_facture(ident, bandeau_html, cons, bt_prefixe):
    corps = (bandeau_html
             + '<div class="ref-l">Référence</div><div class="ref-v moyen">%s</div><div class="titre-doc t18-h2">%s</div>'
               % (FACT['reference'], e(FACT['titre']))
             + grille2([champ('Type', v('Facture fournisseur')), champ('Dossier de classement', v('Finance et comptabilité'))],
                       [champ('Propriétaire', v(P['compta'][0])), champ('Fichier', v(FACT['fichier']))])
             + onglets(['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Description'], 3)
             + cons)
    bts = [bouton(bt_prefixe + '-arch', 'Archiver', 'second'), bouton(bt_prefixe + '-prev', 'Prévisualiser', 'second', 'oeil'),
           bouton(bt_prefixe + '-corb', 'Corbeille', 'second', 'corbeille'), bouton(bt_prefixe + '-part', 'Partager', 'second')]
    return vue(ident, panneau_fiche('Documents', FACT['titre'], '1 / 2', boutons_stat=bouton_stat('Sceaux', '3', 'sceau'))
               + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                   bande(bts, statusbar(['Brouillon', 'Finalisé', 'Archivé'], 1, bt_prefixe + '-sb'), bt_prefixe + '-b'),
                   feuille(corps, identifiant=ident + '-f')))


def ecran_archiviste():
    lat = panneau_lateral([('▤ TYPES', [('Contrat', '', False), ('Pièce de courrier', '', False), ('Procédure / instruction', '', False),
                                        ('Facture fournisseur', '2', False), ('Pièce du dossier du personnel', '', False),
                                        ('Procès-verbal / compte rendu', '', False), ('Document générique', '', False)])])
    lignes = [{'id': 't18-e0', 'cellules': [FACT['reference'], FACT['titre'], 'Facture fournisseur', 'Finance et comptabilité',
                                           P['compta'][0], c_html('<span class="num">1</span>'), c_puce('Finalisé', 'vclair')]},
              {'id': 't18-e1', 'cellules': [FACT2['reference'], FACT2['titre'], 'Facture fournisseur', 'Finance et comptabilité',
                                           P['compta'][0], c_html('<span class="num">1</span>'), c_puce('Finalisé', 'vclair')]}]
    lst = liste(COL_DOCS, lignes, groupes={0: 'Pièces comptables — 10 ans (OHADA) (2)'}, ident='t18-elst').replace('▸ ', '▾ ', 1)
    cp = panneau_liste('Documents échus', '1-1 / 1', facettes=[('≡', 'Règle de conservation')], ident='t18e')
    echus = vue('t18-echus', cp + lat + lst, initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    rouge = ('<div class="bandeau t18-rouge" id="t18-bechu">⌛ Durée de conservation échue (%s) — sort final : Élimination.</div>'
             % FACT['echeance'])
    doc = fiche_facture('t18-doc', rouge, onglet_conservation(
        't18-c', ('Échue — sort final à appliquer', 'rouge'),
        'Échue le %s — sort final : Élimination' % FACT['iso'], FACT['echeance']), 't18-d')
    jaune = bandeau('<span class="t18-marteau">%s</span><b>Gel juridique actif</b> — %s. Ce document ne peut être ni modifié, '
                    'ni mis à la corbeille, ni détruit.' % (ICONES['marteau'], e(GEL['nom'])), 'jaune', 't18-bgel')
    doc2 = fiche_facture('t18-doc2', jaune, onglet_conservation(
        't18-g', ('Archive intermédiaire', 'info'), 'Gel juridique : %s' % GEL['nom'], FACT['echeance']), 't18-h')
    conf = boite('t18-conf', 'Confirmation', 'Mettre ce document à la corbeille ? Il pourra être restauré avant purge automatique.',
                 [('t18-ok', 'Ok', 'prim'), ('t18-non', 'Annuler', 'second')])
    err = boite('t18-err', 'Opération invalide',
                'Gel juridique actif (%s) : impossible de mettre « %s » à la corbeille.' % (e(GEL['nom']), e(FACT['titre'])),
                [('t18-fermer', 'Fermer', 'prim')], haut=230, largeur=760)
    dd = menu_deroulant('t18-ddk', ['Documents échus', "Bordereaux d'élimination", 'Gels juridiques', 'Archives physiques'])
    html = fenetre('ECM', MENUS, [echus, doc, doc2], ARCHI[1], ARCHI[2], calques=conf + err, ident='app-18a')
    return masquer_app(poser_menu(html, 'app-18a', 3, dd), 'app-18a')


CSS = """
#app-18m .t18-menu, #app-18a .t18-menu { position: relative; }
#app-18m .t18-dd, #app-18a .t18-dd { position: absolute; left: -12px; top: 28px; z-index: 30; width: 200px; padding: 6px 0;
  background: #fff; border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 18px rgba(0,0,0,.16); color: #212529; }
#app-18m .t18-dd .it, #app-18a .t18-dd .it { padding: 4px 14px; font-size: 12.5px; white-space: nowrap; }
#app-18m .t18-dd .it.survol, #app-18a .t18-dd .it.survol { background: #EEF3F6; }
#app-18m .t18-poi { color: #ADB5BD; font-size: 11px; letter-spacing: -2px; }
#app-18m .t18-zone { position: absolute; pointer-events: none; }
#t18-sorts { right: 14px; top: 84px; width: 166px; height: 182px; }
#app-18m .t18-sans-bande { padding-top: 10px; }
#app-18m .t18-h1, #app-18a .t18-h1 { font-size: 22px; margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px solid #DEE2E6; width: 64%; }
#app-18a .t18-h2 { font-size: 20px; margin: 0 0 8px; }
#app-18m .t18-tags, #app-18a .t18-tags { display: inline-flex; gap: 4px; }
#app-18m .t18-tag, #app-18a .t18-tag { display: inline-block; padding: 1px 8px; border-radius: 9px; background: #E9ECEF; color: #343A40;
  font-size: 10.5px; line-height: 16px; white-space: nowrap; }
#app-18m .t18-dv { display: inline-block; width: 64px; } #app-18m .t18-du { color: #212529; }
#app-18m .t18-texte { font-size: 12.5px; padding: 2px 4px 6px; }
#app-18m .t18-vide { height: 22px; }
#app-18m .t18-info { background: #D7EEF3; color: #1F2D3D; margin: 10px 0 10px; line-height: 1.45; }
#app-18m .champ { grid-template-columns: 150px 1fr; }
#app-18m .t18-perim-d { margin-top: 8px; }
#t18-toast { position: absolute; right: 12px; top: 8px; width: 290px; z-index: 40; background: #fff; border-left: 4px solid #28A745;
  border-radius: 4px; box-shadow: 0 8px 22px rgba(0,0,0,.2); padding: 10px 30px 10px 14px; font-size: 12.5px; }
#t18-toast b { display: block; font-size: 13.5px; font-weight: 600; margin-bottom: 4px; }
#t18-toast i { position: absolute; right: 10px; top: 8px; font-style: normal; color: #6C757D; font-size: 16px; }
#app-18a .t18-rouge { background: #F8D7DA; color: #58151C; }
#app-18a .bandeau.jaune .t18-marteau svg { width: 12px; height: 12px; display: inline-block; vertical-align: -1px; margin-right: 4px; }
#app-18a .champ { grid-template-columns: 158px 1fr; min-height: 22px; padding: 2px 0; }
#app-18a .t18-cons .sec-t { margin-top: 10px; }
#app-18a .t18-bts { display: flex; gap: 8px; margin-top: 8px; }
#app-18a .t18-bts .bt .ic svg, #app-18m .bt .ic svg { width: 12px; height: 12px; }
#app-18a .t18-bts .bt .ic svg path, #app-18a .t18-bts .bt .ic svg circle { stroke: #343A40; }
#app-18a .t18-bts .bt .ic svg[fill="#5B4C93"] { fill: #343A40; }
#app-18m .o-chatter .ch-bts .bt { padding-left: 6px; padding-right: 6px; }
#app-18m .o-chatter .ch-bts .suivre { display: none; }
#app-18a .t18-msg, #app-18m .t18-msg { font-size: 13px; line-height: 1.5; }
"""

TUTO = {
    'slug': 'tuto-18-conservation-et-gels-juridiques',
    'titre_page': 'AITE ECM — Tutoriel 18 : conservation et gels juridiques',
    'titre': 'Conservation et gels juridiques',
    'serie': dict(ECM, numero=18),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Ce document, on le *garde* ou on le *détruit ?*',
        'sous': "Durées oubliées, archives qui débordent, une pièce détruite en plein contrôle : la conservation ne s'improvise pas.",
        'personnage': (ARCHI[0], 'Archiviste', ARCHI[2]),
        'chaos': [('dossier', 'Archives 2014 ?'), ('bulle', 'On peut jeter ça ?'), ('alerte', 'Contrôle fiscal'),
                  ('note', 'Durée : 5 ans ? 10 ?'), ('doc', 'Facture 2015'), ('bulle', "Qui l'a détruit ?"),
                  ('lettre', 'Avis de vérification'), ('alerte', 'Pièce introuvable')],
        'voix': "Les archives débordent. Faut-il garder cette facture de 2015, ou la détruire ? Et si un contrôle fiscal "
                "s'annonce, comment être sûr que rien ne disparaît ?",
    },
    'revelation': {'voix': "Avec Aïte E C M, chaque document suit sa règle de conservation, et le gel juridique le protège."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Garder ce qu\'il faut, *aussi longtemps* qu\'il faut',
        'pastilles': ['Cinq règles livrées', 'Échéances calculées', 'Gel juridique'],
        'voix': "Une durée, un point de départ et un sort final pour chaque document ; les échéances se calculent seules, et "
                "un gel juridique suspend tout le temps d'un litige. Voyons comment.",
    },
    'ecran': ecran_manager() + ecran_archiviste(), 'vue_initiale': 't18-regles',
    'css': CSS,
    'etapes': [
        {'titre': 'Des règles de conservation',
         'texte': "Une durée, un point de départ, un sort final : élimination, revue avant décision ou conservation définitive.",
         'voix': "Paul, le manager, ouvre les règles de conservation : cinq sont livrées. Celle des pièces comptables : "
                 "dix ans à compter de la finalisation, puis l'élimination, selon l'Acte uniforme OHADA. Le recalcul est "
                 "quotidien, ou immédiat avec Recalculer tout le fonds.",
         'gestes': [anneau('#app-18m-m6', d=1.0, decale=0.2), anneau('#t18-lst', d=1.4),
                    bulle('#t18-sorts', 'Trois sorts finaux', cote='dessous', d=2.2, avec=True),
                    survol('#t18-r0', decale=1.0), clic('#t18-r0', fx=0.3), aller('t18-regle'),
                    zoom('#t18-duree', s=1.55, fx=0.6, fy=0.4, d=0.8),
                    anneau('#t18-d1', d=1.0), bulle('#t18-d3', 'Puis l\'élimination', cote='dessous', fx=0.3, d=2.0, avec=True),
                    dezoom(d=0.7), clic('#t18-recalc'), montrer('#t18-toast', y=-10, d=0.3), anneau('#t18-toast', d=1.4),
                    cacher('#t18-toast', d=0.3, decale=0.4)]},
        {'titre': "Les documents échus, repérés",
         'texte': "Conservation › Documents échus, groupés par règle ; sur la fiche : règle, départ, échéance, sort final.",
         'voix': "Jules, l'archiviste, ouvre les documents échus, regroupés par règle. Cette facture a dépassé ses dix "
                 "ans : un bandeau rouge annonce son sort final, l'élimination. L'onglet Conservation détaille la règle, "
                 "le départ et l'échéance : rien n'est laissé au hasard.",
         'gestes': [montrer('#app-18a', y=0, d=0.4), anneau('#app-18a-m3', d=1.0, decale=0.2),
                    anneau('#t18-elst .groupe', d=1.2), survol('#t18-e0'), clic('#t18-e0', fx=0.3), aller('t18-doc'),
                    anneau('#t18-bechu', d=1.4), curseur('#t18-c-prec', avec=True), zoom('#t18-c-cycle-c', s=1.45, fx=0.4, fy=0.5, d=0.8),
                    anneau('#t18-c-cycle', d=1.2), bulle('#t18-c-cycle', 'Échue', cote='droite', d=1.6, avec=True),
                    anneau('#t18-c-ech', d=1.2, decale=0.2),
                    bulle('#t18-c-ech', 'Départ + 10 ans', cote='droite', d=2.0, avec=True), dezoom(d=0.7)]},
        {'titre': 'Le gel juridique',
         'texte': "Un contrôle, un litige : le manager pose le gel sur un dossier entier ou sur des documents choisis.",
         'voix': "Un contrôle fiscal s'annonce. Paul pose un gel juridique sur tout le dossier Finance et comptabilité, avec "
                 "son motif. Après confirmation, le gel est actif. Seul un manager pourra le lever, et en donnant le motif "
                 "de la levée.",
         'gestes': [cacher('#app-18a', d=0.3), aller('t18-gel', avec=True), anneau('#t18-motif', d=1.0, decale=0.3),
                    anneau('#t18-dossiers', d=1.2), clic('#t18-poser'), ouvrir('t18-gconf'), pause(0.6), clic('#t18-gok'),
                    fermer('t18-gconf'), classe('#t18-gsb-0', retirer=['actif']), classe('#t18-gsb-1', ajouter=['actif'], avec=True),
                    cacher('#t18-gb-a', d=0.2), montrer('#t18-gb-b', y=0, avec=True), texte('#t18-pose', GEL['date'], avec=True),
                    montrer('#t18-levee', y=0, avec=True), montrer('#t18-gmsg', y=10),
                    zoom('#t18-gb', s=1.35, fx=0.5, fy=0.3, d=0.8), anneau('#t18-gsb-1', d=1.0),
                    bulle('#t18-lever', 'Levée motivée', cote='droite', d=2.0, avec=True), dezoom(d=0.7)]},
        {'titre': 'Rien ne bouge sous gel',
         'texte': "Ni modification, ni corbeille, ni élimination : même l'archiviste reçoit un refus.",
         'voix': "Sur la facture, le bandeau jaune l'annonce : gel juridique actif. Le document ne peut plus être modifié, "
                 "ni mis à la corbeille, ni éliminé. Jules essaie : refus immédiat, jusqu'à la levée du gel.",
         'gestes': [montrer('#app-18a', y=0, d=0.4), aller('t18-doc2', avec=True), anneau('#t18-bgel', d=1.6, decale=0.3),
                    clic('#t18-h-corb'), ouvrir('t18-conf'), pause(0.5), clic('#t18-ok'), fermer('t18-conf'),
                    ouvrir('t18-err'), zoom('#t18-err', s=1.3, d=0.8), anneau('#t18-err .t18-msg', d=1.8),
                    dezoom(d=0.7), clic('#t18-fermer'), fermer('t18-err')]},
    ],
    'benefices': {
        'titre': 'Garder, prouver, *éliminer* à temps.',
        'voix': "Les durées sont tenues sans tableau à part, les documents échus remontent d'eux-mêmes, et un gel "
                "juridique protège tout un dossier le temps d'un contrôle.",
        'cartes': [('cible', '5 règles', 'Prêtes à l\'emploi', "Pièces comptables, contrats, personnel, procès-verbaux, procédures."),
                   ('temps', 'Échéances', 'Calculées chaque jour', "Durée, point de départ et sort final, document par document."),
                   ('bouclier', 'Gel juridique', 'Rien ne disparaît', "Ni modification, ni corbeille, ni élimination tant qu'il est actif.")],
    },
    'cta': cta('ecm', 'Vos archives, *sous* *contrôle.*', "Aïte E C M : vos archives, sous contrôle."),
    'youtube': youtube('COMMENT GÉRER LA CONSERVATION ET LES GELS JURIDIQUES AVEC AITE ECM (ODOO 18)',
                       "Règles de conservation (durée, point de départ, sort final), documents échus repérés pour "
                       "l'archiviste et gel juridique qui bloque modification, corbeille et élimination. Tutoriel AITE ECM, "
                       "la gestion documentaire d'AITE Consulting pour Odoo 18.",
                       ['AITE ECM', 'records management', 'durée de conservation', 'gel juridique', 'OHADA']),
}
