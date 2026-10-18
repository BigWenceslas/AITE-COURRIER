# -*- coding: utf-8 -*-
"""Tutoriel 03 — Circuits et délais : SLA, relances, escalade.

Sources :
- menus : aite_courrier_base/views/aite_courrier_menus.xml (« Configuration »,
  « Types de courrier », « Priorités », « Niveaux de confidentialité »),
  aite_courrier_workflow/views/aite_workflow_menus.xml:7 (« Circuits de
  traitement »), aite_courrier_ged/views/aite_courrier_ged_menus.xml
  (« Dossiers », « Étiquettes de documents »),
  aite_courrier_reponse/views/aite_courrier_reponse_template_views.xml:77
  (« Modèles de réponse ») ;
- liste et fiche du circuit : aite_courrier_workflow/views/aite_workflow_views.xml
  (colonnes « Nom », « Type de courrier » ; onglets « Étapes », « Transitions » ;
  bandeau d'information de l'onglet Transitions ; « Actif »),
  aite_ecm_workflow/views/aite_workflow_views.xml (« Objet gouverné »),
  models/aite_workflow_step.py (« Rôles autorisés », « Utilisateurs autorisés »,
  « SLA (heures) », « Étape initiale », « Étape finale »),
  models/aite_workflow_transition.py (« Étape de départ », « Étape d'arrivée »,
  « Libellé », « Sens » : « En avant » / « En arrière », « Commentaire
  obligatoire »), models/aite_workflow_circuit.py:45 (un seul circuit actif
  par type de courrier) ;
- données : aite_courrier_workflow/data/workflow_circuits.xml (5 circuits,
  27 étapes ; Courrier entrant standard : Réception 4 h, Qualification 8 h,
  Affectation 4 h, Traitement 48 h, Archivage 24 h, rôles et transitions),
  aite_courrier_base/security/groups.xml (noms des rôles),
  aite_ecm_dossier/data, aite_ecm_workflow/data (les deux circuits ECM listés
  dans le même menu quand AITE ECM est installé) ;
- relances et escalade : aite_courrier_core/data/ir_cron_data.xml (tâche
  « AITE Courrier : relances et escalades SLA », toutes les heures),
  models/aite_courrier.py:330 (échéance = entrée dans l'étape + SLA),
  :455 _cron_check_sla_overdue (relance : message « ⏰ Relance SLA : … » aux
  habilités de l'étape ; escalade après aite_courrier.sla_escalation_hours,
  24 h par défaut : activité « Escalade SLA — <réf.> » au manager du service
  destinataire, sinon aux Managers, et message « 🔺 Escalade SLA : … »),
  :366 action_launch_circuit (le courrier retient le circuit actif de son
  type), :325 message « Courrier arrivé à l'étape … », :439 destinataires
  de l'escalade ; les 14 transitions « En arrière » livrées exigent un
  commentaire ;
- liste des courriers : aite_courrier_core/views/aite_courrier_views.xml
  (filtre « En retard (SLA) », menus Filtres / Regrouper par) ;
- docs/produits/AITE_Courrier_fiche_avant_vente_technique.md (5 circuits,
  27 étapes, relance puis escalade, 24 h par défaut ; paramétrage sans code).
Modèle visuel : base demo18 (MuK), captures t03_*.
"""

import demo
from ecrans import (ICONES, activite, bande, bouton, bouton_stat, c_html, c_num, c_puce, case, champ, chatter,
                    e, entree, fenetre, feuille, grille2, liste, message, onglets, panneau_fiche, panneau_lateral,
                    panneau_liste, puce, statusbar, table, v, vue)
from scenarios import presentation as base
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, cacher, classe, clic, curseur, montrer, survol, vue as aller
from tutoriel import ECHELLE, bulle, dezoom, zoom

P = demo.PERSONNES
ADMIN, MANAGER, AGENT, ASSIST = P['admin'], P['manager'], P['agent'], P['assistante']
ETAPES = base.ETAPES

# Le courrier en retard de l'étape 4 (fictif) : entré en Qualification le
# 12/10 à 08:47, SLA 8 h → échéance 16:47 ; relance au passage horaire de
# 17:00 ; escalade le lendemain, 24 h après l'échéance.
RETARD = {'reference': 'COUR-2026-0136', 'objet': 'Réclamation sur un retard de livraison',
          'expediteur': demo.FOURNISSEUR, 'courriel': demo.EN_COURS['courriel'], 'date': '12/10/2026',
          'service': 'Commercial', 'priorite': 'Haute', 'confidentialite': 'Interne'}

ROLE = 'AITE Courrier / %s'
# (nom, description, rôles, SLA, initiale, finale) — workflow_circuits.xml
ETAPES_CIRCUIT = [
    ('Réception', 'Enregistrement et numérisation', ['Agent courrier'], 4, True, False),
    ('Qualification', 'Catégorisation, priorité, confidentialité', ['Agent courrier', 'Assistant(e)'], 8, False, False),
    ('Affectation', 'Attribution service/responsable', ['Assistant(e)', 'Manager'], 4, False, False),
    ('Traitement', 'Analyse par le service destinataire', ['Manager'], 48, False, False),
    ('Archivage', 'Clôture, indexation, conservation', ['Archiviste'], 24, False, True),
]
TRANSITIONS = [
    ('Réception', 'Qualification', 'Qualifier', 'En avant', False),
    ('Qualification', 'Affectation', 'Affecter', 'En avant', False),
    ('Qualification', 'Réception', 'Retourner', 'En arrière', True),
    ('Affectation', 'Traitement', 'Transmettre', 'En avant', False),
    ('Affectation', 'Qualification', 'Retourner', 'En arrière', True),
    ('Traitement', 'Archivage', 'Archiver', 'En avant', False),
    ('Traitement', 'Affectation', 'Réaffecter', 'En arrière', True),
]
# ordre de la liste : type de courrier (par code), puis nom ; les circuits ECM n'ont pas de type
CIRCUITS = [('Devis commercial', 'Devis'), ('Courrier entrant standard', 'Courrier entrant'),
            ('Facture fournisseur', 'Facture'), ('Courrier interne', 'Courrier interne'),
            ('Courrier sortant', 'Courrier sortant'), ('Agrément fournisseur — instruction et validation', ''),
            ('Procédure — rédaction, vérification, approbation', '')]
MENU_CONFIG = ['Types de courrier', 'Priorités', 'Niveaux de confidentialité', 'Circuits de traitement', 'Dossiers',
               'Étiquettes de documents', 'Modèles de réponse']

ENTONNOIR = '<svg viewBox="0 0 24 24" fill="#fff"><path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/></svg>'
POIGNEE = ('<svg viewBox="0 0 8 14" fill="#ADB5BD"><circle cx="2" cy="2" r="1.3"/><circle cx="6" cy="2" r="1.3"/>'
           '<circle cx="2" cy="7" r="1.3"/><circle cx="6" cy="7" r="1.3"/><circle cx="2" cy="12" r="1.3"/>'
           '<circle cx="6" cy="12" r="1.3"/></svg>')
COUCHES = ('<svg viewBox="0 0 24 24" fill="#343A40"><path d="M12 3l10 5-10 5L2 8z"/>'
           '<path d="M4.6 11.7L12 15.4l7.4-3.7L22 13l-10 5L2 13z"/></svg>')
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'


def bulle_g(sel, texte, largeur, s=1.0, d=2.2, **kw):
    """Une bulle à gauche de ``sel`` (``largeur`` et ``s`` : conservés pour les appels existants)."""
    return bulle(sel, texte, cote='gauche', d=d, **kw)


def tags(roles):
    return c_html('<span class="t3-tags">%s</span>' % ''.join('<span class="t3-tag">%s</span>' % e(ROLE % r) for r in roles))


def corbeille():
    return c_html('<span class="t3-corb">%s</span>' % ICONES['corbeille'])


# ------------------------------------------------------ l'administrateur --
def ecran_admin():
    # la liste des courriers, d'où part l'administrateur
    lignes = base.LIGNES_COURRIERS[:18]       # les lignes visibles sans défiler
    lst = vue('t3-courriers', panneau_liste('Courriers', '1-80 / 151', ident='t3a') + base.lat_courriers('t3-lat')
              + liste(base.COL_COURRIERS, [base.ligne_courrier('t3-c%d' % i, *l) for i, l in enumerate(lignes)]),
              initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    # la liste des circuits de traitement
    circ = vue('t3-liste', panneau_liste('Circuits de traitement', '1-7 / 7', ident='t3l')
               + liste([('Nom', '1fr'), ('Type de courrier', '300px')],
                       [{'id': 't3-l%d' % i, 'cellules': [n, t]} for i, (n, t) in enumerate(CIRCUITS)])
               + '<div class="t3-zone" id="t3-cinq"%s></div><div class="t3-zone" id="t3-types"%s></div>' % (ZONE, ZONE))
    # la fiche du circuit « Courrier entrant standard »
    etapes = table([('', '10px'), ('Nom', '82px'), ('Description', '1fr'), ('Rôles autorisés', '300px'),
                    ('Utilisateurs autorisés', '96px'), ('SLA (heures)', '64px'), ('Étape initiale', '70px'),
                    ('Étape finale', '62px'), ('', '12px')],
                   [{'id': 't3-e%d' % i, 'cellules': [
                       c_html('<span class="t3-poignee">%s</span>' % POIGNEE), n, d, tags(r), '',
                       c_html('<span class="num" id="t3-e%d-sla">%d</span>' % (i, s)),
                       c_html('<span id="t3-e%d-ini">%s</span>' % (i, case(ini))),
                       c_html('<span id="t3-e%d-fin">%s</span>' % (i, case(fin))), corbeille()]}
                    for i, (n, d, r, s, ini, fin) in enumerate(ETAPES_CIRCUIT)], identifiant='t3-tab-e')
    transitions = ('<div class="bandeau t3-info">Les étapes de départ et d\'arrivée sont limitées aux étapes de ce circuit. '
                   'Enregistrez d\'abord le circuit et ses étapes pour pouvoir les sélectionner.</div>'
                   + table([('Étape de départ', '1fr'), ("Étape d'arrivée", '1fr'), ('Libellé', '1fr'), ('Sens', '0.8fr'),
                            ('Commentaire obligatoire', '120px'), ('', '12px')],
                           [{'id': 't3-t%d' % i, 'cellules': [a, b, c_html('<span class="ell" id="t3-t%d-lib">%s</span>' % (i, e(l))),
                                                              c_html('<span class="ell" id="t3-t%d-sens">%s</span>' % (i, e(s))),
                                                              c_html('<span id="t3-t%d-com">%s</span>' % (i, case(com))), corbeille()]}
                            for i, (a, b, l, s, com) in enumerate(TRANSITIONS)], identifiant='t3-tab-t'))
    corps = (grille2([champ('Nom', entree('t3-nom', '', 'Courrier entrant standard')),
                      champ('Objet gouverné', entree('t3-objet', '', 'Courrier')),
                      champ('Type de courrier', entree('t3-type-v', '', 'Courrier entrant'), identifiant='t3-type')],
                     [champ('Actif', case(True))])
             + onglets(['Étapes', 'Transitions'], 0, 't3-og')
             + '<div class="t3-panes"><div id="t3-pe">%s</div><div class="masque" id="t3-pt">%s</div></div>' % (etapes, transitions))
    form = vue('t3-form', panneau_fiche('Circuits de traitement', 'Courrier entrant standard', '2 / 7')
               + '<div class="o-corps"><div class="o-gauche">%s</div></div>' % feuille(corps, identifiant='t3-feuille'))
    html = fenetre('Courrier', ['Tableau de bord', 'Courriers', 'Espace documentaire', 'Audit', 'Configuration'],
                   [lst, circ, form], ADMIN[1], ADMIN[2], ident='app-3a')
    # le menu déroulant « Configuration »
    dd = '<div class="masque" id="t3-dd"%s>%s</div>' % (ZONE, ''.join(
        '<div class="it" id="t3-dd-%d">%s</div>' % (i, e(m)) for i, m in enumerate(MENU_CONFIG)))
    return html.replace('<span class="menu" id="app-3a-m4">Configuration</span>',
                        '<span class="menu t3-menu" id="app-3a-m4">Configuration%s</span>' % dd, 1)


# ------------------------------------------------------------ le manager --
LIGNES_RETARD = [
    (RETARD['reference'], RETARD['objet'], 'Courrier entrant', RETARD['service'], 'Qualification', 'En traitement', 'gris', RETARD['date']),
    ('COUR-2026-0139', 'Candidature spontanée — poste de comptable', 'Courrier entrant', '', 'Réception', 'Nouveau', 'gris', '12/10/2026'),
    ('COUR-2026-0017', 'Notification de contrôle fiscal', 'Courrier entrant', 'Finance et comptabilité', 'Qualification', 'En traitement', 'gris', '09/10/2026'),
    ('COUR-2026-0005', 'Rappel de cotisations sociales — août', 'Courrier entrant', 'Juridique', 'Traitement', 'En traitement', 'gris', '18/09/2026'),
    ('COUR-2026-0002', 'Demande de rendez-vous avec la Direction', 'Courrier entrant', 'Direction générale', 'Qualification', 'En traitement', 'gris', '15/09/2026'),
    ('COUR-2026-0003', 'Mise en demeure — facture N-2025-6874', 'Courrier entrant', 'Juridique', 'Traitement', 'En traitement', 'gris', '10/09/2026'),
    ('COUR-2026-0004', 'Plainte pour nuisance sonore', 'Courrier entrant', 'Communication', 'Affectation', 'En traitement', 'gris', '08/09/2026'),
]

DD_FILTRES = ('<div class="masque" id="t3-ddf"%s><div class="col"><div class="h">%s Filtres</div>'
              '<div class="f">Brouillons</div><div class="f">Traités</div><div class="f" id="t3-f-retard">En retard (SLA)</div>'
              '<div class="f">Mes courriers</div><div class="f">Reçus ce mois</div><div class="sep"></div>'
              '<div class="f">Entrants</div><div class="f">Sortants</div><div class="f">Internes</div><div class="sep"></div>'
              '<div class="f">Ajouter un filtre personnalisé</div></div>'
              '<div class="col"><div class="h">%s Regrouper par</div><div class="f">Type</div><div class="f">Statut</div>'
              '<div class="f">Priorité</div><div class="f">Service</div><div class="sep"></div>'
              '<div class="f">Ajouter un groupe personnalisé ▾</div></div>'
              '<div class="col"><div class="h"><b class="etoile">★</b> Favoris</div>'
              '<div class="f">Enregistrer la recherche actuelle ▾</div></div></div>'
              % (ZONE, '<span class="t3-ico">%s</span>' % ENTONNOIR.replace('#fff', '#343A40'),
                 '<span class="t3-ico">%s</span>' % COUCHES))


def ecran_manager():
    lignes = list(base.LIGNES_COURRIERS)
    lignes.insert(3, LIGNES_RETARD[0])
    lignes = lignes[:18]
    tous = vue('t3-tous', panneau_liste('Courriers', '1-80 / 152', nouveau=False)
               .replace('<span class="drop">▾</span>', '<span class="drop" id="t3-drop">▾</span>' + DD_FILTRES, 1)
               + base.lat_courriers(None)
               + liste(base.COL_COURRIERS, [base.ligne_courrier('t3-m%d' % i, *l) for i, l in enumerate(lignes)]),
               initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    lat = panneau_lateral([('▰ CATÉGORIE', [('Tous', '', True), ('Entrant', '7', False)]),
                           ('≡ STATUT', [('Nouveau', '1', False), ('En traitement', '6', False)])])
    retard = vue('t3-retard', panneau_liste('Courriers', '1-7 / 7', facettes=[('◆', 'En retard (SLA)')], nouveau=False)
                 .replace('<span class="k">◆</span>', '<span class="k t3-k">%s</span>' % ENTONNOIR, 1)
                 + lat + liste(base.COL_COURRIERS, [base.ligne_courrier('t3-r%d' % i, *l) for i, l in enumerate(LIGNES_RETARD)]))
    retard = retard.replace('class="vue"', 'class="vue avec-lateral"', 1)
    # la fiche du courrier en retard, telle que le manager la trouve le 13/10
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v">%s</div>' % RETARD['reference']
             + grille2([champ('Objet', v(RETARD['objet'])), champ('Contact expéditeur', v(RETARD['expediteur'], True), aide=True),
                        champ('Expéditeur', v(RETARD['expediteur'])), champ('E-mail expéditeur', v(RETARD['courriel'], True), aide=True),
                        champ('Type', v('Courrier entrant', True)), champ('Service destinataire', v(RETARD['service'], True))],
                       [champ('Statut', puce('En traitement', 'gris'), aide=True), champ('Priorité', v(RETARD['priorite'], True)),
                        champ('Confidentialité', v(RETARD['confidentialite'], True)), champ('Date de réception', v(RETARD['date'])),
                        champ('Responsable', v(ASSIST[0], True))])
             + onglets(['Documents', 'Historique'])
             + table([('Nom', '1fr'), ('Dossier', '80px'), ('Extension', '70px'), ('Nombre de versions', '110px'), ('État', '80px')],
                     [{'id': 't3-d1', 'cellules': [RETARD['objet'], '', 'pdf', c_num('1'), c_puce('Brouillon')]}], ajouter=False))
    esc = '<div class="ch-sep t3-ap">▾ Activités planifiées</div>' + activite(
        'Escalade SLA — %s' % RETARD['reference'], MANAGER[0],
        "Le courrier « %s » est bloqué à l'étape « Qualification » au-delà du délai d'escalade "
        "(24 h après l'échéance SLA)." % RETARD['objet'], MANAGER[2], MANAGER[1], 't3-act', masque=False)
    bot = '#7A6FA8'
    ch = chatter([message('OdooBot', bot, '🔺 Escalade SLA : retard signalé à la hiérarchie (%s).' % e(MANAGER[0]),
                          "Aujourd'hui à 17:00", 't3-msg-esc'),
                  '<div class="ch-sep">Hier</div>',
                  message('OdooBot', bot, "⏰ Relance SLA : l'échéance de l'étape « Qualification » est dépassée depuis "
                                          "le 12/10/2026 16h47.", 'Hier à 17:00', 't3-msg-rel'),
                  message(AGENT[0], AGENT[2], "Courrier arrivé à l'étape « Qualification » — traitement attendu.",
                          'Hier à 08:47', 't3-msg-q')],
                 activites=esc, identifiant='t3-chatter')
    stats = bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '1')
    fiche = vue('t3-fiche', panneau_fiche('Courriers', RETARD['reference'], '1 / 7', nouveau=False, boutons_stat=stats)
                + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                    bande([bouton('t3-traiter', 'Traiter', 'prim'), bouton('t3-rej', 'Rejeter', 'second'),
                           bouton('t3-com', 'Commenter', 'second'), bouton('t3-rep', 'Répondre', 'second', 'retour')],
                          statusbar(ETAPES, 1, 't3-sb'), 't3-bande'), feuille(corps), ch))
    html = fenetre('Courrier', base.MENUS_COURRIER, [tous, retard, fiche], MANAGER[1], MANAGER[2], ident='app-3b')
    return html.replace('<div class="o-app muk" id="app-3b">', '<div class="o-app muk masque" id="app-3b">', 1)


CSS = """
#app-3a .t3-menu { position: relative; }
#t3-dd { position: absolute; left: -12px; top: 28px; z-index: 30; width: 196px; padding: 6px 0; background: #fff;
  border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 18px rgba(0,0,0,.16); color: #212529; }
#t3-dd .it { padding: 4px 14px; font-size: 12.5px; white-space: nowrap; }
#t3-dd .it.survol { background: #EEF3F6; }
#app-3a .t3-zone, #app-3b .t3-zone { position: absolute; pointer-events: none; }
#t3-cinq { left: 34px; top: 84px; width: 380px; height: 155px; }
#t3-types { right: 14px; top: 84px; width: 300px; height: 155px; }
#app-3a .t3-panes { display: grid; } #app-3a .t3-panes > div { grid-area: 1 / 1; }
#app-3a .t3-tags { display: flex; gap: 4px; overflow: hidden; }
#app-3a .t3-tag { display: inline-block; padding: 1px 7px; border-radius: 9px; background: #E9ECEF; color: #343A40; font-size: 10px;
  line-height: 15px; white-space: nowrap; }
#app-3a .t3-poignee svg { width: 6px; height: 11px; display: block; }
#app-3a .t3-corb { color: #343A40; } #app-3a .t3-corb svg { width: 12px; height: 12px; display: block; }
#app-3a .t3-info { background: #D7EEF3; color: #1F2D3D; margin: 12px 0 8px; line-height: 1.45; }
#app-3a .o-feuille .entree { width: 92%; }
#app-3b .recherche { position: relative; }
#t3-ddf { position: absolute; right: -1px; top: 31px; z-index: 30; width: 560px; display: grid; grid-template-columns: 1.1fr 1fr 1fr;
  padding: 12px 0; background: #fff; border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 20px rgba(0,0,0,.16);
  color: #212529; font-size: 12px; }
#t3-ddf .col { padding: 0 12px; } #t3-ddf .col + .col { border-left: 1px solid #E9ECEF; }
#t3-ddf .h { display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 12.5px; margin: 0 0 6px 6px; }
#t3-ddf .t3-ico svg { width: 12px; height: 12px; display: block; }
#t3-ddf .etoile { color: #F0A020; font-weight: 400; }
#t3-ddf .f { padding: 3px 8px; white-space: nowrap; }
#t3-ddf .f.survol { background: #EEF3F6; }
#t3-ddf .sep { border-top: 1px solid #E9ECEF; margin: 5px 0; }
#app-3b .t3-k { display: inline-flex; align-items: center; }
#app-3b .t3-ap { margin: 10px 0 8px; color: #343A40; font-weight: 700; }
#app-3b .t3-k svg { width: 10px; height: 10px; display: block; }
"""

TUTO = {
    'slug': 'tuto-03-circuits-et-delais',
    'titre_page': 'AITE Courrier — Tutoriel 03 : circuits et délais',
    'titre': 'Circuits, délais et relances',
    'serie': dict(COURRIER, numero=3),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Ce courrier attend depuis *combien* de *temps ?*',
        'sous': "Délais jamais écrits, relances à la main, retards découverts trop tard : le courrier s'enlise sans bruit.",
        'personnage': (ADMIN[0], 'Administrateur', ADMIN[2]),
        'chaos': [('alerte', 'Délai dépassé'), ('bulle', 'Qui devait le relancer ?'), ('lettre', 'Pli en attente'),
                  ('note', 'Délai : « au plus vite »'), ('dossier', 'Pile « À traiter »'), ('doc', 'Tableau des relances'),
                  ('bulle', "Personne ne m'a prévenu"), ('alerte', 'Relance n° 4')],
        'voix': "Un courrier attend depuis trois jours sur un bureau. Personne ne l'a relancé, et le responsable l'apprend "
                "bien trop tard. Qui fixe les délais, et qui prévient qui ?",
    },
    'revelation': {'voix': "Avec Aïte Courrier, les délais se fixent étape par étape, et les retards remontent d'eux-mêmes."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Des circuits qui tiennent leurs *délais*',
        'pastilles': ['Un délai par étape', 'Relance automatique', 'Escalade au manager'],
        'voix': "L'administrateur règle les étapes, les rôles et les délais. Aïte Courrier relance l'équipe, puis alerte "
                "le manager. Voyons comment.",
    },
    'ecran': ecran_admin() + ecran_manager(), 'vue_initiale': 't3-courriers',
    'etapes': [
        {'titre': 'Les circuits livrés',
         'texte': "Configuration › Circuits de traitement : cinq circuits prêts pour le courrier, un actif par type.",
         'voix': "Martin, l'administrateur, ouvre Configuration, puis Circuits de traitement. Cinq circuits sont livrés "
                 "pour le courrier, vingt-sept étapes en tout, et chacun s'applique à un type de courrier.",
         'gestes': [clic('#app-3a-m4', decale=0.3), montrer('#t3-dd', y=-8, d=0.3), survol('#t3-dd-0', decale=0.2),
                    classe('#t3-dd-0', retirer=['survol'], decale=0.25), survol('#t3-dd-3', avec=True),
                    clic('#t3-dd-3', decale=0.2), cacher('#t3-dd', d=0.15), aller('t3-liste'),
                    zoom('#t3-cinq', s=1.45, fx=0.42, fy=0.3, d=0.9),
                    anneau('#t3-cinq', d=2.4), bulle('#t3-cinq', 'Cinq circuits livrés', d=2.4, avec=True),
                    dezoom(d=0.7),
                    anneau('#t3-types', d=2.4), bulle_g('#t3-types', 'Un circuit actif par type', 300, d=2.4, avec=True)]},
        {'titre': 'Des étapes, des rôles, des délais',
         'texte': "Pour chaque étape : les rôles autorisés, le délai en heures, l'étape initiale et l'étape finale.",
         'voix': "Il ouvre le courrier entrant standard : cinq étapes, de la réception à l'archivage. Pour chacune, les "
                 "rôles autorisés à agir, et le délai de traitement, en heures : quatre pour la réception, quarante-huit "
                 "pour le traitement. Une case marque l'étape initiale, une autre l'étape finale.",
         'gestes': [survol('#t3-l1'), clic('#t3-l1', fx=0.2), aller('t3-form'),
                    curseur('#t3-tab-e .ajout', fx=0.55, fy=1.5, d=0.6),
                    zoom('#t3-e1 .t3-tags', s=1.45, fx=0.45, fy=0.55, d=0.8),
                    anneau('#t3-e1 .t3-tags', d=2.2), bulle('#t3-e1 .t3-tags', 'Rôles autorisés', cote='dessous', d=2.2, avec=True),
                    dezoom(d=0.6), zoom('#t3-e2-sla', s=1.45, fx=0.6, fy=0.55, d=0.8),
                    anneau('#t3-e3-sla', d=2.2), bulle_g('#t3-e3-sla', 'Traitement : 48 h', 64, 1.45, avec=True),
                    anneau('#t3-e0-ini', d=1.8), bulle_g('#t3-e0-ini', 'Étape initiale', 70, 1.45, d=1.8, avec=True),
                    anneau('#t3-e4-fin', d=1.8), bulle_g('#t3-e4-fin', 'Étape finale', 62, 1.45, d=1.8, avec=True),
                    dezoom(d=0.7)]},
        {'titre': 'Avancer, ou revenir en arrière',
         'texte': "Les transitions relient les étapes : en avant, ou en arrière avec un commentaire obligatoire.",
         'voix': "L'onglet Transitions relie les étapes. En avant, le courrier progresse. En arrière, il revient pour "
                 "correction, avec un commentaire obligatoire. Tout se règle ici, sans développement.",
         'gestes': [clic('#t3-og-1'), classe('#t3-og-0', retirer=['actif'], avec=True), classe('#t3-og-1', ajouter=['actif'], avec=True),
                    cacher('#t3-pe', d=0.2), montrer('#t3-pt', y=10),
                    curseur('#t3-t4-lib', fx=0.85, fy=0.6, d=0.6),
                    zoom('#t3-t3-sens', s=1.4, fx=0.55, fy=0.5, d=0.8),
                    anneau('#t3-t0-sens', d=2.2), bulle_g('#t3-t0-sens', 'Le courrier avance', 158, 1.4, avec=True),
                    anneau('#t3-t6-sens', d=2.4),
                    bulle('#t3-t6-com', 'Commentaire obligatoire', cote='dessous', fx=0.08, d=2.4, avec=True),
                    dezoom(d=0.7),
                    anneau('#t3-tab-t .ajout', d=2.2),
                    bulle('#t3-tab-t .ajout .lien', 'Sans développement', cote='dessous', fx=0.1, d=2.2, avec=True)]},
        {'titre': 'Relance, puis escalade',
         'texte': "Délai dépassé : l'équipe est relancée ; 24 h plus tard, le manager reçoit une activité.",
         'voix': "Côté manager, Paul filtre les courriers en retard, et ouvre celui-ci, bloqué à la qualification. Chaque "
                 "heure, une tâche planifiée surveille les échéances. Délai dépassé : l'équipe de l'étape est relancée par "
                 "un message. Vingt-quatre heures après, le retard remonte au manager, avec une activité à traiter.",
         'gestes': [montrer('#app-3b', y=0, d=0.4), clic('#t3-drop', decale=0.3), montrer('#t3-ddf', y=-8, d=0.3),
                    survol('#t3-f-retard', decale=0.2), clic('#t3-f-retard', decale=0.1), cacher('#t3-ddf', d=0.15),
                    aller('t3-retard'), survol('#t3-r0', decale=0.3), clic('#t3-r0', fx=0.35), aller('t3-fiche'),
                    curseur('#t3-msg-q', fx=0.9, fy=0.2, d=0.6),
                    zoom('#t3-msg-esc', s=1.55, fx=0.62, fy=0.52, d=0.8),
                    anneau('#t3-msg-rel', d=2.2), bulle_g('#t3-msg-rel', "L'équipe est relancée", 211, 1.55, avec=True),
                    anneau('#t3-msg-esc', d=2.2), bulle_g('#t3-msg-esc', 'Escalade, 24 h plus tard', 211, 1.55, avec=True),
                    anneau('#t3-act', d=2.2), bulle_g('#t3-act', 'Une activité pour Paul', 211, 1.55, avec=True),
                    dezoom(d=0.7)]},
    ],
    'benefices': {
        'titre': 'Des délais *tenus,* sans courir après.',
        'voix': "Des circuits prêts à l'emploi, réglés sans développement, des délais clairs, étape par étape, et des "
                "retards qui remontent d'eux-mêmes, jusqu'au manager.",
        'cartes': [('cible', '5 circuits', "Prêts à l'emploi", "Entrant, sortant, interne, facture fournisseur, devis : 27 étapes livrées."),
                   ('eclair', 'Chaque heure', 'Relance automatique', "Délai dépassé : l'équipe de l'étape est relancée, sans y penser."),
                   ('equipe', '+ 24 h', 'Escalade au manager', "24 h après l'échéance, par défaut : le manager du service reçoit une activité.")],
    },
    'cta': cta('courrier', 'Des délais *tenus,* sans *relancer.*', "Aïte Courrier : des délais tenus, sans relancer."),
    'youtube': youtube('COMMENT PARAMÉTRER LES CIRCUITS, LES DÉLAIS ET LES RELANCES AVEC AITE COURRIER (ODOO 18)',
                       "Cinq circuits de traitement livrés, des étapes avec leurs rôles et leur délai en heures, des transitions "
                       "en avant et en arrière : l'administrateur règle tout sans développement. En cas de retard, AITE "
                       "Courrier relance l'équipe, puis escalade au manager. Tutoriel AITE Courrier pour Odoo 18.",
                       ['AITE Courrier', 'circuit de traitement', 'SLA', 'relance automatique', 'escalade', 'workflow Odoo']),
    'css': CSS,
}
