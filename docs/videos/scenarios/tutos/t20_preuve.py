# -*- coding: utf-8 -*-
"""Tutoriel 20 — La valeur probante.

Sources (addons/aite_ecm_sae) :
- __manifest__.py : « dans l'esprit de NF Z42-013 / ISO 14641 » (formulation
  reprise telle quelle ; aucune certification n'est revendiquée) ;
  bordereau « manifest.xml » (structure SEDA 2.1) ;
- models/aite_ecm_seal.py : événements « Dépôt d'une version »,
  « Finalisation », « Archivage », « Vérification d'intégrité »,
  « Élimination », « Export d'archives » ; champs « Référence »,
  « Document », « Événement », « Version (libellé) », « Par »,
  « Horodatage », « Source » (« Interne (clé du serveur) »), « Empreinte du
  fichier », « Empreinte du sceau précédent », « Empreinte du sceau »,
  « Détail », « Données scellées », « Jeton d'horodatage » ; empreinte
  SHA-256 du contenu, de l'événement et du sceau précédent ; journal
  inaltérable (write / unlink refusés) ;
- models/aite_ecm_document.py : « Intégrité » (« Non vérifiée »,
  « Intègre », « Anomalie »), « Vérifiée le », « Dernier sceau »,
  « Copie de préservation (PDF/A) » ; action_verify_integrity (sceau
  « Vérification : intègre », message « Vérification d'intégrité : document
  intègre, chaîne de preuve cohérente. ») ; action_proof_report (rapport
  « Attestation d'intégrité », report/proof_report.xml) ; action_create_pdfa
  (« La conversion PDF/A a échoué : LibreOffice (soffice) doit être installé
  sur le serveur. ») ;
- views/aite_ecm_document_views.xml : onglet « Preuve », boutons
  « Vérifier l'intégrité », « Attestation d'intégrité », « Créer la copie
  PDF/A » (archivistes, managers, administrateurs), encadré « Chaque sceau
  couvre… La chaîne est vérifiée chaque semaine ; toute rupture est
  signalée au journal d'audit. » ; views/aite_ecm_seal_views.xml (liste et
  fiche du sceau) ; views/aite_ecm_sae_menus.xml (« Preuve et archivage » :
  « Journal de preuve », « Vérifier l'intégrité », « Export de paquet
  d'archives ») ; data/ir_cron_data.xml (vérification hebdomadaire ; la
  tâche PDF/A quotidienne est livrée inactive : non citée) ;
- wizard/aite_ecm_seda_export.py et _views.xml : « Nom du transfert »
  (« Transfert du %s »), « Périmètre » (« Documents sélectionnés », « Un
  dossier de classement », « Documents à conservation définitive »,
  « Documents échus »), « Inclure toutes les versions », « Service
  versant », « Service d'archives destinataire » (« Service d'archives »),
  encadré manifest.xml / journal de preuve, « Produire le paquet »,
  « Paquet prêt », « Fermer » ; contenu du ZIP (manifest.xml, content/,
  journal_de_preuve.json, LISEZMOI.txt) ; un sceau « export » par document.
Écran de départ : présentation, chapitre 6 (refait ici : fiche du sceau
complétée, onglet Preuve réel). Modèle visuel : captures t20_*.
"""

import hashlib

import demo
from ecrans import (assistant, bande, bouton, bouton_stat, c_html, c_puce, case, champ, chatter, e, entree, fenetre, feuille,
                    grille2, liste, message, onglets, panneau_fiche, panneau_liste, puce, sec_titre, statusbar, table, v, vue)
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import animer, anneau, cacher, choisir, clic, etat, fermer, montrer, ouvrir, pause, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
AUDIT, ARCHI, MANAGER, ASSIST, AGENT, COMPTA = (P[k] for k in ('audit', 'archiviste', 'manager', 'assistante', 'agent', 'compta'))
MENUS = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse']
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'
PV = {'reference': 'DOC-2026-00320', 'titre': 'Procès-verbal du conseil — septembre', 'fichier': 'PV_conseil_septembre.pdf'}


def empreinte(*graines):
    """Une empreinte SHA-256 de démonstration (déterministe)."""
    return hashlib.sha256('|'.join(graines).encode()).hexdigest()


# Le journal : (horodatage, référence, événement, version, par, détail)
EVTS = [('12/10/2026 16:02:11', 'DOC-2026-00317', "Dépôt d'une version", 'v1', ASSIST[0], 'Contrat_entretien_locaux.pdf'),
        ('12/10/2026 16:40:27', 'DOC-2026-00318', "Dépôt d'une version", 'v1', COMPTA[0], 'Facture_F-2026-6402.pdf'),
        ('12/10/2026 17:05:03', 'DOC-2026-00318', 'Finalisation', 'v1', COMPTA[0], 'Finalisé'),
        ('13/10/2026 08:31:44', 'DOC-2026-00319', "Dépôt d'une version", 'v1', AGENT[0], 'Demande_de_partenariat.pdf'),
        ('13/10/2026 09:02:19', PV['reference'], "Dépôt d'une version", 'v2', MANAGER[0], PV['fichier']),
        ('13/10/2026 09:04:52', PV['reference'], 'Finalisation', 'v2', MANAGER[0], 'Finalisé'),
        ('13/10/2026 09:15:08', 'DOC-2026-00311', 'Archivage', 'v1', ARCHI[0], 'Archivé'),
        ('13/10/2026 09:20:36', 'DOC-2026-00290', "Vérification d'intégrité", 'v2', ARCHI[0], 'Vérification : intègre'),
        ('13/10/2026 09:31:57', 'DOC-2026-00321', "Dépôt d'une version", 'v1', ASSIST[0], 'Note_de_service_conges.pdf'),
        ('13/10/2026 09:48:12', 'DOC-2026-00271', "Export d'archives", 'v1', ARCHI[0], "Paquet d'archives « Transfert du 2026-10-12 »")]
HASH = [empreinte('sceau', str(i)) for i in range(len(EVTS))]
FIN = PV['reference'] + '|v2|finalisation'
SEAL = {'hash': HASH[5], 'prec': HASH[4], 'fichier': empreinte('fichier', 'PV v2'), 'jeton': empreinte('jeton', HASH[5])}


def hexa(h, ident=None):
    return '<span class="t20-hex"%s>%s</span>' % (' id="%s"' % ident if ident else '', h)


def menu_deroulant(ident, items):
    return '<div class="t20-dd masque" id="%s"%s>%s</div>' % (ident, ZONE, ''.join(
        '<div class="it" id="%s-%d">%s</div>' % (ident, i, e(m)) for i, m in enumerate(items)))


def poser_menu(html, app, n, dd):
    ancre = '<span class="menu" id="%s-m%d">' % (app, n)
    debut = html.index(ancre)
    fin = html.index('</span>', debut)
    return (html[:debut] + '<span class="menu t20-menu" id="%s-m%d">' % (app, n) + html[debut + len(ancre):fin] + dd
            + html[fin:])


def onglet_preuve(prefixe, pdfa):
    """L'onglet Preuve d'un document (views/aite_ecm_document_views.xml)."""
    sceaux = [('13/10/2026 09:02:19', "Dépôt d'une version", 'v1', MANAGER[0], 'PV_conseil_septembre.pdf', HASH[4]),
              ('13/10/2026 09:04:52', 'Finalisation', 'v2', MANAGER[0], 'Finalisé', HASH[5]),
              ('13/10/2026 09:52:30', 'Archivage', 'v2', ARCHI[0], 'Archivé', empreinte('arch'))]
    lignes = [{'id': '%s-s%d' % (prefixe, i), 'cellules': [h, ev, ve, par, de, c_html(hexa(hs[:20] + '…'))]}
              for i, (h, ev, ve, par, de, hs) in enumerate(sceaux)]
    lignes.append({'id': prefixe + '-snew', 'masque': True,
                   'cellules': ['13/10/2026 10:36:57', "Vérification d'intégrité", 'v2', AUDIT[0], 'Vérification : intègre',
                                c_html(hexa(empreinte('verif')[:20] + '…'))]})
    bts = bouton(prefixe + '-verif', "Vérifier l'intégrité", 'prim', 'verifie') + bouton(prefixe + '-attest', "Attestation d'intégrité", 'second', 'pdf')
    if pdfa:
        bts += bouton(prefixe + '-pdfa', 'Créer la copie PDF/A', 'second', 'archive')
    return ('<div id="%s-preuve">' % prefixe
            + grille2([champ('Intégrité', puce('Non vérifiée', 'gris', prefixe + '-integ'), prefixe + '-integ-c'),
                       champ('Vérifiée le', v('', identifiant=prefixe + '-quand')),
                       champ('Dernier sceau', hexa(empreinte('arch'), prefixe + '-dernier'))],
                      [champ('Copie de préservation (PDF/A)', '')])
            + '<div class="t20-bts" id="%s-bts">%s</div>' % (prefixe, bts)
            + table([('Horodatage', '118px'), ('Événement', '136px'), ('Version (libellé)', '52px'), ('Par', '100px'),
                     ('Détail', '1fr'), ('Empreinte du sceau', '150px')], lignes, identifiant=prefixe + '-sceaux', ajouter=False)
            + '<div class="bandeau t20-info">Chaque sceau couvre le contenu du fichier, l\'événement et l\'empreinte du sceau '
              'précédent. La chaîne est vérifiée chaque semaine ; toute rupture est signalée au journal d\'audit.</div></div>')


def fiche_pv(ident, prefixe, personne, pdfa, ch=''):
    corps = ('<div class="ref-l">Référence</div><div class="ref-v moyen">%s</div><div class="titre-doc t20-h2">%s</div>'
             % (PV['reference'], e(PV['titre']))
             + grille2([champ('Type', v('Procès-verbal / compte rendu')), champ('Dossier de classement', v('Direction générale / Procès-verbaux'))],
                       [champ('Propriétaire', v(MANAGER[0])), champ('Fichier', v(PV['fichier']))])
             + onglets(['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Description'], 4)
             + onglet_preuve(prefixe, pdfa))
    bts = [bouton(prefixe + '-prev', 'Prévisualiser', 'second', 'oeil'), bouton(prefixe + '-corb', 'Corbeille', 'second', 'corbeille')]
    return vue(ident, panneau_fiche('Documents', PV['titre'], '1 / 1', boutons_stat=bouton_stat('Sceaux', '3', 'sceau'))
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande(bts, statusbar(['Brouillon', 'Finalisé', 'Archivé'], 2, prefixe + '-sb'), prefixe + '-b'),
                   feuille(corps), ch))


# ------------------------------------------------------- l'auditrice --
def ecran_audit():
    lignes = [{'id': 't20-l%d' % i, 'cellules': [h, r, c_puce(ev, 'gris'), ve, par, c_html('<span class="ell">%s</span>' % e(de)),
                                                c_html(hexa(HASH[i][:34] + '…'))]}
              for i, (h, r, ev, ve, par, de) in enumerate(EVTS)]
    journal = vue('t20-journal', panneau_liste('Journal de preuve', '1-80 / 1 284', nouveau=False)
                  + liste([('Horodatage', '128px'), ('Référence', '108px'), ('Événement', '150px'), ('Version (libellé)', '56px'),
                           ('Par', '100px'), ('Détail', '1fr'), ('Empreinte du sceau', '240px')], lignes, ident='t20-lst'),
                  initiale=True)
    donnees = ('{"content_sha256": "%s", "detail": "Finalisé", "document_id": 320, "event": "final", "previous_hash": "%s", '
               '"reference": "%s", "timestamp": "2026-10-13 09:04:52", "user": "paul.ebogo", "version": "v2"}'
               % (SEAL['fichier'], SEAL['prec'], PV['reference']))
    corps = (grille2([champ('Référence', v(PV['reference'])), champ('Document', v(PV['titre'], True)),
                      champ('Événement', v('Finalisation')), champ('Version (libellé)', v('v2')), champ('Par', v(MANAGER[0], True))],
                     [champ('Horodatage', v('13/10/2026 09:04:52'), 't20-horo'), champ('Source', v('Interne (clé du serveur)')),
                      champ('Empreinte du fichier', hexa(SEAL['fichier'])),
                      champ('Empreinte du sceau précédent', hexa(SEAL['prec']), 't20-prec'),
                      champ('Empreinte du sceau', hexa(SEAL['hash']), 't20-emp')])
             + sec_titre('Détail') + '<div class="t20-texte">Finalisé</div>'
             + sec_titre('Données scellées') + '<div class="t20-texte t20-json" id="t20-donnees">%s</div>' % e(donnees)
             + sec_titre("Jeton d'horodatage") + '<div class="t20-texte">%s</div>' % hexa(SEAL['jeton'], 't20-jeton'))
    sceau = vue('t20-sceau', panneau_fiche('Journal de preuve', '', '6 / 80', nouveau=False)
                + '<div class="o-corps"><div class="o-gauche t20-sans-bande">%s</div></div>' % feuille(corps))
    ch = chatter([message(AUDIT[0], AUDIT[2], "Vérification d'intégrité : document intègre, chaîne de preuve cohérente.",
                          '10:36', 't20-mv', masque=True)], identifiant='t20-ach', suivre='Suivre')
    doc = fiche_pv('t20-doc', 't20a', AUDIT, False, ch)
    dd = menu_deroulant('t20-dda', ['Journal de preuve'])
    html = fenetre('ECM', MENUS, [journal, sceau, doc], AUDIT[1], AUDIT[2], ident='app-20a')
    return poser_menu(html, 'app-20a', 4, dd)


# ------------------------------------------------------- l'archiviste --
def ecran_archiviste():
    doc = fiche_pv('t20-doc2', 't20b', ARCHI, True)
    doc = doc.replace('class="vue" id="t20-doc2"', 'class="vue initiale" id="t20-doc2"', 1)
    corps = (champ('Nom du transfert', entree('t20-nom', '', 'Transfert du 2026-10-13'))
             + champ('Périmètre', entree('t20-scope', '', 'Documents sélectionnés'), 't20-scope-c')
             + '<div class="t20-pile"><div id="t20-docs-c">%s</div><div class="masque" id="t20-dos-c">%s</div></div>' % (
                 champ('Documents', ''), champ('Dossier', entree('t20-dossier', '', '')))
             + champ('Inclure toutes les versions', case(False), aide=True)
             + champ('Service versant', entree('t20-versant', '', demo.SOCIETE))
             + champ("Service d'archives destinataire", entree('t20-dest', '', "Service d'archives"))
             + '<div class="t20-pile"><div class="bandeau t20-info" id="t20-xinfo">Le paquet contient le bordereau <b>manifest.xml</b> (structure SEDA '
               '2.1 : identité des services, métadonnées, empreintes SHA-256), les fichiers, et le <b>journal de preuve</b>. Il '
               'permet de confier le fonds à un système d\'archivage tiers ou de prouver ce qui a été conservé.</div>'
             + '<div class="masque" id="t20-pret">%s</div></div>' % champ(
                 'Paquet prêt', '<span class="lien t20-zip" id="t20-zip">⤓ Transfert_du_2026-10-13.zip</span>', 't20-pret-c'))
    wiz = assistant('t20-wiz', "Export de paquet d'archives", corps,
                    [('t20-produire', 'Produire le paquet', 'prim'), ('t20-fermer', 'Fermer', 'second')], haut=110, largeur=800)
    dd = menu_deroulant('t20-ddb', ['Journal de preuve', "Vérifier l'intégrité", "Export de paquet d'archives"])
    html = fenetre('ECM', MENUS, [doc], ARCHI[1], ARCHI[2], calques=wiz, ident='app-20b')
    html = poser_menu(html, 'app-20b', 4, dd)
    return html.replace('<div class="o-app muk" id="app-20b">', '<div class="o-app muk masque" id="app-20b">', 1)


CSS = """
#app-20a .t20-menu, #app-20b .t20-menu { position: relative; }
#app-20a .t20-dd, #app-20b .t20-dd { position: absolute; left: -12px; top: 28px; z-index: 30; width: 210px; padding: 6px 0;
  background: #fff; border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 18px rgba(0,0,0,.16); color: #212529; }
#app-20a .t20-dd .it, #app-20b .t20-dd .it { padding: 4px 14px; font-size: 12.5px; white-space: nowrap; }
#app-20a .t20-dd .it.survol, #app-20b .t20-dd .it.survol { background: #EEF3F6; }
#app-20a .t20-hex, #app-20b .t20-hex { font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 10.5px; word-break: break-all; }
#app-20a .o-liste .t20-hex { white-space: nowrap; }
#app-20a .t20-sans-bande { padding-top: 10px; }
#app-20a .champ, #app-20b .champ { grid-template-columns: 170px 1fr; }
#app-20a .t20-texte { font-size: 12.5px; padding: 2px 4px 4px; }
#app-20a .t20-json { font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 10.5px; line-height: 1.5; word-break: break-all; }
#app-20a .t20-h2, #app-20b .t20-h2 { font-size: 20px; margin: 0 0 8px; }
#app-20a .t20-bts, #app-20b .t20-bts { display: flex; gap: 8px; margin: 8px 0 6px; }
#app-20a .t20-bts .bt .ic svg, #app-20b .t20-bts .bt .ic svg { width: 12px; height: 12px; }
#app-20a .t20-bts .bt.second .ic svg path, #app-20b .t20-bts .bt.second .ic svg path { stroke: #343A40; }
#app-20b .t20-bts .bt.second .ic svg[fill="#BFE3DF"] { fill: #343A40; }
#app-20a .t20-info, #app-20b .t20-info { background: #D7EEF3; color: #1F2D3D; margin: 8px 0 4px; line-height: 1.45; }
#app-20a .o-table .tl, #app-20b .o-table .tl { font-size: 11.5px; }
#app-20b .modale .entree { width: 100%; }
#app-20b .modale .champ { padding: 4px 0; }
#app-20b .t20-zip { font-size: 12.5px; }
#app-20a .o-table .t20-hex, #app-20b .o-table .t20-hex { white-space: nowrap; }
#app-20a #t20-sceau .champ { grid-template-columns: 200px 1fr; }
#app-20b .t20-pile { display: grid; } #app-20b .t20-pile > div { grid-area: 1 / 1; }
"""

TUTO = {
    'slug': 'tuto-20-la-valeur-probante',
    'titre_page': 'AITE ECM — Tutoriel 20 : la valeur probante',
    'titre': 'La valeur probante',
    'serie': dict(ECM, numero=20),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Ce document a-t-il été *modifié* depuis son *dépôt ?*',
        'sous': "Un fichier retouché, une date contestée, un auditeur qui demande des preuves : la confiance ne suffit plus.",
        'personnage': (AUDIT[0], 'Auditrice', AUDIT[2]),
        'chaos': [('alerte', 'Pièce contestée'), ('bulle', "C'est bien l'original ?"), ('doc', 'PV signé ?'),
                  ('note', 'Modifié le… ?'), ('dossier', 'Archives 2026'), ('bulle', 'Qui a touché au fichier ?'),
                  ('lettre', "Demande de l'auditeur"), ('alerte', 'Version douteuse')],
        'voix': "Un auditeur conteste une pièce : ce procès-verbal est-il bien celui qui a été déposé ? Qui l'a modifié, "
                "et quand ? Sans preuve, impossible de répondre.",
    },
    'revelation': {'voix': "Avec Aïte E C M, chaque document porte sa preuve d'intégrité."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Prouver qu\'un document *n\'a pas changé*',
        'pastilles': ['Sceaux SHA-256 chaînés', "Vérification d'intégrité", "Paquet d'archives SEDA"],
        'voix': "Chaque événement est scellé et horodaté, l'intégrité se vérifie d'un clic, et le fonds se verse à un "
                "service d'archives : dans l'esprit de N F Z quarante-deux zéro treize et d'iso quatorze mille six cent "
                "quarante et un.",
    },
    'ecran': ecran_audit() + ecran_archiviste(), 'vue_initiale': 't20-journal',
    'css': CSS,
    'etapes': [
        {'titre': 'Le journal de preuve',
         'texte': "Chaque sceau : une empreinte SHA-256 du fichier, de l'événement et du sceau précédent, horodatée.",
         'voix': "Sandrine, l'auditrice, ouvre le journal de preuve. Chaque dépôt, finalisation, archivage ou élimination y "
                 "laisse un sceau : une empreinte SHA-256 du fichier, de l'événement et du sceau précédent. Une chaîne "
                 "horodatée, et inaltérable.",
         'gestes': [anneau('#app-20a-m4', d=1.0, decale=0.2), anneau('#t20-lst', d=1.4), survol('#t20-l5', decale=0.2),
                    clic('#t20-l5', fx=0.3), aller('t20-sceau'), zoom('#t20-prec', s=1.45, fx=0.6, fy=0.4, d=0.8),
                    anneau('#t20-emp', d=1.2), bulle('#t20-prec', 'Chaînée au sceau précédent', cote='gauche', d=2.4, avec=True),
                    anneau('#t20-horo', d=1.2), bulle('#t20-horo', 'Horodatage', cote='gauche', d=1.8, avec=True),
                    dezoom(d=0.7), anneau('#t20-donnees', d=1.4)]},
        {'titre': "Vérifier l'intégrité",
         'texte': "Empreintes recalculées : « Intègre ». L'attestation d'intégrité se télécharge en PDF.",
         'voix': "Sur un procès-verbal, onglet Preuve, elle clique sur Vérifier l'intégrité : les empreintes sont "
                 "recalculées, le document est intègre et la chaîne cohérente. L'attestation se télécharge en PDF. "
                 "Et chaque semaine, toute la chaîne est revérifiée automatiquement.",
         'gestes': [aller('t20-doc'), anneau('#t20a-preuve', d=1.0, decale=0.2), clic('#t20a-verif'),
                    etat('#t20a-integ', 'Intègre', 'vert', decale=0.2), texte('#t20a-quand', '13/10/2026 10:36:57', avec=True),
                    montrer('#t20a-snew', y=6), montrer('#t20-mv', y=10, avec=True),
                    zoom('#t20a-integ-c', s=1.6, fx=0.35, fy=0.35, d=0.8),
                    bulle('#t20a-integ', 'Intègre', cote='droite', d=1.8), dezoom(d=0.7),
                    anneau('#t20a-attest', d=1.2), bulle('#t20a-attest', 'Attestation PDF', cote='dessous', d=1.8, avec=True),
                    anneau('#app-20a .t20-info', d=1.6)]},
        {'titre': 'Copie PDF/A et export',
         'texte': "L'archiviste peut créer la copie de préservation PDF/A, puis ouvre l'export de paquet d'archives.",
         'voix': "Jules, l'archiviste, dispose en plus de Créer la copie PDF/A : une copie de préservation, produite par "
                 "LibreOffice, qui doit être installé sur le serveur. Pour verser un fonds, il ouvre Export de paquet "
                 "d'archives et choisit le périmètre : ici, le dossier des procès-verbaux.",
         'gestes': [montrer('#app-20b', y=0, d=0.4), anneau('#t20b-pdfa', d=1.2, decale=0.3),
                    bulle('#t20b-pdfa', 'Avec LibreOffice', cote='dessous', d=2.2, avec=True), pause(1.2),
                    clic('#app-20b-m4'), montrer('#t20-ddb', y=-8, d=0.3), survol('#t20-ddb-2', decale=0.2),
                    clic('#t20-ddb-2', decale=0.1), cacher('#t20-ddb', d=0.15), ouvrir('t20-wiz'),
                    clic('#t20-scope', fx=0.3), choisir('t20-scope', 'Un dossier de classement'),
                    cacher('#t20-docs-c', d=0.2, avec=True), montrer('#t20-dos-c', y=0, d=0.3),
                    clic('#t20-dossier', fx=0.3), choisir('t20-dossier', 'Direction générale / Procès-verbaux')]},
        {'titre': "Produire le paquet d'archives",
         'texte': "Un ZIP : bordereau manifest.xml (structure SEDA 2.1), fichiers, empreintes et journal de preuve.",
         'voix': "Un clic sur Produire le paquet : une archive ZIP, avec son bordereau structuré selon le SEDA 2.1, les "
                 "fichiers et leurs empreintes, et le journal de preuve. De quoi confier le fonds à un système "
                 "d'archivage tiers, ou prouver ce qui a été conservé.",
         'gestes': [zoom('#t20-xinfo', s=1.4, d=0.8), anneau('#t20-xinfo', d=2.0),
                    bulle('#t20-xinfo', 'Bordereau SEDA 2.1', cote='dessous', fx=0.3, d=2.2, avec=True), dezoom(d=0.7),
                    clic('#t20-produire'), cacher('#t20-xinfo', d=0.25, decale=0.4), animer('#t20-produire', {'autoAlpha': 1}, {'autoAlpha': 0, 'width': 0, 'paddingLeft': 0, 'paddingRight': 0}, d=0.25, avec=True),
                    montrer('#t20-pret', y=0), zoom('#t20-pret-c', s=1.3, fx=0.5, d=0.8),
                    bulle('#t20-zip', 'Le paquet, prêt', cote='droite', d=2.2), dezoom(d=0.7)]},
    ],
    'benefices': {
        'titre': 'La preuve, *à* *portée* *de* clic.',
        'voix': "Chaque événement est scellé, l'intégrité se prouve en un clic, et le fonds peut être versé à un service "
                "d'archives, avec sa preuve.",
        'cartes': [('cadenas', 'SHA-256', 'Un journal inaltérable', "Journal chaîné, dans l'esprit de NF Z42-013 / ISO 14641."),
                   ('bouclier', 'Intègre', 'Vérifié à la demande', "Et chaque semaine sur tout le fonds ; attestation en PDF."),
                   ('doc', 'SEDA 2.1', "Un paquet d'archives", "Bordereau, fichiers, empreintes et journal de preuve dans un ZIP.")],
    },
    'cta': cta('ecm', 'Vos documents, *preuve* à *l\'appui.*', "Aïte E C M : vos documents, preuve à l'appui."),
    'youtube': youtube("COMMENT PROUVER L'INTÉGRITÉ DE VOS DOCUMENTS AVEC AITE ECM (ODOO 18)",
                       "Journal de preuve scellé et chaîné (SHA-256, horodatage), vérification d'intégrité et attestation, "
                       "copie de préservation PDF/A et export de paquet d'archives (bordereau inspiré du SEDA 2.1), dans "
                       "l'esprit de NF Z42-013 / ISO 14641. Tutoriel AITE ECM pour Odoo 18.",
                       ['AITE ECM', 'valeur probante', 'archivage électronique', 'SEDA', 'PDF/A', 'intégrité']),
}
