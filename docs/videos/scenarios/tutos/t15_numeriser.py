# -*- coding: utf-8 -*-
"""Tutoriel 15 — Numériser ses documents.

Sources :
- aite_ecm_document/static/src/explorer/explorer.xml : barre d'outils
  (« Charger », « Numériser » — titre « Photos (appareil photo sur mobile)
  assemblées en un PDF », « Nouveau document », « Nouveau dossier »,
  « Dépôt en cours… », « Rechercher (titre, référence, fichier, contenu)… »,
  « Plus récents »), panneau « Espace de travail » (« Tous », arborescence,
  « Sans classement »), fil « ECM › … », « N / N document(s) », cartes
  (titre, référence · type, date, statut), inspecteur (« Fiche », « Aperçu »,
  « Télécharger », « Nouvelle version », « Réserver », « Finaliser »,
  « Partager », « Corbeille » ; « Fichier », « Versions », « Type »,
  « Dossier », « Étiquettes », « Confidentialité », « Propriétaire »,
  « Modifié ») ; entrée fichier ``accept="image/*" capture="environment"
  multiple`` ;
- static/src/explorer/explorer.js : ``triggerScan`` / ``onScanPicked`` /
  ``uploadFiles(files, null, true)`` (dossier et type courants de
  l'explorateur envoyés), notification « Numérisation enregistrée : %s » ;
- controllers/explorer.py : ``scan`` → ``_images_to_pdf`` (un PDF multipage),
  document « Numérisation du JJ/MM/AAAA HH:MM » créé dans le dossier courant,
  version ``scan_AAAAMMJJ_HHMMSS.pdf`` (heure UTC), commentaire
  « Numérisation (N page(s)) » ;
- models/aite_ecm_capture.py : ``_cron_hotfolder_import`` (fichier ignoré tant
  qu'il a été modifié depuis moins que le délai ; titre = nom du fichier, « _ »
  et « - » remplacés par des espaces ; dossier, type et propriétaire réglés ;
  version commentée « Dossier de dépôt » ; fichier déplacé dans « traites »,
  ou « erreurs ») ; ``message_new`` (un document par pièce jointe, titre =
  objet du message, commentaire « Reçu par e-mail ») ;
- models/res_config_settings.py et views/res_config_settings_views.xml :
  bloc « Numérisation », réglages « Dossier de dépôt surveillé » (« Répertoire
  de dépôt du scanner », « Dossier ECM de destination », « Type des documents
  scannés », « Propriétaire des documents importés », « Délai avant import
  (s) », 30 par défaut) et « Scan vers e-mail et appareil photo » (« Adresse
  de scan vers e-mail ») ; bloc « Documents » (« Réservation et corbeille ») ;
- data/aite_ecm_capture_data.xml : tâche « AITE ECM : import du dossier de
  dépôt (scanner) » toutes les 5 minutes ; alias ``ecm-scan``, sans valeurs
  par défaut (document sans dossier : « Sans classement ») ;
- docs/produits/AITE_Courrier_fiche_avant_vente_technique.md (trois voies de
  numérisation ; alias ``ecm-scan@`` et serveur entrant à configurer).
Modèle visuel : base demo18 (MuK), explorateur et Paramètres › AITE ECM.
Le domaine d'alias ``aite-demo.test`` est celui de la démonstration (t06).
"""

import demo
from ecrans import bouton, e, entree, fenetre, vue
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import anneau, animer, cacher, classe, clic, curseur, montrer, notifier, pause, saisir, texte, choisir, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
AGENT, ADMIN = P['agent'], P['admin']
MENUS = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse']
JOUR = '13/10/2026'
REF_SCAN = 'DOC-2026-00361'
TITRE_SCAN = 'Numérisation du 13/10/2026 10:42'
FICHIER_SCAN = 'scan_20261013_094212.pdf'      # heure UTC dans le nom du fichier, heure locale dans le titre
ALIAS = 'ecm-scan@aite-demo.test'

CAMERA = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 4h6l1.5 2H20a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 '
          '012-2h3.5zm3 4.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9zm0 2a2.5 2.5 0 110 5 2.5 2.5 0 010-5z"/></svg>')
CHARGER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" '
           'stroke-linejoin="round"><path d="M12 15V4m0 0L7.5 8.5M12 4l4.5 4.5M4 19h16"/></svg>')
DOSSIER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.5 6.5a1.5 1.5 0 011.5-1.5h5l2 2h9a1.5 '
           '1.5 0 011.5 1.5v9.5a1.5 1.5 0 01-1.5 1.5H4a1.5 1.5 0 01-1.5-1.5z"/></svg>')
GRILLE = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/></svg>'
LISTE = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="4" width="18" height="2.6"/><rect x="3" y="10.7" width="18" height="2.6"/><rect x="3" y="17.4" width="18" height="2.6"/></svg>'
LOUPE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5l5 5"/></svg>'

# Cartes : (id, titre, référence, type, étiquette (texte, couleur) ou None, statut, miniature)
CARTES_AGR = [
    ('t15-k0', 'Attestation de non-redevance fiscale — Delta Équipements', 'DOC-2026-00358', 'Document générique',
     ('Fiscal', 'rouge'), 'Brouillon', 'page'),
    ('t15-k1', 'Registre de commerce — Groupe Horizon Services', 'DOC-2026-00356', 'Document générique',
     ('Original papier', 'bleu'), 'Brouillon', 'page'),
    ('t15-k2', "Relevé d'identité bancaire — Delta Équipements", 'DOC-2026-00352', 'Document générique', None, 'Finalisé', 'page'),
    ('t15-k3', 'Plan de localisation — Groupe Horizon Services', 'DOC-2026-00336', 'Document générique',
     ('Immobilier', 'jaune'), 'Brouillon', 'plan'),
]
CARTES_FAC = [
    ('t15-f1', 'Facture F-2026-6133 — télécommunications', 'DOC-2026-00311', 'Facture fournisseur', ('2026', 'jaune'), 'Finalisé', 'page'),
    ('t15-f2', 'Facture F-2026-5980 — fournitures', 'DOC-2026-00271', 'Facture fournisseur', None, 'Archivé', 'page'),
    ('t15-f3', 'Facture DOS-2026-1182 — fournitures', 'DOC-2026-00240', 'Facture fournisseur', None, 'Archivé', 'page'),
]
CARTES_SANS = [
    ('t15-s1', 'Note manuscrite — réunion de chantier', 'DOC-2026-00329', '', None, 'Brouillon', 'page'),
    ('t15-s2', 'Photo du compteur — agence de Bonapriso', 'DOC-2026-00317', '', None, 'Brouillon', 'photo'),
]
NOUVELLE_FAC = ('t15-f0', 'Facture Delta 0412', 'DOC-2026-00362', 'Facture fournisseur', None, 'Brouillon', 'scan')
NOUVEAU_MAIL = ('t15-s0', 'Bon de livraison BL-2231', 'DOC-2026-00363', '', None, 'Brouillon', 'scan')
NOUVEAU_SCAN = ('t15-k9', TITRE_SCAN, REF_SCAN, '', None, 'Brouillon', 'scan')

COL, LIG = 196, 188          # pas de la grille des cartes (largeur + écart, hauteur + écart)


def miniature(genre):
    if genre == 'plan':
        return ('<span class="x-pg"><i class="x-l t"></i><i class="x-plan"></i><i class="x-l c"></i></span>')
    if genre == 'photo':
        return '<span class="x-photo"><i></i></span>'
    if genre == 'scan':
        return ('<span class="x-pg x-scan"><i class="x-l t"></i><i class="x-l"></i><i class="x-l"></i><i class="x-l c"></i>'
                '<i class="x-l"></i><i class="x-l c"></i><i class="x-tampon"></i></span>')
    return ('<span class="x-pg"><i class="x-l t"></i><i class="x-l"></i><i class="x-l"></i><i class="x-l c"></i><i class="x-l"></i>'
            '<i class="x-l"></i><i class="x-l c"></i></span>')


def carte(c, pos, masque=False):
    ident, titre, ref, typ, tag, statut, mini = c
    col, lig = pos % 4, pos // 4
    puce = {'Brouillon': 'gris', 'Finalisé': 'vert', 'Archivé': 'noir'}[statut]
    tags = '<span class="x-tag %s">%s</span>' % (tag[1], e(tag[0])) if tag else ''
    return ('<div class="x-carte%s" id="%s" style="left:%dpx;top:%dpx"><div class="x-mini">%s<span class="x-coche"></span></div>'
            '<div class="x-corps"><div class="x-titre ell">%s</div><div class="x-ref ell">%s%s</div><div class="x-tags">%s</div>'
            '<div class="x-bas"><span>%s</span><span class="x-st %s">%s</span></div></div></div>'
            % (' masque' if masque else '', ident, col * COL, lig * LIG, miniature(mini), e(titre), e(ref),
               (' · ' + e(typ)) if typ else '', tags, JOUR if mini == 'scan' else '10/10/2026', puce, e(statut)))


def barre_outils(p, admin=False):
    return ('<div class="x-tb"><span class="bt prim" id="%s-charger">%sCharger</span>'
            '<span class="bt second" id="%s-num">%sNumériser</span><span class="x-lk">Nouveau document</span>%s'
            '<span class="x-depot masque" id="%s-depot">Dépôt en cours…</span>'
            '<span class="x-droite"><span class="x-rech"><span class="x-lp">%s</span><span class="x-ph ell">Rechercher (titre, '
            'référence, fichier, contenu)…</span></span><span class="x-sel">Plus récents <i>▾</i></span>'
            '<span class="x-vues"><span class="actif">%s</span><span>%s</span></span></span></div>'
            % (p, CHARGER, p, CAMERA, '<span class="x-lk">Nouveau dossier</span>' if admin else '', p, LOUPE, GRILLE, LISTE))


def lateral(p, arbre, sans):
    """``arbre`` : (libellé, nombre, profondeur, ouvert (None : pas d'enfant), actif, id)."""
    h = ['<div class="x-sect">Espace de travail</div><div class="x-it">Tous</div>']
    for lib, n, prof, ouvert, actif, ident in arbre:
        caret = '' if ouvert is None else ('▾' if ouvert else '▸')
        h.append('<div class="x-it x-dos%s"%s style="padding-left:%dpx"><span class="x-car">%s</span><span class="x-di">%s</span>'
                 '<span class="x-nom ell">%s</span><i%s>%s</i></div>'
                 % (' actif' if actif else '', (' id="%s"' % ident) if ident else '', 8 + prof * 14, caret, DOSSIER, e(lib),
                    (' id="%s-n"' % ident) if ident else '', e(n)))
    h.append('<div class="x-it x-sans%s" id="%s-sans"><span class="x-nom">Sans classement</span><i id="%s-sans-n">%s</i></div>'
             % (' actif' if sans[1] else '', p, p, sans[0]))
    h.append('<div class="x-sect">Statut</div><div class="x-it">Brouillon<i>118</i></div><div class="x-it">Finalisé<i>96</i></div>'
             '<div class="x-it">Archivé<i>43</i></div>')
    return '<div class="x-lat">%s</div>' % ''.join(h)


def explorateur(ident, p, arbre, sans, fil, compte, cartes, extra='', initiale=False, admin=False):
    fil_html = '<span class="x-ecm">ECM</span>' + ''.join('<span class="x-sep">›</span><span class="x-ecm">%s</span>' % e(f) for f in fil)
    corps = ('<div class="x-exp">%s%s<div class="x-main"><div class="x-fil">%s<span class="x-cpt" id="%s-cpt">%s</span>'
             '<span class="x-tout">Tout sélectionner</span></div><div class="x-grille" id="%s-grille">%s</div>%s</div></div>'
             % (barre_outils(p, admin), lateral(p, arbre, sans), fil_html, p, e(compte), p, ''.join(cartes), extra))
    return vue(ident, corps, initiale=initiale)


ARBRE_AGENT = [('Direction générale', '6', 0, False, False, None), ('Ressources humaines', '4', 0, False, False, None),
               ('Juridique et contrats', '2', 0, False, False, None), ('Finance et comptabilité', '16', 0, False, False, None),
               ('Achats et fournisseurs', '5', 0, True, False, 't15-ach'),
               ('Agréments fournisseurs', '4', 1, None, True, 't15-agr'), ("Appels d'offres", '1', 1, None, False, None),
               ('Qualité et procédures', '8', 0, False, False, None), ('Courrier', '177', 0, False, False, None)]


def inspecteur():
    bts = ''.join('<span class="x-b %s">%s</span>' % (c, e(l)) for l, c in [
        ('Fiche', 'p'), ('Aperçu', 's'), ('Télécharger', 's'), ('Nouvelle version', 's'), ('Réserver', 's'),
        ('Finaliser', 'v'), ('Partager', 's'), ('Corbeille', 'r')])
    props = [('Fichier', '%s <span class="x-mu">(612 Ko)</span>' % FICHIER_SCAN, 't15-i-fic'), ('Versions', '1', None),
             ('Type', '—', None), ('Dossier', 'Achats et fournisseurs / Agréments fournisseurs', 't15-i-dos'),
             ('Étiquettes', '—', None), ('Confidentialité', 'Interne', None), ('Propriétaire', e(AGENT[0]), None),
             ('Modifié', JOUR, None)]
    dl = ''.join('<div class="x-dt">%s</div><div class="x-dd"%s>%s</div>' % (e(k), (' id="%s"' % i) if i else '', v_)
                 for k, v_, i in props)
    return ('<div class="x-insp masque" id="t15-insp"><div class="x-imini">%s</div><div class="x-it5">%s</div>'
            '<div class="x-iref">%s · Brouillon</div><div class="x-bts">%s</div><div class="x-dl">%s</div></div>'
            % (miniature('scan'), e(TITRE_SCAN), REF_SCAN, bts, dl))


def telephone():
    """L'appareil photo du téléphone (sans libellé : c'est l'appareil du système)."""
    return ('<div class="t15-tel masque" id="t15-tel" data-layout-allow-overlap data-layout-allow-occlusion>'
            '<div class="tel-ecran"><div class="tel-visee"><div class="tel-feuille" id="t15-feuille">'
            '<i class="x-l t"></i><i class="x-l"></i><i class="x-l"></i><i class="x-l c"></i><i class="x-l"></i><i class="x-l"></i>'
            '<i class="x-l c"></i><i class="x-l"></i><i class="x-tampon"></i></div>'
            '<span class="tel-coin a"></span><span class="tel-coin b"></span><span class="tel-coin c"></span><span class="tel-coin d"></span>'
            '<div class="tel-flash masque" id="t15-flash"></div></div>'
            '<div class="tel-bas"><span class="tel-vig" id="t15-vig"></span><span class="tel-decl" id="t15-decl"><i></i></span>'
            '<span class="tel-ok masque" id="t15-ok">✓</span></div></div></div>')


def toast(ident, texte_):
    return ('<div class="t15-toast masque" id="%s" data-layout-allow-overlap data-layout-allow-occlusion><span>%s</span><i>×</i></div>'
            % (ident, e(texte_)))


def ecran_agent():
    cartes = [carte(c, i) for i, c in enumerate(CARTES_AGR)] + [carte(NOUVEAU_SCAN, 0, masque=True)]
    exp = explorateur('t15-exp', 't15a', ARBRE_AGENT, ('2', False), ['Achats et fournisseurs', 'Agréments fournisseurs'],
                      '4 / 4 document(s)', cartes, extra=inspecteur(), initiale=True)
    html = fenetre('ECM', MENUS, [exp], AGENT[1], AGENT[2], calques=telephone() + toast('t15-notif', 'Numérisation enregistrée : %s' % REF_SCAN),
                   ident='app-15a')
    return html


# ------------------------------------------------------------ l'administrateur --
def reglages():
    apps = [('Paramètres généraux', 'g'), ('Signature OCA', 's'), ('AITE ECM', 'e'), ('Employés', 'p')]
    gauche = ''.join('<div class="st-app%s"><span class="st-ic %s">%s</span>%s</div>'
                     % (' actif' if c == 'e' else '', c, '<img src="assets/logos/aite_ecm.png" alt="">' if c == 'e' else '', e(n))
                     for n, c in apps)

    def ligne(lib, champ_html, ident=None):
        return '<div class="st-row"%s><span class="st-l">%s</span><span class="st-f">%s</span></div>' % (
            (' id="%s"' % ident) if ident else '', e(lib), champ_html)

    depot = ('<div class="st-set" id="t15-hot"><div class="st-t">Dossier de dépôt surveillé</div>'
             '<div class="st-h">Configurez votre scanner réseau en « scan vers dossier » (SMB/FTP) sur un répertoire du serveur : '
             'la tâche planifiée « AITE ECM : import du dossier de dépôt » en fait des documents.</div>'
             + ligne('Répertoire de dépôt du scanner', entree('t15-rep', '/srv/scans'), 't15-r-rep')
             + ligne('Dossier ECM de destination', entree('t15-dest', ''), 't15-r-dest')
             + ligne('Type des documents scannés', entree('t15-type', ''), 't15-r-type')
             + ligne('Propriétaire des documents importés', entree('t15-prop', ''), 't15-r-prop')
             + ligne('Délai avant import (s)', entree('t15-delai', '', '30'), 't15-r-delai') + '</div>')
    mail = ('<div class="st-set" id="t15-mailset"><div class="st-t">Scan vers e-mail et appareil photo</div>'
            '<div class="st-h">Les pièces reçues sur l\'alias deviennent des documents. Sur mobile, le bouton « Numériser » de '
            'l\'explorateur assemble les photos en un PDF.</div>'
            + ligne('Adresse de scan vers e-mail', '<span class="st-alias" id="t15-alias">%s</span>' % ALIAS)
            + '<div class="st-m">Le domaine d\'alias se définit dans Paramètres › Discussion. Un scanner « scan vers e-mail » '
              'envoie ses PDF à cette adresse.</div></div>')
    docs = ('<div class="st-set"><div class="st-t">Réservation et corbeille</div>'
            + ligne("Durée d'une réservation (h)", entree('t15-res', '', '48'))
            + ligne('Rétention de la corbeille (jours)', entree('t15-ret', '', '30')) + '</div>')
    cp = ('<div class="o-cp"><span class="bt prim" id="t15-enr">Enregistrer</span><span class="bt second">Ignorer</span>'
          '<span class="st-titre">Paramètres</span><span class="st-rech">%s<span>Rechercher…</span></span></div>' % LOUPE)
    corps = ('<div class="st-corps"><div class="st-apps">%s</div><div class="st-page"><div class="st-bloc">Numérisation</div>'
             '<div class="st-g">%s%s</div><div class="st-bloc">Documents</div><div class="st-g">%s<div></div></div></div></div>'
             % (gauche, depot, mail, docs))
    corps = corps.replace('<span class="val" id="t15-dest-val">', '<span class="val ell" id="t15-dest-val">', 1)
    return vue('t15-set', cp + corps, initiale=True)


ARBRE_ADMIN_FAC = [('Direction générale', '6', 0, False, False, None), ('Ressources humaines', '4', 0, False, False, None),
                   ('Juridique et contrats', '2', 0, False, False, None), ('Finance et comptabilité', '7', 0, True, False, None),
                   ('Factures fournisseurs 2026', '4', 1, None, True, None), ('Banques et assurances', '3', 1, None, False, None),
                   ('Achats et fournisseurs', '6', 0, False, False, None), ('Qualité et procédures', '8', 0, False, False, None),
                   ('Courrier', '177', 0, False, False, None)]
ARBRE_ADMIN_SANS = [(l, n, p, o, False, i) for (l, n, p, o, _, i) in ARBRE_ADMIN_FAC]


def ecran_admin():
    fac = explorateur('t15-fac', 't15b', ARBRE_ADMIN_FAC, ('2', False), ['Finance et comptabilité', 'Factures fournisseurs 2026'],
                      '4 / 4 document(s)', [carte(c, i + 1) for i, c in enumerate(CARTES_FAC)] + [carte(NOUVELLE_FAC, 0)],
                      admin=True)
    sans = explorateur('t15-sans', 't15c', ARBRE_ADMIN_SANS, ('3', True), [], '3 / 3 document(s)',
                       [carte(c, i + 1) for i, c in enumerate(CARTES_SANS)] + [carte(NOUVEAU_MAIL, 0)], admin=True)
    html = fenetre('ECM', MENUS + ['Configuration'], [reglages(), fac, sans], ADMIN[1], ADMIN[2], ident='app-15b')
    return html.replace('class="o-app muk" id="app-15b"', 'class="o-app muk masque" id="app-15b"', 1)


EXP = ':is(#app-15a,#app-15b)'
CSS = """
#app-15b { z-index: 5; }
EXP .x-exp { position: absolute; inset: 0; background: #fff; }
EXP .x-tb { position: absolute; left: 0; right: 0; top: 0; height: 46px; display: flex; align-items: center; gap: 8px; padding: 0 12px;
  border-bottom: 1px solid #DEE2E6; background: #fff; }
EXP .x-tb .bt svg { width: 12px; height: 12px; display: block; }
EXP .x-lk { white-space: nowrap; color: #528099; font-weight: 700; text-transform: uppercase; font-size: 12px; padding: 0 6px; }
EXP .x-depot { padding: 3px 8px; border-radius: 4px; background: #0DCAF0; color: #000; font-size: 11px; font-weight: 600; }
EXP .x-droite { margin-left: auto; display: flex; align-items: center; gap: 6px; }
EXP .x-rech { display: flex; align-items: center; width: 196px; height: 27px; border: 1px solid #DEE2E6; border-radius: 4px; overflow: hidden; }
EXP .x-lp { width: 26px; height: 100%; display: flex; align-items: center; justify-content: center; border-right: 1px solid #DEE2E6; color: #343A40; }
EXP .x-lp svg { width: 12px; height: 12px; }
EXP .x-ph { padding: 0 7px; color: #9AA0A6; font-size: 11.5px; white-space: nowrap; overflow: hidden; }
EXP .x-sel { white-space: nowrap; height: 27px; display: flex; align-items: center; gap: 12px; padding: 0 8px; border: 1px solid #DEE2E6; border-radius: 4px; font-size: 12px; }
EXP .x-sel i { font-style: normal; }
EXP .x-vues { display: flex; } EXP .x-vues span { width: 28px; height: 27px; display: flex; align-items: center; justify-content: center;
  background: #DEE2E6; color: #000; } EXP .x-vues span.actif { background: #D9E3EA; border: 1px solid #5D8DA8; }
EXP .x-vues svg { width: 12px; height: 12px; }
EXP .x-lat { position: absolute; left: 0; top: 46px; bottom: 0; width: 196px; border-right: 1px solid #DEE2E6; padding: 12px 0; overflow: hidden;
  background: #fff; }
EXP .x-sect { padding: 6px 10px 4px; font-size: 10px; letter-spacing: .06em; color: #6C757D; text-transform: uppercase; font-weight: 600; }
EXP .x-it { display: flex; align-items: center; gap: 4px; height: 25px; padding: 0 10px; font-size: 12.5px; color: #212529; }
EXP .x-it i { margin-left: auto; font-style: normal; font-size: 11px; color: #6C757D; }
EXP .x-it.actif { background: #EEF3F6; box-shadow: inset 3px 0 0 #8E3A9D; font-weight: 600; }
EXP .x-car { width: 10px; font-size: 9px; color: #6C757D; flex: none; }
EXP .x-di svg { width: 12px; height: 12px; display: block; color: #495057; }
EXP .x-nom { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
EXP .x-sans .x-nom { color: #6C757D; font-style: italic; }
EXP .x-main { position: absolute; left: 196px; right: 0; top: 46px; bottom: 0; padding: 12px 14px; overflow: hidden; }
EXP .x-fil { display: flex; align-items: center; gap: 6px; height: 26px; margin-bottom: 10px; font-size: 15px; }
EXP .x-ecm { font-weight: 600; color: #212529; } EXP .x-sep { color: #6C757D; font-size: 13px; }
EXP .x-cpt { margin-left: 10px; font-size: 11.5px; color: #6C757D; }
EXP .x-tout { margin-left: auto; font-size: 11.5px; color: #528099; }
EXP .x-grille { position: relative; height: 560px; }
EXP .x-carte { position: absolute; width: 184px; height: 176px; border: 1px solid #DEE2E6; border-radius: 4px; background: #fff; overflow: hidden; }
EXP .x-carte.sel { border-color: #8E3A9D; box-shadow: 0 0 0 1px #8E3A9D; }
EXP .x-mini { position: relative; height: 92px; background: #F1F3F5; display: flex; align-items: center; justify-content: center; }
EXP .x-coche { position: absolute; right: 7px; top: 7px; width: 14px; height: 14px; border-radius: 50%; border: 1px solid #ADB5BD; background: #fff; }
EXP .x-carte.sel .x-coche { background: #8E3A9D; border-color: #8E3A9D; }
EXP .x-pg { position: relative; width: 56px; height: 76px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.18); padding: 8px 7px;
  display: flex; flex-direction: column; gap: 4px; }
EXP .x-pg.x-scan, #app-15a .tel-feuille { background: #FBF8F0; transform: rotate(-2deg); }
EXP .x-l { display: block; height: 2px; background: #C9CDD2; border-radius: 1px; }
EXP .x-l.t { width: 60%; height: 3px; background: #6C757D; }
EXP .x-l.c { width: 70%; }
EXP .x-plan { display: block; height: 30px; border: 1px solid #C9CDD2; background: linear-gradient(45deg, transparent 46%, #C9CDD2 48%, transparent 52%); }
EXP .x-tampon, #app-15a .tel-feuille .x-tampon { position: absolute; right: 6px; bottom: 7px; width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid rgba(46,92,184,.55); }
EXP .x-photo { width: 92px; height: 64px; border-radius: 2px; background: linear-gradient(160deg, #8FA3B3, #5F7282); position: relative; }
EXP .x-photo i { position: absolute; left: 26px; top: 16px; width: 40px; height: 30px; border-radius: 4px; background: #E9ECEF; }
EXP .x-corps { padding: 7px 9px; }
EXP .x-titre { font-size: 11.5px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
EXP .x-ref { font-size: 10.5px; color: #6C757D; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
EXP .x-tags { height: 17px; margin-top: 3px; }
EXP .x-tag { display: inline-block; padding: 0 6px; border-radius: 8px; font-size: 9.5px; line-height: 15px; }
EXP .x-tag.rouge { background: #FBE3E4; color: #B02A37; } EXP .x-tag.bleu { background: #DCEBFA; color: #1F5D99; }
EXP .x-tag.jaune { background: #FFF1C9; color: #8A6500; }
EXP .x-bas { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; font-size: 10.5px; color: #6C757D; }
EXP .x-st { padding: 1px 6px; border-radius: 3px; font-size: 9.5px; font-weight: 600; }
EXP .x-st.gris { background: #E9ECEF; color: #212529; } EXP .x-st.vert { background: #198754; color: #fff; }
EXP .x-st.noir { background: #212529; color: #fff; }
EXP .x-insp { position: absolute; right: 0; top: 0; bottom: 0; width: 270px; background: #fff; border-left: 1px solid #DEE2E6; padding: 12px 14px;
  box-shadow: -6px 0 14px rgba(0,0,0,.05); }
EXP .x-imini { height: 104px; background: #F1F3F5; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
EXP .x-it5 { margin-top: 10px; font-size: 13.5px; font-weight: 600; }
EXP .x-iref { font-size: 11px; color: #6C757D; margin: 2px 0 8px; }
EXP .x-bts { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
EXP .x-b { padding: 3px 7px; border-radius: 3px; font-size: 10.5px; background: #DEE2E6; color: #000; }
EXP .x-b.p { background: #5D8DA8; color: #fff; } EXP .x-b.v { background: #198754; color: #fff; }
EXP .x-b.r { background: #fff; color: #DC3545; border: 1px solid #DC3545; padding: 2px 6px; }
EXP .x-dt { font-size: 10.5px; color: #6C757D; margin-top: 5px; }
EXP .x-dd { font-size: 11.5px; color: #212529; }
EXP .x-mu { color: #6C757D; }
#app-15a .t15-tel { position: absolute; left: 650px; top: 92px; width: 236px; height: 470px; border-radius: 34px; background: #16181C;
  padding: 12px; box-shadow: 0 24px 50px rgba(0,0,0,.42), inset 0 0 0 2px #2C3036; z-index: 40; }
#app-15a .tel-ecran { position: relative; width: 100%; height: 100%; border-radius: 24px; overflow: hidden; background: #000; }
#app-15a .tel-visee { position: absolute; left: 0; right: 0; top: 34px; height: 330px; background: radial-gradient(ellipse at 50% 45%, #8C7A62, #4B3F33);
  display: flex; align-items: center; justify-content: center; }
#app-15a .tel-feuille { position: relative; width: 150px; height: 206px; padding: 18px 16px; display: flex; flex-direction: column; gap: 9px;
  box-shadow: 0 8px 18px rgba(0,0,0,.4); }
#app-15a .tel-feuille .x-l { height: 3px; } #app-15a .tel-feuille .x-l.t { height: 5px; }
#app-15a .tel-feuille .x-tampon { right: 14px; bottom: 16px; width: 30px; height: 30px; border-width: 3px; }
#app-15a .tel-coin { position: absolute; width: 22px; height: 22px; border: 3px solid #FFD43B; }
#app-15a .tel-coin.a { left: 30px; top: 50px; border-right: 0; border-bottom: 0; }
#app-15a .tel-coin.b { right: 30px; top: 50px; border-left: 0; border-bottom: 0; }
#app-15a .tel-coin.c { left: 30px; bottom: 50px; border-right: 0; border-top: 0; }
#app-15a .tel-coin.d { right: 30px; bottom: 50px; border-left: 0; border-top: 0; }
#app-15a .tel-flash { position: absolute; inset: 0; background: #fff; }
#app-15a .tel-bas { position: absolute; left: 0; right: 0; bottom: 0; height: 82px; display: flex; align-items: center; justify-content: center; }
#app-15a .tel-vig { position: absolute; left: 22px; width: 36px; height: 36px; border-radius: 6px; background: #2C3036; border: 2px solid #3C4148; }
#app-15a .tel-vig.pris { background: #FBF8F0; border-color: #fff; }
#app-15a .tel-decl { width: 58px; height: 58px; border-radius: 50%; border: 4px solid #fff; display: flex; align-items: center; justify-content: center; }
#app-15a .tel-decl i { width: 44px; height: 44px; border-radius: 50%; background: #fff; }
#app-15a .tel-ok { position: absolute; right: 22px; width: 38px; height: 38px; border-radius: 50%; background: #FFD43B; color: #16181C;
  font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
#app-15a .t15-toast { position: absolute; right: 12px; top: 50px; width: 330px; display: flex; justify-content: space-between; align-items: center;
  padding: 12px 14px; background: #fff; border-left: 5px solid #198754; border-radius: 4px; box-shadow: 0 8px 22px rgba(0,0,0,.18);
  font-size: 12.5px; color: #212529; z-index: 45; }
#app-15a .t15-toast i { font-style: normal; font-size: 18px; color: #6C757D; }
#app-15b .st-corps { position: absolute; left: 0; right: 0; top: 52px; bottom: 0; display: flex; background: #fff; }
#app-15b .st-titre { font-size: 16px; margin-left: 4px; }
#app-15b .st-rech { margin-left: 120px; width: 380px; height: 28px; display: flex; align-items: center; gap: 8px; padding: 0 10px;
  border: 1px solid #DEE2E6; border-radius: 4px; color: #9AA0A6; font-size: 12px; }
#app-15b .st-rech svg { width: 12px; height: 12px; color: #343A40; }
#app-15b .st-apps { width: 178px; background: #F8F9FA; border-right: 1px solid #DEE2E6; padding-top: 6px; flex: none; }
#app-15b .st-app { display: flex; align-items: center; gap: 9px; height: 34px; padding: 0 12px; font-size: 12px; }
#app-15b .st-app.actif { background: #DCE8EF; }
#app-15b .st-ic { width: 16px; height: 16px; border-radius: 4px; overflow: hidden; flex: none; }
#app-15b .st-ic img { width: 16px; height: 16px; display: block; }
#app-15b .st-ic.g { background: conic-gradient(#F0623D, #F6B23C, #9B6BC7, #F0623D); border-radius: 50%; }
#app-15b .st-ic.s { background: linear-gradient(135deg, #F06050, #F6B23C); }
#app-15b .st-ic.p { background: linear-gradient(135deg, #E46F78, #9B6BC7); border-radius: 50%; }
#app-15b .st-page { flex: 1; overflow: hidden; }
#app-15b .st-bloc { height: 34px; display: flex; align-items: center; padding: 0 24px; background: #E9ECEF; font-size: 13px; font-weight: 600; }
#app-15b .st-g { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; padding: 16px 24px 18px 52px; }
#app-15b .st-set { border-left: 1px solid #CED4DA; padding-left: 12px; }
#app-15b .st-t { font-size: 12.5px; font-weight: 600; }
#app-15b .st-h { font-size: 11.5px; color: #6C757D; line-height: 1.45; margin: 3px 0 8px; }
#app-15b .st-row { display: grid; grid-template-columns: 118px 1fr; align-items: center; gap: 8px; min-height: 30px; }
#app-15b .st-l { font-size: 11.5px; line-height: 1.3; }
#app-15b .st-f { min-width: 0; }
#app-15b .st-f .entree { font-size: 12px; min-height: 24px; }
#app-15b .st-f .entree .val { overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
#app-15b .st-alias { font-size: 12px; font-weight: 500; white-space: nowrap; }
#app-15b .st-m { font-size: 11.5px; color: #6C757D; line-height: 1.45; margin-top: 6px; }
""".replace('EXP', EXP)

TUTO = {
    'slug': 'tuto-15-numeriser-ses-documents',
    'titre_page': 'AITE ECM — Tutoriel 15 : numériser ses documents',
    'titre': 'Numériser ses documents',
    'serie': dict(ECM, numero=15),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Ce papier, comment le *faire* *entrer ?*',
        'sous': "Photocopies, scans perdus sur une clé, PDF renommés à la main : le papier reste en marge du fonds documentaire.",
        'personnage': (AGENT[0], 'Agent courrier', AGENT[2]),
        'chaos': [('doc', 'scan0001.pdf'), ('bulle', 'Tu l\'as scanné où ?'), ('dossier', 'Clé USB du copieur'),
                  ('note', 'À classer ?'), ('lettre', 'Attestation papier'), ('alerte', 'Original introuvable'),
                  ('bulle', 'Renvoie-le-moi par mail'), ('doc', 'Copie de copie')],
        'voix': "Une attestation arrive sur papier. Scannée, elle part sur une clé ou dans une boîte mail, et "
                "personne ne la retrouve au bon endroit.",
    },
    'revelation': {'voix': "Avec Aïte E C M, le papier entre dans le fonds par la porte que vous voulez."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Trois façons de *numériser*',
        'pastilles': ['Photo depuis le mobile', 'Dossier du copieur', 'Scan vers e-mail'],
        'voix': "Une photo au téléphone, le dossier du copieur, ou un simple e-mail : trois portes d'entrée, et "
                "chaque fois, un document rangé.",
    },
    'ecran': ecran_agent() + ecran_admin(), 'vue_initiale': 't15-exp',
    'css': CSS,
    'etapes': [
        {'titre': 'Numériser depuis l\'explorateur',
         'texte': "Le bouton Numériser ouvre l'appareil photo du mobile : la pièce est photographiée sur place.",
         'voix': "Dans l'explorateur, Carine est dans le dossier Agréments fournisseurs. Numériser ouvre l'appareil "
                 "photo du téléphone, ou le choix d'images sur un ordinateur. Elle cadre l'attestation, et déclenche.",
         'gestes': [anneau('#t15-agr', d=1.4, decale=0.3), curseur('#t15a-charger', fx=0.7, d=0.6),
                    clic('#t15a-num', fx=0.6), bulle('#t15a-num', 'Photo ou images', cote='dessous', d=1.8),
                    montrer('#t15-tel', y=40, d=0.5), pause(0.4), curseur('#t15-decl', d=0.6),
                    clic('#t15-decl', deplacer=False, decale=0.6),
                    animer('#t15-flash', {'autoAlpha': 0}, {'autoAlpha': 0.95}, d=0.08, avec=True),
                    animer('#t15-flash', {'autoAlpha': 0.95}, {'autoAlpha': 0}, d=0.35),
                    animer('#t15-vig', {'scale': 0.6}, {'scale': 1}, d=0.3, avec=True), classe('#t15-vig', ajouter=['pris'], avec=True),
                    montrer('#t15-ok', y=0, d=0.3), pause(0.4), clic('#t15-ok')]},
        {'titre': 'Un PDF, rangé là où vous êtes',
         'texte': "La photo devient un PDF, créé en brouillon dans le dossier ouvert, avec sa référence et sa version 1.",
         'voix': "Les photos sont assemblées en un seul P D F, et une notification confirme l'enregistrement. Le "
                 "document est créé dans le dossier ouvert, en brouillon, avec sa référence et sa version 1. Son titre "
                 "porte la date et l'heure de la numérisation.",
         'gestes': [cacher('#t15-tel', d=0.35), montrer('#t15a-depot', y=0, d=0.25, avec=True), pause(0.8),
                    cacher('#t15a-depot', d=0.2),
                    animer('#t15-k0', {'x': 0}, {'x': COL}, d=0.45, avec=True),
                    animer('#t15-k1', {'x': 0}, {'x': COL}, d=0.45, avec=True),
                    animer('#t15-k2', {'x': 0}, {'x': COL}, d=0.45, avec=True),
                    animer('#t15-k3', {'x': 0, 'y': 0}, {'x': -3 * COL, 'y': LIG}, d=0.45, avec=True),
                    texte('#t15a-cpt', '5 / 5 document(s)', avec=True), texte('#t15-agr-n', '5', avec=True),
                    texte('#t15-ach-n', '6', avec=True),
                    montrer('#t15-k9', y=-16, d=0.4), notifier('t15-notif', duree=3.0, avec=True),
                    curseur('#t15-notif', fx=0.6, fy=0.9, d=0.6), pause(1.6),
                    zoom('#t15-k9', s=1.7, fx=0.42, fy=0.45, d=0.8),
                    bulle('#t15-k9 .x-titre', 'Un seul PDF, en brouillon', cote='droite', d=2.4),
                    dezoom(d=0.6), clic('#t15-k9', fx=0.5, fy=0.3), classe('#t15-k9', ajouter=['sel'], avec=True),
                    montrer('#t15-insp', y=0, d=0.35),
                    zoom('#t15-i-dos', s=1.6, fx=0.6, fy=0.5, d=0.8), anneau('#t15-i-dos', d=1.2),
                    bulle('#t15-i-dos', 'Le dossier ouvert', cote='gauche', d=2.2), dezoom(d=0.6)]},
        {'titre': 'Le dossier de dépôt du copieur',
         'texte': "Le copieur numérise vers un dossier du serveur ; toutes les 5 minutes, ses fichiers deviennent des documents.",
         'voix': "Pour les gros volumes, le copieur numérise vers un dossier du serveur. Martin, l'administrateur, "
                 "choisit la destination, le type et le propriétaire. Toutes les cinq minutes, une tâche planifiée "
                 "importe les fichiers posés depuis au moins trente secondes : ils deviennent des documents, titrés "
                 "d'après leur nom.",
         'gestes': [texte('#pr-url', 'courrier.aite-demo.test/odoo/settings'), montrer('#app-15b', y=0, d=0.4, avec=True),
                    zoom('#t15-hot', s=1.45, fx=0.42, fy=0.5, d=0.8),
                    clic('#t15-rep', fx=0.3, d=0.5), saisir('t15-rep', '/srv/scans', d=0.6),
                    clic('#t15-dest', fx=0.3, d=0.5), choisir('t15-dest', 'Finance et comptabilité / Factures fournisseurs 2026'),
                    clic('#t15-type', fx=0.3, d=0.5), choisir('t15-type', 'Facture fournisseur'),
                    clic('#t15-prop', fx=0.3, d=0.5), choisir('t15-prop', P['compta'][0]),
                    bulle('#t15-delai', 'Fichier stable depuis 30 s', cote='droite', fx=0.5, d=2.0),
                    dezoom(d=0.6), clic('#t15-enr'), aller('t15-fac'), texte('#pr-url', ADRESSE % 'ecm', avec=True),
                    anneau('#t15-f0', d=1.2),
                    bulle('#t15-f0 .x-titre', 'Importé : Facture_Delta_0412', cote='droite', d=2.4, avec=True)]},
        {'titre': 'Le scan vers e-mail',
         'texte': "Chaque pièce jointe reçue sur l'adresse ecm-scan devient un document, titré d'après l'objet du message.",
         'voix': "Troisième porte : l'e-mail. Le copieur envoie ses P D F à l'adresse ecm-scan : chaque pièce jointe "
                 "devient un document, titré d'après l'objet du message, qui attend dans Sans classement, prêt à être "
                 "rangé.",
         'gestes': [aller('t15-set'), texte('#pr-url', 'courrier.aite-demo.test/odoo/settings', avec=True),
                    zoom('#t15-mailset', s=1.5, fx=0.55, fy=0.45, d=0.8), anneau('#t15-alias', d=1.4),
                    bulle('#t15-alias', 'Une pièce, un document', cote='dessous', d=2.4), dezoom(d=0.6),
                    aller('t15-fac'), texte('#pr-url', ADRESSE % 'ecm', avec=True), clic('#t15b-sans', fx=0.4), aller('t15-sans'),
                    anneau('#t15-s0', d=1.2),
                    bulle('#t15-s0 .x-titre', "L'objet du message", cote='droite', d=2.4, avec=True)]},
    ],
    'benefices': {
        'titre': 'Le papier, *enfin* dans le *fonds.*',
        'voix': "Le papier entre par la porte la plus simple, arrive à sa place avec sa référence, et ne dort plus "
                "sur une clé.",
        'cartes': [('eclair', 'Numériser', 'Depuis le mobile', "Une photo devient un PDF, rangé dans le dossier ouvert."),
                   ('temps', '5 min', 'Le copieur importé', "Le dossier de dépôt est relevé toutes les cinq minutes."),
                   ('doc', 'ecm-scan@', 'Par e-mail', "Chaque pièce jointe reçue devient un document du fonds.")],
    },
    'cta': cta('ecm', 'Le papier, *rangé* dès *l\'entrée.*', "Aïte E C M : le papier, rangé dès l'entrée."),
    'youtube': youtube('COMMENT NUMÉRISER SES DOCUMENTS AVEC AITE ECM (ODOO 18)',
                       "Photo prise au mobile et assemblée en PDF, dossier de dépôt alimenté par le copieur et relevé toutes "
                       "les cinq minutes, scan vers e-mail : trois façons de faire entrer le papier dans le fonds documentaire, "
                       "chaque document arrivant avec sa référence et sa version. Tutoriel AITE ECM pour Odoo 18.",
                       ['AITE ECM', 'numérisation', 'scanner', 'dossier de dépôt', 'scan vers e-mail', 'GED Odoo']),
}
