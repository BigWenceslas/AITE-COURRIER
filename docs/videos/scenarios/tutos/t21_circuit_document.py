# -*- coding: utf-8 -*-
"""Tutoriel 21 — Circuit de validation d'un document.

Sources :
- addons/aite_ecm_workflow/data/aite_ecm_document_circuit_data.xml : le
  circuit livré « Procédure — rédaction, vérification, approbation » (type
  « Procédure / instruction ») : Rédaction (agents, assistantes ; 72 h ;
  initiale), Vérification (managers ; 48 h), Approuvée (managers,
  signataires ; finale) ; transitions « Transmettre pour vérification »,
  « Retour au rédacteur » (commentaire obligatoire), « Approuver » ;
- addons/aite_ecm_workflow/models/aite_ecm_document.py : le circuit est le
  circuit actif du type du document ; lancement refusé sans fichier, hors
  brouillon ou sous réservation ; à l'étape finale, « Finaliser en fin de
  circuit » (vrai par défaut) passe le document au statut Finalisé ;
- addons/aite_ecm_workflow/models/aite_workflow_mixin.py : « Circuit »,
  « Étape courante », « Circuit — statut » (« Non lancé », « En cours »,
  « Terminé », « Rejeté »), « Échéance SLA » ; lancement (message « Circuit
  « %s » lancé — étape « %s ». »), échéance = entrée + SLA ; activité
  « [Circuit] <étape> — <réf.> » (« Étape « %s » à traiter. ») pour chaque
  utilisateur des rôles de l'étape, sauf l'étape finale ; contrôle serveur
  des habilitations (managers partout) ; « Réinitialiser le circuit »
  (managers : retour à « Non lancé ») ;
- addons/aite_ecm_workflow/models/aite_workflow_circuit.py : historique
  (« Étape », « Entrée », « Sortie », « Durée (h) », « Par »,
  « Transition », « Commentaire ») ;
- addons/aite_ecm_workflow/views/aite_ecm_document_views.xml : boutons
  « Lancer le circuit », « Traiter », « Réinitialiser le circuit » (et sa
  confirmation), bandeau « Circuit en cours — étape … · échéance … »,
  onglet « Circuit » ; wizard/aite_workflow_action_wizard_views.xml
  (« Action de circuit » : « Objet », « Étape courante », « Action » —
  « Appliquer une transition » / « Rejeter », « Transition »,
  « Commentaire » et son indication, « Valider », « Annuler » ; titre de la
  fenêtre : « Action — <réf.> ») ;
- addons/aite_courrier_workflow/models/aite_workflow_step.py:128
  (can_user_act : rôle de l'étape, et utilisateurs nommés s'il y en a).
Modèle visuel : base demo18 (MuK), captures t21_* (assistante puis manager,
document de test lancé, transmis et approuvé).
"""

import demo
from ecrans import (activite, bande, bandeau, bouton, bouton_stat, c_num, case, champ, chatter, e, entree, fenetre, feuille,
                    grille2, message, onglets, panneau_fiche, statusbar, table, v, vue, assistant)
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import anneau, cacher, choisir, classe, clic, fermer, montrer, ouvrir, pause, saisir, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ASSIST, MANAGER = P['assistante'], P['manager']
MENUS_A = ['Documents', 'Dossiers métier', 'Plan de classement', 'Analyse']
MENUS_M = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse', 'Configuration']
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'
REF = 'DOC-2026-00360'
TITRE = 'Procédure de traitement du courrier entrant'
CIRCUIT = 'Procédure — rédaction, vérification, approbation'
ONGLETS = ['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Circuit', 'Description']
ALEA = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M3 7h4l10 10h4M17 21l4-4-4-4M3 17h4l3-3M14 10l3-3h4M17 3l4 4-4 4"/></svg>')


def bt_traiter(ident):
    return '<span class="bt prim" id="%s"><span class="ic t21-ic">%s</span>Traiter</span>' % (ident, ALEA)


def bandeau_circuit(ident, etape, echeance, masque):
    return ('<div class="bandeau t21-info%s" id="%s"><span class="t21-ic2">%s</span>Circuit en cours — étape '
            '<b class="lien" id="%s-et">%s</b> · échéance <span id="%s-ech">%s</span></div>'
            % (' masque' if masque else '', ident, ALEA, ident, e(etape), ident, e(echeance)))


def versions(prefixe):
    return table([('Version', '60px'), ('Nom du fichier', '1fr'), ('Commentaire de version', '1fr'), ('Taille (octets)', '96px'),
                  ('Téléversé par', '110px'), ('Date', '120px')],
                 [{'id': prefixe + '-v1', 'cellules': ['v1', 'Procedure_courrier_entrant.docx', 'Version initiale', c_num('52 418'),
                                                       ASSIST[0], '13/10/2026 09:58']}], identifiant=prefixe + '-vers', ajouter=False)


def corps_doc(prefixe, bandeau_html, onglet, contenu):
    return (bandeau_html
            + '<div class="ref-l">Référence</div><div class="ref-v moyen">%s</div><div class="titre-doc t21-h2">%s</div>' % (REF, e(TITRE))
            + grille2([champ('Type', v('Procédure / instruction'), prefixe + '-type'),
                       champ('Dossier de classement', v('Qualité et procédures / Procédures en vigueur'))],
                      [champ('Propriétaire', v(ASSIST[0])), champ('Fichier', v('Procedure_courrier_entrant.docx'))])
            + onglets(ONGLETS, onglet, prefixe + '-og') + contenu)


def action_wizard(ident, etape, options):
    """L'assistant « Action de circuit » (titre de la fenêtre : « Action — <réf.> »)."""
    radio = ('<span class="t21-radio"><span class="t21-r on"><i></i>Appliquer une transition</span>'
             '<span class="t21-r"><i></i>Rejeter</span></span>')
    dd = '<div class="t21-dd masque" id="%s-dd"%s>%s</div>' % (ident, ZONE, ''.join(
        '<div class="it" id="%s-o%d">%s</div>' % (ident, i, e(o)) for i, o in enumerate(options)))
    corps = (champ('Objet', v(REF)) + champ('Étape courante', v(etape))
             + champ('Action', radio, ident + '-action')
             + '<div class="t21-trans">%s%s</div>' % (champ('Transition', entree(ident + '-t', '', ''), ident + '-tc'), dd)
             + champ('Commentaire', entree(ident + '-c', 'Commentaire (obligatoire pour un rejet ou un retour)'), ident + '-cc'))
    return assistant(ident, 'Action — %s' % REF, corps, [(ident + '-ok', 'Valider', 'prim'), (ident + '-non', 'Annuler', 'second')],
                     haut=170, largeur=760)


# ------------------------------------------------------- l'assistante --
def ecran_assistante():
    a = [bouton('t21-lancer', 'Lancer le circuit', 'prim', 'lecture'), bouton('t21-fin', 'Finaliser', 'prim'),
         bouton('t21-res', 'Réserver', 'second', 'cadenas'), bouton('t21-prev', 'Prévisualiser', 'second', 'oeil'),
         bouton('t21-corb', 'Corbeille', 'second', 'corbeille'), bouton('t21-part', 'Partager', 'second')]
    b = [bt_traiter('t21-traiter'), bouton('t21-res2', 'Réserver', 'second', 'cadenas'),
         bouton('t21-prev2', 'Prévisualiser', 'second', 'oeil'), bouton('t21-corb2', 'Corbeille', 'second', 'corbeille'),
         bouton('t21-part2', 'Partager', 'second')]
    c = [bouton('t21-res3', 'Réserver', 'second', 'cadenas'), bouton('t21-prev3', 'Prévisualiser', 'second', 'oeil'),
         bouton('t21-corb3', 'Corbeille', 'second', 'corbeille'), bouton('t21-part3', 'Partager', 'second')]
    corps = corps_doc('t21a', bandeau_circuit('t21-bc', 'Rédaction', '16/10/2026 10:42', True), 0, versions('t21a'))
    acts = ('<div class="ch-sep t21-ap masque" id="t21-aps">▾ Activités planifiées</div>'
            + activite('[Circuit] Rédaction — %s' % REF, ASSIST[0], 'Étape « Rédaction » à traiter.', ASSIST[2], ASSIST[1],
                       't21-act0').replace("Aujourd'hui :", 'Dû dans 3 jours :'))
    ch = chatter([message(ASSIST[0], ASSIST[2], '• Rédaction → <span class="lien">Vérification</span> <i>(Étape courante)</i>',
                          '15:06', 't21-m2', masque=True),
                  message(ASSIST[0], ASSIST[2], 'Circuit « %s » lancé — étape « Rédaction ».' % e(CIRCUIT), '10:42', 't21-m1',
                          masque=True),
                  message(ASSIST[0], ASSIST[2], 'Version v1 déposée.', '09:58')],
                 activites=acts, identifiant='t21-ach', suivre='Suivre')
    doc = vue('t21-doc', panneau_fiche('Documents', TITRE, '1 / 1', boutons_stat=bouton_stat('Sceaux', '1', 'sceau'))
              + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                  bande(a, statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 't21-sb'), 't21-b', [b, c]),
                  feuille(corps), ch), initiale=True)
    wiz = action_wizard('t21-wa', 'Rédaction', ['Transmettre pour vérification (Rédaction → Vérification)', 'Recherche avancée…'])
    return fenetre('ECM', MENUS_A, [doc], ASSIST[1], ASSIST[2], calques=wiz, ident='app-21a')


# ---------------------------------------------------------- le manager --
HISTO = [('Approuvée', '13/10/2026 16:31', '', '00:00', MANAGER[0], '', ''),
         ('Vérification', '13/10/2026 15:06', '13/10/2026 16:31', '01:25', MANAGER[0], 'Approuver', ''),
         ('Rédaction', '13/10/2026 10:42', '13/10/2026 15:06', '04:24', ASSIST[0], 'Transmettre pour vérification',
          'Rédaction terminée, prête pour relecture.')]


def ecran_manager():
    a = [bt_traiter('t21-mtraiter'), bouton('t21-reset', 'Réinitialiser le circuit', 'second'),
         bouton('t21-mres', 'Réserver', 'second', 'cadenas'), bouton('t21-mprev', 'Prévisualiser', 'second', 'oeil'),
         bouton('t21-mcorb', 'Corbeille', 'second', 'corbeille'), bouton('t21-mpart', 'Partager', 'second')]
    b = [bouton('t21-reset2', 'Réinitialiser le circuit', 'second'), bouton('t21-march', 'Archiver', 'second'),
         bouton('t21-mbr', 'Remettre en brouillon', 'second'), bouton('t21-mprev2', 'Prévisualiser', 'second', 'oeil'),
         bouton('t21-mcorb2', 'Corbeille', 'second', 'corbeille'), bouton('t21-mpart2', 'Partager', 'second')]
    circuit = ('<div class="masque t21-pane" id="t21-pc">%s%s</div>' % (
        grille2([champ('Circuit', v(CIRCUIT, True)), champ('Circuit — statut', v('Terminé'), 't21-stat')],
                [champ('Étape courante', v('Approuvée', True)), champ('Échéance SLA', '')]),
        table([('Étape', '86px'), ('Entrée', '108px'), ('Sortie', '108px'), ('Durée (h)', '56px'), ('Par', '96px'),
               ('Transition', '1fr'), ('Commentaire', '1fr')],
              [{'id': 't21-h%d' % i, 'cellules': list(h)} for i, h in enumerate(HISTO)], identifiant='t21-histo', ajouter=False)))
    contenu = ('<div class="t21-panes"><div class="t21-pane" id="t21-pv">%s</div>%s</div>' % (versions('t21m'), circuit))
    corps = corps_doc('t21m', bandeau_circuit('t21-mbc', 'Vérification', '15/10/2026 15:06', False), 0, contenu)
    acts = ('<div class="ch-sep t21-ap" id="t21-maps">▾ Activités planifiées</div>'
            + activite('[Circuit] Vérification — %s' % REF, MANAGER[0], 'Étape « Vérification » à traiter.', MANAGER[2],
                       MANAGER[1], 't21-mact', masque=False).replace("Aujourd'hui :", 'Dû dans 2 jours :'))
    ch = chatter([message(MANAGER[0], MANAGER[2], '• Vérification → <span class="lien">Approuvée</span> <i>(Étape courante)</i>',
                          '16:31', 't21-mm2', masque=True),
                  message(ASSIST[0], ASSIST[2], '• Rédaction → <span class="lien">Vérification</span> <i>(Étape courante)</i>',
                          '15:06'),
                  message(ASSIST[0], ASSIST[2], 'Circuit « %s » lancé — étape « Rédaction ».' % e(CIRCUIT), '10:42')],
                 activites=acts, identifiant='t21-mch', suivre='Suivre')
    doc = vue('t21-mdoc', panneau_fiche('Documents', TITRE, '1 / 1', boutons_stat=bouton_stat('Sceaux', '1', 'sceau'))
              + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                  bande(a, statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 't21-msb'), 't21-mb', b),
                  feuille(corps), ch), initiale=True)
    wiz = action_wizard('t21-wm', 'Vérification', ['Retour au rédacteur (Vérification → Rédaction)',
                                                   'Approuver (Vérification → Approuvée)', 'Recherche avancée…'])
    html = fenetre('ECM', MENUS_M, [doc], MANAGER[1], MANAGER[2], calques=wiz, ident='app-21m')
    return html.replace('<div class="o-app muk" id="app-21m">', '<div class="o-app muk masque" id="app-21m">', 1)


CSS = """
#app-21a .t21-h2, #app-21m .t21-h2 { font-size: 20px; margin: 0 0 8px; }
#app-21a .champ, #app-21m .champ { grid-template-columns: 140px 1fr; }
#app-21a .t21-ic svg, #app-21m .t21-ic svg { width: 12px; height: 12px; display: block; }
#app-21a .t21-info, #app-21m .t21-info { background: #D7EEF3; color: #1F2D3D; }
#app-21a .t21-info b, #app-21m .t21-info b { font-weight: 600; }
#app-21a .t21-ic2 svg, #app-21m .t21-ic2 svg { width: 12px; height: 12px; display: inline-block; vertical-align: -1px; margin-right: 5px; }
#app-21a .t21-ap, #app-21m .t21-ap { margin: 10px 0 8px; color: #343A40; font-weight: 700; }
#app-21a .o-chatter .act .at, #app-21m .o-chatter .act .at { line-height: 1.35; }
#app-21a .modale .champ, #app-21m .modale .champ { padding: 5px 0; grid-template-columns: 130px 1fr; }
#app-21a .modale .entree, #app-21m .modale .entree { width: 100%; }
#app-21a .t21-radio, #app-21m .t21-radio { display: flex; flex-direction: column; gap: 6px; }
#app-21a .t21-r, #app-21m .t21-r { display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; }
#app-21a .t21-r i, #app-21m .t21-r i { width: 12px; height: 12px; border-radius: 50%; border: 1px solid #ADB5BD; display: inline-block; }
#app-21a .t21-r.on i, #app-21m .t21-r.on i { border: 4px solid #5D8DA8; width: 6px; height: 6px; }
#app-21a .t21-trans, #app-21m .t21-trans { position: relative; }
#app-21a .t21-dd, #app-21m .t21-dd { position: absolute; left: 130px; top: 32px; z-index: 30; min-width: 380px; padding: 4px 0; background: #fff;
  border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 18px rgba(0,0,0,.16); color: #212529; font-size: 12.5px; }
#app-21a .t21-dd .it, #app-21m .t21-dd .it { padding: 5px 14px; white-space: nowrap; }
#app-21a .t21-dd .it:last-child, #app-21m .t21-dd .it:last-child { color: #528099; }
#app-21a .t21-dd .it.survol, #app-21m .t21-dd .it.survol { background: #EEF3F6; }
#app-21m .o-bande .bt { padding: 0 7px; font-size: 11.5px; gap: 4px; }
#app-21m .o-bande .groupe-bt { gap: 3px; }
#app-21m .o-bande .sb { font-size: 11px; padding: 0 4px 0 13px; }
#app-21m .t21-panes { display: grid; } #app-21m .t21-panes > .t21-pane { grid-area: 1 / 1; }
#app-21m .o-table .tl { height: auto; min-height: 28px; padding-top: 4px; padding-bottom: 4px; }
#app-21m .o-table .tl .ell { white-space: normal; }
"""

TUTO = {
    'slug': 'tuto-21-circuit-de-validation-d-un-document',
    'titre_page': "AITE ECM — Tutoriel 21 : circuit de validation d'un document",
    'titre': 'Circuit de validation',
    'serie': dict(ECM, numero=21),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Cette procédure, qui doit la *valider ?*',
        'sous': "Relectures par e-mail, versions qui se croisent, validation orale : une procédure met des semaines à paraître.",
        'personnage': (ASSIST[0], 'Assistante', ASSIST[2]),
        'chaos': [('doc', 'Procédure_v3_final.docx'), ('bulle', "Tu l'as relue ?"), ('alerte', 'Validation en attente'),
                  ('note', 'Qui valide ?'), ('lettre', 'Re: Re: relecture'), ('bulle', 'Je ne savais pas'),
                  ('dossier', 'Brouillons'), ('alerte', 'Version périmée')],
        'voix': "Une procédure part en relecture par e-mail. Les versions se croisent, personne ne sait qui doit la valider, "
                "et la validation finit par se faire de vive voix.",
    },
    'revelation': {'voix': "Avec Aïte E C M, chaque document suit son circuit de validation."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Faire *valider* un document, étape par étape',
        'pastilles': ['Un circuit par type', 'Le valideur prévenu', 'Finalisé en fin de circuit'],
        'voix': "Le type du document désigne son circuit ; à chaque étape, les bonnes personnes sont prévenues, et à la "
                "fin, le document est finalisé tout seul. Voyons comment.",
    },
    'ecran': ecran_assistante() + ecran_manager(), 'vue_initiale': 't21-doc',
    'css': CSS,
    'etapes': [
        {'titre': 'Lancer le circuit',
         'texte': "Sur un document en brouillon : le type désigne le circuit, le document entre à sa première étape.",
         'voix': "Estelle, l'assistante, a rédigé une procédure, encore en brouillon. Elle clique sur Lancer le circuit : "
                 "le type, Procédure ou instruction, désigne le circuit, rédaction, vérification, approbation. Le document "
                 "entre à l'étape Rédaction, avec son échéance.",
         'gestes': [anneau('#t21a-type', d=1.2, decale=0.3), clic('#t21-lancer'), cacher('#t21-b-a', d=0.2),
                    montrer('#t21-b-b', y=0, avec=True), montrer('#t21-bc', y=-6), montrer('#t21-m1', y=10, avec=True),
                    montrer('#t21-aps', y=6, avec=True), montrer('#t21-act0', y=6, avec=True),
                    zoom('#t21-bc', s=1.6, fx=0.5, fy=0.35, d=0.8), anneau('#t21-bc', d=1.4),
                    bulle('#t21-bc-ech', 'Rédaction : 72 h', cote='dessous', d=2.2, avec=True), dezoom(d=0.7),
                    anneau('#t21-act0', d=1.4)]},
        {'titre': 'Traiter et transmettre',
         'texte': "« Traiter » ouvre l'action de circuit : une transition permise, un commentaire, puis Valider.",
         'voix': "Son travail terminé, elle clique sur Traiter. L'action de circuit ne propose que les transitions "
                 "permises : Transmettre pour vérification. Un commentaire, Valider : le document passe à l'étape "
                 "Vérification, et chaque manager reçoit une activité à traiter.",
         'gestes': [clic('#t21-traiter'), ouvrir('t21-wa'), anneau('#t21-wa-action', d=1.0),
                    clic('#t21-wa-t', fx=0.3), montrer('#t21-wa-dd', y=-6, d=0.25), survol('#t21-wa-o0', decale=0.2),
                    clic('#t21-wa-o0', fx=0.3), cacher('#t21-wa-dd', d=0.15),
                    choisir('t21-wa-t', 'Transmettre pour vérification', avec=True),
                    clic('#t21-wa-c', fx=0.2), saisir('t21-wa-c', 'Rédaction terminée, prête pour relecture.', d=1.6),
                    clic('#t21-wa-ok'), fermer('t21-wa'), texte('#t21-bc-et', 'Vérification', decale=0.2),
                    texte('#t21-bc-ech', '15/10/2026 15:06', avec=True), cacher('#t21-b-b', d=0.2),
                    montrer('#t21-b-c', y=0, avec=True), cacher('#t21-act0', d=0.2, avec=True), cacher('#t21-aps', d=0.2, avec=True),
                    montrer('#t21-m2', y=10), anneau('#t21-bc', d=1.4)]},
        {'titre': 'Le manager approuve',
         'texte': "Prévenu par une activité, le manager approuve ; à l'étape finale, le document est finalisé.",
         'voix': "Paul, le manager, trouve dans son fil l'activité qui l'attend. Il traite à son tour : la liste propose "
                 "Retour au rédacteur, qui exigerait un commentaire, ou Approuver. Il approuve. À l'étape finale, le "
                 "circuit est terminé, et le document passe tout seul au statut Finalisé.",
         'gestes': [montrer('#app-21m', y=0, d=0.4), anneau('#t21-mact', d=1.6, decale=0.3), clic('#t21-mtraiter'),
                    ouvrir('t21-wm'), clic('#t21-wm-t', fx=0.3), montrer('#t21-wm-dd', y=-6, d=0.25),
                    anneau('#t21-wm-o0', d=1.2), bulle('#t21-wm-o0', 'Commentaire obligatoire', cote='droite', d=2.0, avec=True),
                    survol('#t21-wm-o1', decale=0.6), clic('#t21-wm-o1', fx=0.3), cacher('#t21-wm-dd', d=0.15),
                    choisir('t21-wm-t', 'Approuver', avec=True), clic('#t21-wm-ok'), fermer('t21-wm'),
                    cacher('#t21-mbc', d=0.3, decale=0.2), classe('#t21-msb-0', retirer=['actif'], avec=True),
                    classe('#t21-msb-1', ajouter=['actif'], avec=True), cacher('#t21-mb-a', d=0.2, avec=True),
                    montrer('#t21-mb-b', y=0, avec=True), cacher('#t21-maps', d=0.2, avec=True), cacher('#t21-mact', d=0.2, avec=True),
                    montrer('#t21-mm2', y=10), zoom('#t21-msb', s=1.7, fx=0.6, fy=0.3, d=0.8),
                    bulle('#t21-msb-1', 'Finalisé', cote='dessous', d=1.8), dezoom(d=0.7)]},
        {'titre': "L'historique, et la remise à zéro",
         'texte': "L'onglet Circuit garde chaque étape ; un manager peut réinitialiser le circuit.",
         'voix': "L'onglet Circuit garde tout l'historique : chaque étape, son entrée, sa sortie, sa durée, l'intervenant, "
                 "la transition et le commentaire. Et si besoin, un manager peut réinitialiser le circuit, qui revient à "
                 "l'état non lancé.",
         'gestes': [clic('#t21m-og-5'), classe('#t21m-og-0', retirer=['actif'], avec=True),
                    classe('#t21m-og-5', ajouter=['actif'], avec=True), cacher('#t21-pv', d=0.2, avec=True),
                    montrer('#t21-pc', y=10), anneau('#t21-stat', d=1.0),
                    zoom('#t21-histo', s=1.4, fy=0.5, d=0.8), anneau('#t21-histo', d=1.8),
                    bulle('#t21-h2', 'Qui, quand, quelle décision', cote='dessous', fx=0.5, d=2.4, avec=True), dezoom(d=0.7),
                    anneau('#t21-reset2', d=1.2), bulle('#t21-reset2', 'Retour à « Non lancé »', cote='dessous', d=2.2, avec=True)]},
    ],
    'benefices': {
        'titre': 'Des documents *validés,* sans relance.',
        'voix': "Le bon circuit s'applique tout seul, chaque valideur est prévenu au bon moment, et la validation laisse "
                "son historique, jusqu'au document finalisé.",
        'cartes': [('cible', '1 par type', 'Le bon circuit', "Le type du document désigne son circuit actif."),
                   ('equipe', 'Activités', 'Le valideur prévenu', "Chaque personne de l'étape reçoit son activité, avec l'échéance."),
                   ('trace', 'Finalisé', 'Une trace complète', "Historique des étapes, puis finalisation automatique.")],
    },
    'cta': cta('ecm', 'Vos validations, *enfin* *fluides.*', "Aïte E C M : vos validations, enfin fluides."),
    'youtube': youtube("COMMENT FAIRE VALIDER UN DOCUMENT PAR UN CIRCUIT AVEC AITE ECM (ODOO 18)",
                       "Lancer le circuit d'un document en brouillon, traiter l'étape, prévenir le valideur, approuver, puis "
                       "retrouver l'historique dans l'onglet Circuit : le document est finalisé automatiquement en fin de "
                       "circuit. Tutoriel AITE ECM pour Odoo 18.",
                       ['AITE ECM', 'circuit de validation', 'workflow documentaire', 'validation de procédure']),
}
