# -*- coding: utf-8 -*-
"""Tutoriel 09 — Signature électronique (Odoo Community, module OCA sign_oca).

Sources :
- addons/aite_courrier_sign_oca/models/aite_workflow_step.py (case
  « Signature requise ») ; views/aite_workflow_views.xml (colonne ajoutée
  après « Étape finale » dans la liste des étapes du circuit) ;
- addons/aite_courrier_sign_oca/views/aite_courrier_views.xml (bouton
  orange « Demander la signature », visible sur une étape cochée pour qui
  peut agir sur l'étape, tant que la signature n'est pas obtenue ; bouton
  statistique « Signatures ») ;
- addons/aite_courrier_sign_oca/models/aite_courrier.py :
  action_request_signature (dernière version PDF, signataire = responsable du
  courrier, zone page 1 en bas à droite, message « Demande de signature
  envoyée à … (document « … »). », audit « Demande de signature » ;
  « Signataire : … — … ») ; do_transition (garde : message « Cette étape exige
  une signature électronique : aucune demande n'a été signée depuis
  l'arrivée du courrier sur l'étape. Utilisez « Demander la signature » puis
  attendez la signature. », audit « Action bloquée » : « Étape « … » :
  signature électronique manquante. ») ; _sign_oca_on_request_signed
  (« <pièce>_signe.pdf » en nouvelle version, « Demande « … » signée par … PDF
  signé versé en v2. », audit « Signature complétée », source Système) ;
- addons/aite_courrier_ged : audit « Ajout pièce jointe » ; colonnes des
  versions (« Version », « Nom du fichier », « Extension », « Taille
  (octets) », « Téléversé par », « Date ») ;
- aite_courrier_base : colonnes du journal d'audit, types « Information »,
  « Succès », « Erreur », sources « Interface », « Système » ;
- aite_courrier_workflow/data/workflow_circuits.xml (circuit « Courrier
  sortant » : Préparation 24 h, Contrôle 8 h, Validation 24 h — rôle Manager,
  Signature 24 h, Émission 4 h ; transition « Soumettre visa ») ;
- aite_courrier_validation (assistant « Action sur le courrier ») ;
- sign_oca 18.0.1.4.3 (/home/user/odoo-env/oca-sign/sign_oca) : page publique
  /sign_oca/document/<id>/<jeton> (« Please Review And Act On This
  Document », repère « Click to start », bouton « Validate & Send document »
  traduit « Valider et envoyer le document »), e-mail « Nouveau document à
  signer » ; fenêtre « Adopter votre signature » (Nom complet, Automatique,
  Dessiner, Charger, Adopter & Signer, Annuler) relevée sur la base demo18 ;
- docs/TUTORIEL_SIGNATURE_COMMUNITY.md (parcours, garde par passage,
  signature électronique simple, un signataire, PDF seulement ; « convient
  aux visas, validations et approbations internes »).
Modèle visuel : base demo18 (MuK), captures t09_*.
"""

import demo
from ecrans import (ICONES, assistant, bande, bouton, bouton_stat, c_html, c_num, c_puce, case, champ, chatter, e, entree,
                    fenetre, feuille, grille2, liste, message, activite, onglets, panneau_fiche, panneau_liste, puce,
                    statusbar, table, v, vue)
from scenarios.tutos import ADRESSE, COURRIER, cta, youtube
from moteur import anneau, animer, cacher, choisir, clic, curseur, fermer, montrer, ouvrir, pause, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ADMIN, MANAGER, SIGN, ASSIST = P['admin'], P['manager'], P['signataire'], P['assistante']
REF = 'COUR-2026-0144'
OBJET = 'Convention de partenariat — %s' % demo.TIERS
PIECE = 'Convention de partenariat'
FICHIER = 'Convention_partenariat.pdf'
SIGNE = 'Convention_partenariat_signe.pdf'
DEMANDE = 'Signature — %s' % REF
ETAPES_SORT = ['Préparation', 'Contrôle', 'Validation', 'Signature', 'Émission']
ROLE = 'AITE Courrier / %s'
# workflow_circuits.xml, circuit 2 — (nom, description, rôles, SLA, initiale, finale)
CIRCUIT = [
    ('Préparation', 'Rédaction et mise en forme', ['Agent courrier', 'Assistant(e)'], 24, True, False),
    ('Contrôle', 'Vérification administrative et conformité', ['Assistant(e)'], 8, False, False),
    ('Validation', 'Validation par responsable de service', ['Manager'], 24, False, False),
    ('Signature', 'Visa formel et approbation finale', ['Signataire'], 24, False, False),
    ('Émission', 'Envoi destinataire et archivage', ['Agent courrier', 'Archiviste'], 4, False, True),
]
BOT = '#7A6FA8'
CRAYON = ('<svg viewBox="0 0 24 24" fill="#1C1620"><path d="M3 17.2V21h3.8L17.8 10l-3.8-3.8zM20.7 7.1a1 1 0 000-1.4l-2.4-2.4'
          'a1 1 0 00-1.4 0l-1.8 1.8 3.8 3.8z"/></svg>')
CRAYON_STAT = CRAYON.replace('#1C1620', '#5B4C93')
# une signature manuscrite stylisée (mode « Automatique » : le nom en écriture manuscrite)
SIGNATURE = ('<svg viewBox="0 0 300 90"><path d="M12 62C22 18 40 14 34 56S48 82 62 40C68 24 72 62 80 50C88 38 92 58 100 48'
             'M112 30C106 72 114 76 122 50C130 30 142 46 134 60C128 70 150 52 158 50C164 48 162 63 172 55C182 47 180 70 192 52'
             'C198 44 202 63 212 50C222 40 224 76 216 86C208 94 232 50 262 40M60 74C110 70 170 66 236 64" fill="none" '
             'stroke="#0B1B8F" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'


# ------------------------------------------------- l'administrateur --
def tags(roles):
    return c_html('<span class="t9-tags">%s</span>' % ''.join('<span class="t9-tag">%s</span>' % e(ROLE % r) for r in roles))


def ecran_admin():
    lignes = []
    for i, (n, d, r, s, ini, fin) in enumerate(CIRCUIT):
        sig = '<span class="t9-cc" id="t9-e%d-sig">%s%s</span>' % (
            i, case(False), '<span class="t9-on masque" id="t9-e%d-on">%s</span>' % (i, case(True)) if i == 2 else '')
        lignes.append({'id': 't9-e%d' % i, 'cellules': [
            c_html('<span class="t9-poignee">⋮⋮</span>'), n, d, tags(r), '', c_num(str(s)), c_html(case(ini)), c_html(case(fin)),
            c_html(sig), c_html('<span class="t9-corb">%s</span>' % ICONES['corbeille'])]})
    etapes = table([('', '10px'), ('Nom', '74px'), ('Description', '1fr'), ('Rôles autorisés', '262px'),
                    ('Utilisateurs autorisés', '74px'), ('SLA (heures)', '50px'), ('Étape initiale', '54px'),
                    ('Étape finale', '50px'), ('Signature requise', '66px'), ('', '12px')], lignes, identifiant='t9-tab')
    etapes = etapes.replace('<span class="ell">Signature requise</span>', '<span class="ell" id="t9-h-sig">Signature requise</span>', 1)
    corps = (grille2([champ('Nom', entree('t9-nom', '', 'Courrier sortant')), champ('Objet gouverné', entree('t9-obj', '', 'Courrier')),
                      champ('Type de courrier', entree('t9-typ', '', 'Courrier sortant'))], [champ('Actif', case(True))])
             + onglets(['Étapes', 'Transitions'], 0) + etapes)
    circ = vue('t9-circuit', panneau_fiche('Circuits de traitement', 'Courrier sortant', '2 / 7', sauver_id='t9-sauver')
               + '<div class="o-corps"><div class="o-gauche">%s</div></div>' % feuille(corps), initiale=True)
    # le journal d'audit, tel que l'administrateur le trouve après la signature
    lignes = [
        ('13/10/2026 15:41:37', MANAGER[0], 'Ajout pièce jointe', ('Information', 'gris'), PIECE, 'Système', 'v2 — %s (36 Ko)' % SIGNE),
        ('13/10/2026 15:41:37', 'OdooBot', 'Signature complétée', ('Succès', 'vert'), REF, 'Système',
         'Demande « %s » signée par %s. PDF signé versé en v2.' % (DEMANDE, SIGN[0])),
        ('13/10/2026 15:12:20', MANAGER[0], 'Demande de signature', ('Information', 'gris'), REF, 'Interface',
         'Signataire : %s — %s' % (SIGN[0], FICHIER)),
        ('13/10/2026 15:11:48', MANAGER[0], 'Action bloquée', ('Erreur', 'rouge'), REF, 'Interface',
         'Étape « Validation » : signature électronique manquante.'),
        ('13/10/2026 14:56:02', ASSIST[0], 'Valider', ('Succès', 'vert'), REF, 'Interface', "Vers l'étape « Validation »."),
        ('13/10/2026 14:31:15', P['agent'][0], 'Soumettre', ('Succès', 'vert'), REF, 'Interface', "Vers l'étape « Contrôle »."),
        ('13/10/2026 14:30:40', P['agent'][0], 'Ajout pièce jointe', ('Information', 'gris'), PIECE, 'Interface', 'v1 — %s (34 Ko)' % FICHIER),
        ('13/10/2026 14:29:58', P['agent'][0], 'Création courrier', ('Information', 'gris'), REF, 'Interface',
         'Lancement du circuit « Courrier sortant ».'),
        ('13/10/2026 11:04:46', P['archiviste'][0], 'Archiver', ('Succès', 'vert'), 'COUR-2026-0011', 'Interface', "Vers l'étape « Archivage »."),
        ('13/10/2026 10:31:07', P['archiviste'][0], 'Création document', ('Information', 'gris'), 'DOC-2026-00360', 'Interface',
         'Type : Procédure / instruction'),
        ('13/10/2026 10:29:41', MANAGER[0], 'Transmettre', ('Succès', 'vert'), 'COUR-2026-0014', 'Interface', "Vers l'étape « Traitement »."),
        ('13/10/2026 10:29:01', P['agent'][0], 'Création courrier', ('Information', 'gris'), 'COUR-2026-0141', 'Interface',
         'Lancement du circuit « Courrier entrant standard ».'),
    ]
    audit = vue('t9-audit', panneau_liste("Journal d'audit", '1-80 / 1 652', nouveau=False)
                + liste([('Date/heure', '118px'), ('Utilisateur', '92px'), ('Action', '124px'), ('Type', '78px'), ('Objet', '112px'),
                         ('Source', '62px'), ('Détails', '1fr')],
                        [{'id': 't9-a%d' % i, 'cellules': [d, c_html('<span class="ell">%s</span>' % e(u)), a, c_puce(t[0], t[1]), o, s, det]}
                         for i, (d, u, a, t, o, s, det) in enumerate(lignes)])
                + '<div class="t9-zone" id="t9-trois"%s></div>' % ZONE)
    return fenetre('Courrier', ['Tableau de bord', 'Courriers', 'Espace documentaire', 'Audit', 'Configuration'], [circ, audit],
                   ADMIN[1], ADMIN[2], ident='app-9a')


# ------------------------------------------------------------ le manager --
def ecran_manager():
    demander = ('<span class="bt orange" id="t9-dem"><span class="ic">%s</span>Demander la signature</span>' % CRAYON)
    stats = (bouton_stat('Documents ECM', '1')
             + '<span class="stat masque" id="t9-stat"><span class="ic">%s</span><span><b>Signatures</b><i>1</i></span></span>' % CRAYON_STAT)
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v">%s</div>' % REF
             + grille2([champ('Objet', v(OBJET)), champ('Contact expéditeur', '', aide=True), champ('Expéditeur', ''),
                        champ('E-mail expéditeur', '', aide=True), champ('Type', v('Courrier sortant', True)),
                        champ('Service destinataire', v('Direction générale', True))],
                       [champ('Statut', puce('En traitement', 'gris'), aide=True), champ('Priorité', v('Normale', True)),
                        champ('Confidentialité', v('Interne', True)), champ('Date de réception', v('13/10/2026')),
                        champ('Responsable', v(SIGN[0], True), 't9-resp')])
             + onglets(['Documents', 'Historique'], 0)
             + table([('Nom', '1fr'), ('Dossier', '70px'), ('Extension', '64px'), ('Nombre de versions', '108px'), ('État', '74px')],
                     [{'id': 't9-d1', 'cellules': [PIECE, '', 'pdf', c_html('<span class="num" id="t9-nv">1</span>'),
                                                   c_puce('Brouillon')]}], identifiant='t9-docs', ajouter=False))
    acts = activite('Courrier %s — étape « Validation »' % REF, MANAGER[0],
                    "Le courrier « %s » attend votre traitement à l'étape « Validation »." % OBJET, MANAGER[2], MANAGER[1],
                    masque=False)
    ch = chatter([message('OdooBot', BOT, 'Demande « %s » signée par %s. PDF signé versé en v2.' % (e(DEMANDE), e(SIGN[0])),
                          '15:41', 't9-msg-sig'),
                  message(MANAGER[0], MANAGER[2], 'Demande de signature envoyée à %s (document « %s »).' % (e(SIGN[0]), FICHIER),
                          '15:12', 't9-msg-dem'),
                  message(ASSIST[0], ASSIST[2], "Courrier arrivé à l'étape « Validation » — traitement attendu.", '14:56')],
                 activites=acts, identifiant='t9-chatter')
    fiche = vue('t9-fiche', panneau_fiche('Courriers', REF, '1 / 12', nouveau=False, boutons_stat=stats)
                + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                    bande([bouton('t9-traiter', 'Traiter', 'prim'), bouton('t9-rej', 'Rejeter', 'second'),
                           bouton('t9-com', 'Commenter', 'second'), bouton('t9-rep', 'Répondre', 'second', 'retour'), demander],
                          statusbar(ETAPES_SORT, 2, 't9-sb'), 't9-bande'), feuille(corps), ch), initiale=True)
    wiz = assistant('t9-as', 'Action sur le courrier',
                    champ('Action', v('Traiter (valider / retourner)')) + champ('Transition', entree('t9-trans'))
                    + champ('Commentaire', entree('t9-comm', "Commentaire (obligatoire pour le rejet ou les actions qui l'exigent)")),
                    [('t9-ok', 'Confirmer', 'prim'), ('t9-annuler', 'Annuler', 'second')], haut=170, largeur=720)
    err = assistant('t9-err', 'Opération invalide',
                    '<div class="t9-errtx" id="t9-errtx">Cette étape exige une signature électronique : aucune demande n\'a été '
                    'signée depuis l\'arrivée du courrier sur l\'étape. Utilisez « Demander la signature » puis attendez la '
                    'signature.</div>', [('t9-fermer', 'Fermer', 'prim')], haut=200, largeur=760)
    docm = assistant('t9-docm', 'Ouvrir : Documents',
                     '<div class="t9-dtitre">%s</div>' % PIECE
                     + grille2([champ('Courrier', v(REF, True))], [champ('Nombre de versions', v('2'))])
                     + onglets(['Versions'], 0)
                     + table([('Version', '54px'), ('Nom du fichier', '1fr'), ('Extension', '62px'), ('Taille (octets)', '88px'),
                              ('Téléversé par', '96px'), ('Date', '118px')],
                             [{'id': 't9-v2', 'cellules': ['v2', c_html('<span class="ell" id="t9-v2-nom">%s</span>' % SIGNE), 'pdf',
                                                          c_num('36 412'), MANAGER[0], '13/10/2026 15:41']},
                              {'id': 't9-v1', 'cellules': ['v1', FICHIER, 'pdf', c_num('34 876'), P['agent'][0], '13/10/2026 14:30']}],
                             identifiant='t9-vers', ajouter=False),
                     [('t9-docm-f', 'Fermer', 'prim')], haut=120, largeur=760)
    html = fenetre('Courrier', ['Tableau de bord', 'Courriers', 'Espace documentaire'], [fiche], MANAGER[1], MANAGER[2],
                   calques=wiz + err + docm, ident='app-9b')
    return html.replace('<div class="o-app muk" id="app-9b">', '<div class="o-app muk masque" id="app-9b">', 1)


# --------------------------------------------- la page de signature --
def ecran_signature():
    outils = ''.join('<i></i>' for _ in range(3))
    page = ('<div class="t9-page" id="t9-page"><div class="t9-ph1">%s</div>'
            '<div class="t9-pl">Entre AITE Démo et %s.</div>'
            '<div class="t9-pl b">Article 1 — Objet</div><div class="t9-pl">La présente convention fixe le cadre du partenariat.</div>'
            '<div class="t9-pl b">Article 2 — Durée</div><div class="t9-pl">Un an, renouvelable.</div>'
            '<div class="t9-pl">Fait à Douala, le 13/10/2026.</div>'
            '<div class="t9-zonesig" id="t9-zsig"><span class="t9-sig masque" id="t9-sig">%s</span></div></div>'
            % (PIECE, demo.TIERS, SIGNATURE))
    adopt = assistant('t9-adopt', 'Adopter votre signature',
                      '<div class="t9-al">Nom complet</div><div class="t9-ain">%s</div>'
                      '<div class="t9-cadre"><div class="t9-ogs"><span class="on">Automatique</span><span>Dessiner</span>'
                      '<span>Charger</span></div><div class="t9-trace" id="t9-trace">%s</div></div>'
                      '<div class="t9-legal">En cliquant sur Adopter &amp; Signer, j\'accepte que la signature ou les initiales '
                      'choisies seront une représentation valide et électronique de ma signature ou mes initiales manuscrites pour '
                      'tous les besoins quand celles-ci sont utilisées pour des documents, y compris des contrats juridiquement '
                      'contraignants.</div>' % (e(SIGN[0]), SIGNATURE),
                      [('t9-adopter', 'Adopter & Signer', 'prim'), ('t9-annuler2', 'Annuler', 'second')], haut=52, largeur=640)
    return ('<div class="o-app t9-signe masque" id="app-9c">'
            '<div class="t9-sh"><span class="t9-logo">AITE Démo</span>'
            '<span class="t9-info" id="t9-p-info">Please Review And Act On This Document</span></div>'
            '<div class="t9-tb"><span class="t9-ti">%s</span><span class="t9-pg">1</span><span class="t9-tz"></span>'
            '<span class="t9-ti d">%s</span></div>'
            '<div class="t9-fond"><div class="t9-start" id="t9-start">Click to start</div>%s</div>'
            '<div class="t9-pied masque" id="t9-pied"><span class="bt prim" id="t9-valider">Valider et envoyer le document</span></div>'
            '%s</div>' % (outils, outils, page, adopt))


CSS = """
#app-9a .t9-tags { display: flex; gap: 4px; overflow: hidden; }
#app-9a .t9-tag { display: inline-block; padding: 1px 7px; border-radius: 9px; background: #E9ECEF; color: #343A40; font-size: 10px;
  line-height: 15px; white-space: nowrap; }
#app-9a .t9-poignee { color: #ADB5BD; font-size: 9px; letter-spacing: -2px; }
#app-9a .t9-corb { color: #343A40; } #app-9a .t9-corb svg { width: 12px; height: 12px; display: block; }
#app-9a .t9-cc { position: relative; display: inline-flex; }
#app-9a .t9-on { position: absolute; left: 0; top: 0; }
#app-9a .o-feuille .entree { width: 92%; }
#app-9a .t9-zone { position: absolute; pointer-events: none; left: 0; right: 0; top: 84px; height: 124px; }
#app-9b .o-bande .bt { padding: 0 8px; font-size: 12px; }
#app-9b .o-bande .groupe-bt { gap: 3px; }
#app-9b .o-bande .sb { padding: 0 4px 0 13px; font-size: 11px; }
#app-9b .o-bande .sb:first-child { padding-left: 8px; }
#app-9b .bt.orange .ic svg { width: 11px; height: 11px; }
#app-9b .o-cp .stats { margin-left: 120px; }
#app-9b .stat .ic svg { width: 16px; height: 16px; }
#t9-msg-sig, #t9-msg-dem { height: 0; margin-bottom: 0; overflow: hidden; opacity: 0; visibility: hidden; }
#app-9b .t9-errtx { font-size: 13px; line-height: 1.55; }
#app-9b .t9-dtitre { font-size: 20px; margin-bottom: 8px; }
#t9-err .mt { font-size: 19px; border-bottom: 0; padding-bottom: 4px; }
#t9-err .mp { border-top: 0; padding-top: 4px; }
#app-9c { background: #fff; font-family: var(--odoo); }
#app-9c .t9-sh { height: 60px; display: flex; align-items: flex-start; padding: 8px 14px; position: relative; }
#app-9c .t9-logo { font-size: 20px; font-weight: 700; color: #5B4C93; }
#app-9c .t9-info { position: absolute; left: 0; right: 0; top: 4px; text-align: center; font-size: 10px; color: #333; }
#app-9c .t9-tb { height: 22px; background: #F9F9FA; border-bottom: 1px solid #DDD; display: flex; align-items: center; gap: 8px; padding: 0 10px; }
#app-9c .t9-ti { display: inline-flex; gap: 8px; } #app-9c .t9-ti i { width: 11px; height: 10px; border: 1.5px solid #666; border-radius: 2px; }
#app-9c .t9-ti.d { margin-left: auto; }
#app-9c .t9-pg { width: 32px; height: 15px; border: 1px solid #BBB; border-radius: 3px; font-size: 9px; text-align: right; padding-right: 4px; line-height: 14px; background: #fff; }
#app-9c .t9-tz { width: 90px; height: 15px; margin-left: 230px; background: #E4E4E8; border-radius: 2px; }
#app-9c .t9-fond { position: absolute; left: 0; right: 0; top: 83px; bottom: 0; background: #D4D4D7; overflow: hidden; }
#app-9c .t9-page { position: absolute; left: 338px; top: 10px; width: 424px; height: 600px; background: #fff; padding: 56px 46px;
  font-family: Arial, sans-serif; color: #111; }
#app-9c .t9-ph1 { font-size: 15px; font-weight: 700; margin-bottom: 18px; }
#app-9c .t9-pl { font-size: 10.5px; line-height: 1.5; margin-bottom: 4px; } #app-9c .t9-pl.b { margin-top: 10px; }
#app-9c .t9-zonesig { position: absolute; left: 280px; top: 528px; width: 94px; height: 36px; background: #FDB7B7; }
#app-9c .t9-sig { position: absolute; inset: 2px 4px; } #app-9c .t9-sig svg { width: 100%; height: 100%; display: block; }
#app-9c .t9-start { position: absolute; left: 0; top: 520px; height: 34px; line-height: 34px; padding: 0 8px 0 6px; background: #7A6BA8;
  color: #fff; font-size: 15px; text-transform: uppercase; }
#app-9c .t9-start::after { content: ''; position: absolute; right: -17px; top: 0; border-left: 17px solid #7A6BA8;
  border-top: 17px solid transparent; border-bottom: 17px solid transparent; }
#app-9c .t9-pied { position: absolute; left: 0; right: 0; bottom: 0; height: 44px; background: rgba(46,148,148,.6); display: flex;
  align-items: center; justify-content: center; }
#app-9c .t9-pied .bt.prim { background: #4E8AA6; }
#app-9c .t9-al { font-size: 12px; margin-bottom: 4px; }
#app-9c .t9-ain { border: 1px solid #9DB6C6; border-radius: 4px; padding: 5px 8px; font-size: 12px; margin-bottom: 10px; box-shadow: 0 0 0 2px #E2ECF2; }
#app-9c .t9-cadre { border: 1px solid #DEE2E6; border-radius: 4px; background: #F7F8F9; }
#app-9c .t9-ogs { display: flex; gap: 6px; padding: 7px 10px; border-bottom: 1px solid #DEE2E6; font-size: 12px; }
#app-9c .t9-ogs span { padding: 4px 8px; border-radius: 4px; background: #fff; }
#app-9c .t9-ogs span.on { background: #DCE8EF; border: 1px solid #5D8DA8; }
#app-9c .t9-trace { height: 128px; padding: 10px 70px; } #app-9c .t9-trace svg { width: 100%; height: 100%; display: block; }
#app-9c .t9-legal { font-size: 9.5px; line-height: 1.4; margin-top: 6px; color: #333; }
#app-9c .modale .mt { font-size: 15px; }
#app-9c .bt.prim { background: #5D8DA8; color: #fff; }
#app-9c .bt.second { background: #DEE2E6; color: #000; }
"""

TUTO = {
    'slug': 'tuto-09-signature-electronique',
    'titre_page': 'AITE Courrier — Tutoriel 09 : signature électronique',
    'titre': 'Signature électronique',
    'serie': dict(COURRIER, numero=9),
    'adresse': ADRESSE % 'courrier',
    'accroche': {
        'question': 'Ce courrier est-il *enfin* *signé ?*',
        'sous': "Un parapheur qui traîne, une signataire absente.",
        'personnage': (SIGN[0], 'Signataire', SIGN[2]),
        'chaos': [('doc', 'Convention à signer'), ('alerte', 'Parapheur en retard'), ('bulle', 'Tu peux passer signer ?'),
                  ('note', 'Signé ? À vérifier'), ('lettre', 'Envoi en attente'), ('dossier', 'Parapheur'),
                  ('bulle', 'Elle est en déplacement'), ('alerte', 'Relance n° 2')],
        'voix': "Une convention attend sa signature. La signataire est en déplacement, le parapheur traîne sur un bureau, "
                "et personne ne sait si le courrier peut partir.",
    },
    'revelation': {'voix': "Avec Aïte Courrier, la signature s'inscrit dans le circuit, et rien n'avance sans elle."},
    'apercu': {
        'kicker': 'AITE Courrier · Odoo 18', 'titre': 'Signer un courrier, *sans* parapheur',
        'pastilles': ['Signature requise par étape', 'Signature dans le navigateur', 'PDF signé versé au courrier'],
        'voix': "Une étape exige la signature, la signataire signe depuis un lien, et le P D F signé revient au courrier.",
    },
    'ecran': ecran_admin() + ecran_manager() + ecran_signature(), 'vue_initiale': 't9-circuit',
    'etapes': [
        {'titre': "Une étape qui exige la signature",
         'texte': "Configuration › Circuits de traitement : la case « Signature requise » sur l'étape voulue.",
         'voix': "Côté paramétrage, une case suffit. Dans le circuit du courrier sortant, l'administrateur coche Signature "
                 "requise sur l'étape Validation. Désormais, le courrier ne peut plus avancer sans signature.",
         'gestes': [curseur('#t9-e1', fx=0.3, d=0.6), zoom('#t9-e2-sig', s=1.5, fx=0.72, fy=0.55, d=0.9),
                    anneau('#t9-h-sig', d=1.4), clic('#t9-e2-sig'), montrer('#t9-e2-on', y=0, d=0.2),
                    bulle('#t9-e2-sig', 'Signature requise', cote='gauche', d=2.2), dezoom(d=0.7),
                    clic('#t9-sauver'), cacher('#t9-sauver', d=0.2)]},
        {'titre': 'Bloqué, puis demander la signature',
         'texte': "Sans signature, la transition est refusée ; « Demander la signature » envoie le PDF à la signataire.",
         'voix': "Paul, le manager, veut soumettre la convention au visa. Refus : l'étape exige une signature électronique, "
                 "et le serveur bloque la transition. Paul clique donc sur Demander la signature. La dernière version P D F "
                 "du courrier part chez Nicole, la responsable du courrier, et la demande s'inscrit dans le fil.",
         'gestes': [montrer('#app-9b', y=0, d=0.4), clic('#t9-traiter', decale=0.2), ouvrir('t9-as'),
                    clic('#t9-trans', fx=0.2, d=0.6), choisir('t9-trans', 'Soumettre visa'), clic('#t9-ok', d=0.6), ouvrir('t9-err'),
                    zoom('#t9-errtx', s=1.35, d=0.7),
                    bulle('#t9-errtx', 'Le serveur refuse', cote='dessous', fx=0.5, d=2.0), dezoom(d=0.5),
                    clic('#t9-fermer', d=0.6), fermer('t9-err'), clic('#t9-annuler', d=0.5), fermer('t9-as'),
                    clic('#t9-dem', d=0.6), animer('#t9-msg-dem', {'height': 0, 'autoAlpha': 0, 'marginBottom': 0},
                                                   {'height': 50, 'autoAlpha': 1, 'marginBottom': 10}, d=0.5),
                    montrer('#t9-stat', y=0, avec=True), anneau('#t9-msg-dem', d=1.4)]},
        {'titre': 'La signataire signe dans son navigateur',
         'texte': "Depuis le lien reçu par e-mail, sans ouvrir de session : la zone, « Adopter & Signer », puis valider.",
         'voix': "Nicole reçoit un e-mail : nouveau document à signer. Elle ouvre le lien dans son navigateur, sans même se "
                 "connecter. Un clic sur la zone de signature, en bas de la page, elle adopte sa signature, puis valide et "
                 "envoie le document.",
         'gestes': [texte('#pr-url', 'courrier.aite-demo.test/sign_oca/document/7/…'), montrer('#app-9c', y=0, d=0.4),
                    pause(0.3), bulle('#t9-p-info', 'Le lien reçu par e-mail', cote='dessous', d=2.0),
                    anneau('#t9-start', d=1.2), clic('#t9-zsig'), ouvrir('t9-adopt'), pause(0.4), anneau('#t9-trace', d=1.4),
                    clic('#t9-adopter'), fermer('t9-adopt'), montrer('#t9-sig', y=0, d=0.3), montrer('#t9-pied', y=0, d=0.3),
                    zoom('#t9-zsig', s=1.5, fx=0.6, fy=0.5, d=0.7),
                    bulle('#t9-zsig', 'Signature apposée', cote='gauche', d=1.8), dezoom(d=0.6),
                    clic('#t9-valider'), cacher('#t9-pied', d=0.3)]},
        {'titre': 'Le PDF signé revient au courrier',
         'texte': "Nouvelle version « _signe.pdf », bouton « Signatures », et les traces au journal d'audit.",
         'voix': "Aussitôt, le P D F signé revient dans le courrier, en nouvelle version : l'original reste consultable. Le "
                 "bouton Signatures regroupe les demandes, et le journal d'audit garde la trace de tout : l'action bloquée, "
                 "la demande, la signature complétée.",
         'gestes': [texte('#pr-url', ADRESSE % 'courrier'), cacher('#app-9c', d=0.3),
                    animer('#t9-msg-sig', {'height': 0, 'autoAlpha': 0, 'marginBottom': 0},
                           {'height': 50, 'autoAlpha': 1, 'marginBottom': 10}, d=0.5),
                    cacher('#t9-dem', d=0.3, avec=True), texte('#t9-nv', '2', avec=True), anneau('#t9-msg-sig', d=1.2),
                    clic('#t9-d1', fx=0.3), ouvrir('t9-docm'), zoom('#t9-vers', s=1.35, d=0.7),
                    bulle('#t9-v2-nom', 'v2 : le PDF signé', cote='dessous', fx=0.3, d=1.8), dezoom(d=0.5),
                    clic('#t9-docm-f'), fermer('t9-docm'), anneau('#t9-stat', d=1.0),
                    cacher('#app-9b', d=0.3), aller('t9-audit'),
                    zoom('#t9-trois', s=1.18, fx=0.5, fy=0.32, d=0.7),
                    bulle('#t9-a3 .puce', 'Le refus', cote='droite', d=1.4),
                    bulle('#t9-a2 .puce', 'La demande', cote='droite', d=1.4),
                    bulle('#t9-a1 .puce', 'La signature', cote='droite', d=1.4), dezoom(d=0.6)]},
    ],
    'benefices': {
        'titre': 'La signature, *dans* le circuit.',
        'voix': "Une signature électronique simple, apposée sur le P D F : idéale pour les visas et les validations "
                "internes, et tracée de bout en bout.",
        'cartes': [('cadenas', 'Une case', 'Rien ne passe sans elle', "Aucune transition en avant tant que l'étape n'est pas signée."),
                   ('equipe', 'Un lien', 'Signer de partout', "La signataire signe dans son navigateur, depuis l'e-mail reçu."),
                   ('trace', 'PDF signé', 'Versé au courrier', "Nouvelle version de la pièce ; l'original reste, et l'audit trace tout.")],
    },
    'cta': cta('courrier', 'Vos signatures, *sans* *parapheur.*', "Aïte Courrier : vos signatures, sans parapheur."),
    'youtube': youtube('COMMENT FAIRE SIGNER UN COURRIER ÉLECTRONIQUEMENT AVEC AITE COURRIER (ODOO 18 COMMUNITY)',
                       "Une étape « Signature requise » dans le circuit, une demande envoyée par e-mail, une signature dans le "
                       "navigateur sans ouvrir de session, et le PDF signé versé en nouvelle version du courrier, avec la trace "
                       "au journal d'audit. Signature électronique simple, adossée au module OCA sign_oca. Tutoriel AITE "
                       "Courrier pour Odoo 18.",
                       ['AITE Courrier', 'signature électronique', 'sign_oca', 'OCA', 'Odoo Community', 'parapheur électronique']),
    'css': CSS,
}
