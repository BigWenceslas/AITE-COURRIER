# -*- coding: utf-8 -*-
"""Tutoriel 06 — Capture automatique des e-mails.

Sources :
- aite_courrier_capture/__manifest__.py (alias ``courrier@<domaine>``, courrier
  en brouillon, objet = sujet, expéditeur extrait du ``From``, contact lié
  s'il est reconnu, type par défaut, pièces jointes → documents versionnés v1,
  petites images écartées, corps dans le fil, audit source « Système ») ;
- aite_courrier_capture/data/mail_alias_data.xml (alias ``courrier``, modèle
  courrier, ``alias_contact`` = everyone) ;
- aite_courrier_capture/models/aite_courrier.py : ``message_new`` (subject,
  sender, sender_email, sender_partner_id = author_id, type_id, date_received
  du jour), ``_capture_default_type`` (type marqué, sinon premier type
  « Entrant »), ``_capture_attachments_to_ged`` (images < 8 Ko écartées,
  ``add_version`` → v1), audit « Courrier créé par e-mail » ;
- aite_courrier_capture/models/aite_courrier_type.py et
  views/aite_courrier_type_views.xml (« Type par défaut (capture e-mail) ») ;
- aite_courrier_base/views/aite_courrier_menus.xml (Configuration › Types de
  courrier, réservé au groupe admin), aite_courrier_referentiel_views.xml
  (liste Code / Libellé / Catégorie, fiche du type), data (types ENTR…) ;
- aite_courrier_core/views/aite_courrier_views.xml (filtre « Brouillons »,
  liste, fiche, « Enregistrer et lancer le circuit », « Aperçu du circuit »,
  « Historique expéditeur ») et models/aite_courrier.py (libellés des champs,
  nom affiché « objet (brouillon) », lancement : référence, statut Nouveau) ;
- aite_courrier_ged (onglet « Documents », colonnes, état « Brouillon »),
  aite_courrier_core/views/aite_courrier_type_views.xml (« Accusé de réception
  automatique »), aite_courrier_ged/models/aite_courrier_type.py (« Dossier GED
  par défaut »), aite_courrier_ecm (« Documents ECM ») ;
- docs/TUTORIEL_CAPTURE_OCR.md (A.1 à A.5 : prérequis serveur entrant).
Écrans : composés d'après la base de démonstration (thème MuK) ; liste des
courriers reprise de la présentation, chapitre 1. La messagerie du tiers est
générique, sans marque.
"""

import demo
from ecrans import (ICONES, bande, bouton, bouton_stat, c_html, c_lien, c_num, case, champ, chatter, e, entree, fenetre,
                    feuille, grille2, liste, onglets, panneau_fiche, panneau_lateral, panneau_liste, puce, sec_titre,
                    statusbar, table, v, vue)
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, animer, cacher, choisir, classe, clic, curseur, defiler, etat, montrer, pause, saisir, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

AGENT = demo.PERSONNES['agent']
ADMIN = demo.PERSONNES['admin']
TIERS, COURRIEL = demo.TIERS, demo.TIERS_COURRIEL
ALIAS = 'courrier@aite-demo.test'
OBJET = 'Réclamation — facture de septembre'
DATE = demo.NOUVEAU['date']
REF = 'COUR-2026-0142'
PJ = [('reclamation.pdf', '184 Ko', 'pdf'), ('facture_septembre.pdf', '96 Ko', 'pdf'), ('logo.png', '3 Ko', 'img')]
CORPS = ("Bonjour,", "Nous contestons le montant de la facture de septembre. Vous trouverez ci-joint notre réclamation "
         "et la facture concernée.", "Cordialement,", "Service clients — %s" % TIERS)

# Les brouillons : le courrier capturé en tête, puis les brouillons déjà là.
CAPTURE = ('', OBJET, 'Courrier entrant', '', '', 'Brouillon', 'gris', DATE)
BROUILLONS = [
    ('', 'Suite à votre demande COUR-2026-0010', 'Courrier sortant', 'Juridique', '', 'Brouillon', 'gris', '08/10/2026'),
    ('', 'Facture F-2026-0412 — fournitures de bureau', 'Facture', 'Finance et comptabilité', '', 'Brouillon', 'gris', '06/10/2026'),
    ('', "Note de service — congés de fin d'année", 'Courrier interne', 'Ressources humaines', '', 'Brouillon', 'gris', '02/10/2026'),
    ('', 'Devis D-2026-7712 — maintenance des ascenseurs', 'Devis', 'Direction générale', '', 'Brouillon', 'gris', '29/09/2026'),
]


# La liste du chapitre 1, sans son brouillon de tête (un autre courrier).
AUTRES = list(base.LIGNES_COURRIERS[1:])


def _jour(ligne):
    j, m, a = ligne[7].split('/')
    return a + m + j


# ------------------------------------------------------------- l'écran --
def _messagerie():
    """La messagerie du tiers : générique, sans marque."""
    env = ('<svg viewBox="0 0 24 24" fill="none" stroke="#3C4A5C" stroke-width="2" stroke-linejoin="round">'
           '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6l8.5 7 8.5-7"/></svg>')
    pdf = ('<svg viewBox="0 0 24 24" fill="none" stroke="#C0392B" stroke-width="2" stroke-linejoin="round">'
           '<path d="M14 2H6v20h12V6z"/><path d="M14 2v4h4"/></svg>')
    img = ('<svg viewBox="0 0 24 24" fill="none" stroke="#2E7D5B" stroke-width="2" stroke-linejoin="round">'
           '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 16l5-5 4 4 3-3 6 6"/></svg>')
    pjs = ''.join('<span class="wm-pj" id="t6-wm-pj%d"><span class="wm-pi">%s</span><b>%s</b><i>%s</i></span>'
                  % (i, pdf if k == 'pdf' else img, e(n), e(t)) for i, (n, t, k) in enumerate(PJ))
    corps = ''.join('<p>%s</p>' % e(x) for x in CORPS)
    dossiers = ''.join('<div class="wm-dos%s">%s<i>%s</i></div>' % (' actif' if i == 0 else '', e(n), e(c))
                       for i, (n, c) in enumerate([('Boîte de réception', '12'), ('Envoyés', ''), ('Brouillons', '1'), ('Corbeille', '')]))
    carte = ('<div class="wm-carte" id="t6-wm-carte"><div class="wm-ct"><span>Nouveau message</span><span>— ✕</span></div>'
             '<div class="wm-ligne"><span class="wm-l">De</span><span>%s &lt;%s&gt;</span></div>'
             '<div class="wm-ligne"><span class="wm-l">À</span>%s</div>'
             '<div class="wm-ligne"><span class="wm-l">Objet</span><span>%s</span></div>'
             '<div class="wm-corps">%s</div><div class="wm-pjs" id="t6-wm-pjs">%s</div>'
             '<div class="wm-pied"><span class="wm-env" id="t6-wm-envoyer">Envoyer</span><span class="wm-tr">%s</span></div></div>'
             % (e(TIERS), e(COURRIEL), entree('t6-wm-a', 'Destinataires'), e(OBJET), corps, pjs, ICONES['trombone']))
    return ('<div class="o-app t6wm masque" id="t6-wm"><div class="wm-haut"><span class="wm-logo">%s</span><b>Messagerie</b>'
            '<span class="wm-rech">Rechercher dans les messages</span><span class="wm-av">G</span></div>'
            '<div class="wm-lat"><div class="wm-nouv">Nouveau message</div>%s</div>%s'
            '<div class="wm-ok masque" id="t6-wm-ok">Message envoyé</div></div>' % (env, dossiers, carte))


def _liste_initiale():
    lignes = sorted(AUTRES + [b for b in BROUILLONS if b not in AUTRES], key=_jour, reverse=True)
    lat = panneau_lateral([('▰ CATÉGORIE', [('Tous', '', True), ('Entrant', '61', False), ('Interne', '22', False),
                                            ('Sortant', '52', False)]),
                           ('≡ STATUT', [('Archivé', '50', False), ('Brouillon', '4', False), ('Nouveau', '16', False),
                                         ('En traitement', '54', False), ('Rejeté', '11', False)])], 't6-lat')
    filtres = ('<div class="t6-dd masque" id="t6-filtres"><div class="t6-col"><div class="t6-h">▼ Filtres</div>%s<hr>%s<hr>'
               '<div class="t6-it">Ajouter un filtre personnalisé</div></div>'
               '<div class="t6-col"><div class="t6-h">◆ Regrouper par</div>%s<hr><div class="t6-it">Ajouter un groupe personnal…</div></div>'
               '<div class="t6-col"><div class="t6-h">★ Favoris</div><div class="t6-it">Enregistrer la recherche a…</div></div></div>'
               % (''.join('<div class="t6-it" id="t6-f%d">%s</div>' % (i, e(n)) for i, n in
                          enumerate(['Brouillons', 'Traités', 'En retard (SLA)', 'Mes courriers', 'Reçus ce mois'])),
                  ''.join('<div class="t6-it">%s</div>' % e(n) for n in ['Entrants', 'Sortants', 'Internes']),
                  ''.join('<div class="t6-it">%s</div>' % e(n) for n in ['Type', 'Statut', 'Priorité', 'Service'])))
    return vue('t6-liste', panneau_liste('Courriers', '1-80 / 135', ident='t6', recherche_id='t6-rech') + lat
               + liste(base.COL_COURRIERS, [base.ligne_courrier('t6-l%d' % i, *l) for i, l in enumerate(lignes)]) + filtres,
               initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)


def _liste_brouillons():
    lat = panneau_lateral([('▰ CATÉGORIE', [('Tous', '', True), ('Entrant', '2', False), ('Interne', '1', False),
                                            ('Sortant', '2', False)]),
                           ('≡ STATUT', [('Brouillon', '5', False)])])
    return vue('t6-brouillons', panneau_liste('Courriers', '1-5 / 5', facettes=[('≡', 'Brouillons')])
               + lat + liste(base.COL_COURRIERS, [base.ligne_courrier('t6-b%d' % i, *l) for i, l in enumerate([CAPTURE] + BROUILLONS)])
               ).replace('class="vue"', 'class="vue avec-lateral"', 1)


def _fiche():
    stats = bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '2')
    circuit = ('<div id="t6-circuit">%s%s%s</div>' % (
        sec_titre('Aperçu du circuit'), champ('Circuit prévu', v('Courrier entrant standard', True)),
        table([('Séquence', '70px'), ('Nom', '1fr'), ('SLA (heures)', '90px'), ('Étape initiale', '90px'), ('Étape finale', '80px')],
              [{'id': 't6-s%d' % i, 'cellules': [c_num(str(i + 1)), n, c_num(s), c_html(case(i == 0)), c_html(case(i == 4))]}
               for i, (n, s) in enumerate(zip(base.ETAPES, ['4', '8', '4', '48', '24']))], ajouter=False)))
    prev = '<span class="lien t6-prev">%s Prévisualiser</span>' % ICONES['oeil']
    docs = table([('Nom', '1fr'), ('Dossier', '52px'), ('Étiquettes', '62px'), ('Extension', '62px'), ('Nombre de versions', '72px'),
                  ('État', '66px'), ('Verrouillé', '58px'), ('', '92px')],
                 [{'id': 't6-d%d' % i, 'cellules': [n, '', '', 'pdf', c_html('<span class="num" id="t6-d%d-v">1</span>' % i),
                                                    c_html('<span>%s</span>' % puce('Brouillon')), c_html(case(False)), c_html(prev)]}
                  for i, n in enumerate(['facture_septembre.pdf', 'reclamation.pdf'])], identifiant='t6-docs')
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v" id="t6-ref"></div>'
             + '<div id="t6-champs">' + grille2(
                 [champ('Objet', v(OBJET, identifiant='t6-objet')),
                  champ('Contact expéditeur', v(TIERS, identifiant='t6-contact'), aide=True),
                  champ('Expéditeur', v(TIERS, identifiant='t6-exp')),
                  champ('E-mail expéditeur', v(COURRIEL, identifiant='t6-mail-exp'), aide=True),
                  champ('Type', v('Courrier entrant', identifiant='t6-typev')),
                  champ('Service destinataire', entree('t6-service'))],
                 [champ('Statut', puce('Brouillon', 'gris', 't6-statut'), aide=True), champ('Priorité', ''),
                  champ('Confidentialité', ''), champ('Date de réception', v(DATE, identifiant='t6-date')),
                  champ('Responsable', '')]) + '</div>'
             + circuit + onglets(['Documents', 'Historique']) + docs)
    apres = [bouton('t6-traiter', 'Traiter', 'prim'), bouton('t6-rejeter', 'Rejeter', 'second'),
             bouton('t6-comm2', 'Commenter', 'second'), bouton('t6-rep', 'Répondre', 'second', 'retour')]
    bd = bande([bouton('t6-lancer', 'Enregistrer et lancer le circuit', 'prim'), bouton('t6-comm', 'Commenter', 'second')],
               '<span class="masque" id="t6-sb">%s</span>' % statusbar(base.ETAPES, 0, 't6-etapes'), 't6-bande', apres)
    batiment = ('<svg viewBox="0 0 24 24" fill="#fff"><path d="M5 3h10v18H5zM16 9h3v12h-3z"/><path d="M7.5 6h2v2h-2zm3 0h2v2h-2zm-3 4h2v2h-2zm3 '
                '0h2v2h-2zm-3 4h2v2h-2zm3 0h2v2h-2z" fill="#9AA3AD"/></svg>')
    pdf = '<span class="t6-pi">%s</span>' % ICONES['pdf']
    pjs = ''.join('<div class="t6-pj" id="t6-pj%d">%s<span><b>%s</b><i>%s</i></span></div>'
                  % (i, pdf if k == 'pdf' else '<span class="t6-vig"></span>', e(n), 'PDF' if k == 'pdf' else 'PNG')
                  for i, (n, _, k) in enumerate(PJ))
    courriel = ('<div class="msg" id="t6-mail"><span class="av" style="background:#B8C0C8">%s</span><div class="t6-mc">'
                '<div class="au">%s <i>10:29</i></div><div class="t6-bulle"><div class="t6-sujet">Sujet : %s</div>%s</div>'
                '<div class="t6-pjs">%s</div></div></div>'
                % (batiment, e(TIERS), e(OBJET), ''.join('<p>%s</p>' % e(x) for x in CORPS), pjs))
    ch = chatter([courriel], identifiant='t6-chatter', suivre='')
    return vue('t6-fiche', panneau_fiche('Courriers', '%s (brouillon)' % OBJET, boutons_stat=stats, ref_id='t6-titre')
               + '<div class="o-corps"><div class="o-gauche"><div id="t6-defil">%s%s</div></div>%s</div>'
               % (bd, feuille(corps), ch))


def _admin():
    types = [('DEVIS', 'Devis', 'Sortant'), ('ENTR', 'Courrier entrant', 'Entrant'), ('FACT', 'Facture', 'Entrant'),
             ('INT', 'Courrier interne', 'Interne'), ('SORT', 'Courrier sortant', 'Sortant')]
    accueil = vue('t6a-liste', panneau_liste('Courriers', '1-80 / 136', ident='t6a') + base.lat_courriers(None)
                  + liste(base.COL_COURRIERS, [base.ligne_courrier('t6a-l%d' % i, *l) for i, l in
                                               enumerate([(REF, OBJET, 'Courrier entrant', 'Finance et comptabilité', 'Réception', 'Nouveau', 'gris', DATE)]
                                                         + AUTRES)]),
                  initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    lst = vue('t6-types', panneau_liste('Types de courrier', '1-5 / 5', ident='t6t')
              + liste([('Code', '260px'), ('Libellé', '1fr'), ('Catégorie', '300px')],
                      [{'id': 't6t-l%d' % i, 'cellules': list(t)} for i, t in enumerate(types)]))
    coche = '<span class="case" id="t6-cap">%s</span>' % ICONES['coche']
    fiche = vue('t6-type', panneau_fiche('Types de courrier', 'Courrier entrant', '2 / 5', sauver_id='t6-sauver')
                + '<div class="o-corps"><div class="o-gauche">%s</div></div>' % feuille(grille2(
                    [champ('Code', v('ENTR')), champ('Libellé', v('Courrier entrant'))],
                    [champ('Catégorie', v('Entrant'), aide=True),
                     champ('Type par défaut (capture e-mail)', coche, 't6-cap-l', aide=True),
                     champ('Dossier GED par défaut', '', aide=True),
                     champ('Accusé de réception automatique', case(False), aide=True),
                     champ('Actif', case(True))]), identifiant='t6-type-f'))
    menu = ('<div class="t6-dd t6-cfg masque" id="t6-cfg">%s</div>'
            % ''.join('<div class="t6-it" id="t6-cfg%d">%s</div>' % (i, e(n)) for i, n in enumerate(
                ['Types de courrier', 'Priorités', 'Niveaux de confidentialité', 'Circuits de traitement', 'Dossiers',
                 'Étiquettes de documents', 'Modèles de réponse'])))
    html = fenetre('Courrier', ['Tableau de bord', 'Courriers', 'Espace documentaire', 'Audit', 'Configuration'],
                   [accueil, lst, fiche], ADMIN[1], ADMIN[2], ident='app-6b')
    html = html.replace('<span class="menu" id="app-6b-m4">Configuration</span>',
                        '<span class="menu t6-menu" id="app-6b-m4">Configuration%s</span>' % menu, 1)
    html = html.replace('<span class="sauver" id="t6-sauver">', '<span class="sauver masque" id="t6-sauver">', 1)
    return html.replace('class="o-app muk" id="app-6b"', 'class="o-app muk masque" id="app-6b"', 1)


def ecran():
    agent = fenetre('Courrier', ['Courriers', 'Espace documentaire'], [_liste_initiale(), _liste_brouillons(), _fiche()],
                    AGENT[1], AGENT[2], ident='app-6')
    return agent + _admin() + _messagerie()


CSS = """
#t6-wm { background: #F6F7FB; font-family: var(--sans); color: #1F2933; }
#t6-wm .wm-haut { height: 54px; display: flex; align-items: center; gap: 12px; padding: 0 20px; background: #fff; border-bottom: 1px solid #E3E6EC; }
#t6-wm .wm-logo svg { width: 26px; height: 26px; display: block; }
#t6-wm .wm-haut b { font-size: 17px; font-weight: 600; color: #3C4A5C; }
#t6-wm .wm-rech { margin-left: 70px; width: 420px; height: 34px; border-radius: 17px; background: #EEF1F6; color: #8A93A0; font-size: 13px;
  display: flex; align-items: center; padding: 0 18px; }
#t6-wm .wm-av { margin-left: auto; width: 30px; height: 30px; border-radius: 50%; background: #1E8E8A; color: #fff; font-weight: 600;
  display: flex; align-items: center; justify-content: center; }
#t6-wm .wm-lat { position: absolute; left: 0; top: 54px; bottom: 0; width: 196px; padding: 16px 12px; }
#t6-wm .wm-nouv { display: inline-block; padding: 10px 18px; border-radius: 14px; background: #DCE4EE; font-size: 13px; font-weight: 600;
  color: #3C4A5C; margin-bottom: 14px; }
#t6-wm .wm-dos { display: flex; justify-content: space-between; padding: 7px 12px; border-radius: 0 14px 14px 0; font-size: 13px; color: #3C4A5C; }
#t6-wm .wm-dos.actif { background: #E3E8F0; font-weight: 600; }
#t6-wm .wm-dos i { font-style: normal; font-size: 12px; }
#t6-wm .wm-carte { position: absolute; left: 236px; top: 74px; width: 640px; height: 520px; background: #fff; border-radius: 12px;
  box-shadow: 0 18px 44px rgba(28,35,48,.22), 0 0 0 1px rgba(28,35,48,.06); overflow: hidden; }
#t6-wm .wm-ct { height: 42px; display: flex; justify-content: space-between; align-items: center; padding: 0 16px; background: #3C4A5C;
  color: #fff; font-size: 14px; font-weight: 600; }
#t6-wm .wm-ligne { height: 40px; display: flex; align-items: center; gap: 12px; padding: 0 18px; border-bottom: 1px solid #EDF0F4; font-size: 13.5px; }
#t6-wm .wm-l { width: 46px; color: #7A8492; }
#t6-wm .entree { width: 300px; border-bottom: 0; font-size: 13.5px; }
#t6-wm .wm-corps { padding: 14px 18px 4px; font-size: 13.5px; line-height: 1.55; height: 166px; }
#t6-wm .wm-corps p { margin-bottom: 8px; }
#t6-wm .wm-pjs { display: flex; flex-wrap: wrap; gap: 8px; padding: 6px 18px; }
#t6-wm .wm-pj { display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px; border: 1px solid #D5DAE1; border-radius: 8px;
  font-size: 12.5px; background: #FAFBFC; }
#t6-wm .wm-pj b { font-weight: 500; } #t6-wm .wm-pj i { font-style: normal; color: #8A93A0; }
#t6-wm .wm-pi svg { width: 17px; height: 17px; display: block; }
#t6-wm .wm-pied { position: absolute; left: 0; right: 0; bottom: 0; height: 64px; display: flex; align-items: center; gap: 14px; padding: 0 18px;
  border-top: 1px solid #EDF0F4; }
#t6-wm .wm-env { padding: 9px 26px; border-radius: 18px; background: #2F6FDE; color: #fff; font-size: 14px; font-weight: 600; }
#t6-wm .wm-tr svg { width: 20px; height: 20px; display: block; }
#t6-wm .wm-ok { position: absolute; left: 24px; bottom: 24px; padding: 12px 20px; border-radius: 8px; background: #2B3440; color: #fff;
  font-size: 13.5px; box-shadow: 0 10px 24px rgba(0,0,0,.25); }
#app-6 .t6-dd, #app-6b .t6-dd { position: absolute; z-index: 30; background: #fff; border: 1px solid #DEE2E6; border-radius: 4px;
  box-shadow: 0 10px 26px rgba(0,0,0,.16); font-size: 12.5px; color: #212529; }
#t6-filtres { left: 300px; top: 50px; width: 548px; display: grid; grid-template-columns: 1.15fr 1.1fr 1fr; padding: 10px 0; }
#t6-filtres .t6-col { padding: 0 14px; } #t6-filtres .t6-col + .t6-col { border-left: 1px solid #E9ECEF; }
#app-6 .t6-h { font-weight: 600; font-size: 13px; margin: 2px 0 6px; }
#app-6 .t6-it, #app-6b .t6-it { padding: 4px 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#t6-filtres hr { border: 0; border-top: 1px solid #E9ECEF; margin: 6px 0; }
#app-6b .t6-menu { position: relative; }
#t6-cfg { left: -10px; top: 29px; width: 178px; padding: 6px 0; font-size: 12px; }
#t6-cfg .t6-it { padding: 5px 14px; }
#t6-mail .t6-mc { min-width: 0; }
#t6-mail .av svg { width: 20px; height: 20px; }
#t6-mail .t6-bulle { margin-top: 3px; padding: 6px 8px; border: 1px solid #A8D8E2; border-radius: 6px; background: #E3F3F6; font-size: 11px;
  line-height: 1.4; }
#t6-mail .t6-sujet { font-style: italic; color: #5C6670; font-size: 10.5px; margin-bottom: 3px; }
#t6-mail .t6-bulle p { margin-bottom: 3px; }
#t6-mail .t6-pjs { margin-top: 6px; display: flex; flex-direction: column; gap: 4px; }
#t6-mail .t6-pj { display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-radius: 4px; background: #E9ECEF; font-size: 10.5px;
  line-height: 1.2; }
#t6-mail .t6-pj b { display: block; font-weight: 500; } #t6-mail .t6-pj i { font-style: normal; color: #6C757D; font-size: 9.5px; }
#t6-mail .t6-pi { width: 20px; height: 22px; border: 1px solid #DC3545; border-radius: 3px; background: #fff; display: flex; align-items: center;
  justify-content: center; } #t6-mail .t6-pi svg { width: 12px; height: 12px; }
#t6-mail .t6-vig { width: 20px; height: 22px; border-radius: 3px; background: #CDD3DA; }
#t6-champs .v { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#t6-docs .t6-prev { display: inline-flex; align-items: center; gap: 4px; }
#t6-docs .t6-prev svg { width: 12px; height: 12px; }
#t6-type-f .champ { grid-template-columns: 132px 1fr; min-height: 30px; }
#t6-circuit { overflow: hidden; }
#t6-cap svg { opacity: 0; } #t6-cap.on svg { opacity: 1; }
"""

TUTO = {
    'slug': 'tuto-06-capture-automatique-des-e-mails',
    'titre_page': 'AITE Courrier — Tutoriel 06 : capture automatique des e-mails',
    'titre': 'Capture automatique des e-mails',
    'serie': dict(COURRIER, numero=6),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Vos courriers arrivent *aussi* par *e-mail ?*',
        'sous': 'Boîte partagée, pièces jointes à télécharger, ressaisie à la main : un e-mail important finit par se perdre.',
        'personnage': (AGENT[0], 'Agent courrier', AGENT[2]),
        'chaos': [('lettre', 'Boîte partagée saturée'), ('alerte', 'Réclamation oubliée'), ('bulle', 'Qui a traité ce mail ?'),
                  ('note', 'À ressaisir'), ('doc', 'facture (1).pdf'), ('bulle', 'Tu me le transfères ?'),
                  ('dossier', 'Téléchargements'), ('alerte', 'Pièce jointe perdue')],
        'voix': "Les courriers arrivent aussi par e-mail. Il faut les ressaisir, télécharger les pièces jointes… "
                "et une réclamation finit par s'oublier dans la boîte partagée.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, l'e-mail devient un courrier, tout seul."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Vos *e-mails* deviennent des *courriers*',
        'pastilles': ['Brouillon déjà rempli', 'Pièces jointes versionnées', 'Rien à ressaisir'],
        'voix': "Chaque e-mail envoyé à l'adresse dédiée crée un brouillon déjà rempli, et ses pièces jointes deviennent "
                "des documents versionnés. Voyons comment.",
    },
    'ecran': ecran(), 'vue_initiale': 't6-liste',
    'css': CSS,
    'etapes': [
        {'titre': 'Un e-mail, un brouillon',
         'texte': "Tout e-mail envoyé à l'adresse dédiée crée un courrier en brouillon, sans aucune ressaisie.",
         'voix': "Un client envoie sa réclamation à l'adresse dédiée, courrier arobase votre domaine, avec la facture en "
                 "pièce jointe. Côté Aïte Courrier, Carine n'a rien à saisir : elle filtre les brouillons, et le courrier "
                 "est déjà là, créé dès l'arrivée de l'e-mail.",
         'gestes': [texte('#pr-url', 'webmail.horizon-services.test'), montrer('#t6-wm', y=0, d=0.4, avec=True),
                    zoom('#t6-wm-carte', s=1.25, d=0.8), clic('#t6-wm-a', fx=0.15), saisir('t6-wm-a', ALIAS, d=1.2),
                    bulle('#t6-wm-a', "L'adresse dédiée", cote='droite', fx=0.62, d=2.0),
                    curseur('#t6-wm-envoyer', fx=0.4, d=0.6, avec=True, decale=0.3), anneau('#t6-wm-pjs', d=1.2),
                    clic('#t6-wm-envoyer'),
                    animer('#t6-wm-carte', {'autoAlpha': 1, 'y': 0, 'scale': 1}, {'autoAlpha': 0, 'y': -60, 'scale': 0.8}, d=0.5),
                    dezoom(d=0.6), montrer('#t6-wm-ok', y=12, d=0.3), pause(0.5),
                    cacher('#t6-wm', d=0.35), texte('#pr-url', ADRESSE % 'courrier', avec=True),
                    clic('#t6-rech .drop'), montrer('#t6-filtres', y=8, d=0.25), clic('#t6-f0', fx=0.3), aller('t6-brouillons'),
                    classe('#t6-b0', ajouter=['survol']), anneau('#t6-b0', d=1.2), bulle('#t6-b0', 'Courrier créé par e-mail', cote='dessous', fx=0.3, d=2.2)]},
        {'titre': 'Un brouillon déjà rempli',
         'texte': "Objet, expéditeur, e-mail, contact, type et date de réception : tout vient du message.",
         'voix': "Elle l'ouvre. L'objet reprend le sujet de l'e-mail, l'expéditeur et son adresse viennent de l'en-tête, "
                 "le contact connu est lié, et le type par défaut est posé. Le message d'origine reste dans le fil de discussion.",
         'gestes': [clic('#t6-b0', fx=0.3), aller('t6-fiche'), zoom('#t6-champs', s=1.45, fx=0.5, fy=0.45, d=0.8),
                    anneau('#t6-objet', d=1.0), bulle('#t6-objet', "Le sujet de l'e-mail", cote='droite', d=1.8),
                    anneau('#t6-exp', d=0.8), anneau('#t6-mail-exp', d=0.8), anneau('#t6-contact', d=0.8),
                    bulle('#t6-typev', 'Type par défaut', cote='droite', d=1.8), dezoom(d=0.6),
                    anneau('#t6-mail', d=1.2), bulle('#t6-mail .t6-bulle', "Le message d'origine", cote='dessous', fx=0.3, d=2.0)]},
        {'titre': 'Pièces jointes, puis circuit',
         'texte': "Les pièces jointes deviennent des documents versionnés ; il ne reste qu'à qualifier et lancer.",
         'voix': "Ses pièces jointes sont devenues des documents du courrier, chacun en version 1 ; les petites images, "
                 "comme les logos de signature, sont écartées. Il ne reste qu'à qualifier : Carine choisit le service "
                 "destinataire, puis lance le circuit. La référence est attribuée.",
         'gestes': [defiler('#t6-defil', y=-110, d=0.8), curseur('#t6-d1', fx=0.62, fy=0.9, d=0.7, avec=True),
                    zoom('#t6-docs', s=1.35, d=0.8),
                    anneau('#t6-docs', d=1.0), bulle('#t6-d1-v', 'Version v1', cote='dessous', d=1.8), dezoom(d=0.6),
                    anneau('#t6-pj2', d=1.0), bulle('#t6-pj2', 'Image de 3 Ko : écartée', cote='dessous', fx=0.3, d=2.0),
                    defiler('#t6-defil', y=0, d=0.7), clic('#t6-service', fx=0.3), choisir('t6-service', 'Finance et comptabilité'),
                    clic('#t6-lancer'),
                    animer('#t6-circuit', {'height': 233, 'autoAlpha': 1}, {'height': 0, 'autoAlpha': 0}, d=0.45),
                    texte('#t6-ref', REF, avec=True),
                    texte('#t6-titre', REF, avec=True), etat('#t6-statut', 'Nouveau', 'gris', avec=True, decale=0.1),
                    cacher('#t6-bande-a', d=0.2), montrer('#t6-bande-b', y=0, avec=True), montrer('#t6-sb', y=0, avec=True),
                    anneau('#t6-ref', d=1.2), anneau('#t6-sb', d=1.2)]},
        {'titre': 'Le type par défaut',
         'texte': "Configuration › Types de courrier. Prérequis : un serveur de messagerie entrant.",
         'voix': "Le paramétrage tient en une case : dans Configuration, Types de courrier, l'administrateur coche Type par "
                 "défaut, capture e-mail. Sans ce choix, le premier type entrant s'applique. Prérequis : un serveur de "
                 "messagerie entrant.",
         'gestes': [montrer('#app-6b', y=0, d=0.4), pause(0.3), clic('#app-6b-m4'), montrer('#t6-cfg', y=6, d=0.25),
                    clic('#t6-cfg0', fx=0.3), cacher('#t6-cfg', d=0.15), aller('t6-types'),
                    cacher('#t6a-liste', d=0.25, avec=True), clic('#t6t-l1', fx=0.15), aller('t6-type'),
                    zoom('#t6-cap-l', s=1.7, fx=0.5, fy=0.4, d=0.8), clic('#t6-cap'), classe('#t6-cap', ajouter=['on'], avec=True, decale=0.9),
                    montrer('#t6-sauver', y=0, d=0.2, avec=True, decale=0.95),
                    bulle('#t6-cap', 'Type des e-mails capturés', cote='droite', d=2.4), dezoom(d=0.7)]},
    ],
    'benefices': {
        'titre': 'Plus rien à *ressaisir.*',
        'voix': "Plus de ressaisie, des pièces jointes versionnées, et chaque capture tracée au journal d'audit.",
        'cartes': [('eclair', 'courrier@', 'Une adresse dédiée', "Chaque e-mail reçu devient un courrier en brouillon, déjà rempli."),
                   ('doc', 'v1', 'Pièces versionnées', "Les pièces jointes deviennent des documents du courrier."),
                   ('trace', 'Système', 'Capture tracée', "Chaque capture est inscrite au journal d'audit, source Système.")],
    },
    'cta': cta('courrier', 'Le courrier qui *arrive* *seul.*', "Aïte Courrier : le courrier qui arrive seul."),
    'youtube': youtube('COMMENT TRANSFORMER AUTOMATIQUEMENT VOS E-MAILS EN COURRIERS AVEC AITE COURRIER (ODOO 18)',
                       "Tout e-mail envoyé à l'adresse dédiée crée un courrier en brouillon, déjà rempli : objet, expéditeur, "
                       "type par défaut. Ses pièces jointes deviennent des documents versionnés, et chaque capture est tracée "
                       "au journal d'audit. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'capture e-mail', 'alias e-mail Odoo', 'pièces jointes', 'courrier électronique']),
}
