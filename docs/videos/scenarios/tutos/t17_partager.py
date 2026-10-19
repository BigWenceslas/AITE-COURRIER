# -*- coding: utf-8 -*-
"""Tutoriel 17 — Partager en toute sécurité.

Sources :
- aite_ecm_share/models/aite_ecm_share.py : ``action_create_share`` (bouton
  « Partager » : lien créé aussitôt, libellé « Partage — <référence> »,
  expiration à J+7, fiche ouverte dans une fenêtre) ; champs « Libellé »,
  « Document », « Destinataire (info) », « Lien », « Expire le »,
  « Téléchargements max. » (0 = illimité), « Consultation seule »,
  « Filigrane » (coché par défaut, activé d'office à la création pour les
  documents Confidentiel / Secret), « Texte du filigrane » (« Diffusion contrôlée — AITE
  ECM » par défaut), « Accès », « Dernier accès », « Valide » ; filigrane
  incrusté dans le PDF servi : texte, date du jour, 8 premiers caractères du
  jeton ; audit « Création d'un lien de partage » (« Lien xxxxxxxx — expire
  … ») et « Accès par lien de partage » (« Lien xxxxxxxx — accès n°N »,
  source Système) ; ``action_deactivate`` ;
- views/aite_ecm_share_views.xml : fiche « Lien de partage » (« Désactiver »,
  ruban « Désactivé », groupe « Suivi », lien copiable), liste (colonnes),
  menu Documents › « Partages externes », bouton « Partager » du document
  (invisible sans version), bouton « Partages » ;
- controllers/share.py et views/aite_ecm_share_templates.xml : page publique
  sans connexion (titre, « Référence … · fichier (N Ko) », « Lien valable
  jusqu'au … », « Accès restants : N. », « Télécharger le document » ou
  « Consulter le document », « AITE ECM — diffusion contrôlée. ») ; page
  « Lien indisponible. Ce lien de partage a expiré, a atteint son quota
  d'accès ou a été désactivé. » ; accès compté au téléchargement du fichier ;
- aite_ecm_document/views/aite_ecm_menus.xml (menu Documents),
  aite_ecm_document/views/aite_ecm_document_views.xml (fiche du document) ;
- aite_courrier_base/views/aite_courrier_audit_log_views.xml et menus
  (Courrier › Audit › « Journal d'audit », colonnes « Date/heure »,
  « Utilisateur », « Action », « Type », « Objet », « Source », « Détails »,
  réservé au rôle Audit) ;
- web (Odoo 18) : bulle « Copié » du champ copiable.
Le module n'envoie aucun e-mail : le lien se copie et se transmet.
Modèle visuel : base demo18 (MuK) — partage créé sur un document de test,
page publique ouverte sans session, journal d'audit vu par le rôle Audit.
"""

import demo
from ecrans import (ICONES, assistant, bande, bouton, bouton_stat, c_html, c_num, case, champ, e, entree, fenetre, feuille,
                    grille2, liste, onglets, panneau_fiche, panneau_liste, puce, sec_titre, statusbar, table, v, vue)
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import anneau, cacher, classe, clic, curseur, fermer, montrer, ouvrir, pause, saisir, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
MANAGER, AUDIT = P['manager'], P['audit']
MENUS = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse', 'Configuration']
REF = 'DOC-2026-00344'
TITRE = 'Contrat de partenariat — %s' % demo.TIERS
FICHIER = 'Contrat_partenariat_Horizon.pdf'
JETON = 'UXM0cocIvy5YvvYULGRepP3pK7dQa2Wn'
LIEN = 'https://courrier.aite-demo.test/ecm/share/' + JETON
EXPIRE = '20/10/2026 10:42:15'
LIBELLE = 'Partage — %s' % REF
FILIGRANE = 'Diffusion contrôlée — AITE ECM'
COPIER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="8" y="8" width="12" height="12" rx="2"/>'
          '<path d="M16 8V5a1 1 0 00-1-1H5a1 1 0 00-1 1v10a1 1 0 001 1h3"/></svg>')
PARTAGE = ('<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
           '<path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" stroke="currentColor" stroke-width="2"/></svg>')


# ------------------------------------------------------------ le document --
def fiche_document():
    bd = bande([bouton('t17-fin', 'Finaliser', 'prim'), bouton('t17-res', 'Réserver', 'second', 'cadenas'),
                bouton('t17-prev', 'Prévisualiser', 'second', 'oeil'), bouton('t17-corb', 'Corbeille', 'second', 'corbeille'),
                '<span class="bt second" id="t17-partager"><span class="ic">%s</span>Partager</span>' % PARTAGE],
               statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 't17-sb'), 't17-b')
    corps = ('<div class="ref-l">Référence</div><div class="ref-v moyen">%s</div><div class="titre-doc">%s</div>' % (REF, e(TITRE))
             + grille2([champ('Type', v('Contrat')), champ('Dossier de classement', v('Juridique et contrats / Contrats fournisseurs')),
                        champ('Étiquettes', ''), champ('Confidentialité', v('Confidentiel', identifiant='t17-conf'), 't17-conf-l')],
                       [champ('Propriétaire', v(MANAGER[0])), champ('Fichier', v(FICHIER))])
             + sec_titre('Métadonnées')
             + grille2([champ('Parties', v('AITE Démo — %s' % demo.TIERS)), champ('Objet du contrat', v('Partenariat commercial')),
                        champ("Date d'effet", v('01/11/2026'))],
                       [champ('Montant', v('0,00')), champ('Devise', v('FCFA')), champ('Tacite reconduction', case(False))])
             + onglets(['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Description'])
             + table([('Version', '60px'), ('Nom du fichier', '1fr'), ('Commentaire de version', '1fr'), ('Taille (octets)', '100px'),
                      ('Téléversé par', '120px'), ('Date', '130px')],
                     [{'id': 't17-v1', 'cellules': ['v1', FICHIER, 'Version pour signature', c_num('217 088'), MANAGER[0],
                                                   '12/10/2026 16:05']}], ajouter=False))
    stats = (bouton_stat('Sceaux', '1', 'sceau') + '<span class="masque" id="t17-stat-p">%s</span>'
             % bouton_stat('Partages', '1', 'document'))
    return vue('t17-doc', panneau_fiche('Documents', TITRE, '5 / 257', boutons_stat=stats)
               + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (bd, feuille(corps)), initiale=True)


def champs_partage(p, destinataire, maxi, acces, dernier, valide, saisie=False):
    lien = ('<span class="t17-lien" id="%s-lien"><span class="ell">%s</span><span class="t17-cp" id="%s-cp">%s</span>'
            '<span class="t17-copie masque" id="%s-copie">Copié</span></span>' % (p, e(LIEN), p, COPIER, p))
    gauche = [champ('Libellé', v(LIBELLE)), champ('Document', v(TITRE)),
              champ('Destinataire (info)', entree(p + '-dest') if saisie else v(destinataire), p + '-dest-l'),
              champ('Lien', lien, p + '-lien-l')]
    droite = [champ('Expire le', v(EXPIRE), p + '-exp'),
              champ('Téléchargements max.', entree(p + '-max', '', '0') if saisie else v(maxi), p + '-max-l', aide=True),
              champ('Consultation seule', case(False), p + '-vo', aide=True),
              champ('Filigrane', case(True), p + '-fil', aide=True), champ('Texte du filigrane', v(FILIGRANE), p + '-txt')]
    suivi = (sec_titre('Suivi') + '<div class="t17-suivi" id="%s-suivi">%s%s%s</div>'
             % (p, champ('Accès', v(acces)), champ('Dernier accès', v(dernier)),
                champ('Valide', '<span id="%s-valide">%s</span>' % (p, case(valide)))))
    return grille2(gauche, droite) + suivi


def dialogue_partage():
    corps = ('<div class="t17-dh">%s</div>' % bouton('t17d-desact', 'Désactiver', 'rouge')
             + champs_partage('t17d', '', '0', '0', '', True, saisie=True))
    return assistant('t17-dlg', 'Odoo', corps, [('t17d-enr', 'Enregistrer', 'prim'), ('t17d-ign', 'Ignorer', 'second')],
                     haut=60, largeur=860)


# -------------------------------------------------- les partages externes --
AUTRES = [('Partage — DOC-2026-00352', "Relevé d'identité bancaire — Delta Équipements", 'contact@delta-equipements.test',
           '25/10/2026 09:18:40', '2', '5', False, True, True),
          ('Partage — DOC-2026-00320', 'Procès-verbal du conseil — septembre', 'Commissaire aux comptes', '17/10/2026 15:02:11',
           '1', '3', True, True, True),
          ('Partage — DOC-2026-00336', 'Plan de localisation — Groupe Horizon Services', demo.TIERS_COURRIEL, '09/10/2026 11:30:00',
           '0', '0', False, True, False),
          ('Partage — DOC-2026-00290', 'Cahier des charges — logiciel de paie', 'Éditeurs consultés', '30/10/2026 08:45:27', '4', '10',
           False, False, True),
          ('Partage — DOC-2026-00231', "Attestation d'assurance — locaux", 'contact@delta-equipements.test', '05/10/2026 17:20:03', '3', '3',
           False, True, False)]


def liste_partages():
    cols = [('Libellé', '170px'), ('Document', '1fr'), ('Destinataire (info)', '190px'), ('Expire le', '128px'), ('Accès', '44px'),
            ('Téléchar…', '62px'), ('Consult…', '54px'), ('Filig…', '40px'), ('Vali…', '36px')]
    lignes = [{'id': 't17-l0', 'cellules': [LIBELLE, TITRE, demo.TIERS_COURRIEL, EXPIRE,
                                            c_html('<span class="num" id="t17-l0-acc">1</span>'), c_num('3'), c_html(case(False)),
                                            c_html(case(True)), c_html('<span id="t17-l0-val">%s</span>' % case(True))]}]
    for i, (lib, doc, dest, exp, acc, mx, vo, fil, val) in enumerate(AUTRES, 1):
        lignes.append({'id': 't17-l%d' % i, 'classe': '' if val else 'gris',
                       'cellules': [lib, doc, dest, exp, c_num(acc), c_num(mx), c_html(case(vo)), c_html(case(fil)), c_html(case(val))]})
    return vue('t17-liste', panneau_liste('Partages externes', '1-6 / 6', ident='t17p') + liste(cols, lignes))


def fiche_partage():
    corps = champs_partage('t17f', demo.TIERS_COURRIEL, '3', '1', '13/10/2026 11:05:12', True)
    ruban = '<span class="ruban rouge masque" id="t17-ruban"><b>DÉSACTIVÉ</b></span>'
    bd = bande([bouton('t17-desact', 'Désactiver', 'rouge')], '', 't17-pb', [])
    return vue('t17-part', panneau_fiche('Partages externes', LIBELLE, '1 / 6')
               + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>'
               % (bd, feuille(corps).replace('<div class="o-feuille">', '<div class="o-feuille">' + ruban, 1)))


def menu_documents():
    return ('<div class="t17-dd masque" id="t17-dd" data-layout-allow-overlap data-layout-allow-occlusion>%s</div>'
            % ''.join('<div class="it" id="t17-dd%d">%s</div>' % (i, e(n)) for i, n in enumerate(
                ['Explorateur', 'Tous les documents', 'Mes documents', 'Partages externes', 'Corbeille'])))


def ecran_manager():
    html = fenetre('ECM', MENUS, [fiche_document(), liste_partages(), fiche_partage()], MANAGER[1], MANAGER[2],
                   calques=dialogue_partage(), ident='app-17a')
    return html.replace('<span class="menu" id="app-17a-m0">Documents</span>',
                        '<span class="menu t17-menu" id="app-17a-m0">Documents%s</span>' % menu_documents(), 1)


# ------------------------------------------------------- le destinataire --
def page_publique():
    carte = ('<div class="pub-carte" id="t17-carte"><div class="pub-t">%s</div>'
             '<div class="pub-r">Référence %s · %s (212 Ko)</div>'
             '<div class="pub-s"><span id="t17-restant">Lien valable jusqu\'au %s. Accès restants : 3.</span></div>'
             '<span class="pub-bt" id="t17-tele">Télécharger le document</span></div>' % (e(TITRE), REF, FICHIER, EXPIRE))
    lignes = ''.join('<i class="pdf-l%s"></i>' % (' c' if k % 4 == 3 else '') for k in range(16))
    pdf = ('<div class="pub-pdf masque" id="t17-pdf"><div class="pdf-page" id="t17-page"><div class="pdf-h">CONTRAT DE PARTENARIAT</div>'
           '%s<i class="pdf-ancre" id="t17-ancre"></i><div class="pdf-fil" id="t17-fil">%s · 13/10/2026 · %s<span>%s · 13/10/2026 · %s</span></div></div></div>'
           % (lignes, e(FILIGRANE), JETON[:8], e(FILIGRANE), JETON[:8]))
    invalide = ('<div class="pub-alerte masque" id="t17-indispo"><b>Lien indisponible.</b> Ce lien de partage a expiré, a atteint son '
                'quota d\'accès ou a été désactivé.</div>')
    return ('<div class="o-app t17-pub masque" id="app-17p"><div class="pub-cont"><div id="t17-ok">%s</div>%s'
            '<p class="pub-pied">AITE ECM — diffusion contrôlée.</p></div>%s</div>' % (carte, invalide, pdf))


# ------------------------------------------------------------- l'audit --
JOURNAL = [('13/10/2026 11:05:12', 'Public user', 'Accès par lien de partage', REF, 'Système', 'Lien %s — accès n°1' % JETON[:8]),
           ('13/10/2026 10:42:15', MANAGER[0], "Création d'un lien de partage", REF, 'Interface',
            'Lien %s — expire 2026-10-20 09:42:15' % JETON[:8]),
           ('13/10/2026 10:31:40', P['assistante'][0], 'Ajout de version', 'DOC-2026-00341', 'WebDAV',
            'v3 — Contrat_maintenance_climatisation.docx (48 Ko) — sha256 5ccc0955730f…'),
           ('13/10/2026 10:12:08', P['archiviste'][0], 'Création document', 'DOC-2026-00360', 'Interface', 'Type : Procédure / instruction'),
           ('13/10/2026 09:58:51', P['agent'][0], 'Ajout de version', 'DOC-2026-00359', 'Interface',
            'v1 — Procedure_recette.pdf (52 Ko) — sha256 7b36600b8b85…'),
           ('13/10/2026 09:41:27', P['compta'][0], 'Création du dossier', 'DOS-2026-0041', 'Interface', 'Agrément fournisseur')]


def ecran_audit():
    cols = [('Date/heure', '128px'), ('Utilisateur', '110px'), ('Action', '170px'), ('Type', '84px'), ('Objet', '116px'),
            ('Source', '76px'), ('Détails', '1fr')]
    lignes = [{'id': 't17-j%d' % i, 'cellules': [d, u, c_html('<span class="ell" id="t17-j%d-a">%s</span>' % (i, e(a))),
                                                c_html('<span>%s</span>' % puce('Information', 'gris')), o, s,
                                                c_html('<span class="ell" id="t17-j%d-d">%s</span>' % (i, e(det)))]}
              for i, (d, u, a, o, s, det) in enumerate(JOURNAL)]
    jr = vue('t17-journal', panneau_liste("Journal d'audit", '1-80 / 1 674', nouveau=False) + liste(cols, lignes), initiale=True)
    html = fenetre('Courrier', ['Tableau de bord', 'Courriers', 'Espace documentaire', 'Audit'], [jr], AUDIT[1], AUDIT[2],
                   ident='app-17c')
    return html.replace('class="o-app muk" id="app-17c"', 'class="o-app muk masque" id="app-17c"', 1)


CSS = """
#app-17p, #app-17c { z-index: 5; }
#app-17a .t17-menu { position: relative; }
#t17-dd { position: absolute; left: -10px; top: 29px; z-index: 30; width: 170px; padding: 6px 0; background: #fff; color: #212529;
  border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 18px rgba(0,0,0,.16); }
#t17-dd .it { padding: 5px 14px; font-size: 12px; white-space: nowrap; } #t17-dd .it.survol { background: #EEF3F6; }
#app-17a .bt .ic svg { width: 12px; height: 12px; display: block; }
#app-17a .t17-dh { margin-bottom: 10px; }
#app-17a .t17-lien { position: relative; display: flex; align-items: center; gap: 6px; height: 24px; padding: 0 6px; border: 1px solid #DEE2E6;
  border-radius: 4px; font-size: 11.5px; max-width: 290px; }
#app-17a .t17-lien .ell { min-width: 0; }
#app-17a .t17-cp { flex: none; color: #343A40; } #app-17a .t17-cp svg { width: 13px; height: 13px; display: block; }
#app-17a .t17-copie { position: absolute; right: -14px; top: -30px; padding: 3px 9px; border-radius: 4px; background: #212529; color: #fff;
  font-size: 11px; }
#app-17a .t17-suivi .champ { grid-template-columns: 110px 1fr; }
#t17-dlg .champ, #t17-part .champ { grid-template-columns: 140px 1fr; min-height: 30px; }
#t17-dlg .entree { width: 100%; }
#app-17a .o-liste .ligne.gris .ell, #app-17a .o-liste .ligne.gris .num { color: #ADB5BD; }
#app-17p { background: #fff; font-family: var(--odoo); color: #212529; }
#app-17p .pub-cont { position: absolute; left: 50%; top: 34px; width: 560px; margin-left: -280px; }
#app-17p .pub-carte { border: 1px solid #DEE2E6; border-radius: 6px; padding: 16px 16px 18px; }
#app-17p .pub-t { font-size: 19px; margin-bottom: 8px; }
#app-17p .pub-r { font-size: 12.5px; color: #6C757D; margin-bottom: 4px; }
#app-17p .pub-s { font-size: 11px; color: #6C757D; margin-bottom: 14px; }
#app-17p .pub-bt { display: inline-block; padding: 7px 12px; border-radius: 5px; background: #243742; color: #fff; font-size: 12.5px; }
#app-17p .pub-pied { margin-top: 22px; font-size: 11px; color: #6C757D; }
#app-17p .pub-alerte { padding: 13px 16px; border-radius: 5px; background: #FFF3CD; color: #664D03; border: 1px solid #FFE69C;
  font-size: 13px; line-height: 1.45; }
#app-17p .pub-pdf { position: absolute; inset: 0; background: #525659; display: flex; justify-content: center; padding-top: 22px; }
#app-17p .pdf-page { position: relative; width: 470px; height: 640px; background: #fff; padding: 48px 46px; overflow: hidden;
  box-shadow: 0 4px 14px rgba(0,0,0,.35); display: flex; flex-direction: column; gap: 12px; }
#app-17p .pdf-h { font-size: 15px; font-weight: 700; letter-spacing: .06em; margin-bottom: 10px; color: #212529; }
#app-17p .pdf-l { display: block; height: 4px; background: #D5D9DE; border-radius: 2px; } #app-17p .pdf-l.c { width: 64%; }
#app-17p .pdf-fil { position: absolute; left: 50%; top: 50%; width: 640px; margin-left: -320px; transform: rotate(-35deg);
  text-align: center; color: rgba(115,51,102,.30); font-size: 15px; font-weight: 700; white-space: nowrap; }
#app-17p .pdf-ancre { position: absolute; left: 50%; top: 66%; width: 2px; height: 2px; }
#app-17p .pdf-fil span { display: block; margin-top: 8px; font-size: 8px; font-weight: 400; }
#app-17c .o-liste .ligne { font-size: 11.5px; }
"""

TUTO = {
    'slug': 'tuto-17-partager-en-toute-securite',
    'titre_page': 'AITE ECM — Tutoriel 17 : partager en toute sécurité',
    'titre': 'Partager en toute sécurité',
    'serie': dict(ECM, numero=17),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Ce document, *qui* l\'a *téléchargé ?*',
        'sous': "Pièces jointes transférées sans fin, liens publics qui n'expirent jamais : un contrat confidentiel vous échappe vite.",
        'personnage': (MANAGER[0], 'Manager', MANAGER[2]),
        'chaos': [('lettre', 'TR: TR: contrat.pdf'), ('alerte', 'Lien public sans fin'), ('bulle', 'Tu peux me le renvoyer ?'),
                  ('note', 'Expire : jamais'), ('doc', 'contrat_v3_final.pdf'), ('bulle', "Qui l'a ouvert ?"),
                  ('dossier', 'Boîte « Envoyés »'), ('alerte', 'Copie non tracée')],
        'voix': "Un contrat confidentiel part en pièce jointe. Il est transféré, retransféré, et plus personne ne sait "
                "qui l'a ouvert, ni jusqu'à quand.",
    },
    'revelation': {'voix': "Avec Aïte E C M, vous partagez un lien, et vous gardez la main."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Partager, *sans* perdre le *contrôle*',
        'pastilles': ['Lien qui expire', 'Filigrane', 'Chaque accès tracé'],
        'voix': "Un lien qui expire, un nombre de téléchargements limité, un filigrane sur le document, et chaque accès "
                "tracé. Voyons comment.",
    },
    'ecran': ecran_manager() + page_publique() + ecran_audit(), 'vue_initiale': 't17-doc',
    'css': CSS,
    'etapes': [
        {'titre': 'Partager, en un clic',
         'texte': "Partager crée aussitôt un lien valable 7 jours ; filigrane d'office pour un document confidentiel.",
         'voix': "Paul, le manager, doit transmettre un contrat confidentiel à son partenaire. Un clic sur Partager crée "
                 "aussitôt le lien, valable sept jours par défaut. Le document est confidentiel : le filigrane est "
                 "activé d'office.",
         'gestes': [anneau('#t17-conf-l', d=1.4, decale=0.3), clic('#t17-partager'), ouvrir('t17-dlg'), pause(0.3),
                    zoom('#t17d-exp', s=1.5, fx=0.55, fy=0.35, d=0.8), anneau('#t17d-exp', d=1.2),
                    bulle('#t17d-exp', 'J+7 par défaut', cote='droite', fx=0.74, d=2.2),
                    pause(0.6), anneau('#t17d-fil', d=1.2), bulle('#t17d-fil', "Activé d'office", cote='droite', fx=0.62, d=2.2),
                    dezoom(d=0.6)]},
        {'titre': 'Vos règles, puis le lien',
         'texte': "Destinataire pour mémoire, téléchargements limités ; le lien se copie et se transmet, sans e-mail.",
         'voix': "Il note le destinataire, pour mémoire, et limite le lien à trois téléchargements. En consultation "
                 "seule, le P D F s'afficherait dans le navigateur, sans téléchargement. Aïte n'envoie aucun e-mail : Paul copie "
                 "le lien, et le transmet lui-même.",
         'gestes': [clic('#t17d-dest', fx=0.2), saisir('t17d-dest', demo.TIERS_COURRIEL, d=1.2),
                    clic('#t17d-max', fx=0.2), texte('#t17d-max-val', '3', avec=True, decale=0.3),
                    anneau('#t17d-vo', d=1.4), bulle('#t17d-vo', 'Sans téléchargement', cote='droite', fx=0.62, d=2.0),
                    clic('#t17d-cp'), montrer('#t17d-copie', y=4, d=0.2), bulle('#t17d-lien', 'À transmettre soi-même', cote='dessous', d=2.2),
                    cacher('#t17d-copie', d=0.2), clic('#t17d-enr'), fermer('t17-dlg'), montrer('#t17-stat-p', y=0, d=0.3),
                    anneau('#t17-stat-p', d=1.2)]},
        {'titre': 'Ce que voit le destinataire',
         'texte': "Sans compte : le document, l'expiration, les accès restants ; le PDF téléchargé porte un filigrane.",
         'voix': "Le partenaire ouvre le lien, sans compte ni mot de passe : il voit le titre, la référence, la date "
                 "d'expiration et les accès restants. Le P D F téléchargé porte en filigrane le texte choisi, la date "
                 "du jour, et le début du jeton du lien.",
         'gestes': [texte('#pr-url', 'courrier.aite-demo.test/ecm/share/' + JETON), montrer('#app-17p', y=0, d=0.4, avec=True),
                    curseur('#t17-tele'), zoom('#t17-carte', s=1.45, fx=0.5, fy=0.4, d=0.8),
                    anneau('#t17-restant', d=1.2), bulle('#t17-restant', 'Expiration et quota', cote='dessous', fx=0.85, d=2.2),
                    dezoom(d=0.6), clic('#t17-tele'), montrer('#t17-pdf', y=0, d=0.4), pause(0.3),
                    zoom('#t17-fil', s=1.5, fx=0.5, fy=0.5, d=0.8),
                    bulle('#t17-ancre', 'Texte, date et jeton', cote='dessous', d=2.2), dezoom(d=0.6)]},
        {'titre': 'Suivre, tracer, désactiver',
         'texte': "Partages externes : accès comptés, journal d'audit ; Désactiver coupe le lien aussitôt.",
         'voix': "Dans Documents, Partages externes, Paul suit chaque lien : ici, un accès sur trois, avec la date du "
                 "dernier accès. Chaque téléchargement est aussi inscrit au journal d'audit, consulté par l'audit "
                 "interne. Et un clic sur Désactiver suffit : le lien ne mène plus nulle part.",
         'gestes': [cacher('#app-17p', d=0.35), texte('#pr-url', ADRESSE % 'ecm', avec=True),
                    clic('#app-17a-m0', d=0.5), montrer('#t17-dd', y=-6, d=0.2), clic('#t17-dd3', fx=0.4, d=0.4),
                    cacher('#t17-dd', d=0.15), aller('t17-liste'),
                    bulle('#t17-l0-acc', '1 accès sur 3', cote='dessous', d=2.0), pause(1.8),
                    texte('#pr-url', ADRESSE % 'courrier'), montrer('#app-17c', y=0, d=0.4, avec=True), anneau('#t17-j0-a', d=1.6),
                    bulle('#t17-j0-d', 'Accès n°1, par le lien', cote='dessous', fx=0.3, d=2.2, avec=True),
                    cacher('#app-17c', d=0.35), texte('#pr-url', ADRESSE % 'ecm', avec=True), clic('#t17-l0', fx=0.2), aller('t17-part'),
                    clic('#t17-desact'), montrer('#t17-ruban', y=0, d=0.3), cacher('#t17-desact', d=0.2, avec=True),
                    classe('#t17f-valide .case', retirer=['on'], avec=True),
                    texte('#pr-url', 'courrier.aite-demo.test/ecm/share/' + JETON), montrer('#app-17p', y=0, d=0.4, avec=True),
                    cacher('#t17-pdf', d=0.01, avec=True), cacher('#t17-ok', d=0.01, avec=True), montrer('#t17-indispo', y=0, d=0.3),
                    anneau('#t17-indispo', d=1.4)]},
    ],
    'benefices': {
        'titre': 'Partager, et *garder* la *main.*',
        'voix': "Des liens qui expirent, des téléchargements comptés, un filigrane qui suit le document, et une "
                "désactivation en un clic.",
        'cartes': [('temps', 'J+7', 'Un lien qui expire', "Sept jours par défaut, et un quota de téléchargements au choix."),
                   ('bouclier', 'Filigrane', 'Le document marqué', "Texte, date et jeton incrustés dans le PDF servi."),
                   ('trace', 'Accès n°1', 'Chaque accès tracé', "Compté sur le lien, inscrit au journal d'audit.")],
    },
    'cta': cta('ecm', 'Partager, *sans* rien *lâcher.*', "Aïte E C M : partager, sans rien lâcher."),
    'youtube': youtube('COMMENT PARTAGER UN DOCUMENT EN TOUTE SÉCURITÉ AVEC AITE ECM (ODOO 18)',
                       "Un lien de partage qui expire après sept jours par défaut, un nombre de téléchargements limité, un "
                       "filigrane daté sur le PDF, chaque accès compté et inscrit au journal d'audit, et une désactivation en un "
                       "clic. Tutoriel AITE ECM pour Odoo 18.",
                       ['AITE ECM', 'partage sécurisé', 'lien de partage', 'filigrane PDF', 'GED Odoo', "journal d'audit"]),
}
