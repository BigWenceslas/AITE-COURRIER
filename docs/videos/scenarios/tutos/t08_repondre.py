# -*- coding: utf-8 -*-
"""Tutoriel 08 — Répondre à un courrier avec un modèle.

Sources :
- aite_courrier_reponse/__manifest__.py (« répondre à un courrier en quelques
  clics, sans quitter l'application », PDF sur l'en-tête société versionné en
  GED, envoi à l'expéditeur, courrier sortant lié « Préparation → … →
  Émission », lien croisé « Réponse à / Réponses », trace chatter + audit,
  3 modèles livrés) ;
- aite_courrier_reponse/views/aite_courrier_views.xml (bouton « Répondre »
  invisible en brouillon, icône fa-reply ; boutons statistiques « Réponses »
  (si reply_count > 0) et « Courrier d'origine » (si reply_to_courrier_id)) ;
- aite_courrier_reponse/wizard/aite_courrier_reponse_wizard_views.xml
  (« Répondre au courrier » : Courrier d'origine, Modèle | Créer le courrier
  sortant lié, Type du courrier sortant, Envoyer par e-mail à l'expéditeur,
  E-mail expéditeur si coché ; Objet ; corps sans libellé ; « Générer la
  réponse », « Annuler ») ;
- aite_courrier_reponse/wizard/aite_courrier_reponse_wizard.py (titre de la
  fenêtre « Répondre — <référence> » : models/aite_courrier.py
  action_open_reponse_wizard ; create_outgoing coché par défaut ; type par
  défaut = premier type « sortant » actif, ordre par code → « Devis » ;
  _onchange_template_id : fusion objet + corps ; action_generate : PDF →
  courrier sortant en brouillon (objet, expéditeur, contact, e-mail, service,
  priorité, confidentialité du courrier d'origine, responsable = l'utilisateur,
  « Courrier de réponse à … ») → document « Réponse — <objet> » version 1 →
  e-mail à l'expéditeur PDF joint → message « Réponse générée : « … » —
  courrier sortant … créé — envoyée à … » + audit « Génération de réponse » →
  ouverture du courrier sortant) ;
- aite_courrier_reponse/data/reponse_template_data.xml (les 3 modèles, leur
  objet et leur corps mot pour mot) ;
- aite_courrier_reponse/report/report_reponse_templates.xml (date, « Objet : »,
  « Vos références : … — courrier du … », corps ; web.external_layout) ;
- aite_courrier_reponse/views/aite_courrier_reponse_template_views.xml (menu
  Configuration › Modèles de réponse, liste Nom / Objet / Types de courrier /
  Actif, fiche, encadré « Champs de fusion ») ; menu Configuration réservé au
  groupe admin (aite_courrier_base/views/aite_courrier_menus.xml) ;
- aite_courrier_ged (onglet Documents, « Prévisualiser » : la dernière version
  s'ouvre dans un onglet, /web/content/<id>?download=false) ;
- aite_courrier_workflow/data/workflow_circuits.xml (Qualification : agent et
  assistante ; circuit Courrier sortant : Préparation 24 h, Contrôle 8 h,
  Validation 24 h, Signature 24 h, Émission 4 h).
Droits : seuls l'agent courrier et l'administrateur peuvent créer un courrier
et ses documents (ir.model.access) : le personnage est donc l'agent.
Écrans : composés d'après la base de démonstration (thème MuK) — fiche du
courrier (présentation, chapitre 2, adaptée), assistant, courrier sortant,
modèles de réponse. Courrier : celui du tutoriel 01 (demo.NOUVEAU).
"""

import demo
from ecrans import (ICONES, activite, assistant, bande, bouton, bouton_stat, c_html, c_num, c_puce, case, champ, chatter, e,
                    entree, fenetre, feuille, grille2, liste, message, onglets, panneau_fiche, panneau_liste, puce, sec_titre,
                    statusbar, table, v, vue)
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, cacher, choisir, classe, clic, fermer, montrer, ouvrir, pause, saisir, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

AGENT = demo.PERSONNES['agent']
ASSIST = demo.PERSONNES['assistante']
ADMIN = demo.PERSONNES['admin']
N1 = demo.NOUVEAU
REF, OBJET, EXP, COURRIEL = N1['reference'], N1['objet'], N1['expediteur'], N1['courriel']
TIERS = demo.TIERS
SERVICE = 'Commercial'
DATE_REP = '14/10/2026'
MODELE = 'Demande de pièces complémentaires'
MODELES = ['Réponse standard', MODELE, 'Notification de clôture']
OBJETS_MODELES = ['Réponse à votre courrier {{ object.reference }}', 'Pièces complémentaires — dossier {{ object.reference }}',
                  'Clôture de votre dossier {{ object.reference }}']
OBJET_REP = 'Pièces complémentaires — dossier %s' % REF
PIECES = 'Statuts de la société et derniers états financiers.'
URL_PDF = 'courrier.aite-demo.test/web/content/1287?download=false'

# icônes des boutons statistiques (fa-reply-all, fa-level-up)
REPLY_ALL = ('<svg viewBox="0 0 24 24" fill="none" stroke="#343A40" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M8 6L3 11l5 5"/><path d="M13 6l-5 5 5 5"/><path d="M8 11h7a6 6 0 016 6v1"/></svg>')
LEVEL_UP = ('<svg viewBox="0 0 24 24" fill="none" stroke="#343A40" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 8l-4-4-4 4"/><path d="M10 4v12a4 4 0 004 4h6"/></svg>')


def _stat(identifiant, libelle, valeur, svg, masque=False):
    return ('<span class="stat%s" id="%s"><span class="ic">%s</span><span><b>%s</b>%s</span></span>'
            % (' masque' if masque else '', identifiant, svg, e(libelle), '<i>%s</i>' % e(valeur) if valeur else ''))


def _corps_lettre(pieces_html, ref_id=None):
    """Le corps fusionné du modèle « Demande de pièces complémentaires »."""
    return ''.join('<p>%s</p>' % p for p in [
        'Madame, Monsieur,',
        'Votre demande référencée <strong%s>%s</strong> (« %s ») est en cours d\'instruction.'
        % (' id="%s"' % ref_id if ref_id else '', e(REF), e(OBJET)),
        'Afin de poursuivre son traitement, nous vous remercions de bien vouloir nous transmettre les pièces suivantes :',
        pieces_html,
        'Sans retour de votre part, votre dossier restera en attente. Merci de rappeler la référence ci-dessus dans votre réponse.',
        'Cordialement,',
        '%s<br>%s' % (e(AGENT[0]), e(SERVICE))])


# ------------------------------------------------------------- l'écran --
def _fiche():
    """Le courrier d'origine (fiche du chapitre 2, adaptée) : étape Qualification."""
    stats = (bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '1')
             + _stat('t8-st-rep', 'Réponses', '1', REPLY_ALL, masque=True))
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v">%s</div>' % REF
             + grille2([champ('Objet', v(OBJET)), champ('Contact expéditeur', v(TIERS, True), aide=True),
                        champ('Expéditeur', v(EXP)), champ('E-mail expéditeur', v(COURRIEL, True), aide=True),
                        champ('Type', v('Courrier entrant', True)), champ('Service destinataire', v(SERVICE, True))],
                       [champ('Statut', puce('En traitement', 'gris'), aide=True), champ('Priorité', v('Normale', True)),
                        champ('Confidentialité', v('Interne', True)), champ('Date de réception', v(N1['date'])),
                        champ('Responsable', '')])
             + onglets(['Documents', 'Historique'])
             + table([('Nom', '1fr'), ('Dossier', '80px'), ('Extension', '70px'), ('Nombre de versions', '110px'), ('État', '80px')],
                     [{'id': 't8-d0', 'cellules': [OBJET, '', 'pdf', c_num('1'), c_puce('Brouillon')]}], ajouter=False))
    acts = activite('Courrier %s — étape « Qualification »' % REF, AGENT[0],
                    'Le courrier « %s » attend votre traitement à l\'étape « Qualification ».' % OBJET, AGENT[2], AGENT[1],
                    masque=False)
    trace = ('Réponse générée : « %s » — courrier sortant %s (brouillon) créé — envoyée à %s' % (OBJET_REP, OBJET_REP, COURRIEL))
    ch = chatter([message(AGENT[0], AGENT[2], 'Réception → <span class="lien">Qualification</span> (Étape courante)', '09:12'),
                  message(AGENT[0], AGENT[2], e(trace), '10:41', 't8-msg', masque=True)],
                 activites=acts, identifiant='t8-chatter', suivre='')
    return vue('t8-fiche', panneau_fiche('Courriers', REF, '1 / 16', boutons_stat=stats)
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande([bouton('t8-traiter', 'Traiter', 'prim'), bouton('t8-rejeter', 'Rejeter', 'second'),
                          bouton('t8-comm', 'Commenter', 'second'), bouton('t8-rep', 'Répondre', 'second', 'retour')],
                         statusbar(base.ETAPES, 1, 't8-sb'), 't8-bande'),
                   feuille(corps), ch), initiale=True)


def _liste_deroulante(identifiant, items):
    lignes = ''.join('<div class="t8-it%s" id="%s-%d">%s</div>' % (' t8-sel' if i == 0 else '', identifiant, i, e(x))
                     for i, x in enumerate(items))
    return ('<div class="t8-dd masque" id="%s">%s<div class="t8-it t8-av">Recherche avancée...</div></div>'
            % (identifiant, lignes))


def _assistant():
    m2o = '<span class="t8-m2o">%s<span class="t8-car">▾</span>%s</span>'
    gauche = [champ("Courrier d'origine", v(REF, True), 't8-w-orig'),
              champ('Modèle', m2o % (entree('t8-w-modele'), _liste_deroulante('t8-dd-mod', MODELES)), 't8-w-mod-l', aide=True)]
    mail = '<span class="case" id="t8-w-mail">%s</span>' % ICONES['coche']
    droite = [champ('Créer le courrier sortant lié', case(True), 't8-w-creer', aide=True),
              champ('Type du courrier sortant', m2o % (entree('t8-w-type', valeur='Devis'),
                                                       _liste_deroulante('t8-dd-type', ['Devis', 'Courrier sortant'])), 't8-w-type-l'),
              champ("Envoyer par e-mail à l'expéditeur", mail, 't8-w-mail-l', aide=True),
              '<div class="masque" id="t8-w-exp">%s</div>' % champ('E-mail expéditeur', v(COURRIEL), aide=True)]
    pieces = entree('t8-w-pieces', '[Liste des pièces attendues]')
    corps = ('<div class="t8-wg" id="t8-w-haut"><div id="t8-w-gauche">%s</div><div id="t8-w-droite">%s</div></div>'
             % (''.join(gauche), ''.join(droite))
             + champ('Objet', entree('t8-w-objet'), 't8-w-objet-l')
             + '<div class="t8-corps" id="t8-corps"><div class="masque" id="t8-txt">%s</div></div>' % _corps_lettre(pieces, 't8-w-ref'))
    return assistant('t8-as', 'Répondre — %s' % REF, corps,
                     [('t8-gen', 'Générer la réponse', 'prim'), ('t8-annuler', 'Annuler', 'second')], haut=46, largeur=720)


def _sortant():
    """Le courrier sortant créé par l'assistant, en brouillon."""
    stats = (bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '1')
             + _stat('t8-st-orig', "Courrier d'origine", '', LEVEL_UP))
    circuit = ('<div id="t8-s-circuit">%s%s%s</div>' % (
        sec_titre('Aperçu du circuit'), champ('Circuit prévu', v('Courrier sortant', True)),
        table([('Séquence', '70px'), ('Nom', '1fr'), ('SLA (heures)', '90px'), ('Étape initiale', '90px'), ('Étape finale', '80px')],
              [{'id': 't8-s-s%d' % i, 'cellules': [c_num(str(i + 1)), n, c_num(s), c_html(case(i == 0)), c_html(case(i == 4))]}
               for i, (n, s) in enumerate([('Préparation', '24'), ('Contrôle', '8'), ('Validation', '24'), ('Signature', '24'),
                                           ('Émission', '4')])], ajouter=False)))
    prev = '<span class="lien t8-prev" id="t8-s-prev">%s Prévisualiser</span>' % ICONES['oeil']
    docs = table([('Nom', '1fr'), ('Dossier', '50px'), ('Étiquettes', '60px'), ('Extension', '60px'), ('Nombre de versions', '72px'),
                  ('État', '64px'), ('Verrouillé', '56px'), ('', '92px')],
                 [{'id': 't8-s-d0', 'cellules': ['Réponse — %s' % OBJET_REP, '', '', 'pdf', c_num('1'),
                                                 c_html('<span>%s</span>' % puce('Brouillon')), c_html(case(False)), c_html(prev)]}],
                 identifiant='t8-s-docs')
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v"></div>'
             + grille2([champ('Objet', v(OBJET_REP)), champ('Contact expéditeur', v(TIERS, True), aide=True),
                        champ('Expéditeur', v(EXP)), champ('E-mail expéditeur', v(COURRIEL, True), aide=True),
                        champ('Type', v('Courrier sortant', True), 't8-s-type'), champ('Service destinataire', v(SERVICE, True))],
                       [champ('Statut', puce('Brouillon', 'gris', 't8-s-statut'), aide=True), champ('Priorité', v('Normale', True)),
                        champ('Confidentialité', v('Interne', True)), champ('Date de réception', v(DATE_REP)),
                        champ('Responsable', v(AGENT[0], True), 't8-s-resp')])
             + circuit + onglets(['Documents', 'Historique']) + docs)
    ch = chatter([message(AGENT[0], AGENT[2], 'Courrier de réponse à %s.' % REF, '10:41', 't8-s-msg')], suivre='')
    bd = bande([bouton('t8-s-lancer', 'Enregistrer et lancer le circuit', 'prim'), bouton('t8-s-comm', 'Commenter', 'second')],
               '', 't8-s-bande')
    return vue('t8-sortant', panneau_fiche('Courriers / %s' % REF, '%s (brouillon)' % OBJET_REP, '1 / 1', boutons_stat=stats,
                                           ref_id='t8-s-titre')
               + '<div class="o-corps"><div class="o-gauche"><div id="t8-defil">%s%s</div></div>%s</div>' % (bd, feuille(corps), ch))


def _pdf():
    """La dernière version ouverte dans un onglet : le PDF dans la visionneuse du navigateur (générique)."""
    lettre = (_corps_lettre(e(PIECES)))
    page = ('<div class="t8p-page" id="t8-pdf-page"><div class="t8p-tete" id="t8-pdf-tete"><b>AITE Démo</b></div>'
            '<div class="t8p-date">%s</div><div class="t8p-objet" id="t8-pdf-objet"><b>Objet :</b> %s</div>'
            '<div class="t8p-refs" id="t8-pdf-refs">Vos références : %s — courrier du %s</div><div class="t8p-corps">%s</div>'
            '<div class="t8p-pied"></div></div>' % (DATE_REP, e(OBJET_REP), e(REF), e(N1['date']), lettre))
    return ('<div class="o-app t8pdf masque" id="t8-pdf"><div class="t8p-barre"><span class="t8p-menu">☰</span>'
            '<span class="t8p-pg">1 / 1</span><span class="t8p-zoom">−&nbsp;&nbsp;100 %&nbsp;&nbsp;+</span></div>' + page + '</div>')


def _admin():
    """L'administrateur : Configuration › Modèles de réponse."""
    accueil = vue('t8a-liste', panneau_liste('Courriers', '1-80 / 151', ident='t8a') + base.lat_courriers(None)
                  + liste(base.COL_COURRIERS, [base.ligne_courrier('t8a-l%d' % i, *l) for i, l in enumerate(base.LIGNES_COURRIERS)]),
                  initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    poignee = c_html('<span class="t8-poignee">⠿</span>')
    lst = vue('t8-modeles', panneau_liste('Modèles de réponse', '1-3 / 3', ident='t8m')
              + liste([('', '14px'), ('Nom', '1fr'), ('Objet', '1.3fr'), ('Types de courrier', '150px'), ('Actif', '44px')],
                      [{'id': 't8m-l%d' % i, 'cellules': [poignee, n, o, '', c_html(case(True))]}
                       for i, (n, o) in enumerate(zip(MODELES, OBJETS_MODELES))], ident='t8m-liste'))
    brut = ''.join('<p>%s</p>' % p for p in [
        'Madame, Monsieur,',
        'Votre demande référencée <strong id="t8-mod-ref">{{ object.reference }}</strong> (« {{ object.subject }} ») est en '
        'cours d\'instruction.',
        'Afin de poursuivre son traitement, nous vous remercions de bien vouloir nous transmettre les pièces suivantes :',
        '[Liste des pièces attendues]',
        'Sans retour de votre part, votre dossier restera en attente. Merci de rappeler la référence ci-dessus dans votre réponse.',
        'Cordialement,', '{{ user.name }}<br>{{ object.department_id.name }}'])
    codes = ', '.join('<code>%s</code>' % e(c) for c in ['{{ object.reference }}', '{{ object.subject }}', '{{ object.sender }}',
                                                          '{{ object.date_received }}', '{{ object.department_id.name }}',
                                                          '{{ object.responsible_id.name }}', '{{ user.name }}'])
    aide = ('<div class="t8-alerte" id="t8-mod-aide"><strong>Champs de fusion</strong> (moteur des modèles d\'e-mails Odoo) — insérer '
            'par exemple : %s.<br><code>object</code> désigne le courrier d\'origine auquel on répond.</div>' % codes)
    corps = ('<div class="t8-h1" id="t8-mod-nom">%s</div>' % e(MODELE)
             + grille2([champ('Types de courrier', '', 't8-mod-types', aide=True), champ('Séquence', v('20'))],
                       [champ('Actif', case(True))])
             + champ('Objet', v(OBJETS_MODELES[1]), 't8-mod-objet', aide=True)
             + '<div class="t8-mod-corps" id="t8-mod-corps">%s</div>' % brut + aide)
    fiche = vue('t8-modele', panneau_fiche('Modèles de réponse', MODELE, '2 / 3')
                + '<div class="o-corps"><div class="o-gauche">%s</div></div>' % feuille(corps, identifiant='t8-mod-f'))
    menu = ('<div class="t8-dd t8-cfg masque" id="t8-cfg">%s</div>'
            % ''.join('<div class="t8-it" id="t8-cfg%d">%s</div>' % (i, e(n)) for i, n in enumerate(
                ['Types de courrier', 'Priorités', 'Niveaux de confidentialité', 'Circuits de traitement', 'Dossiers',
                 'Étiquettes de documents', 'Modèles de réponse'])))
    html = fenetre('Courrier', ['Tableau de bord', 'Courriers', 'Espace documentaire', 'Audit', 'Configuration'],
                   [accueil, lst, fiche], ADMIN[1], ADMIN[2], ident='app-8b')
    html = html.replace('<span class="menu" id="app-8b-m4">Configuration</span>',
                        '<span class="menu t8-menu" id="app-8b-m4">Configuration%s</span>' % menu, 1)
    return html.replace('class="o-app muk" id="app-8b"', 'class="o-app muk masque" id="app-8b"', 1)


def ecran():
    agent = fenetre('Courrier', ['Courriers', 'Espace documentaire'], [_fiche(), _sortant()], AGENT[1], AGENT[2],
                    calques=_assistant(), ident='app-8')
    return agent + _pdf() + _admin()


CSS = """
#t8-fiche .o-cp .stats, #t8-sortant .o-cp .stats { margin-left: 40px; }
#t8-sortant .o-cp .ref { display: block; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#t8-sortant .o-cp .parent { white-space: nowrap; }
#app-8 .stat .ic svg { width: 16px; height: 16px; display: block; }
#t8-chatter .act .tx, #t8-chatter .act .at { font-size: 11px; }
#app-8 .ch-bts .bt { padding: 0 6px; font-size: 11px; }
#t8-msg .tx { font-size: 11px; line-height: 1.35; }
/* l'assistant « Répondre » */
#t8-as .mt { font-size: 15px; }
#t8-as .mc { padding: 14px 16px 10px; }
#t8-as .champ { grid-template-columns: 112px 1fr; font-size: 12.5px; }
#t8-as .champ .l { padding-right: 8px; }
#t8-w-orig .l { color: #6C757D; font-weight: 400; }
#t8-as .t8-wg { display: grid; grid-template-columns: 1.12fr 1fr; column-gap: 28px; margin-bottom: 6px; }
#t8-w-droite .champ { grid-template-columns: 136px 1fr; min-height: 34px; align-items: center; }
#t8-w-droite .champ .l { line-height: 1.3; }
#t8-w-droite .champ .v { overflow-wrap: anywhere; }
#t8-as .t8-m2o { position: relative; display: flex; align-items: center; width: 100%; }
#t8-as .t8-m2o .entree { padding-right: 14px; }
#t8-as .t8-car { position: absolute; right: 2px; top: 3px; font-size: 10px; color: #5D8DA8; }
#t8-w-objet-l { grid-template-columns: 52px 1fr; margin-bottom: 8px; }
#t8-as .t8-corps { height: 252px; font-size: 12px; line-height: 1.42; color: #212529; overflow: hidden; }
#t8-as .t8-corps p { margin: 0 0 6px; }
#t8-w-pieces { border-bottom: 0; min-height: 17px; display: inline-flex; }
#t8-w-pieces .ph { color: #212529; }
#t8-w-pieces.focus { background: #EEF3F6; }
#t8-w-mail svg { opacity: 0; } #t8-w-mail.on svg { opacity: 1; }
#app-8 .t8-dd, #app-8b .t8-dd { position: absolute; z-index: 30; background: #fff; border: 1px solid #DEE2E6; border-radius: 4px;
  box-shadow: 0 10px 26px rgba(0,0,0,.16); font-size: 12.5px; color: #212529; padding: 4px 0; }
#t8-as .t8-dd { left: 0; top: 24px; width: 100%; min-width: 240px; }
#app-8 .t8-it, #app-8b .t8-it { padding: 5px 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#app-8 .t8-it.t8-sel { background: #EEF3F6; }
#app-8 .t8-it.survol { background: #DCE8EF; }
#app-8 .t8-av { color: #528099; padding-left: 24px; }
/* le courrier sortant */
#t8-s-docs .t8-prev { display: inline-flex; align-items: center; gap: 4px; }
#t8-s-docs .t8-prev svg { width: 12px; height: 12px; }
#t8-s-circuit { overflow: hidden; }
#t8-sortant .o-feuille { padding-top: 10px; padding-bottom: 8px; }
#t8-sortant .champ { min-height: 24px; padding: 2px 0; }
#t8-sortant .sec-t { margin: 8px 0 4px; }
#t8-s-circuit .o-table .tt { height: 26px; }
#t8-s-circuit .o-table .tl { height: 24px; }
#t8-sortant .onglets { margin-top: 8px; }
#t8-sortant .og { padding: 6px 14px; }
/* la visionneuse PDF du navigateur (générique) */
#t8-pdf { background: #525659; font-family: var(--odoo); }
#t8-pdf .t8p-barre { height: 38px; background: #323639; color: #F1F1F1; display: flex; align-items: center; gap: 22px; padding: 0 18px;
  font-size: 13px; }
#t8-pdf .t8p-menu { font-size: 16px; } #t8-pdf .t8p-zoom { margin-left: auto; margin-right: auto; } #t8-pdf .t8p-pg { margin-left: 330px; }
#t8-pdf .t8p-page { position: absolute; left: 315px; top: 54px; width: 470px; height: 640px; background: #fff; padding: 30px 40px;
  box-shadow: 0 4px 14px rgba(0,0,0,.4); font-size: 9.6px; line-height: 1.45; color: #212529; }
#t8-pdf .t8p-tete { padding-bottom: 8px; border-bottom: 1px solid #ADB5BD; margin-bottom: 18px; }
#t8-pdf .t8p-tete b { font-size: 15px; color: #5E4E8C; letter-spacing: .02em; }
#t8-pdf .t8p-date { text-align: right; margin-bottom: 16px; }
#t8-pdf .t8p-objet { margin-bottom: 10px; }
#t8-pdf .t8p-refs { margin-bottom: 16px; color: #6C757D; }
#t8-pdf .t8p-corps p { margin: 0 0 7px; }
#t8-pdf .t8p-pied { position: absolute; left: 40px; right: 40px; bottom: 26px; border-top: 1px solid #ADB5BD; }
/* l'administrateur : modèles de réponse */
#app-8b .t8-menu { position: relative; }
#t8-cfg { left: -10px; top: 29px; width: 178px; padding: 6px 0; font-size: 12px; }
#t8-cfg .t8-it { padding: 5px 14px; }
#t8m-liste .t8-poignee { color: #ADB5BD; font-size: 13px; }
#t8-mod-f { padding: 14px 18px; }
#t8-mod-f .t8-h1 { font-size: 23px; padding-bottom: 6px; border-bottom: 1px solid #DEE2E6; margin: 0 0 10px; width: 75%; }
#t8-mod-objet { grid-template-columns: 60px 1fr; margin-top: 2px; border-bottom: 1px solid #DEE2E6; }
#t8-mod-corps { padding: 10px 2px 6px; font-size: 12px; line-height: 1.42; border-bottom: 1px solid #ADB5BD; }
#t8-mod-corps p { margin: 0 0 6px; }
#t8-mod-f .t8-alerte { margin-top: 12px; padding: 10px 14px; border-radius: 4px; background: #CFF4FC; color: #055160; font-size: 11.5px;
  line-height: 1.6; }
#t8-mod-f .t8-alerte code { font-family: var(--mono, monospace); font-size: 10.5px; color: #D63384; }
"""

TUTO = {
    'slug': 'tuto-08-repondre-avec-un-modele',
    'titre_page': 'AITE Courrier — Tutoriel 08 : répondre avec un modèle',
    'titre': 'Répondre avec un modèle',
    'serie': dict(COURRIER, numero=8),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Chaque réponse, *réécrite* depuis une *page* *blanche ?*',
        'sous': 'Modèle introuvable, référence à recopier, en-tête à refaire, PDF à classer : répondre prend plus de temps que lire.',
        'personnage': (AGENT[0], 'Agent courrier', AGENT[2]),
        'chaos': [('doc', 'modele_reponse_v3.docx'), ('alerte', 'Client sans réponse'), ('bulle', 'Tu as le bon en-tête ?'),
                  ('note', 'Réf. à recopier'), ('lettre', 'Réponse à rédiger'), ('bulle', 'Le PDF est parti ?'),
                  ('dossier', 'Réponses envoyées'), ('alerte', 'Relance du client')],
        'voix': "Un client attend votre réponse. Retrouver le bon modèle, recopier la référence, refaire l'en-tête, "
                "classer le P D F… Répondre prend plus de temps que lire.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, vous répondez en quelques clics, sans quitter l'application."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Répondre avec un *modèle,* en quelques clics',
        'pastilles': ['Modèle fusionné', 'PDF à votre en-tête', 'Courrier sortant lié'],
        'voix': "Un modèle, et le texte se remplit seul. La réponse devient un P D F à votre en-tête, rangé dans un "
                "courrier sortant lié. Voyons comment.",
    },
    'ecran': ecran(), 'vue_initiale': 't8-fiche',
    'css': CSS,
    'etapes': [
        {'titre': 'Répondre, puis choisir un modèle',
         'texte': "Le bouton Répondre ouvre l'assistant ; le modèle remplit l'objet et le corps de la réponse.",
         'voix': "En qualifiant la demande de partenariat du Groupe Horizon Services, Carine constate qu'il manque des pièces. "
                 "Elle clique sur Répondre, puis choisit le modèle Demande de pièces complémentaires : l'objet et le corps "
                 "se remplissent aussitôt.",
         'gestes': [anneau('#t8-sb-1', d=1.2, decale=0.3), anneau('#t8-d0', d=1.3), pause(0.5), clic('#t8-rep'), ouvrir('t8-as'),
                    zoom('#t8-w-haut', s=1.45, fx=0.5, fy=0.3, d=0.8),
                    clic('#t8-w-modele', fx=0.3), montrer('#t8-dd-mod', y=6, d=0.25), anneau('#t8-dd-mod', d=1.0),
                    clic('#t8-dd-mod-1', fx=0.3), cacher('#t8-dd-mod', d=0.15), choisir('t8-w-modele', MODELE),
                    choisir('t8-w-objet', OBJET_REP, avec=True, decale=0.25), montrer('#t8-txt', y=8, d=0.4, avec=True, decale=0.35),
                    dezoom(d=0.6), zoom('#t8-corps', s=1.3, fx=0.5, fy=0.5, d=0.8),
                    bulle('#t8-w-ref', 'Référence et objet fusionnés', cote='dessous', d=2.2)]},
        {'titre': 'Retoucher, régler, générer',
         'texte': "Le corps reste modifiable ; type du courrier sortant, envoi par e-mail, puis « Générer la réponse ».",
         'voix': "Le texte reste modifiable : elle précise les pièces attendues. La création du courrier sortant lié est "
                 "cochée d'office ; elle en choisit le type, Courrier sortant, puis coche l'envoi par e-mail à "
                 "l'expéditeur, P D F joint. Il ne reste qu'à générer la réponse.",
         'gestes': [clic('#t8-w-pieces', fx=0.15, d=0.6), saisir('t8-w-pieces', PIECES, d=1.7), dezoom(d=0.6),
                    zoom('#t8-w-droite', s=1.5, fx=0.55, fy=0.3, d=0.8), anneau('#t8-w-creer', d=0.9),
                    clic('#t8-w-type', fx=0.3, d=0.6), montrer('#t8-dd-type', y=6, d=0.25), clic('#t8-dd-type-1', fx=0.3, d=0.6),
                    cacher('#t8-dd-type', d=0.15), choisir('t8-w-type', 'Courrier sortant'),
                    clic('#t8-w-mail', d=0.6), classe('#t8-w-mail', ajouter=['on'], avec=True, decale=0.75),
                    montrer('#t8-w-exp', y=6, d=0.3), bulle('#t8-w-exp .v', "L'adresse de l'expéditeur", cote='dessous', d=2.0),
                    dezoom(d=0.6), clic('#t8-gen')]},
        {'titre': 'Le PDF, dans un courrier sortant',
         'texte': "Un courrier sortant en brouillon, le PDF de la réponse dans ses documents, le lien vers la demande.",
         'voix': "Le courrier sortant s'ouvre aussitôt, en brouillon, prêt à suivre son circuit, de la préparation à "
                 "l'émission. Dans ses documents, le P D F de la réponse, à l'en-tête de la société. Et le bouton "
                 "Courrier d'origine ramène à la demande, qui compte désormais une réponse.",
         'gestes': [fermer('t8-as'), aller('t8-sortant'), anneau('#t8-s-circuit', d=1.2),
                    bulle('#t8-s-s2', 'Préparation → Émission', cote='droite', fx=0.3, d=2.0), pause(1.0),
                    clic('#t8-s-prev', fx=0.4),
                    texte('#pr-url', URL_PDF), montrer('#t8-pdf', y=0, d=0.4, avec=True),
                    zoom('#t8-pdf-objet', s=1.8, fx=0.5, fy=0.4, d=0.8),
                    bulle('#t8-pdf-tete b', "L'en-tête de la société", cote='droite', d=1.9),
                    dezoom(d=0.6), cacher('#t8-pdf', d=0.3), texte('#pr-url', ADRESSE % 'courrier', avec=True),
                    clic('#t8-st-orig'), aller('t8-fiche'),
                    montrer('#t8-st-rep', y=0, d=0.3), montrer('#t8-msg', y=10, d=0.4, avec=True, decale=0.2),
                    zoom('#t8-st-rep', s=1.6, fx=0.5, fy=0.3, d=0.8),
                    bulle('#t8-st-rep', 'Réponses : 1', cote='droite', d=1.9), dezoom(d=0.6)]},
        {'titre': 'Trois modèles livrés, à adapter',
         'texte': "Configuration › Modèles de réponse : objet et corps, avec leurs champs de fusion.",
         'voix': "Les modèles se gèrent dans Configuration, Modèles de réponse. Trois sont livrés : réponse standard, "
                 "demande de pièces complémentaires et notification de clôture. L'administrateur les adapte librement : "
                 "objet, corps, et champs de fusion, comme la référence du courrier.",
         'gestes': [montrer('#app-8b', y=0, d=0.4), clic('#app-8b-m4'), montrer('#t8-cfg', y=6, d=0.25),
                    clic('#t8-cfg6', fx=0.3, d=0.6), cacher('#t8-cfg', d=0.15), aller('t8-modeles'),
                    cacher('#t8a-liste', d=0.25, avec=True), anneau('#t8m-l0', d=0.6), anneau('#t8m-l1', d=0.6), anneau('#t8m-l2', d=0.6),
                    bulle('#t8m-l2', '3 modèles livrés', cote='dessous', fx=0.3, d=1.9),
                    clic('#t8m-l1', fx=0.2), aller('t8-modele'), zoom('#t8-mod-ref', s=1.45, fx=0.3, fy=0.4, d=0.8),
                    bulle('#t8-mod-ref', 'Un champ de fusion', cote='dessous', d=2.0),
                    dezoom(d=0.6), anneau('#t8-mod-aide', d=1.2)]},
    ],
    'benefices': {
        'titre': 'Des réponses *rapides,* et *tracées.*',
        'voix': "Des réponses rédigées en quelques clics, à votre en-tête, et chacune tracée : dans le fil du courrier, "
                "comme au journal d'audit.",
        'cartes': [('eclair', '3 modèles', 'Prêts à l\'emploi', "Réponse standard, pièces complémentaires, notification de clôture."),
                   ('doc', 'PDF', 'À votre en-tête', "Le PDF rejoint les documents du courrier sortant lié, en version 1."),
                   ('trace', 'Audit', 'Chaque réponse tracée', "Un message dans le fil du courrier, une ligne au journal d'audit.")],
    },
    'cta': cta('courrier', 'Vos réponses, en *quelques* *clics.*', "Aïte Courrier : vos réponses, en quelques clics."),
    'youtube': youtube('COMMENT RÉPONDRE À UN COURRIER EN QUELQUES CLICS AVEC AITE COURRIER (ODOO 18)',
                       "Répondre à un courrier sans quitter l'application : un modèle de réponse fusionne la référence et "
                       "l'objet du courrier, le PDF est produit à l'en-tête de la société, versé dans un courrier sortant "
                       "lié et envoyé à l'expéditeur par e-mail. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'modèle de réponse', 'courrier sortant', 'réponse courrier', 'publipostage Odoo']),
}
