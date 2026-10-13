# -*- coding: utf-8 -*-
"""Les écrans d'AITE Courrier et d'AITE ECM (Odoo 18 Community), rejoués en HTML.

Aucune capture dans la vidéo : chaque écran est reconstruit avec les couleurs
d'Odoo 18 (barre #71639E, fond #F8F9FA, pastilles Bootstrap) et les libellés
relevés dans les vues des modules (``addons/aite_*/views``) et dans les
données du circuit standard (``aite_courrier_workflow/data``). Les captures
de la recette (``docs/recette/captures``) n'ont servi que de modèle visuel.

L'interface est écrite à sa taille d'écran (1100 × 700 px), puis agrandie
par le cadre de la scène. Les identifiants posés sur les éléments servent de
cibles au curseur et aux gestes : uniques dans toute la vidéo.
"""

from html import escape as _e


def e(texte):
    return _e(str(texte), quote=True)


def _id(identifiant):
    return ' id="%s"' % identifiant if identifiant else ''


ICONES = {
    'grille': '<svg viewBox="0 0 24 24" fill="#fff"><rect x="3" y="3" width="5" height="5" rx="1"/><rect x="9.5" y="3" width="5" height="5" rx="1"/><rect x="16" y="3" width="5" height="5" rx="1"/><rect x="3" y="9.5" width="5" height="5" rx="1"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><rect x="16" y="9.5" width="5" height="5" rx="1"/><rect x="3" y="16" width="5" height="5" rx="1"/><rect x="9.5" y="16" width="5" height="5" rx="1"/><rect x="16" y="16" width="5" height="5" rx="1"/></svg>',
    'loupe': '<svg viewBox="0 0 24 24" fill="none" stroke="#495057" stroke-width="2.4"><circle cx="10.5" cy="10.5" r="7"/><path d="M16 16l5 5"/></svg>',
    'roue': '<svg viewBox="0 0 24 24" fill="#495057"><path d="M12 8.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7zm8.6 5.1l-1.9-.5a6.9 6.9 0 000-2.2l1.9-.5-1.2-2.9-1.8.9a7 7 0 00-1.6-1.6l.9-1.8-2.9-1.2-.5 1.9a6.9 6.9 0 00-2.2 0l-.5-1.9-2.9 1.2.9 1.8a7 7 0 00-1.6 1.6l-1.8-.9-1.2 2.9 1.9.5a6.9 6.9 0 000 2.2l-1.9.5 1.2 2.9 1.8-.9a7 7 0 001.6 1.6l-.9 1.8 2.9 1.2.5-1.9a6.9 6.9 0 002.2 0l.5 1.9 2.9-1.2-.9-1.8a7 7 0 001.6-1.6l1.8.9z"/></svg>',
    'bulle': '<svg viewBox="0 0 24 24" fill="#fff"><path d="M3 5h18v11H9l-5 4v-4H3z"/></svg>',
    'horloge': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2.5"/></svg>',
    'retour': '<svg viewBox="0 0 24 24" fill="none" stroke="#343A40" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6L4 11l5 5"/><path d="M4 11h10a6 6 0 016 6v1"/></svg>',
    'oeil': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    'cadenas': '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 10V7a5 5 0 0110 0v3h1.5v11h-13V10zm2.4 0h5.2V7a2.6 2.6 0 00-5.2 0z"/></svg>',
    'corbeille': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>',
    'lecture': '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4l13 8-13 8z"/></svg>',
    'televerser': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4m0 0L7 9m5-5l5 5M4 20h16"/></svg>',
    'nuage': '<svg viewBox="0 0 24 24" fill="#A3A9C2"><path d="M7 19a5 5 0 01-.7-9.95A6 6 0 0118 8.2 4.5 4.5 0 0117.5 19H13v-5l2 2 1.4-1.4L12 10.2l-4.4 4.4L9 16l2-2v5z"/></svg>',
    'envoi': '<svg viewBox="0 0 24 24" fill="#fff"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>',
    'sceau': '<svg viewBox="0 0 24 24" fill="#5B4C93"><path d="M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5z"/></svg>',
    'document': '<svg viewBox="0 0 24 24" fill="none" stroke="#5B4C93" stroke-width="2" stroke-linejoin="round"><path d="M14 2H6v20h12V6z"/><path d="M14 2v4h4M9 12h6M9 16h6"/></svg>',
    'histo': '<svg viewBox="0 0 24 24" fill="none" stroke="#5B4C93" stroke-width="2.4" stroke-linecap="round"><path d="M3 12a9 9 0 103-6.7L3 8M3 3v5h5M12 7v5l3 2"/></svg>',
    'verifie': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#fff"/><path d="M7 12.5l3 3 7-7" fill="none" stroke="#5B4C93" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    'pdf': '<svg viewBox="0 0 24 24" fill="none" stroke="#343A40" stroke-width="2" stroke-linejoin="round"><path d="M14 2H6v20h12V6z"/><path d="M14 2v4h4"/></svg>',
    'coche': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    'trombone': '<svg viewBox="0 0 24 24" fill="none" stroke="#6C757D" stroke-width="2.2" stroke-linecap="round"><path d="M20 11l-8.5 8.5a5 5 0 01-7-7L13 4a3.3 3.3 0 014.7 4.7l-8.6 8.6a1.7 1.7 0 01-2.4-2.4L15 7.5"/></svg>',
    'maison': '<svg viewBox="0 0 24 24" fill="#71639E"><path d="M12 3l9 8h-3v9h-4v-6h-4v6H6v-9H3z"/></svg>',
    'boite': '<svg viewBox="0 0 24 24" fill="#C5CBE8"><path d="M3 4h18v5H3zM4 10h16v10H4zm5 2v2h6v-2z"/></svg>',
    'alerte': '<svg viewBox="0 0 24 24" fill="#F7C3BE"><path d="M12 2L1 21h22zM11 9h2v6h-2zm0 8h2v2h-2z"/></svg>',
    'telecharge': '<svg viewBox="0 0 24 24" fill="#BDE5CC"><path d="M11 3h2v9l3-3 1.4 1.4L12 15.8 6.6 10.4 8 9l3 3zM4 18h16v3H4z"/></svg>',
    'archive': '<svg viewBox="0 0 24 24" fill="#BFE3DF"><path d="M3 3h18v4H3zM4 8h16v13H4zm5 3v2h6v-2z"/></svg>',
    'croix': '<svg viewBox="0 0 24 24" fill="#FBE3B8"><circle cx="12" cy="12" r="10"/><path d="M8.5 8.5l7 7m0-7l-7 7" stroke="#fff" stroke-width="2.4"/></svg>',
    'montre': '<svg viewBox="0 0 24 24" fill="none" stroke="#C9C3EC" stroke-width="2.4"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    'marteau': '<svg viewBox="0 0 24 24" fill="#6B4E00"><path d="M13.8 2.6l7.6 7.6-2.1 2.1-1.4-1.4-2.8 2.8 1.4 1.4-2.1 2.1-7.6-7.6 2.1-2.1 1.4 1.4 2.8-2.8-1.4-1.4zM4.7 15.5l3.8 3.8L5.2 22.6 1.4 18.8z"/></svg>',
}


def icone(nom, classe='ic'):
    return '<span class="%s">%s</span>' % (classe, ICONES[nom])


def curseur_svg():
    return ('<svg id="curseur-fleche" viewBox="0 0 32 32"><path d="M5 3l20 12-9 2.2L20.5 27l-4.2 2-4.4-9.6L5 25z" '
            'fill="#fff" stroke="#1C1620" stroke-width="2" stroke-linejoin="round"/></svg>')


def puce(texte, genre='gris', identifiant=None):
    """Pastille Odoo : gris, bleu, vert, rouge, jaune, info."""
    return '<span class="puce %s"%s>%s</span>' % (genre, _id(identifiant), e(texte))


def entree(identifiant, placeholder='', valeur='', classe='entree'):
    """Champ de saisie : le texte indicatif s'efface quand la saisie commence."""
    return ('<span class="%s" id="%s"><span class="ph" id="%s-ph">%s</span><span class="val" id="%s-val">%s</span></span>'
            % (classe, identifiant, identifiant, e(placeholder), identifiant, e(valeur)))


def bouton(identifiant, libelle, style='second', ico=None):
    return '<span class="bt %s" id="%s">%s%s</span>' % (style, identifiant, icone(ico) if ico else '', e(libelle))


# ------------------------------------------------------------ fenêtre --

def fenetre(app, menus, vues, avatar='A', couleur_avatar='#B5404A', calques='', ident='app'):
    """Le cadre d'Odoo 18 : barre violette, puis les vues empilées."""
    m = ''.join('<span class="menu" id="%s-m%d">%s</span>' % (ident, i, e(x)) for i, x in enumerate(menus))
    return ('<div class="o-app" id="%s"><div class="o-nav"><span class="grille">%s</span><span class="nom-app">%s</span>%s'
            '<span class="droite"><span class="pi">%s<b>3</b></span><span class="pi">%s</span>'
            '<span class="societe">AITE Démo</span><span class="avatar" style="background:%s">%s</span></span></div>'
            '<div class="o-contenu">%s</div>%s</div>'
            % (ident, ICONES['grille'], e(app), m, ICONES['bulle'], ICONES['horloge'], couleur_avatar, e(avatar),
               ''.join(vues), calques))


def vue(identifiant, contenu, initiale=False, groupe='odoo'):
    return '<div class="vue%s" id="%s" data-groupe="%s">%s</div>' % (
        ' initiale' if initiale else '', identifiant, groupe, contenu)


def panneau_liste(titre, pager, facettes=(), nouveau=True, ident=None, recherche_id=None):
    f = ''.join('<span class="facette"><span class="k">%s</span>%s<i>×</i></span>' % (e(k), e(v)) for k, v in facettes)
    return ('<div class="o-cp">%s<span class="titre">%s %s</span>'
            '<span class="recherche"%s>%s%s%s<span class="drop">▾</span></span>'
            '<span class="pager">%s</span><span class="fleches">‹ ›</span></div>'
            % ('<span class="bt prim"%s>Nouveau</span>' % _id(ident and ident + '-nouveau') if nouveau else '', e(titre),
               ICONES['roue'] if nouveau else '', _id(recherche_id), ICONES['loupe'], f,
               entree(recherche_id + '-q', 'Rechercher…') if recherche_id else '<span class="ph">Rechercher…</span>',
               e(pager)))


def panneau_fiche(parent, reference, pager='1 / 1', nouveau=True, boutons_stat='', ref_id=None, sauver_id=None):
    sauver = ('<span class="sauver" id="%s">%s</span>' % (sauver_id, ICONES['nuage'])) if sauver_id else ''
    return ('<div class="o-cp fiche">%s<span class="fil"><span class="parent">%s</span>'
            '<span class="ref"%s>%s</span></span>%s<span class="stats">%s</span><span class="pager">%s</span>'
            '<span class="fleches">‹ ›</span></div>'
            % ('<span class="bt contour">Nouveau</span>' if nouveau else '', e(parent), _id(ref_id), e(reference),
               sauver, boutons_stat, e(pager)))


def bouton_stat(libelle, valeur, ico='document', identifiant=None):
    return '<span class="stat"%s>%s<span><b>%s</b><i>%s</i></span></span>' % (
        _id(identifiant), icone(ico), e(libelle), e(valeur))


def liste(colonnes, lignes, groupes=None, ident=None, vide=None):
    """``colonnes`` : (libellé, largeur CSS) ; ``lignes`` : {'id', 'cellules',
    'classe'} ; une cellule est un texte, ou un tuple (html,)."""
    gabarit = '28px ' + ' '.join(l for _, l in colonnes)
    tete = '<div class="tete" style="grid-template-columns:%s"><span class="cb"></span>%s</div>' % (
        gabarit, ''.join('<span class="ell">%s</span>' % e(c) for c, _ in colonnes))
    corps = []
    for i, l in enumerate(lignes):
        if groupes and i in groupes:
            corps.append('<div class="groupe">▸ %s</div>' % e(groupes[i]))
        cells = ''.join(c[0] if isinstance(c, tuple) else '<span class="ell">%s</span>' % e(c) for c in l['cellules'])
        corps.append('<div class="ligne%s" id="%s" style="grid-template-columns:%s"><span class="cb"></span>%s</div>'
                     % ((' ' + l['classe']) if l.get('classe') else '', l['id'], gabarit, cells))
    if vide:
        corps.append(vide)
    return '<div class="o-liste"%s>%s%s</div>' % (_id(ident), tete, ''.join(corps))


def c_lien(texte):
    return ('<span class="lien ell">%s</span>' % e(texte),)


def c_puce(texte, genre='gris', identifiant=None):
    return ('<span>%s</span>' % puce(texte, genre, identifiant),)


def c_num(texte):
    return ('<span class="num">%s</span>' % e(texte),)


def c_html(html):
    return (html,)


def panneau_lateral(blocs, identifiant=None):
    """Le panneau de recherche à gauche : (titre, [(libellé, nombre, actif)])."""
    h = []
    for titre, items in blocs:
        h.append('<div class="pl-titre">%s</div>' % e(titre))
        for lib, n, actif in items:
            h.append('<div class="pl-it%s"><span>%s</span><i>%s</i></div>' % (' actif' if actif else '', e(lib), e(n)))
    return '<div class="o-lateral"%s>%s</div>' % (_id(identifiant), ''.join(h))


def statusbar(etapes, actif, identifiant):
    """La barre d'étapes d'Odoo, chaque étape adressable : ``<id>-<n>``."""
    return '<span class="statusbar" id="%s">%s</span>' % (identifiant, ''.join(
        '<span class="sb%s" id="%s-%d">%s</span>' % (' actif' if i == actif else '', identifiant, i, e(n))
        for i, n in enumerate(etapes)))


def bande(boutons, droite='', identifiant=None, apres=None):
    """Bande d'actions de la fiche ; ``apres`` : la bande après un geste,
    groupe ``<id>-b`` révélé à la place de ``<id>-a``."""
    g = '<span class="groupe-bt" id="%s-a">%s</span>' % (identifiant, ''.join(boutons))
    if apres is not None:
        g += '<span class="groupe-bt masque" id="%s-b">%s</span>' % (identifiant, ''.join(apres))
    return '<div class="o-bande" id="%s"><span class="pile">%s</span><span class="sb-zone">%s</span></div>' % (identifiant, g, droite)


def champ(libelle, valeur_html, identifiant=None, aide=False):
    return '<div class="champ"%s><span class="l">%s%s</span><span class="v">%s</span></div>' % (
        _id(identifiant), e(libelle), '<sup>?</sup>' if aide else '', valeur_html)


def v(texte, lien=False, identifiant=None):
    return '<span class="%s"%s>%s</span>' % ('lien' if lien else '', _id(identifiant), e(texte))


def feuille(contenu, ruban=None, ruban_id=None, identifiant=None, largeur=None):
    r = ''
    if ruban:
        r = '<span class="ruban %s"%s><b>%s</b></span>' % (ruban[1], _id(ruban_id), e(ruban[0]))
    style = ' style="width:%s"' % largeur if largeur else ''
    return '<div class="o-feuille"%s%s>%s%s</div>' % (_id(identifiant), style, r, contenu)


def grille2(gauche, droite):
    return '<div class="g2"><div>%s</div><div>%s</div></div>' % (''.join(gauche), ''.join(droite))


def sec_titre(t):
    return '<div class="sec-t">%s</div>' % e(t)


def onglets(noms, actif=0, identifiant=None):
    return '<div class="onglets"%s>%s</div>' % (_id(identifiant), ''.join(
        '<span class="og%s"%s>%s</span>' % (' actif' if i == actif else '',
                                          _id(identifiant and '%s-%d' % (identifiant, i)), e(n))
        for i, n in enumerate(noms)))


def table(colonnes, lignes, identifiant=None, ajouter=True):
    """Une liste dans une fiche (one2many) : colonnes (libellé, largeur)."""
    gab = ' '.join(l for _, l in colonnes)
    tete = '<div class="tt" style="grid-template-columns:%s">%s</div>' % (
        gab, ''.join('<span class="ell">%s</span>' % e(c) for c, _ in colonnes))
    corps = ''.join('<div class="tl%s" id="%s" style="grid-template-columns:%s">%s</div>' % (
        ' masque' if l.get('masque') else '', l['id'], gab,
        ''.join(c[0] if isinstance(c, tuple) else '<span class="ell">%s</span>' % e(c) for c in l['cellules']))
        for l in lignes)
    return '<div class="o-table"%s>%s%s%s</div>' % (_id(identifiant), tete, corps,
                                                     '<div class="tl ajout"><span class="lien">Ajouter une ligne</span></div>' if ajouter else '')


def fiche(identifiant, cp, bande_html, feuille_html, chatter='', initiale=False):
    return vue(identifiant, cp + '<div class="o-corps">%s%s%s</div>' % (
        '<div class="o-gauche">%s%s</div>' % (bande_html, feuille_html), chatter, ''), initiale)


def chatter(messages, activites='', identifiant=None, suivre='Suivi'):
    """Le fil de discussion à droite de la fiche."""
    return ('<div class="o-chatter"%s><div class="ch-bts"><span class="bt prim petit">Envoyer un message</span>'
            '<span class="bt second petit">Note</span><span class="bt second petit">Activités</span>'
            '<span class="suivre">%s</span></div>%s<div class="ch-sep">Aujourd\'hui</div>%s</div>'
            % (_id(identifiant), e(suivre), activites, ''.join(messages)))


def message(auteur, couleur, texte_html, heure='10:29', identifiant=None, masque=False):
    return ('<div class="msg%s"%s><span class="av" style="background:%s">%s</span><div><div class="au">%s <i>%s</i></div>'
            '<div class="tx">%s</div></div></div>' % (' masque' if masque else '', _id(identifiant), couleur,
                                                     e(auteur[0]), e(auteur), e(heure), texte_html))


def activite(titre, pour, texte, couleur, initiale, identifiant=None, masque=True):
    return ('<div class="act%s"%s><span class="av" style="background:%s">%s<em>✓</em></span><div>'
            '<div class="at"><b class="auj">Aujourd\'hui :</b> <b>« %s »</b> pour %s</div><div class="tx">%s</div></div></div>'
            % (' masque' if masque else '', _id(identifiant), couleur, e(initiale), e(titre), e(pour), e(texte)))


def assistant(identifiant, titre, corps, boutons, haut=150, largeur=780):
    pied = ''.join('<span class="bt %s" id="%s">%s</span>' % (s, i, e(l)) for i, l, s in boutons)
    return ('<div class="voile masque" id="%s-voile" data-layout-allow-overlap data-layout-allow-occlusion></div>'
            '<div class="modale masque" id="%s" style="top:%dpx;width:%dpx;margin-left:-%dpx" data-layout-allow-overlap '
            'data-layout-allow-occlusion><div class="mt"><span>%s</span><span class="x">×</span></div>'
            '<div class="mc">%s</div><div class="mp">%s</div></div>'
            % (identifiant, identifiant, haut, largeur, largeur // 2, e(titre), corps, pied))


def bandeau(texte_html, genre='vert', identifiant=None, masque=False):
    return '<div class="bandeau %s%s"%s>%s</div>' % (genre, ' masque' if masque else '', _id(identifiant), texte_html)


def barre(pourcent, identifiant=None):
    return ('<span class="jauge"><i%s style="width:%d%%"></i></span><span class="jv">%d %%</span>'
            % (_id(identifiant), pourcent, pourcent))


def interrupteur(actif):
    return '<span class="inter%s"><i></i></span>' % (' on' if actif else '')


def case(cochee=True):
    return '<span class="case%s">%s</span>' % (' on' if cochee else '', ICONES['coche'] if cochee else '')


# ------------------------------------------------------------- portail --

def portail(vues, utilisateur, ident='app-portail'):
    """Le portail Odoo des tiers : bandeau gris, page centrée, pied."""
    return ('<div class="o-app portail" id="%s"><div class="p-nav"><span class="logo">AITE Démo</span>'
            '<span class="u">%s ▾</span></div><div class="p-page">%s</div>'
            '<div class="p-pied"><span>Copyright © AITE Démo</span><span>Propulsé par <b>odoo</b></span></div></div>'
            % (ident, e(utilisateur), ''.join(vues)))


def p_entete():
    return ('<div class="p-entete"><span class="logo">AITE Démo</span><span><b>AITE Démo</b>'
            '<i>Espace de dépôt et de suivi de vos courriers</i></span></div>')


def p_fil(*elements):
    return '<div class="p-fil">%s %s</div>' % (ICONES['maison'], ''.join(
        '<span>/</span><span class="%s">%s</span>' % ('lien' if i < len(elements) - 1 else '', e(x))
        for i, x in enumerate(elements)))


# ------------------------------------------------------ tableau de bord --

def tuile(identifiant, valeur, libelle, couleur, ico):
    return ('<div class="tuile" id="%s" style="border-left-color:%s"><span class="ti">%s</span>'
            '<div class="tn" id="%s-n">%s</div><div class="tlb">%s</div></div>'
            % (identifiant, couleur, ICONES[ico], identifiant, e(valeur), e(libelle)))


def barres(lignes):
    """(identifiant, libellé, valeur, proportion 0-1)."""
    return ''.join('<div class="br"><span class="ell">%s</span><span class="piste"><i id="%s" style="width:%.1f%%"></i>'
                   '</span><b>%s</b></div>' % (e(l), i, p * 100, e(val)) for i, l, val, p in lignes)
