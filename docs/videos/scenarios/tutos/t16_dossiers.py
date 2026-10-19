# -*- coding: utf-8 -*-
"""Tutoriel 16 — Les dossiers métier.

Sources :
- aite_ecm_dossier/views/aite_ecm_dossier_views.xml : fiche « Dossier
  métier » (boutons « Ouvrir le dossier », « Traiter », « Clôturer »,
  « Annuler », « Régénérer les pièces » et leurs conditions ; barre d'états
  Brouillon / En cours / Clôturé ; bouton « Documents » ; bandeau « Circuit en
  cours — étape … · échéance … » ; « Objet du dossier » ; onglets « Pièces »,
  « Circuit », « Description » ; colonnes des pièces et boutons « Fournir » /
  « Ouvrir »), liste (colonnes), panneau de recherche (« Types », « Statut ») ;
- models/aite_ecm_dossier.py : champs (« Type de dossier », « Tiers
  concerné », « Responsable », « Échéance du dossier », « Ouvert le »,
  « Clôturé le », « Complétude (%) », « Pièces obligatoires manquantes »,
  « Pièce », « Type attendu », « Obligatoire », « Document fourni »,
  « Validée », « État » : Manquante / Fournie / Validée, « Consigne ») ;
  pièces instanciées depuis le type à la création ; complétude = pièces
  fournies / pièces attendues ; ``action_open`` (lance le circuit actif du
  type) ; ``action_close`` : « Le dossier est incomplet : %d pièce(s)
  obligatoire(s) manquante(s). Seul un manager peut forcer la clôture. » ;
  ``_wf_on_finished`` (clôture automatique seulement si complet) ;
  ``action_new_document`` (document typé, rattaché, nommé d'après la pièce) ;
- models/aite_ecm_dossier_type.py, data/aite_ecm_dossier_data.xml : type
  « Agrément fournisseur » (dossier de classement Achats et fournisseurs ;
  métadonnées « Catégorie d'achat », « Plafond annuel (FCFA) », « Agrément
  valide jusqu'au » ; pièces « Registre de commerce (RCCM) »,
  « Attestation de non-redevance fiscale (ANR) » — consigne « En cours de
  validité à la date du dépôt » —, « Plan de localisation » obligatoires,
  « Relevé d'identité bancaire », « Contrat cadre signé » facultatives) ;
  circuit « Agrément fournisseur — instruction et validation » : Instruction
  (48 h, agent courrier et assistante), Validation achats (72 h, manager),
  Décision (manager, signataire) ; transitions « Transmettre pour
  validation », « Retour pour complément », « Accorder l'agrément » ;
  data/ir_sequence_data.xml (DOS-AAAA-NNNN) ;
- aite_ecm_workflow : mixin (« Circuit — statut » : Non lancé / En cours /
  Terminé / Rejeté ; habilitations par rôle, contrôle serveur), assistant
  « Action — <référence> » (« Objet », « Étape courante », « Action » :
  « Appliquer une transition » / « Rejeter », « Transition », « Commentaire »
  et son texte indicatif, « Valider », « Annuler ») ;
- aite_ecm_document : fiche du document dans la fenêtre « Fournir »
  (« Téléverser une nouvelle version », « Nouvelle version », « Commentaire »,
  « Ajouter la version », « Enregistrement lié »).
Modèle visuel : base demo18 (MuK) — liste, fiche, fenêtre « Fournir »,
assistant de circuit, refus « Opération invalide » relevés sur un dossier de
test. Écran inspiré du chapitre 7 de la présentation (vue c7-dossier),
recomposé pour l'agrément fournisseur.
"""

import demo
from ecrans import (ICONES, assistant, bande, bouton, bouton_stat, c_html, case, champ, e, entree, fenetre, feuille, grille2,
                    interrupteur, liste, onglets, panneau_fiche, panneau_lateral, panneau_liste, puce, sec_titre, statusbar,
                    table, v, vue)
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import (anneau, animer, cacher, choisir, classe, clic, compter, curseur, etat, fermer, montrer, ouvrir, pause,
                    saisir, texte, vue as aller)
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
COMPTA, ASSIST = P['compta'], P['assistante']
FOURN = demo.FOURNISSEUR
MENUS = ['Documents', 'Dossiers métier', 'Plan de classement', 'Analyse']
OBJET = 'Agrément fournisseur — %s' % FOURN
REF = 'DOS-2026-0041'
ETATS = ['Brouillon', 'En cours', 'Clôturé']
ECHEANCE = '15/10/2026 10:42'
# (pièce, type attendu, obligatoire, consigne, document fourni)
PIECES = [('Registre de commerce (RCCM)', 'Document générique', True, '', 'Registre de commerce (RCCM)'),
          ('Attestation de non-redevance fiscale (ANR)', 'Document générique', True, 'En cours de validité à la date du dépôt',
           'Attestation de non-redevance fiscale (ANR)'),
          ('Plan de localisation', 'Document générique', True, '', 'Plan de localisation'),
          ("Relevé d'identité bancaire", 'Document générique', False, '', "Relevé d'identité bancaire"),
          ('Contrat cadre signé', 'Contrat', False, '', '')]
POIGNEE = ('<svg viewBox="0 0 8 14" fill="#ADB5BD"><circle cx="2" cy="2" r="1.3"/><circle cx="6" cy="2" r="1.3"/>'
           '<circle cx="2" cy="7" r="1.3"/><circle cx="6" cy="7" r="1.3"/><circle cx="2" cy="12" r="1.3"/>'
           '<circle cx="6" cy="12" r="1.3"/></svg>')
FOURNIR = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" '
           'stroke-linejoin="round"><path d="M12 15V4m0 0L7.5 8.5M12 4l4.5 4.5M4 19h16"/></svg>')
ALEA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M3 7h4l10 10h4M3 17h4l10-10h4"/></svg>'


# --------------------------------------------------------------- la liste --
LIGNES = [('DOS-2026-0040', 'Dossier du personnel — %s' % P['archiviste'][0], 'Dossier du personnel', P['archiviste'][0],
           COMPTA[0], '', 75, '20/10/2026', 'Brouillon'),
          ('DOS-2026-0039', 'Agrément fournisseur — %s' % demo.TIERS, 'Agrément fournisseur', demo.TIERS, COMPTA[0],
           'Validation achats', 100, '24/10/2026', 'En cours'),
          ('DOS-2026-0038', 'Dossier du personnel — %s' % P['audit'][0], 'Dossier du personnel', P['audit'][0], ASSIST[0],
           '', 100, '18/10/2026', 'Clôturé'),
          ('DOS-2026-0037', 'Dossier du personnel — %s' % P['signataire'][0], 'Dossier du personnel', P['signataire'][0],
           ASSIST[0], '', 50, '30/10/2026', 'En cours'),
          ('DOS-2026-0036', 'Dossier du personnel — %s' % P['agent'][0], 'Dossier du personnel', P['agent'][0], ASSIST[0],
           '', 100, '09/10/2026', 'Clôturé')]
GENRE = {'Brouillon': 'gris', 'En cours': 'info', 'Clôturé': 'vert'}


def ecran_liste():
    lat = panneau_lateral([('▰ TYPES', [('Tous', '', True), ('Agrément fournisseur', '20', False), ('Dossier du personnel', '20', False)]),
                           ('≡ STATUT', [('Tous', '', True), ('Clôturé', '7', False), ('Brouillon', '4', False), ('En cours', '29', False)])])
    cols = [('Référence', '96px'), ('Objet', '1fr'), ('Type de dossier', '128px'), ('Tiers concerné', '140px'), ('Responsable', '96px'),
            ('Étape courante', '100px'), ('Complétude (%)', '96px'), ('Échéance du dossier', '84px'), ('Statut', '66px')]
    lignes = [{'id': 't16-l%d' % i, 'cellules': [r, o, t, ti, re, et,
                                                c_html('<span class="t16-mini"><span class="jauge"><i style="width:%d%%"></i></span>'
                                                       '<span class="jv">%d %%</span></span>' % (c, c)), d,
                                                c_html('<span>%s</span>' % puce(s, GENRE[s]))]}
              for i, (r, o, t, ti, re, et, c, d, s) in enumerate(LIGNES)]
    return vue('t16-liste', panneau_liste('Dossiers métier', '1-40 / 40', ident='t16') + lat + liste(cols, lignes), initiale=True
               ).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)


# ------------------------------------------------------------- la fiche --
def pieces(p, etats):
    """``etats`` : par pièce, (état, document fourni ?, validée ?)."""
    lignes = []
    for i, ((nom, typ, obl, consigne, doc), (st, fourni, valide)) in enumerate(zip(PIECES, etats)):
        rouge = obl and st == 'Manquante'
        classe_l = ' rouge' if rouge else (' verte' if st == 'Validée' else '')
        genre = {'Manquante': 'rouge', 'Fournie': 'info', 'Validée': 'vert'}[st]
        lignes.append({'id': '%s-p%d' % (p, i), 'cellules': [
            c_html('<span class="t16-poi">%s</span>' % POIGNEE),
            c_html('<span class="ell t16-nom%s" id="%s-p%d-nom">%s</span>' % (classe_l, p, i, e(nom))),
            c_html('<span class="ell t16-nom%s" id="%s-p%d-typ">%s</span>' % (classe_l, p, i, e(typ))),
            c_html(case(obl)),
            c_html('<span class="ell" id="%s-p%d-doc">%s</span>' % (p, i, e(doc) if fourni else '')),
            c_html('<span id="%s-p%d-val">%s</span>' % (p, i, interrupteur(valide))),
            c_html('<span>%s</span>' % puce(st, genre, '%s-p%d-et' % (p, i))),
            c_html('<span class="ell t16-nom%s" id="%s-p%d-con">%s</span>' % (classe_l, p, i, e(consigne))),
            c_html('<span class="t16-act%s" id="%s-p%d-bt"><span class="f">%sFournir</span><span class="o">%sOuvrir</span></span>'
                   % (' ok' if fourni else '', p, i, FOURNIR, ICONES['oeil'])),
            c_html('<span class="t16-corb">%s</span>' % ICONES['corbeille'])]})
    return table([('', '10px'), ('Pièce', '178px'), ('Type attendu', '112px'), ('Obligatoire', '58px'), ('Document fourni', '1fr'),
                  ('Validée', '46px'), ('État', '74px'), ('Consigne', '150px'), ('', '62px'), ('', '12px')],
                 lignes, identifiant='%s-pieces' % p, ajouter=False)


def corps_fiche(p, ref, objet, type_v, tiers_v, droite, meta_masque, etats, pieces_masque, bandeau_html=''):
    titre = ('<div class="titre-doc">%s</div>' % objet) if objet else '<div class="titre-doc">%s</div>' % entree(p + '-objet', 'Objet du dossier')
    tab = pieces(p, etats)
    if pieces_masque:
        for i in range(len(PIECES)):
            tab = tab.replace('class="tl" id="%s-p%d"' % (p, i), 'class="tl masque" id="%s-p%d"' % (p, i), 1)
    meta = ('<div class="%s" id="%s-meta">%s%s</div>'
            % ('masque' if meta_masque else '', p, sec_titre('Métadonnées'),
               grille2([champ("Catégorie d'achat", ''), champ('Plafond annuel (FCFA)', v('0,00'))], [champ("Agrément valide jusqu'au", '')])))
    return (bandeau_html
            + '<div class="ref-l">Référence</div><div class="ref-v moyen" id="%s-ref">%s</div>%s' % (p, ref, titre)
            + grille2([champ('Type de dossier', type_v), champ('Tiers concerné', tiers_v), champ('Responsable', v(COMPTA[0]))], droite)
            + meta + onglets(['Pièces', 'Circuit', 'Description'], 0) + tab)


def droite(p, ouvert, compl, manq, wf):
    return [champ('Échéance du dossier', ''), champ('Ouvert le', v(ouvert, identifiant=p + '-ouv')),
            champ('Clôturé le', v('', identifiant=p + '-clo')),
            champ('Complétude (%)', '<span class="jauge"><i id="%s-jg" style="width:%d%%"></i></span><span class="jv" id="%s-jv">%d %%</span>'
                  % (p, compl, p, compl), p + '-compl'),
            champ('Pièces obligatoires manquantes', v(manq, identifiant=p + '-manq'), p + '-manq-l'),
            champ('Circuit — statut', v(wf, identifiant=p + '-wf'), p + '-wf-l')]


def bandeau_circuit(p, etape, masque=True):
    return ('<div class="t16-info%s" id="%s-band">%sCircuit en cours — étape <b class="lien" id="%s-etape">%s</b> · échéance '
            '<span id="%s-ech">%s</span></div>' % (' masque' if masque else '', p, ALEA, p, e(etape), p, ECHEANCE))


def dialogue_fournir():
    """La fenêtre « Fournir » : la fiche du document, déjà typée et rattachée."""
    entete = ('<div class="t16-dh"><span class="t16-dbts">%s%s%s</span>%s</div>'
              % (bouton('t16d-fin', 'Finaliser', 'prim'), bouton('t16d-res', 'Réserver', 'second', 'cadenas'),
                 bouton('t16d-corb', 'Corbeille', 'second', 'corbeille'), statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 't16d-sb')))
    corps = (entete + '<div class="ref-l">Référence</div><div class="ref-v moyen">Nouveau</div>'
             + '<div class="titre-doc">Registre de commerce (RCCM)</div>'
             + grille2([champ('Type', v('Document générique')), champ('Dossier de classement', v('Achats et fournisseurs')),
                        champ('Confidentialité', v('Interne'))],
                       [champ('Propriétaire', v(COMPTA[0])), champ('Enregistrement lié', v('Dossier métier : %s' % OBJET), 't16d-lie')])
             + onglets(['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Description'], 0)
             + sec_titre('Téléverser une nouvelle version')
             + champ('Nouvelle version', '<span class="t16-up">%s<span class="t16-fic masque" id="t16d-fic">RCCM_Delta_Equipements.pdf</span></span>'
                     % bouton('t16d-charger', 'Charger votre fichier', 'prim'), 't16d-nv')
             + champ('Commentaire', entree('t16d-com'))
             + '<div style="margin:4px 0 6px">%s</div>' % bouton('t16d-ajout', 'Ajouter la version', 'prim', 'televerser')
             + table([('Version', '56px'), ('Nom du fichier', '1fr'), ('Commentaire de version', '150px'), ('Taille (o…', '70px'),
                      ('Téléversé par', '110px'), ('Date', '110px')],
                     [{'id': 't16d-v1', 'masque': True, 'cellules': ['v1', 'RCCM_Delta_Equipements.pdf', '', c_html('<span class="num">184 312</span>'),
                                                                    COMPTA[0], '13/10/2026 10:47']}], ajouter=False))
    return assistant('t16-dlg', 'Odoo', corps, [('t16d-enr', 'Enregistrer', 'prim'), ('t16d-ign', 'Ignorer', 'second')], haut=30, largeur=900)


def erreur():
    return assistant('t16-err', 'Opération invalide',
                     '<div class="t16-err">Le dossier est incomplet : 1 pièce(s) obligatoire(s) manquante(s). Seul un manager peut '
                     'forcer la clôture.</div>', [('t16-fermer', 'Fermer', 'prim')], haut=250, largeur=760)


def ecran_compta():
    p = 't16a'
    etats = [('Manquante', False, False)] * 5
    apres = [[bouton('t16-ann2', 'Annuler', 'second')],
             [bouton('t16-clot', 'Clôturer', 'second'), bouton('t16-ann3', 'Annuler', 'second')],
             []]
    bd = bande([bouton('t16-ouvrir', 'Ouvrir le dossier', 'prim'), bouton('t16-ann', 'Annuler', 'second'),
                bouton('t16-regen', 'Régénérer les pièces', 'second')], statusbar(ETATS, 0, 't16-sb'), 't16-b', apres)
    corps = corps_fiche(p, 'Nouveau', None, entree('t16a-type'), entree('t16a-tiers'), droite(p, '', 0, '0', 'Non lancé'),
                        True, etats, True, bandeau_circuit(p, 'Instruction'))
    stats = bouton_stat('Documents', '0', 'document', 't16-docs')
    fiche = vue('t16-fiche', panneau_fiche('Dossiers métier', 'Nouveau', '1 / 1', boutons_stat=stats, ref_id='t16-fil', sauver_id='t16-sauver')
                + '<div class="o-corps"><div class="o-gauche">%s<div class="t16-defil" id="t16a-defil">%s</div></div></div>'
                % (bd, feuille(corps, identifiant='t16a-feuille')))
    fiche = fiche.replace('<span class="sauver" id="t16-sauver">', '<span class="sauver masque" id="t16-sauver">', 1)
    return fenetre('ECM', MENUS, [ecran_liste(), fiche], COMPTA[1], COMPTA[2], calques=dialogue_fournir() + erreur(), ident='app-16a')


def ecran_assistante():
    p = 't16b'
    etats = [('Validée', True, True), ('Manquante', False, False), ('Fournie', True, False), ('Fournie', True, False),
             ('Manquante', False, False)]
    bd = bande([bouton('t16-traiter', 'Traiter', 'prim', 'lecture'), bouton('t16b-ann', 'Annuler', 'second')],
               statusbar(ETATS, 1, 't16b-sb'), 't16b-b')
    corps = corps_fiche(p, REF, e(OBJET), v('Agrément fournisseur', True), v(FOURN, True), droite(p, '13/10/2026', 60, '1', 'En cours'),
                        False, etats, False, bandeau_circuit(p, 'Instruction', masque=False))
    stats = bouton_stat('Documents', '3', 'document')
    fiche = vue('t16b-fiche', panneau_fiche('Dossiers métier', OBJET, '1 / 1', boutons_stat=stats)
                + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (bd, feuille(corps)), initiale=True)
    radio = ('<span class="t16-radio"><span class="r on" id="t16-r1"><i></i>Appliquer une transition</span>'
             '<span class="r"><i></i>Rejeter</span></span>')
    wiz = assistant('t16-wiz', 'Action — %s' % REF,
                    '<div class="t16-wz">%s%s%s%s%s</div>' % (
                        champ('Objet', v(REF)), champ('Étape courante', v('Instruction')), champ('Action', radio),
                        champ('Transition', entree('t16-trans'), 't16-trans-l'),
                        champ('Commentaire', entree('t16-com', 'Commentaire (obligatoire pour un rejet ou un retour)'))),
                    [('t16-valider', 'Valider', 'prim'), ('t16-wann', 'Annuler', 'second')], haut=170, largeur=760)
    html = fenetre('ECM', MENUS, [fiche], ASSIST[1], ASSIST[2], calques=wiz, ident='app-16b')
    return html.replace('class="o-app muk" id="app-16b"', 'class="o-app muk masque" id="app-16b"', 1)


CSS = """
#app-16b { z-index: 5; }
:is(#app-16a,#app-16b) .o-feuille { padding: 10px 16px 6px; }
:is(#app-16a,#app-16b) .o-feuille .titre-doc { margin-bottom: 4px; }
:is(#app-16a,#app-16b) .o-feuille .titre-doc { font-size: 20px; }
:is(#app-16a,#app-16b) .o-feuille .titre-doc .entree { font-size: 20px; min-height: 26px; width: 70%; }
:is(#app-16a,#app-16b) .o-feuille .champ { min-height: 21px; padding: 1px 0; grid-template-columns: 150px 1fr; }
:is(#app-16a,#app-16b) .o-feuille .sec-t { margin: 6px 0 3px; }
:is(#app-16a,#app-16b) .o-feuille .onglets { margin-top: 6px; }
:is(#app-16a,#app-16b) .o-feuille .og { padding: 6px 14px; }
:is(#app-16a,#app-16b) .o-table .tt { height: 26px; }
:is(#app-16a,#app-16b) .o-table .tl { height: 25px; }
:is(#app-16a,#app-16b) .t16-poi svg { width: 6px; height: 11px; display: block; }
:is(#app-16a,#app-16b) .t16-nom.rouge { color: #DC3545; }
:is(#app-16a,#app-16b) .t16-nom.verte { color: #198754; }
:is(#app-16a,#app-16b) .t16-act { color: #528099; display: inline-flex; }
:is(#app-16a,#app-16b) .t16-act > span { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
:is(#app-16a,#app-16b) .t16-act svg { width: 11px; height: 11px; }
:is(#app-16a,#app-16b) .t16-act .o { display: none; } :is(#app-16a,#app-16b) .t16-act.ok .o { display: inline-flex; }
:is(#app-16a,#app-16b) .t16-act.ok .f { display: none; }
:is(#app-16a,#app-16b) .t16-corb { color: #343A40; } :is(#app-16a,#app-16b) .t16-corb svg { width: 11px; height: 11px; display: block; }
:is(#app-16a,#app-16b) .t16-info { display: flex; align-items: center; gap: 6px; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px;
  background: #CFF4FC; color: #055160; font-size: 12.5px; }
:is(#app-16a,#app-16b) .t16-info svg { width: 13px; height: 13px; }
:is(#app-16a,#app-16b) .t16-info b { font-weight: 500; }
#app-16a .t16-mini { display: inline-flex; align-items: center; } #app-16a .t16-mini .jauge { width: 40px; }
#app-16a .t16-defil { position: relative; }
#t16-dlg .mc { padding: 10px 16px; }
#t16-dlg .t16-dh { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
#t16-dlg .t16-dbts { display: inline-flex; gap: 4px; }
#t16-dlg .titre-doc { font-size: 22px; margin: 2px 0 8px; }
#t16-dlg .champ { grid-template-columns: 140px 1fr; min-height: 24px; }
#t16-dlg .t16-up { display: inline-flex; align-items: center; gap: 10px; }
#t16-dlg .t16-fic { font-size: 12px; }
#t16-dlg .entree { width: 100%; }
#app-16a .t16-err { font-size: 13.5px; line-height: 1.5; }
#t16-err .mt { font-size: 22px; }
#t16-wiz .t16-wz .champ { grid-template-columns: 130px 1fr; min-height: 34px; align-items: center; }
#t16-wiz .t16-radio { display: flex; flex-direction: column; gap: 6px; }
#t16-wiz .t16-radio .r { display: inline-flex; align-items: center; gap: 7px; }
#t16-wiz .t16-radio i { width: 12px; height: 12px; border-radius: 50%; border: 1px solid #ADB5BD; }
#t16-wiz .t16-radio .r.on i { border: 4px solid #5D8DA8; }
"""


def fournir(i, nom, compl_de, compl_a, manq=None, ndoc=None, avec=True):
    """La pièce ``i`` devient fournie (document rattaché) ; la complétude suit."""
    g = [texte('#t16a-p%d-doc' % i, nom, avec=avec), etat('#t16a-p%d-et' % i, 'Fournie', 'info', avec=True),
         classe('#t16a-p%d-bt' % i, ajouter=['ok'], avec=True),
         classe('#t16a-p%d-nom' % i, retirer=['rouge'], avec=True), classe('#t16a-p%d-typ' % i, retirer=['rouge'], avec=True),
         classe('#t16a-p%d-con' % i, retirer=['rouge'], avec=True),
         animer('#t16a-jg', {'width': '%d%%' % compl_de}, {'width': '%d%%' % compl_a}, d=0.5, avec=True),
         compter('#t16a-jv', compl_de, compl_a, d=0.5, apres=' %', avec=True)]
    if manq is not None:
        g.append(texte('#t16a-manq', manq, avec=True))
    if ndoc is not None:
        g.append(texte('#t16-docs i', ndoc, avec=True))
    return g


TUTO = {
    'slug': 'tuto-16-les-dossiers-metier',
    'titre_page': 'AITE ECM — Tutoriel 16 : les dossiers métier',
    'titre': 'Les dossiers métier',
    'serie': dict(ECM, numero=16),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Ce dossier est-il *vraiment* *complet ?*',
        'sous': "Pièces éparpillées, relances au hasard.",
        'personnage': (COMPTA[0], 'Comptabilité', COMPTA[2]),
        'chaos': [('doc', 'RIB, version 2 ?'), ('alerte', 'Pièce manquante'), ('bulle', "Tu as reçu l'attestation ?"),
                  ('note', 'Checklist'), ('dossier', 'Chemise « Agréments »'), ('lettre', 'Relance fournisseur'),
                  ('bulle', 'On peut valider ?'), ('doc', 'RCCM de 2019')],
        'voix': "Un fournisseur demande son agrément. Registre de commerce, attestation fiscale, plan de localisation : "
                "il manque toujours une pièce, et personne ne sait laquelle.",
    },
    'revelation': {'voix': "Avec Aïte E C M, chaque dossier sait ce qui lui manque."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Des dossiers qui se *savent* *complets*',
        'pastilles': ['Pièces attendues', 'Complétude calculée', 'Clôture contrôlée'],
        'voix': "Le type de dossier fixe les pièces attendues et le circuit ; la complétude se calcule toute seule, et la "
                "clôture attend que l'essentiel soit là.",
    },
    'ecran': ecran_compta() + ecran_assistante(), 'vue_initiale': 't16-liste',
    'css': CSS,
    'etapes': [
        {'titre': 'Un type, et ses pièces attendues',
         'texte': "Le type « Agrément fournisseur » installe cinq pièces attendues, dont trois obligatoires.",
         'voix': "Hervé, à la comptabilité, crée un nouveau dossier métier. Il saisit l'objet, choisit le type "
                 "Agrément fournisseur, puis le tiers concerné. À l'enregistrement, le dossier reçoit sa référence, et "
                 "les cinq pièces attendues s'installent d'elles-mêmes, les obligatoires en rouge.",
         'gestes': [curseur('#t16-l1', fx=0.3, d=0.6), clic('#t16-nouveau'), aller('t16-fiche'),
                    clic('#t16a-objet', fx=0.2), saisir('t16a-objet', OBJET, d=1.0),
                    texte('#t16-fil', OBJET, avec=True, decale=1.0), montrer('#t16-sauver', y=0, d=0.2, avec=True),
                    clic('#t16a-type', fx=0.3), choisir('t16a-type', 'Agrément fournisseur'), montrer('#t16a-meta', y=8, d=0.3),
                    clic('#t16a-tiers', fx=0.3), choisir('t16a-tiers', FOURN),
                    clic('#t16-sauver'), cacher('#t16-sauver', d=0.2), texte('#t16a-ref', REF, avec=True),
                    texte('#t16a-manq', '3', avec=True),
                    montrer('#t16a-p0', y=8, d=0.25), montrer('#t16a-p1', y=8, d=0.25, avec=True, decale=0.1),
                    montrer('#t16a-p2', y=8, d=0.25, avec=True, decale=0.1), montrer('#t16a-p3', y=8, d=0.25, avec=True, decale=0.1),
                    montrer('#t16a-p4', y=8, d=0.25, avec=True, decale=0.1),
                    zoom('#t16a-p1-typ', s=1.25, fx=0.35, fy=0.6, d=0.8),
                    bulle('#t16a-p1-et', 'Obligatoire et manquante', cote='dessous', d=2.4), dezoom(d=0.6)]},
        {'titre': 'Fournir : la complétude suit',
         'texte': "Fournir crée le document, déjà typé, classé et rattaché : il n'y a plus qu'à charger le fichier.",
         'voix': "Pour chaque pièce, Fournir ouvre le document, déjà typé, classé et rattaché au dossier : Hervé charge le "
                 "fichier, et ajoute la version. La complétude se calcule toute seule. Trois pièces sur cinq : soixante "
                 "pour cent. L'attestation fiscale, obligatoire, manque encore.",
         'gestes': [clic('#t16a-p0-bt', fx=0.4), ouvrir('t16-dlg'), anneau('#t16d-lie', d=1.2),
                    clic('#t16d-charger'), montrer('#t16d-fic', y=0, d=0.3), clic('#t16d-ajout'), montrer('#t16d-v1', y=6, d=0.3),
                    clic('#t16d-enr'), fermer('t16-dlg')]
                   + fournir(0, PIECES[0][4], 0, 20, '2', '1', avec=False)
                   + [pause(0.6)] + fournir(2, PIECES[2][4], 20, 40, '1', '2', avec=False)
                   + [pause(0.3)] + fournir(3, PIECES[3][4], 40, 60, None, '3', avec=False)
                   + [clic('#t16a-p0-val', fx=0.5), classe('#t16a-p0-val .inter', ajouter=['on'], avec=True),
                      etat('#t16a-p0-et', 'Validée', 'vert', avec=True), classe('#t16a-p0-nom', ajouter=['verte'], avec=True),
                      classe('#t16a-p0-typ', ajouter=['verte'], avec=True), classe('#t16a-p0-con', ajouter=['verte'], avec=True),
                      zoom('#t16a-compl', s=1.6, fx=0.45, fy=0.5, d=0.8),
                      bulle('#t16a-jv', '3 pièces sur 5', cote='droite', d=2.0), anneau('#t16a-manq-l', d=1.2), dezoom(d=0.6)]},
        {'titre': 'Ouvrir le dossier : le circuit démarre',
         'texte': "Instruction, validation achats, décision : chaque étape revient aux rôles habilités, qui cliquent sur Traiter.",
         'voix': "Hervé ouvre le dossier : le circuit d'agrément démarre, instruction, validation achats, puis décision. "
                 "Chaque étape revient aux rôles habilités. Estelle, l'assistante, clique sur Traiter, et transmet le "
                 "dossier pour validation.",
         'gestes': [clic('#t16-ouvrir'), classe('#t16-sb-0', retirer=['actif'], avec=True), classe('#t16-sb-1', ajouter=['actif'], avec=True),
                    cacher('#t16-b-a', d=0.2, avec=True), montrer('#t16-b-b', y=0, avec=True),
                    montrer('#t16a-band', y=-6, d=0.35, avec=True), texte('#t16a-ouv', '13/10/2026', avec=True),
                    texte('#t16a-wf', 'En cours', avec=True),
                    bulle('#t16a-etape', 'Instruction : 48 h', cote='dessous', d=2.0),
                    pause(0.6), montrer('#app-16b', y=0, d=0.4), pause(0.3), clic('#t16-traiter'), ouvrir('t16-wiz'),
                    clic('#t16-trans', fx=0.3), choisir('t16-trans', 'Transmettre pour validation'),
                    clic('#t16-valider'), fermer('t16-wiz'), texte('#t16b-etape', 'Validation achats'),
                    texte('#t16b-ech', '16/10/2026 10:44', avec=True),
                    anneau('#t16b-band', d=1.2), bulle('#t16b-etape', 'Validation achats : 72 h', cote='dessous', d=2.0)]},
        {'titre': 'Clôturer ? Pas sans ses pièces',
         'texte': "Tant qu'une pièce obligatoire manque, la clôture est refusée ; seul un manager peut la forcer.",
         'voix': "Le circuit terminé, le dossier ne se clôt de lui-même que s'il est complet. Hervé tente de clôturer : "
                 "refusé, une pièce obligatoire manque, et seul un manager peut forcer. L'attestation fournie, la "
                 "clôture passe.",
         'gestes': [cacher('#app-16b', d=0.4), cacher('#t16a-band', d=0.3, avec=True), texte('#t16a-wf', 'Terminé', avec=True),
                    cacher('#t16-b-b', d=0.2, avec=True), montrer('#t16-b-c', y=0, avec=True),
                    anneau('#t16a-wf-l', d=1.0), clic('#t16-clot'), ouvrir('t16-err'),
                    zoom('#t16-err', s=1.3, d=0.7), bulle('#t16-err .t16-err', 'Clôture refusée', cote='dessous', fx=0.3, d=2.2),
                    dezoom(d=0.5), clic('#t16-fermer'), fermer('t16-err')]
                   + fournir(1, PIECES[1][4], 60, 80, '0', '4', avec=False)
                   + [pause(0.4), clic('#t16-clot'), classe('#t16-sb-1', retirer=['actif']),
                      classe('#t16-sb-2', ajouter=['actif'], avec=True), cacher('#t16-b-c', d=0.2, avec=True),
                      texte('#t16a-clo', '16/10/2026', avec=True), anneau('#t16-sb-2', d=1.4)]},
    ],
    'benefices': {
        'titre': 'Des dossiers *complets,* enfin.',
        'voix': "Des pièces attendues dès la création, une complétude toujours à jour, et une clôture impossible tant que "
                "l'essentiel manque.",
        'cartes': [('cible', '5 pièces', 'Une liste attendue', "Le type de dossier fixe les pièces, obligatoires ou non."),
                   ('trace', 'Complétude', 'Calculée, pas estimée', "Chaque pièce fournie fait monter le taux, sans calcul à la main."),
                   ('bouclier', 'Clôturer', 'Une clôture contrôlée', "Refusée tant qu'une pièce obligatoire manque, sauf manager.")],
    },
    'cta': cta('ecm', 'Le dossier *complet,* avant *tout.*', "Aïte E C M : le dossier complet, avant tout."),
    'youtube': youtube('COMMENT GÉRER DES DOSSIERS MÉTIER COMPLETS AVEC AITE ECM (ODOO 18)',
                       "Un dossier métier connaît ses pièces attendues : le type « Agrément fournisseur » les installe à la "
                       "création, chaque pièce fournie fait monter la complétude, le circuit d'agrément se lance à l'ouverture, "
                       "et la clôture est refusée tant qu'une pièce obligatoire manque. Tutoriel AITE ECM pour Odoo 18.",
                       ['AITE ECM', 'dossier métier', 'complétude', 'agrément fournisseur', 'GED Odoo', 'workflow']),
}
