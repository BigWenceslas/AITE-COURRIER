# -*- coding: utf-8 -*-
"""Tutoriel 19 — Élimination et archives physiques.

Sources (addons/aite_ecm_records) :
- views/aite_ecm_disposition_views.xml : boutons « Rassembler les documents
  échus », « Soumettre à validation », « Valider » et « Exécuter
  l'élimination » (réservés aux managers et administrateurs), confirmation
  « Les documents listés seront définitivement supprimés. Un certificat sera
  généré. Confirmer ? », « Annuler » ; barre d'états Projet / À valider /
  Validé / Exécuté ; champs « Date du bordereau », « Préparé par »,
  « Validé par », « Exécuté le », « Certificat de destruction » (visible une
  fois exécuté), lignes « Référence », « Titre », « Dossier », « Règle
  appliquée », « Échéance », « Détruit » ; « Observations » ;
- models/aite_ecm_retention.py:233-373 : états « Projet », « À valider »,
  « Validé », « Exécuté », « Annulé » ; action_collect (documents échus,
  sort final Élimination, hors gel juridique, pas déjà sur un bordereau) ;
  action_submit (« Le bordereau est vide. ») ; action_approve (manager,
  message « Bordereau validé : %d document(s). ») ; action_execute (manager,
  refus « Gel juridique actif sur %d document(s) : retirez-les du bordereau
  avant exécution. », suppression des documents, ligne « Détruit » et
  empreinte conservées, certificat) ; _create_certificate (document
  « Certificat de destruction %s », PDF du rapport « Bordereau
  d'élimination », dossier « Archives et éliminations », finalisé) ;
  :397-451 boîte d'archives (« En constitution », « Rangée », « Sortie
  (prêt) », « Détruite » ; action_lend : emprunteur = l'utilisateur, sortie
  ce jour, retour prévu à 30 jours ; action_store : « Ranger ») ;
- report/disposition_report.xml (rapport « Bordereau d'élimination », colonnes
  dont « Empreinte SHA-256 ») ; data/ir_sequence_data.xml (BORD-AAAA-NNN,
  BTE-NNNNN) ; data/aite_ecm_records_data.xml (dossier « Archives et
  éliminations ») ;
- views/aite_ecm_box_views.xml (« Sortir (prêt) », « Ranger », « Code »,
  « Emplacement », « Emprunteur », « Sortie le », « Retour prévu », liste
  des documents, « Notes ») ; views/aite_ecm_records_menus.xml (menu
  Conservation : « Documents échus », « Bordereaux d'élimination », « Gels
  juridiques », « Archives physiques »).
Titre de boîte « Confirmation » : Odoo 18. Modèle visuel : base demo18
(MuK), captures t19_*.
"""

import demo
from ecrans import (assistant, bande, bouton, c_html, case, champ, chatter, e, fenetre, feuille, grille2, liste, message,
                    panneau_fiche, panneau_liste, sec_titre, statusbar, table, v, vue)
from scenarios.tutos import ADRESSE, ECM, cta, youtube
from moteur import anneau, cacher, classe, clic, fermer, montrer, ouvrir, pause, survol, texte, vue as aller
from tutoriel import bulle, dezoom, zoom

P = demo.PERSONNES
ARCHI, MANAGER = P['archiviste'], P['manager']
MENUS = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse']
MENUS_CONFIG = MENUS + ['Configuration']
ZONE = ' data-layout-allow-overlap data-layout-allow-occlusion'
NUM = 'BORD-2026-002'
REGLE = 'Pièces comptables — 10 ans (OHADA)'
DOSSIER = 'Finance et comptabilité / Factures fournisseurs'
# Les deux factures échues (fictives), finalisées il y a plus de dix ans.
ECHUS = [('DOC-2014-00931', 'Facture F-2014-0931 — %s' % demo.FOURNISSEUR, '03/06/2024'),
         ('DOC-2015-00127', 'Facture F-2015-0127 — %s' % demo.FOURNISSEUR, '14/02/2025')]
BOITE = {'code': 'BTE-00007', 'nom': 'Factures fournisseurs 2016', 'empl': 'Salle 2 — travée C — étagère 4',
         'sortie': '13/10/2026', 'retour': '12/11/2026'}


def menu_deroulant(ident, items):
    return '<div class="t19-dd masque" id="%s"%s>%s</div>' % (ident, ZONE, ''.join(
        '<div class="it" id="%s-%d">%s</div>' % (ident, i, e(m)) for i, m in enumerate(items)))


def poser_menu(html, app, n, dd):
    ancre = '<span class="menu" id="%s-m%d">' % (app, n)
    debut = html.index(ancre)
    fin = html.index('</span>', debut)
    return (html[:debut] + '<span class="menu t19-menu" id="%s-m%d">' % (app, n) + html[debut + len(ancre):fin] + dd
            + html[fin:])


def lignes_bordereau(prefixe, masque, detruit_id=False):
    lignes = []
    for i, (ref, titre, ech) in enumerate(ECHUS):
        det = case(False)
        if detruit_id:
            det = ('<span class="t19-det">%s<span class="t19-det-on masque" id="%s-det%d">%s</span></span>'
                   % (case(False), prefixe, i, case(True)))
        lignes.append({'id': '%s-l%d' % (prefixe, i), 'masque': masque,
                       'cellules': [ref, titre, DOSSIER, REGLE, ech, c_html('<span>%s</span>' % det)]})
    return table([('Référence', '106px'), ('Titre', '1fr'), ('Dossier', '150px'), ('Règle appliquée', '150px'),
                  ('Échéance', '72px'), ('Détruit', '42px')], lignes, identifiant=prefixe + '-tab')


def corps_bordereau(prefixe, nom, valide_par='', masque_lignes=False, detruit=False):
    return ('<div class="titre-doc t19-h1" id="%s-nom">%s</div>' % (prefixe, nom)
            + grille2([champ('Date du bordereau', v('13/10/2026')), champ('Préparé par', v(ARCHI[0], True))],
                      [champ('Validé par', v(valide_par, True, prefixe + '-valpar')),
                       champ('Exécuté le', v('', identifiant=prefixe + '-exec-le')),
                       '<div class="masque" id="%s-cert">%s</div>' % (prefixe, champ(
                           'Certificat de destruction', v('Certificat de destruction %s' % NUM, True)))])
            + lignes_bordereau(prefixe, masque_lignes, detruit)
            + sec_titre('Observations') + '<div class="t19-texte">Campagne d\'élimination annuelle.</div>')


# ------------------------------------------------------- l'archiviste --
def ecran_archiviste():
    bord = vue('t19-bord', panneau_fiche("Bordereaux d'élimination", 'Nouveau', '', ref_id='t19-fil')
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande([bouton('t19-rass', 'Rassembler les documents échus', 'second'),
                          bouton('t19-soum', 'Soumettre à validation', 'prim'), bouton('t19-ann', 'Annuler', 'second')],
                         statusbar(['Projet', 'À valider', 'Validé', 'Exécuté'], 0, 't19-sb'), 't19-b',
                         [bouton('t19-ann2', 'Annuler', 'second')]),
                   feuille(corps_bordereau('t19', 'Nouveau', masque_lignes=True)),
                   chatter([message(ARCHI[0], ARCHI[2], 'Création d\'un enregistrement…', '09:12')], suivre='Suivre')),
               initiale=True)
    # les archives physiques : la liste, puis la boîte
    cols = [('Code', '100px'), ('Libellé', '1fr'), ('Emplacement', '240px'), ('Emprunteur', '130px'), ('Retour prévu', '96px')]
    boites = [('BTE-00005', 'Procès-verbaux 2018', 'Salle 1 — travée A — étagère 2', '', ''),
              ('BTE-00006', 'Dossiers du personnel 2019', 'Salle 1 — travée C — étagère 1', MANAGER[0], '30/10/2026'),
              (BOITE['code'], BOITE['nom'], BOITE['empl'], '', ''),
              ('BTE-00008', 'Contrats fournisseurs 2017', 'Salle 2 — travée D — étagère 2', '', '')]
    lst = vue('t19-boites', panneau_liste('Archives physiques', '1-4 / 4', ident='t19x')
              + liste(cols, [{'id': 't19-x%d' % i, 'cellules': list(b), 'classe': 't19-pret' if b[3] else ''}
                             for i, b in enumerate(boites)]))
    docs = table([('Référence', '120px'), ('Titre', '1fr'), ('Cycle de vie archivistique', '190px'),
                  ('Échéance de conservation', '150px')],
                 [{'id': 't19-bd%d' % i, 'cellules': list(x)} for i, x in enumerate([
                     ('DOC-2016-00044', 'Facture F-2016-0044 — %s' % demo.FOURNISSEUR, 'Archive intermédiaire', '18/11/2026'),
                     ('DOC-2016-00102', 'Facture F-2016-0102 — %s' % demo.FOURNISSEUR, 'Archive intermédiaire', '05/12/2026'),
                     ('DOC-2016-00187', 'Facture F-2016-0187 — %s' % demo.FOURNISSEUR, 'Archive intermédiaire', '21/12/2026')])],
                 identifiant='t19-bdocs')
    pret = ('<div class="masque" id="t19-pret">%s</div>' % ''.join([
        champ('Emprunteur', v(ARCHI[0])), champ('Sortie le', v(BOITE['sortie'])),
        champ('Retour prévu', v(BOITE['retour']), 't19-retour')]))
    corps = ('<div class="ref-l">Code</div><div class="ref-v moyen">%s</div><div class="titre-doc t19-h1">%s</div>'
             % (BOITE['code'], BOITE['nom'])
             + grille2([champ('Emplacement', v(BOITE['empl']), 't19-empl', aide=True)], [pret])
             + docs + sec_titre('Notes') + '<div class="t19-texte t19-vide"></div>')
    boite = vue('t19-boite', panneau_fiche('Archives physiques', BOITE['nom'], '3 / 4')
                + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                    bande([bouton('t19-sortir', 'Sortir (prêt)', 'second')],
                          statusbar(['En constitution', 'Rangée', 'Sortie (prêt)'], 1, 't19-xsb'), 't19-xb',
                          [bouton('t19-ranger', 'Ranger', 'prim')]),
                    feuille(corps)))
    dd = menu_deroulant('t19-ddk', ['Documents échus', "Bordereaux d'élimination", 'Gels juridiques', 'Archives physiques'])
    html = fenetre('ECM', MENUS, [bord, lst, boite], ARCHI[1], ARCHI[2], ident='app-19a')
    return poser_menu(html, 'app-19a', 3, dd)


# ---------------------------------------------------------- le manager --
def ecran_manager():
    ch = chatter([message(MANAGER[0], MANAGER[2], 'Bordereau validé : 2 document(s).', '10:05', 't19-mmsg', masque=True)],
                 identifiant='t19-mch', suivre='Suivre')
    bord = vue('t19-mbord', panneau_fiche("Bordereaux d'élimination", NUM, '1 / 2')
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande([bouton('t19-val', 'Valider', 'prim'), bouton('t19-mann', 'Annuler', 'second')],
                         statusbar(['Projet', 'À valider', 'Validé', 'Exécuté'], 1, 't19-msb'), 't19-mb',
                         [[bouton('t19-exec', "Exécuter l'élimination", 'rouge'), bouton('t19-mann2', 'Annuler', 'second')], []]),
                   feuille(corps_bordereau('t19-m', NUM, detruit=True)), ch), initiale=True)
    conf = assistant('t19-conf', 'Confirmation', '<div class="t19-msg">Les documents listés seront définitivement supprimés. '
                     'Un certificat sera généré. Confirmer ?</div>', [('t19-ok', 'Ok', 'prim'), ('t19-non', 'Annuler', 'second')],
                     haut=250, largeur=600)
    html = fenetre('ECM', MENUS_CONFIG, [bord], MANAGER[1], MANAGER[2], calques=conf, ident='app-19m')
    return html.replace('<div class="o-app muk" id="app-19m">', '<div class="o-app muk masque" id="app-19m">', 1)


CSS = """
#app-19a .t19-menu { position: relative; }
#app-19a .t19-dd { position: absolute; left: -12px; top: 28px; z-index: 30; width: 200px; padding: 6px 0; background: #fff;
  border: 1px solid #DEE2E6; border-radius: 4px; box-shadow: 0 8px 18px rgba(0,0,0,.16); color: #212529; }
#app-19a .t19-dd .it { padding: 4px 14px; font-size: 12.5px; white-space: nowrap; }
#app-19a .t19-dd .it.survol { background: #EEF3F6; }
#app-19a .t19-h1, #app-19m .t19-h1 { font-size: 22px; margin-bottom: 8px; }
#app-19a .t19-texte, #app-19m .t19-texte { font-size: 12.5px; padding: 2px 4px 6px; }
#app-19a .t19-vide { height: 22px; }
#app-19a .champ, #app-19m .champ { grid-template-columns: 150px 1fr; }
#app-19a .o-table, #app-19m .o-table { margin-top: 10px; }
#app-19a .o-liste .ligne.t19-pret { color: #B07A0A; }
#app-19m .t19-det { position: relative; display: inline-block; }
#app-19m .t19-det-on { position: absolute; left: 0; top: 0; }
#app-19m .t19-msg { font-size: 13px; line-height: 1.5; }
"""

TUTO = {
    'slug': 'tuto-19-elimination-et-archives-physiques',
    'titre_page': 'AITE ECM — Tutoriel 19 : élimination et archives physiques',
    'titre': 'Élimination et archives physiques',
    'serie': dict(ECM, numero=19),
    'adresse': ADRESSE % 'ecm',
    'accroche': {
        'question': 'Qui a *détruit* ces archives, et *pourquoi ?*',
        'sous': "Cartons jetés sans trace, boîtes empruntées jamais rendues : les archives papier se perdent en silence.",
        'personnage': (ARCHI[0], 'Archiviste', ARCHI[2]),
        'chaos': [('dossier', 'Carton « 2014 »'), ('bulle', 'On peut les jeter ?'), ('alerte', 'Boîte introuvable'),
                  ('note', 'Rendu quand ?'), ('doc', 'Liste manuscrite'), ('bulle', 'Qui a validé ?'),
                  ('lettre', 'Demande d\'audit'), ('alerte', 'Aucune preuve')],
        'voix': "Des cartons d'archives partent à la benne sans trace, une boîte empruntée n'est jamais revenue. "
                "Le jour de l'audit, qui peut prouver ce qui a été détruit, et pourquoi ?",
    },
    'revelation': {'voix': "Avec Aïte E C M, chaque élimination est validée, tracée et certifiée."},
    'apercu': {
        'kicker': 'AITE ECM · Odoo 18', 'titre': 'Éliminer *sans* rien *perdre* de la preuve',
        'pastilles': ["Bordereau d'élimination", 'Certificat de destruction', 'Prêts des boîtes suivis'],
        'voix': "Un bordereau d'élimination préparé, validé puis exécuté, un certificat de destruction, et des boîtes "
                "d'archives dont on suit chaque sortie. Voyons comment.",
    },
    'ecran': ecran_archiviste() + ecran_manager(), 'vue_initiale': 't19-bord',
    'css': CSS,
    'etapes': [
        {'titre': 'Rassembler les documents échus',
         'texte': "Un clic remplit le bordereau : documents échus, à éliminer, hors gel juridique.",
         'voix': "Jules, l'archiviste, crée un bordereau d'élimination, puis clique sur Rassembler les documents échus. "
                 "N'y entrent que les documents échus dont le sort final est l'élimination, et qu'aucun gel juridique "
                 "ne protège.",
         'gestes': [anneau('#t19-sb-0', d=1.0, decale=0.3), clic('#t19-rass'), texte('#t19-nom', NUM, decale=0.2),
                    texte('#t19-fil', NUM, avec=True), montrer('#t19-l0', y=10), montrer('#t19-l1', y=10, decale=0.15),
                    zoom('#t19-tab', s=1.4, fy=0.45, d=0.8), anneau('#t19-tab', d=1.6),
                    bulle('#t19-l1', 'Échus, à éliminer, hors gel', cote='dessous', fx=0.35, d=2.4, avec=True),
                    dezoom(d=0.7)]},
        {'titre': 'Soumettre, puis valider',
         'texte': "L'archiviste soumet le bordereau ; seul un manager peut le valider.",
         'voix': "Il le soumet à validation : le bordereau passe à l'état À valider. Paul, le manager, l'ouvre et clique "
                 "sur Valider. Son nom s'inscrit dans Validé par, et le fil de discussion garde la trace de la décision.",
         'gestes': [clic('#t19-soum'), classe('#t19-sb-0', retirer=['actif']), classe('#t19-sb-1', ajouter=['actif'], avec=True),
                    cacher('#t19-b-a', d=0.2), montrer('#t19-b-b', y=0, avec=True), anneau('#t19-sb-1', d=1.0),
                    montrer('#app-19m', y=0, d=0.4, decale=0.4), anneau('#t19-msb-1', d=1.0, decale=0.2),
                    clic('#t19-val'), classe('#t19-msb-1', retirer=['actif']), classe('#t19-msb-2', ajouter=['actif'], avec=True),
                    cacher('#t19-mb-a', d=0.2), montrer('#t19-mb-b', y=0, avec=True),
                    texte('#t19-m-valpar', MANAGER[0], avec=True), montrer('#t19-mmsg', y=10),
                    anneau('#t19-m-valpar', d=1.2), anneau('#t19-mmsg', d=1.2)]},
        {'titre': "Exécuter l'élimination",
         'texte': "Les documents sont supprimés ; le bordereau et le certificat de destruction en gardent la preuve.",
         'voix': "Paul exécute l'élimination, après confirmation. Les documents sont supprimés, mais le bordereau garde leur "
                 "référence et leur empreinte, et un certificat de destruction est déposé dans la gestion documentaire. "
                 "Un document passé sous gel juridique bloquerait l'exécution.",
         'gestes': [clic('#t19-exec'), ouvrir('t19-conf'), zoom('#t19-conf', s=1.3, d=0.7), anneau('#t19-conf .t19-msg', d=1.4),
                    dezoom(d=0.6), clic('#t19-ok'), fermer('t19-conf'),
                    classe('#t19-msb-2', retirer=['actif']), classe('#t19-msb-3', ajouter=['actif'], avec=True),
                    cacher('#t19-mb-b', d=0.2), texte('#t19-m-exec-le', '13/10/2026 10:21', avec=True),
                    montrer('#t19-m-det0', y=0, d=0.2), montrer('#t19-m-det1', y=0, d=0.2, decale=0.1),
                    montrer('#t19-m-cert', y=0), zoom('#t19-m-cert', s=1.6, fx=0.55, fy=0.4, d=0.8),
                    bulle('#t19-m-cert', 'Certificat déposé dans l\'ECM', cote='gauche', d=2.4),
                    dezoom(d=0.7)]},
        {'titre': 'Les archives physiques',
         'texte': "Chaque boîte a son code, son emplacement, son contenu ; ses sorties en prêt sont suivies.",
         'voix': "Reste le papier. Dans Archives physiques, chaque boîte a son code, son emplacement et la liste de ses "
                 "documents. Jules sort une boîte en prêt : elle passe à l'état Sortie, à son nom, avec un retour prévu "
                 "sous trente jours. À son retour, un clic sur Ranger la remet en place.",
         'gestes': [cacher('#app-19m', d=0.3), clic('#app-19a-m3', decale=0.3), montrer('#t19-ddk', y=-8, d=0.3),
                    survol('#t19-ddk-3', decale=0.2), clic('#t19-ddk-3', decale=0.1), cacher('#t19-ddk', d=0.15),
                    aller('t19-boites'), survol('#t19-x2', decale=0.2), clic('#t19-x2', fx=0.3), aller('t19-boite'),
                    anneau('#t19-empl', d=1.0), anneau('#t19-bdocs', d=1.0), clic('#t19-sortir'),
                    classe('#t19-xsb-1', retirer=['actif']), classe('#t19-xsb-2', ajouter=['actif'], avec=True),
                    cacher('#t19-xb-a', d=0.2), montrer('#t19-xb-b', y=0, avec=True), montrer('#t19-pret', y=0, avec=True),
                    zoom('#t19-pret', s=1.5, fx=0.55, fy=0.4, d=0.8),
                    bulle('#t19-retour', 'Retour à 30 jours', cote='dessous', fx=0.3, d=2.2), dezoom(d=0.7),
                    anneau('#t19-ranger', d=1.0)]},
    ],
    'benefices': {
        'titre': "Détruire à temps, *prouver* toujours.",
        'voix': "Rien n'est détruit sans validation, chaque élimination laisse son certificat, et chaque boîte d'archives "
                "sait où elle est, et chez qui.",
        'cartes': [('equipe', 'Validé', 'Une décision à deux', "L'archiviste prépare, le manager valide et exécute."),
                   ('doc', 'Certificat', 'La preuve reste', "Référence, titre et empreinte de chaque document éliminé."),
                   ('cible', '30 jours', 'Prêts suivis', "Emprunteur, date de sortie et retour prévu pour chaque boîte.")],
    },
    'cta': cta('ecm', 'Éliminer, oui. *Sans* *trace,* jamais.', "Aïte E C M : éliminer, oui ; sans trace, jamais."),
    'youtube': youtube("COMMENT ÉLIMINER DES ARCHIVES ET SUIVRE LES ARCHIVES PHYSIQUES AVEC AITE ECM (ODOO 18)",
                       "Bordereau d'élimination (rassembler les documents échus, soumettre, valider, exécuter), certificat de "
                       "destruction déposé dans l'ECM, boîtes d'archives physiques et suivi des prêts. Tutoriel AITE ECM pour "
                       "Odoo 18.",
                       ['AITE ECM', "bordereau d'élimination", 'certificat de destruction', 'archives physiques']),
}
