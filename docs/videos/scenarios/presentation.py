# -*- coding: utf-8 -*-
"""Présentation complète d'AITE Courrier et d'AITE ECM, chapitre par chapitre.

Sources : les dix-huit scénarios de la recette applicative
(docs/recette/GUIDE_RECETTE.md, captures docs/recette/captures), la recette
des interfaces (même guide), le plan de test (docs/recette/PLAN_DE_TEST.md).
Libellés relevés dans les vues des modules (addons/aite_*/views), le circuit
standard (aite_courrier_workflow/data/workflow_circuits.xml), les groupes
(aite_courrier_base/security/groups.xml) et le portail
(aite_courrier_portal/views/portal_templates.xml, controllers/portal.py).
Données : toutes fictives (demo.py).
"""

import demo
from ecrans import (ICONES, activite, assistant, bande, bandeau, barre, barres, bouton, bouton_stat, c_html, c_lien,
                    c_num, c_puce, case, champ, chatter, e, entree, fenetre, feuille, grille2, interrupteur, liste,
                    message, onglets, p_entete, p_fil, panneau_fiche, panneau_lateral, panneau_liste, portail, puce,
                    sec_titre, statusbar, table, tuile, v, vue)
from moteur import (anneau, cacher, choisir, clic, compter, curseur, etat, fermer, montrer, ouvrir, pause, saisir, survol,
                    texte, vue as aller, animer, classe)

P = demo.PERSONNES
AGENT, ASSIST, MANAGER, ARCHI, AUDIT, COMPTA = (P[k] for k in ('agent', 'assistante', 'manager', 'archiviste', 'audit', 'compta'))
N1, N2, CLOS = demo.NOUVEAU, demo.EN_COURS, demo.CLOS
ETAPES = ['Réception', 'Qualification', 'Affectation', 'Traitement', 'Archivage']
MENUS_COURRIER = ['Tableau de bord', 'Courriers', 'Espace documentaire']
MENUS_ECM = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse']


def lat_courriers(ident):
    return panneau_lateral([('▰ CATÉGORIE', [('Tous', '', True), ('Entrant', '68', False), ('Interne', '26', False),
                                             ('Sortant', '57', False)]),
                            ('≡ STATUT', [('Archivé', '50', False), ('Brouillon', '20', False), ('Nouveau', '16', False),
                                          ('En traitement', '54', False), ('Rejeté', '11', False)])], ident)


COL_COURRIERS = [('Référence', '104px'), ('Objet', '1fr'), ('Type', '104px'), ('Service destinataire', '128px'),
                 ('Étape courante', '96px'), ('Statut', '88px'), ('Date de r…', '74px')]


def ligne_courrier(i, ref, objet, typ, service, etape, statut, genre, date, classe=''):
    brouillon = statut == 'Brouillon'
    cell = (lambda x: c_lien(x)) if brouillon else (lambda x: x)
    return {'id': i, 'classe': classe, 'cellules': [ref, cell(objet), cell(typ), service, etape, c_puce(statut, genre),
                                                    c_lien(date) if brouillon else date]}


LIGNES_COURRIERS = [
    ('', 'Réclamation sur la facture de septembre', 'Courrier entrant', '', '', 'Brouillon', 'gris', '13/10/2026'),
    ('COUR-2026-0140', 'Demande de rendez-vous — Cabinet Ndzana Conseil', 'Courrier entrant', '', 'Réception', 'Nouveau', 'gris', '13/10/2026'),
    ('COUR-2026-0139', 'Candidature spontanée — poste de comptable', 'Courrier entrant', '', 'Réception', 'Nouveau', 'gris', '12/10/2026'),
    ('COUR-2026-0017', 'Notification de contrôle fiscal', 'Courrier entrant', 'Finance et comptabilité', 'Qualification', 'En traitement', 'gris', '09/10/2026'),
    ('COUR-2026-0119', "Proposition d'amélioration qualité", 'Courrier interne', 'Direction générale', 'Création', 'Nouveau', 'gris', '08/10/2026'),
    ('', 'Suite à votre demande COUR-2026-0010', 'Courrier sortant', 'Juridique', '', 'Brouillon', 'gris', '08/10/2026'),
    ('COUR-2026-0077', 'Réponse à votre courrier COUR-2026-0014', 'Courrier sortant', 'Ressources humaines', 'Validation', 'Rejeté', 'rouge', '07/10/2026'),
    ('COUR-2026-0031', 'Facture F-2026-3262 — maintenance climatisation', 'Facture', 'Direction générale', 'Archivage', 'Archivé', 'gris', '06/10/2026', 'gris'),
    ('COUR-2026-0026', 'Rappel de cotisations sociales — septembre', 'Courrier entrant', 'Juridique', 'Archivage', 'Archivé', 'gris', '05/10/2026', 'gris'),
    ('COUR-2026-0079', 'Devis D-2026-7840 — mise en place d\'un ERP', 'Devis', 'Commercial', 'Archivage', 'Archivé', 'gris', '03/10/2026', 'gris'),
    ('COUR-2026-0060', 'Réponse à votre courrier COUR-2026-0027', 'Courrier sortant', 'Commercial', 'Signature', 'Rejeté', 'rouge', '01/10/2026'),
    ('COUR-2026-0123', "Proposition d'amélioration qualité", 'Courrier interne', 'Communication', 'Archivage', 'Archivé', 'gris', '30/09/2026', 'gris'),
    ('COUR-2026-0014', N2['objet'], 'Courrier entrant', 'Juridique', 'Affectation', 'En traitement', 'gris', '22/09/2026'),
    ('COUR-2026-0009', CLOS['objet'], 'Courrier entrant', 'Finance et comptabilité', 'Archivage', 'Archivé', 'gris', '20/09/2026', 'gris'),
    ('COUR-2026-0005', 'Rappel de cotisations sociales — août', 'Courrier entrant', 'Juridique', 'Traitement', 'En traitement', 'gris', '18/09/2026'),
    ('COUR-2026-0002', 'Demande de rendez-vous avec la Direction', 'Courrier entrant', 'Direction générale', 'Qualification', 'En traitement', 'gris', '15/09/2026'),
    ('COUR-2026-0001', 'Notification de changement de RIB', 'Courrier entrant', 'Finance et comptabilité', 'Archivage', 'Archivé', 'gris', '12/09/2026', 'gris'),
    ('COUR-2026-0003', 'Mise en demeure — facture N-2025-6874', 'Courrier entrant', 'Juridique', 'Traitement', 'En traitement', 'gris', '10/09/2026'),
    ('COUR-2026-0004', 'Plainte pour nuisance sonore', 'Courrier entrant', 'Communication', 'Affectation', 'En traitement', 'gris', '08/09/2026'),
]


def chatter_cree(auteur, ident, suivre='Suivre'):
    return chatter([message(auteur[0], auteur[2], 'Création d\'un enregistrement…', '10:28')], identifiant=ident, suivre=suivre)


# ================================================================ chapitre 1
def ecran_1():
    lst = vue('c1-liste', panneau_liste('Courriers', '1-80 / 151', ident='c1') + lat_courriers('c1-lat')
              + liste(COL_COURRIERS, [ligne_courrier('c1-l%d' % i, *l) for i, l in enumerate(LIGNES_COURRIERS)]),
              initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    circuit = ('<div class="masque" id="c1-circuit">%s%s%s</div>' % (
        sec_titre('Aperçu du circuit'), champ('Circuit prévu', v('Courrier entrant standard', True)),
        table([('Séquence', '70px'), ('Nom', '1fr'), ('SLA (heures)', '90px'), ('Étape initiale', '90px'), ('Étape finale', '80px')],
              [{'id': 'c1-s%d' % i, 'cellules': [c_num(str(i + 1)), n, c_num(s), c_html(case(i == 0)), c_html(case(i == 4))]}
               for i, (n, s) in enumerate(zip(ETAPES, ['4', '8', '4', '48', '24'])) ], ajouter=False)))
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v" id="c1-ref"></div>'
             + grille2([champ('Objet', entree('c1-objet')), champ('Contact expéditeur', '', aide=True),
                        champ('Expéditeur', entree('c1-exp')), champ('E-mail expéditeur', entree('c1-mail'), aide=True),
                        champ('Type', entree('c1-type')), champ('Service destinataire', entree('c1-service'))],
                       [champ('Statut', puce('Brouillon', 'gris', 'c1-statut'), aide=True), champ('Priorité', ''),
                        champ('Confidentialité', ''), champ('Date de réception', v(N1['date'])), champ('Responsable', '')])
             + circuit + onglets(['Documents', 'Historique'])
             + table([('Nom', '1fr'), ('Dossier', '90px'), ('Étiquettes', '90px'), ('Extension', '80px'), ('État', '80px'), ('Verrouillé', '70px')], []))
    apres = [bouton('c1-traiter', 'Traiter', 'prim'), bouton('c1-rejeter', 'Rejeter', 'second'),
             bouton('c1-comm2', 'Commenter', 'second'), bouton('c1-rep', 'Répondre', 'second', 'retour')]
    activites = ''.join(activite('Courrier %s — étape « Réception »' % N1['reference'], p[0],
                                 'Le courrier « %s » attend votre traitement à l\'étape « Réception ».' % N1['objet'],
                                 p[2], p[1], 'c1-act%d' % i) for i, p in enumerate([AGENT, ASSIST]))
    ch = chatter([message(AGENT[0], AGENT[2], 'Création d\'un enregistrement…', '10:28', 'c1-msg0'),
                  message(AGENT[0], AGENT[2], 'Courrier arrivé à l\'étape « Réception » — traitement attendu.', '10:29',
                          'c1-msg1', masque=True)], activites=activites, identifiant='c1-chatter')
    form = vue('c1-form', panneau_fiche('Courriers', 'Nouveau courrier', ref_id='c1-titre', sauver_id='c1-sauver')
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande([bouton('c1-lancer', 'Enregistrer et lancer le circuit', 'prim'), bouton('c1-comm', 'Commenter', 'second')],
                         '<span class="masque" id="c1-sb">%s</span>' % statusbar(ETAPES, 0, 'c1-etapes'), 'c1-bande', apres),
                   feuille(corps), ch))
    return fenetre('Courrier', ['Courriers', 'Espace documentaire'], [lst, form], AGENT[1], AGENT[2], ident='app-1')


CH1 = {
    'titre': 'Enregistrer un courrier', 'qui': 'Agent courrier',
    'sous': "Du pli reçu à un courrier référencé, en circulation dans son circuit.",
    'roles': ['Agent courrier'],
    'voix': "Premier chapitre : enregistrer un courrier. C'est le geste de l'agent courrier, à l'accueil.",
    'ecran': ecran_1(), 'vue_initiale': 'c1-liste',
    'etapes': [
        {'qui': "Étape 1 · L'agent courrier", 'titre': 'La liste des courriers',
         'texte': 'Entrants, internes, sortants : le panneau de gauche filtre par catégorie et par statut.',
         'voix': "L'agent courrier ouvre la liste des courriers. À gauche, le panneau filtre par catégorie, "
                 "entrant, interne ou sortant, et par statut, du brouillon jusqu'à l'archive.",
         'gestes': [anneau('#c1-lat', d=2.0), survol('#c1-l3', decale=0.2), pause(1.2), clic('#c1-nouveau'),
                    aller('c1-form')]},
        {'qui': "Étape 2 · L'agent courrier", 'titre': "Saisir l'essentiel",
         'texte': "Objet, expéditeur, adresse et type. Le type désigne le circuit que suivra le courrier.",
         'voix': "Elle saisit l'objet, l'expéditeur et son adresse, puis choisit le type. Le type désigne le circuit : "
                 "ici, le courrier entrant standard, en cinq étapes, chacune avec son délai en heures.",
         'gestes': [clic('#c1-objet', fx=0.3), saisir('c1-objet', N1['objet'], d=1.6),
                    clic('#c1-exp', fx=0.3), saisir('c1-exp', N1['expediteur'], d=1.3),
                    clic('#c1-mail', fx=0.3), saisir('c1-mail', N1['courriel'], d=1.0),
                    clic('#c1-type', fx=0.3), choisir('c1-type', 'Courrier entrant'),
                    montrer('#c1-circuit', d=0.5), anneau('#c1-circuit', d=2.2)]},
        {'qui': "Étape 3 · L'agent courrier", 'titre': 'Enregistrer et lancer le circuit',
         'texte': "Un clic : la référence est attribuée, le courrier entre à l'étape Réception, chacun est prévenu.",
         'voix': "Un clic sur Enregistrer et lancer le circuit. La référence est attribuée automatiquement, le courrier "
                 "passe de Brouillon à Nouveau, il entre à l'étape Réception, et chaque personne concernée reçoit "
                 "une activité à traiter.",
         'gestes': [clic('#c1-lancer'), cacher('#c1-circuit', d=0.3), texte('#c1-ref', N1['reference'], avec=True),
                    texte('#c1-titre', N1['reference'], avec=True), texte('#c1-msg0 .tx', 'Courrier créé', avec=True), etat('#c1-statut', 'Nouveau', 'gris', avec=True, decale=0.1),
                    cacher('#c1-bande-a', d=0.2), montrer('#c1-bande-b', y=0, avec=True), montrer('#c1-sb', y=0, avec=True),
                    anneau('#c1-ref', d=1.4), montrer('#c1-msg1', y=10), montrer('#c1-act0', y=10, decale=0.3),
                    montrer('#c1-act1', y=10, decale=0.3), anneau('#c1-sb', d=1.6)]},
    ],
}


# ================================================================ chapitre 2
def ecran_2():
    lignes = [l for l in LIGNES_COURRIERS if l[5] == 'En traitement']
    lst = vue('c2-liste', panneau_liste('Courriers', '1-%d / 54' % len(lignes), facettes=[('≡', 'En traitement')], ident='c2')
              + lat_courriers(None)
              + liste(COL_COURRIERS, [ligne_courrier('c2-l%d' % i, *l) for i, l in enumerate(lignes)]),
              initiale=True).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    stats = bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '1') + bouton_stat('Réponses', '1', 'histo')
    corps = ('<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v">%s</div>' % N2['reference']
             + grille2([champ('Objet', v(N2['objet'])), champ('Contact expéditeur', v(N2['expediteur'], True), aide=True),
                        champ('Expéditeur', v(N2['expediteur'])), champ('E-mail expéditeur', v(N2['courriel'], True), aide=True),
                        champ('Type', v('Courrier entrant', True)), champ('Service destinataire', v(N2['service'], True))],
                       [champ('Statut', puce('En traitement', 'gris'), aide=True), champ('Priorité', v(N2['priorite'], True)),
                        champ('Confidentialité', v(N2['confidentialite'], True)), champ('Date de réception', v(N2['date'])),
                        champ('Responsable', v(MANAGER[0], True))])
             + onglets(['Documents', 'Historique'], 0, 'c2-og')
             + '<div id="c2-docs">%s</div>' % table([('Nom', '1fr'), ('Dossier', '80px'), ('Extension', '70px'), ('Nombre de versions', '110px'), ('État', '80px')],
                                                      [{'id': 'c2-d1', 'cellules': [N2['objet'], '', 'pdf', c_num('1'), c_puce('Brouillon')]}], ajouter=False)
             + '<div class="masque" id="c2-histo">%s</div>' % table(
                 [('Étape', '100px'), ('Entrée le', '120px'), ('Sortie le', '120px'), ('Intervenant', '120px'), ('Transition', '90px'), ('Commentaire', '1fr')],
                 [{'id': 'c2-h0', 'cellules': ['Réception', '22/09/2026 08:50', '24/09/2026 15:51', AGENT[0], 'Qualifier', 'Transmis pour suite à donner.']},
                  {'id': 'c2-h1', 'cellules': ['Qualification', '24/09/2026 15:51', '27/09/2026 09:22', AGENT[0], 'Affecter', '']},
                  {'id': 'c2-h2', 'cellules': ['Affectation', '27/09/2026 09:22', '13/10/2026 10:29', ASSIST[0], 'Transmettre', 'Dossier complet, à instruire.']},
                  {'id': 'c2-h3', 'cellules': ['Traitement', '13/10/2026 10:29', '', MANAGER[0], '', '']}], ajouter=False))
    acts = ''.join(activite('Courrier %s — étape « %s »' % (N2['reference'], et), p[0],
                            'Le courrier « %s » attend votre traitement à l\'étape « %s ».' % (N2['objet'], et), p[2], p[1], masque=False)
                   for et, p in [('Affectation', ASSIST), ('Affectation', MANAGER)])
    ch = chatter([message(ASSIST[0], ASSIST[2], 'Courrier arrivé à l\'étape « Affectation » — traitement attendu.', '09:22'),
                  message(MANAGER[0], MANAGER[2], 'Affectation → <span class="lien">Traitement</span> (Étape courante)', '10:29',
                          'c2-msg', masque=True)], activites=acts, suivre='Suivi')
    fiche = vue('c2-fiche', panneau_fiche('Courriers', N2['reference'], '4 / 54', nouveau=False, boutons_stat=stats)
                + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                    bande([bouton('c2-traiter', 'Traiter', 'prim'), bouton('c2-rej', 'Rejeter', 'second'),
                           bouton('c2-com', 'Commenter', 'second'), bouton('c2-rep', 'Répondre', 'second', 'retour')],
                          statusbar(ETAPES, 2, 'c2-sb'), 'c2-bande'), feuille(corps), ch))
    # le courrier clos : ruban « TRAITÉ » et onglet Cachet
    corps_clos = (bandeau('Circuit terminé — courrier archivé.', 'vert')
                  + '<div class="ref-l">Référence <sup>?</sup></div><div class="ref-v">%s</div>' % CLOS['reference']
                  + grille2([champ('Objet', v(CLOS['objet'])), champ('Contact expéditeur', v(CLOS['expediteur'], True), aide=True),
                             champ('Expéditeur', v(CLOS['expediteur'])), champ('Type', v('Courrier entrant', True)),
                             champ('Service destinataire', v(CLOS['service'], True))],
                            [champ('Statut', puce('Archivé', 'gris'), aide=True), champ('Priorité', v('Haute', True)),
                             champ('Confidentialité', v('Interne', True)), champ('Date de réception', v(CLOS['date'])),
                             champ('Responsable', v(AGENT[0], True))])
                  + onglets(['Documents', 'Historique', 'Cachet'], 2)
                  + bandeau('✹ Courrier traité le 11/10/2026 à 09:36 — 2 visa(s).', 'vert', 'c2-cachet-b')
                  + table([('Étape', '120px'), ('Intervenant', '1fr'), ('Fonction', '1fr'), ('Le', '150px')],
                          [{'id': 'c2-v0', 'cellules': ['Réception', AGENT[0], 'Agent courrier', '05/10/2026 15:13']},
                           {'id': 'c2-v1', 'cellules': ['Archivage', ARCHI[0], 'Archiviste', '11/10/2026 09:36']}],
                          identifiant='c2-cachet', ajouter=False))
    clos = vue('c2-clos', panneau_fiche('Courriers', CLOS['reference'], '1 / 52', nouveau=False,
                                        boutons_stat=bouton_stat('Historique expéditeur', '', 'histo') + bouton_stat('Documents ECM', '1'))
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   bande([bouton('c2-rep2', 'Répondre', 'second', 'retour')], statusbar(ETAPES, 4, 'c2-sb2'), 'c2-bande2'),
                   feuille(corps_clos, ruban=('TRAITÉ', 'vert'), ruban_id='c2-ruban'),
                   chatter([message(ARCHI[0], ARCHI[2], 'Réception → <span class="lien">Archivage</span> (Étape courante)', '09:36')])))
    modale = assistant('c2-as', 'Action sur le courrier',
                       champ('Action', v('Traiter (valider / retourner)')) + champ('Transition', entree('c2-trans'))
                       + champ('Commentaire', entree('c2-comm', 'Commentaire (obligatoire pour le rejet ou les actions qui l\'exigent)')),
                       [('c2-ok', 'Confirmer', 'prim'), ('c2-annuler', 'Annuler', 'second')], haut=210, largeur=720)
    return fenetre('Courrier', MENUS_COURRIER, [lst, fiche, clos], MANAGER[1], MANAGER[2], calques=modale, ident='app-2')


CH2 = {
    'titre': 'Faire avancer le circuit', 'qui': 'Manager, assistante',
    'sous': "Chaque étape a ses rôles, ses délais et sa trace — jusqu'au cachet de traitement.",
    'roles': ['Assistante', 'Manager', 'Archiviste'],
    'voix': "Deuxième chapitre : faire avancer le circuit. Le courrier passe d'étape en étape, entre les mains des rôles habilités.",
    'ecran': ecran_2(), 'vue_initiale': 'c2-liste',
    'etapes': [
        {'qui': 'Étape 1 · Le manager', 'titre': 'Sa file de travail',
         'texte': "Le filtre « En traitement » ne garde que les courriers en circulation.",
         'voix': "Le manager du service filtre les courriers en traitement. Il ouvre la demande d'agrément fournisseur, "
                 "arrivée à l'étape Affectation.",
         'gestes': [anneau('#app-2 .o-cp .facette', d=1.3), survol('#c2-l3', decale=0.2), clic('#c2-l3', fx=0.35), aller('c2-fiche'),
                    anneau('#c2-sb', d=1.6)]},
        {'qui': 'Étape 2 · Le manager', 'titre': 'Traiter, en un seul geste',
         'texte': "Le bouton Traiter ouvre l'action : une transition, un commentaire, puis Confirmer.",
         'voix': "Le bouton Traiter ouvre l'action sur le courrier. Il choisit la transition, Transmettre, et laisse un "
                 "commentaire. Seuls les rôles habilités à l'étape peuvent la faire avancer ; un refus est tracé au journal d'audit.",
         'gestes': [clic('#c2-traiter'), ouvrir('c2-as'), clic('#c2-trans', fx=0.2), choisir('c2-trans', 'Transmettre'),
                    clic('#c2-comm', fx=0.2), saisir('c2-comm', 'Dossier complet, à instruire.', d=1.3), pause(0.3),
                    clic('#c2-ok'), fermer('c2-as'), classe('#c2-sb-2', retirer=['actif']),
                    classe('#c2-sb-3', ajouter=['actif'], avec=True), montrer('#c2-msg', y=10), anneau('#c2-sb-3', d=1.4)]},
        {'qui': 'Étape 3 · Le manager', 'titre': 'Un historique complet',
         'texte': "Pour chaque étape : l'entrée, la sortie, l'intervenant, la transition et le commentaire.",
         'voix': "L'onglet Historique garde la trace de chaque étape franchie : la date d'entrée et de sortie, "
                 "l'intervenant, la transition choisie et son commentaire.",
         'gestes': [clic('#c2-og-1'), classe('#c2-og-0', retirer=['actif'], avec=True), classe('#c2-og-1', ajouter=['actif'], avec=True),
                    cacher('#c2-docs', d=0.2), montrer('#c2-histo', y=10), anneau('#c2-histo', d=2.4)]},
        {'qui': "Étape 4 · L'archiviste", 'titre': 'Le cachet de traitement',
         'texte': "Au bout du circuit : courrier archivé, ruban « Traité », et les visas de chaque étape.",
         'voix': "Au bout du circuit, l'archiviste clôt le courrier : il est archivé et marqué Traité. "
                 "L'onglet Cachet récapitule les visas, avec l'étape, l'intervenant, sa fonction et la date.",
         'gestes': [aller('c2-clos'), anneau('#c2-ruban', d=1.4, decale=0.3), anneau('#c2-cachet-b', d=1.4), anneau('#c2-cachet', d=1.8)]},
    ],
}


# ================================================================ chapitre 3
def ecran_3():
    groupes = vue('c3-liste', panneau_liste('Espace documentaire', '1-4 / 4', facettes=[('≡', 'Dossier')], nouveau=False)
                  + liste([('Nom', '1fr'), ('Courrier', '110px'), ('Dossier', '90px'), ('Extension', '70px'), ('Nombre de versions', '100px'),
                           ('Confidentialité (héritée)', '150px'), ('État', '70px')],
                          [{'id': 'c3-g%d' % i, 'classe': 'grp', 'cellules': [c_html('<span class="ell"><b>▸</b> %s</span>' % e(n)), '', '', '', c_num(nb), '', '']}
                           for i, (n, nb) in enumerate([('Devis (38)', '49'), ('Factures (37)', '44'), ('Direction (35)', '44'), ('Aucun (73)', '85')])]),
                  initiale=True)
    aide = ('<div style="margin:8px 0;color:#495057;font-size:12px">Cliquez <b>Prévisualiser</b> (en-tête) pour ouvrir la dernière '
            'version dans un onglet — le PDF s\'affiche directement. Chaque version est aussi téléchargeable ou ouvrable ci-dessous.</div>')
    corps = ('<div class="titre-doc">Devis D-2026-3468 — mise en place d\'un ERP</div>'
             + grille2([champ('Courrier', v('COUR-2026-0107', True)), champ('Dossier', v('Devis', True)), champ('Étiquettes', '')],
                       [champ('Confidentialité (héritée)', v('Secret'), 'c3-conf'), champ('Nombre de versions', v('2')),
                        champ('Verrouillé', case(True), aide=True)])
             + aide + onglets(['Versions', 'ECM'])
             + table([('Version', '60px'), ('Nom du fichier', '1fr'), ('', '64px'), ('Télécharger', '84px'), ('Taille (octets)', '90px'),
                      ('Téléversé par', '110px'), ('Indexation', '80px')],
                     [{'id': 'c3-v2', 'cellules': ['v2', 'Devis_D-2026-3468_ERP_v2.pdf', c_html('<span class="lien">↗ Ouvrir</span>'), '1.12 Ko', c_num('1 145'), ASSIST[0], c_puce('En attente', 'jaune')]},
                      {'id': 'c3-v1', 'cellules': ['v1', 'Devis_D-2026-3468_ERP.pdf', c_html('<span class="lien">↗ Ouvrir</span>'), '1.22 Ko', c_num('1 251'), ASSIST[0], c_puce('En attente', 'jaune')]}],
                     identifiant='c3-versions', ajouter=False))
    fiche = vue('c3-fiche', panneau_fiche('Espace documentaire', "Devis D-2026-3468 — mise en place d'un ERP", '1 / 38', nouveau=False)
                + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                    bande([bouton('c3-prev', 'Prévisualiser', 'second', 'oeil'), bouton('c3-fin', 'Finaliser', 'prim')],
                          statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 'c3-sb'), 'c3-bande'),
                    feuille(corps, ruban=('VERROUILLÉ', 'gris'), ruban_id='c3-ruban')))
    return fenetre('Courrier', ['Courriers', 'Espace documentaire'], [groupes, fiche], ASSIST[1], ASSIST[2], ident='app-3')


CH3 = {
    'titre': 'Les pièces et leurs versions', 'qui': 'Assistante',
    'sous': "L'espace documentaire du courrier : chaque pièce, chaque version, sa confidentialité.",
    'roles': ['Assistante'],
    'voix': "Troisième chapitre : les pièces du courrier, et leurs versions.",
    'ecran': ecran_3(), 'vue_initiale': 'c3-liste',
    'etapes': [
        {'qui': "Étape 1 · L'assistante", 'titre': "L'espace documentaire",
         'texte': 'Toutes les pièces des courriers, regroupées par dossier : devis, factures, direction.',
         'voix': "L'espace documentaire réunit toutes les pièces jointes aux courriers, regroupées par dossier : "
                 "les devis, les factures, la direction. L'assistante ouvre un devis.",
         'gestes': [anneau('#c3-g0', d=1.2), anneau('#c3-g1', d=1.0), survol('#c3-g0'), clic('#c3-g0', fx=0.2), aller('c3-fiche')]},
        {'qui': "Étape 2 · L'assistante", 'titre': 'Une pièce, toutes ses versions',
         'texte': "Confidentialité héritée du courrier, versions empilées, pièce verrouillée : rien ne s'écrase.",
         'voix': "La pièce hérite de la confidentialité de son courrier, ici Secret. Ses versions s'empilent, la dernière en tête : "
                 "rien n'est écrasé. Verrouillée, elle ne se modifie plus. Prévisualiser ouvre le PDF directement.",
         'gestes': [anneau('#c3-conf', d=1.6, decale=0.3), anneau('#c3-versions', d=2.0), anneau('#c3-ruban', d=1.4),
                    curseur('#c3-prev'), anneau('#c3-prev', d=1.2)]},
    ],
}


# ================================================================ chapitre 4
LIGNES_DOCS = [
    ('DOC-2026-00359', 'Procédure de recette des documents', 'Procédure / instruction', 'Qualité et procédures', '', ARCHI[0], '1', 'Brouillon'),
    ('DOC-2026-00358', 'Attestation de non-redevance fiscale — Delta Équipements', 'Document générique', 'Achats et fournisseurs', ('Fiscal', 'rouge'), ASSIST[0], '1', 'Brouillon'),
    ('DOC-2026-00356', 'Registre de commerce — Groupe Horizon Services', 'Document générique', 'Achats et fournisseurs', ('Original papier', 'bleu'), AGENT[0], '1', 'Brouillon'),
    ('DOC-2026-00352', 'Relevé d\'identité bancaire — Delta Équipements', 'Document générique', 'Achats et fournisseurs', '', ASSIST[0], '1', 'Finalisé'),
    ('DOC-2026-00341', 'Contrat de maintenance — climatisation', 'Contrat', 'Juridique et contrats', ('À renouveler', 'jaune'), MANAGER[0], '2', 'Finalisé'),
    ('DOC-2026-00336', 'Plan de localisation — Groupe Horizon Services', 'Document générique', 'Achats et fournisseurs', ('Immobilier', 'jaune'), AGENT[0], '1', 'Brouillon'),
    ('DOC-2026-00320', 'Procès-verbal du conseil — septembre', 'Procès-verbal / compte rendu', 'Direction générale', '', MANAGER[0], '1', 'Finalisé'),
    ('DOC-2026-00311', 'Facture F-2026-6133 — télécommunications', 'Facture fournisseur', 'Finance et comptabilité', ('2026', 'jaune'), COMPTA[0], '1', 'Finalisé'),
    ('DOC-2026-00302', 'Procédure de gestion des congés', 'Procédure / instruction', 'Ressources humaines', ('Confidentiel RH', 'bleu'), ASSIST[0], '3', 'Finalisé'),
    ('DOC-2026-00298', 'Note de service — horaires d\'été', 'Document générique', 'Ressources humaines', '', ASSIST[0], '1', 'Archivé'),
    ('DOC-2026-00290', 'Cahier des charges — logiciel de paie', 'Document générique', 'Qualité et procédures', ('Appel d\'offres', 'rouge'), MANAGER[0], '2', 'Finalisé'),
    ('DOC-2026-00271', 'Facture F-2026-5980 — fournitures', 'Facture fournisseur', 'Finance et comptabilité', '', COMPTA[0], '1', 'Archivé'),
    ('DOC-2026-00255', 'Pièce de courrier — demande de devis', 'Pièce de courrier', 'Courrier / 2026', '', AGENT[0], '1', 'Finalisé'),
    ('DOC-2026-00240', 'Facture DOS-2026-1182 — fournitures', 'Facture fournisseur', 'Finance et comptabilité', '', COMPTA[0], '1', 'Archivé'),
    ('DOC-2026-00231', 'Attestation d\'assurance — locaux', 'Document générique', 'Finance et comptabilité', ('Assurance', 'jaune'), COMPTA[0], '1', 'Finalisé'),
    ('DOC-2026-00221', 'Bail commercial — agence', 'Contrat', 'Juridique et contrats', '', MANAGER[0], '1', 'Finalisé'),
    ('DOC-2026-00210', 'Candidature spontanée — comptable', 'Pièce de courrier', 'Courrier / 2026', ('Confidentiel RH', 'bleu'), AGENT[0], '1', 'Brouillon'),
    ('DOC-2026-00200', 'Facture F-2026-6314 — conseil juridique', 'Facture fournisseur', 'Finance et comptabilité', '', COMPTA[0], '1', 'Archivé'),
]

PLAN = [('Courrier', '', '177'), ('Direction générale', '', '6'), ('Ressources humaines / Dossiers du personnel', '', '4'),
        ('Juridique et contrats / Contrats fournisseurs', '', '2'), ('Juridique et contrats / Contentieux', 'AITE Courrier / Manager', '0'),
        ('Finance et comptabilité / Factures fournisseurs 2026', '', '13'), ('Finance et comptabilité / Banques et assurances', 'AITE Courrier / Comptabilité', '3'),
        ('Ressources humaines / Recrutements', 'AITE Courrier / Manager', '1'), ('Achats et fournisseurs / Agréments fournisseurs', '', '4'),
        ('Achats et fournisseurs / Appels d\'offres', '', '1'), ('Qualité et procédures / Procédures en vigueur', '', '8'),
        ('Direction générale / Procès-verbaux', '', '6'), ('Courrier / 2026', '', '177'), ('Courrier / 2026 / COUR-2026-0001', '', '1'),
        ('Courrier / 2026 / COUR-2026-0002', '', '1'), ('Courrier / 2026 / COUR-2026-0003', '', '1'), ('Courrier / 2026 / COUR-2026-0004', '', '2'),
        ('Courrier / 2026 / COUR-2026-0005', '', '1')]


def doc_bande(prefixe, apres=None):
    return bande([bouton(prefixe + '-circ', 'Lancer le circuit', 'prim', 'lecture'), bouton(prefixe + '-fin', 'Finaliser', 'prim'),
                  bouton(prefixe + '-res', 'Réserver', 'second', 'cadenas'), bouton(prefixe + '-prev', 'Prévisualiser', 'second', 'oeil'),
                  bouton(prefixe + '-corb', 'Corbeille', 'second', 'corbeille')],
                 statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, prefixe + '-sb'), prefixe + '-bande', apres)


ONGLETS_DOC = ['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Circuit', 'Description']


def ecran_4():
    lat = panneau_lateral([('▤ TYPES', [('Contrat', '3', False), ('Pièce de courrier', '177', False), ('Procédure / instruction', '13', False),
                                        ('Facture fournisseur', '12', False), ('Pièce du dossier du personnel', '3', False),
                                        ('Procès-verbal / compte rendu', '5', False), ('Document générique', '46', False)]),
                           ('◆ ÉTIQUETTES', [('2026', '5', False), ('Appel d\'offres', '6', False), ('Assurance', '4', False),
                                             ('Confidentiel RH', '3', False), ('Fiscal', '6', False), ('Original papier', '6', False),
                                             ('À renouveler', '3', False)])], 'c4-lat')
    cols = [('Référence', '108px'), ('Titre', '1fr'), ('Type', '120px'), ('Dossier de classement', '150px'), ('Étiquettes', '96px'),
            ('Propriétaire', '100px'), ('Vers.', '36px'), ('Statut', '72px')]
    lignes = [{'id': 'c4-l%d' % i, 'cellules': [r, t, ty, d, c_puce(*et) if et else '', pr, c_num(vs),
                                               c_puce(st, 'gris' if st != 'Finalisé' else 'vclair')]}
              for i, (r, t, ty, d, et, pr, vs, st) in enumerate(LIGNES_DOCS)]
    lst = vue('c4-liste', panneau_liste('Documents', '1-80 / 257', ident='c4') + lat + liste(cols, lignes), initiale=True
              ).replace('class="vue initiale"', 'class="vue initiale avec-lateral"', 1)
    plan = vue('c4-plan', panneau_liste('Plan de classement', '1-80 / 307')
               + liste([('Chemin', '1fr'), ('Lecture effective', '200px'), ('Documents', '80px')],
                       [{'id': 'c4-p%d' % i, 'cellules': [c_html('<span class="ell">⋮⋮&nbsp; %s</span>' % e(ch)),
                                                          c_puce(le, 'gris', 'c4-le%d' % i) if le else '', c_num(n)]}
                        for i, (ch, le, n) in enumerate(PLAN)]))
    versions = ('<div class="sec-t">Téléverser une nouvelle version</div>'
                + champ('Nouvelle version', bouton('c4-upload', 'Téléverser votre fichier', 'prim')
                        + '<span style="display:inline-block;margin-left:10px;width:300px">%s</span>' % entree('c4-fic'))
                + champ('Commentaire', entree('c4-vcomm'))
                + '<div style="margin:6px 0 8px">%s</div>' % bouton('c4-ajout', 'Ajouter la version', 'prim', 'televerser')
                + table([('Version', '60px'), ('Nom du fichier', '1fr'), ('Commentaire de version', '1fr'), ('Taille (octets)', '90px'),
                         ('Téléversé par', '100px'), ('', '130px')],
                        [{'id': 'c4-ver1', 'masque': True, 'cellules': ['v1', 'Procedure_courrier_entrant.pdf', 'Version initiale', c_num('48 210'),
                                                                        ARCHI[0], c_html('<span class="lien">◉ Ouvrir · ⤓ Télécharger</span>')]}],
                        ajouter=False))
    corps = ('<div class="ref-l">Référence</div><div class="ref-v moyen" id="c4-ref">Nouveau</div>'
             + '<div class="titre-doc">%s</div>' % entree('c4-titre', 'Titre du document')
             + grille2([champ('Type', entree('c4-type')), champ('Dossier de classement', entree('c4-dossier')), champ('Étiquettes', ''),
                        champ('Confidentialité', v('Interne'))], [champ('Propriétaire', v(ARCHI[0]))])
             + sec_titre('Métadonnées') + grille2([champ('Domaine', ''), champ('Date d\'application', '')],
                                                  [champ('Prochaine revue', ''), champ('Responsable du processus', '')])
             + onglets(ONGLETS_DOC) + versions)
    form = vue('c4-form', panneau_fiche('Documents', 'Nouveau', ref_id='c4-fil', sauver_id='c4-sauver')
               + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                   doc_bande('c4'), feuille(corps),
                   chatter([message(ARCHI[0], ARCHI[2], 'Création d\'un enregistrement…', '10:31', 'c4-m0'),
                            message(ARCHI[0], ARCHI[2], 'Document ECM créé', '10:31', 'c4-m1', masque=True),
                            message(ARCHI[0], ARCHI[2], 'Version v1 déposée.', '10:32', 'c4-m2', masque=True)], suivre='Suivi')))
    return fenetre('ECM', MENUS_ECM, [lst, plan, form], ARCHI[1], ARCHI[2], ident='app-4')


CH4 = {
    'titre': 'La gestion documentaire', 'qui': 'Archiviste',
    'sous': "AITE ECM : un fonds documentaire classé, typé, versionné, au-delà du courrier.",
    'roles': ['Archiviste', 'Tous les rôles selon leurs droits'],
    'voix': "Quatrième chapitre : la gestion documentaire. Aïte E C M organise tout le fonds documentaire de l'organisation, pas seulement le courrier.",
    'ecran': ecran_4(), 'vue_initiale': 'c4-liste',
    'etapes': [
        {'qui': "Étape 1 · L'archiviste", 'titre': 'Le fonds documentaire',
         'texte': "Chaque document a une référence, un type, un dossier de classement, des étiquettes et un statut.",
         'voix': "La liste des documents montre tout le fonds : chaque document porte une référence, un type, un dossier de classement, "
                 "des étiquettes, son propriétaire et son nombre de versions. À gauche, on filtre par type et par étiquette.",
         'gestes': [anneau('#c4-lat', d=1.8), survol('#c4-l4', decale=0.2), anneau('#c4-l4', d=1.6), pause(0.6)]},
        {'qui': "Étape 2 · L'archiviste", 'titre': 'Le plan de classement',
         'texte': "Une arborescence de dossiers ; certains réservent la lecture à un rôle, d'autres en héritent.",
         'voix': "Le plan de classement range les documents dans une arborescence de dossiers. La colonne Lecture effective montre "
                 "les dossiers dont la lecture est réservée à un rôle, comme le contentieux, réservé aux managers.",
         'gestes': [clic('#app-4-m2'), aller('c4-plan'), anneau('#c4-le4', d=1.6, decale=0.3), anneau('#c4-le6', d=1.3), pause(0.4)]},
        {'qui': "Étape 3 · L'archiviste", 'titre': 'Créer un document',
         'texte': "Titre, type et dossier de classement ; l'enregistrement attribue la référence.",
         'voix': "Pour créer un document, l'archiviste donne un titre, choisit le type, Procédure ou instruction, puis son dossier "
                 "de classement. À l'enregistrement, la référence est attribuée.",
         'gestes': [clic('#app-4-m0'), aller('c4-liste'), clic('#c4-nouveau', decale=0.2), aller('c4-form'),
                    clic('#c4-titre', fx=0.2), saisir('c4-titre', 'Procédure de traitement du courrier entrant', d=1.6),
                    clic('#c4-type', fx=0.2), choisir('c4-type', 'Procédure / instruction'),
                    clic('#c4-dossier', fx=0.2), choisir('c4-dossier', 'Qualité et procédures'),
                    clic('#c4-sauver'), texte('#c4-ref', 'DOC-2026-00360', avec=True),
                    texte('#c4-fil', 'Procédure de traitement du courrier entrant', avec=True), montrer('#c4-m1', y=10),
                    anneau('#c4-ref', d=1.3)]},
        {'qui': "Étape 4 · L'archiviste", 'titre': 'Déposer une version',
         'texte': "Chaque dépôt crée une version numérotée ; la précédente reste consultable.",
         'voix': "Il dépose ensuite le fichier, avec un commentaire, et clique sur Ajouter la version. Chaque dépôt crée une version "
                 "numérotée, scellée dans le journal de preuve ; les précédentes restent consultables et téléchargeables.",
         'gestes': [clic('#c4-upload'), choisir('c4-fic', 'Procedure_courrier_entrant.pdf'), clic('#c4-vcomm', fx=0.2),
                    saisir('c4-vcomm', 'Version initiale', d=0.9), clic('#c4-ajout'), montrer('#c4-ver1', y=10),
                    montrer('#c4-m2', y=10, avec=True), anneau('#c4-ver1', d=1.6)]},
    ],
}


# ================================================================ chapitre 5
def ecran_5():
    regles = vue('c5-regles', panneau_liste('Règles de conservation', '1-5 / 5')
                 + liste([('Code', '90px'), ('Libellé', '1fr'), ('Durée', '50px'), ('Unité', '60px'), ('Point de départ', '190px'),
                          ('Sort final', '150px'), ('Documents', '70px')],
                         [{'id': 'c5-r%d' % i, 'cellules': [c, l, c_num(d), 'années', p, c_puce(s, g, 'c5-sf%d' % i), c_num(n)]}
                          for i, (c, l, d, p, s, g, n) in enumerate([
                              ('OHADA-10', 'Pièces comptables — 10 ans (OHADA)', '10', 'Finalisation', 'Élimination', 'rouge', '12'),
                              ('CONTRAT-10', 'Contrats — 10 ans après la fin du contrat', '10', 'Date portée par une métadonnée', 'Revue avant décision', 'gris', '1'),
                              ('RH-5', 'Dossiers du personnel — 5 ans après le départ', '5', 'Archivage', 'Revue avant décision', 'gris', '3'),
                              ('PV-PERM', 'Procès-verbaux et actes de gouvernance — définitif', '1', 'Finalisation', 'Conservation définitive', 'vert', '5'),
                              ('PROC-3', 'Procédures — 3 ans après remplacement', '3', 'Archivage', 'Revue avant décision', 'gris', '14')])]),
                 initiale=True)
    gel_corps = ('<div class="titre-doc">Audit interne 2027</div>'
                 + grille2([champ('Référence du dossier (litige, audit)', v('AUD-2027')), champ('À la demande de', v("Comité d'audit")),
                            champ('Responsable', v(MANAGER[0]))], [champ('Posé le', v('02/10/2026'))])
                 + sec_titre('Motif') + '<div style="padding:4px 0 6px" id="c5-motif">Pièces réclamées par l\'auditeur.</div>'
                 + onglets(['Périmètre'])
                 + table([('Référence', '110px'), ('Titre', '1fr'), ('Dossier de classement', '200px'), ('Cycle de vie archivistique', '150px')],
                         [{'id': 'c5-gl%d' % i, 'cellules': list(x)} for i, x in enumerate([
                             ('DOC-2026-00311', 'Facture F-2026-6133 — télécommunications', 'Finance et comptabilité', 'Archive intermédiaire'),
                             ('DOC-2026-00290', 'Cahier des charges — logiciel de paie', 'Qualité et procédures', 'Sans politique'),
                             ('DOC-2026-00240', 'Facture DOS-2026-1182 — fournitures', 'Finance et comptabilité', 'Archive intermédiaire'),
                             ('DOC-2026-00231', 'Attestation d\'assurance — locaux', 'Finance et comptabilité', 'Utilité courante')])],
                         identifiant='c5-perim'))
    gel = vue('c5-gel', panneau_fiche('Gels juridiques', 'Audit interne 2027', '1 / 2', boutons_stat=bouton_stat('Documents gelés', '4', 'document'))
              + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                  bande([bouton('c5-lever', 'Lever le gel', 'orange')], statusbar(['Brouillon', 'Actif', 'Levé'], 1, 'c5-gsb'), 'c5-gb'),
                  feuille(gel_corps)))
    bord_corps = ('<div class="ref-v">BORD-2026-001</div>'
                  + grille2([champ('Date du bordereau', v('12/10/2026')), champ('Préparé par', v(ARCHI[0], True))],
                            [champ('Validé par', v('', identifiant='c5-valpar')), champ('Exécuté le', '')])
                  + table([('Référence', '110px'), ('Titre', '1fr'), ('Dossier', '170px'), ('Règle appliquée', '170px'), ('Échéance', '80px')],
                          [{'id': 'c5-b0', 'cellules': ['DOC-2026-00221', 'Facture F-2015-4037 — fournitures', 'Finance et comptabilité',
                                                        'Pièces comptables — 10 ans', '19/09/2025']},
                           {'id': 'c5-b1', 'cellules': ['DOC-2026-00200', 'Facture F-2014-6314 — conseil juridique', 'Finance et comptabilité',
                                                        'Pièces comptables — 10 ans', '19/09/2024']}], ajouter=False)
                  + sec_titre('Observations') + '<div style="padding:4px 0">Campagne d\'élimination annuelle.</div>')
    bord = vue('c5-bord', panneau_fiche("Bordereaux d'élimination", 'BORD-2026-001', '1 / 1')
               + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                   bande([bouton('c5-valider', 'Valider', 'prim'), bouton('c5-annuler', 'Annuler', 'second')],
                         statusbar(['Projet', 'À valider', 'Validé', 'Exécuté'], 1, 'c5-bsb'), 'c5-bb',
                         [bouton('c5-exec', "Exécuter l'élimination", 'prim'), bouton('c5-annuler2', 'Annuler', 'second')]),
                   feuille(bord_corps)))
    boite_corps = ('<div class="ref-l">Code</div><div class="ref-v moyen">BTE-00001</div><div class="titre-doc">PV du conseil 2019</div>'
                   + grille2([champ('Emplacement', v('Salle 3 — travée D — étagère 1'), 'c5-empl', aide=True)],
                             [champ('Emprunteur', v(ARCHI[0])), champ('Sortie le', v('06/10/2026')), champ('Retour prévu', v('06/11/2026'), 'c5-retour')])
                   + table([('Référence', '110px'), ('Titre', '1fr'), ('Cycle de vie archivistique', '200px'), ('Échéance', '80px')],
                           [{'id': 'c5-x%d' % i, 'cellules': list(x)} for i, x in enumerate([
                               ('DOC-2026-00255', 'Procédure de gestion des congés — v1', 'Utilité courante', ''),
                               ('DOC-2026-00240', 'Facture DOS-2026-1182 — fournitures', 'Archive intermédiaire', '16/09/2036'),
                               ('DOC-2026-00228', 'Plan de continuité d\'activité — v2', 'Utilité courante', ''),
                               ('DOC-2026-00221', 'Facture F-2015-4037 — fournitures', 'Échue — sort final à appliquer', '19/09/2025')])]))
    boite = vue('c5-boite', panneau_fiche('Archives physiques', 'PV du conseil 2019', '1 / 4')
                + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                    bande([bouton('c5-ranger', 'Ranger', 'prim')], statusbar(['En constitution', 'Rangée', 'Sortie (prêt)'], 2, 'c5-xsb'), 'c5-xb'),
                    feuille(boite_corps)))
    return fenetre('ECM', MENUS_ECM, [regles, gel, bord, boite], ARCHI[1], ARCHI[2], ident='app-5')


CH5 = {
    'titre': 'Conservation et archives', 'qui': 'Archiviste, manager',
    'sous': "Combien de temps garder, quoi éliminer, quoi protéger — et où est le papier.",
    'roles': ['Archiviste', 'Manager'],
    'voix': "Cinquième chapitre : la conservation et les archives. Combien de temps garder chaque document, que faire à l'échéance, "
            "et où se trouvent les originaux papier.",
    'ecran': ecran_5(), 'vue_initiale': 'c5-regles',
    'etapes': [
        {'qui': "Étape 1 · L'archiviste", 'titre': 'Les règles de conservation',
         'texte': "Une durée, un point de départ et un sort final : élimination, revue ou conservation définitive.",
         'voix': "Chaque règle de conservation fixe une durée, un point de départ, par exemple la finalisation, et un sort final : "
                 "l'élimination, une revue avant décision, ou la conservation définitive. Les pièces comptables, par exemple, "
                 "se gardent dix ans, comme le prévoit l'OHADA.",
         'gestes': [anneau('#c5-r0', d=1.8, decale=0.2), anneau('#c5-sf0', d=1.0), anneau('#c5-sf3', d=1.2), pause(0.5)]},
        {'qui': 'Étape 2 · Le manager', 'titre': 'Le gel juridique',
         'texte': "Un audit, un litige : les documents gelés ne peuvent être ni modifiés, ni mis à la corbeille, ni détruits.",
         'voix': "Un audit ou un litige s'annonce : on pose un gel juridique. Les documents de son périmètre ne peuvent plus être "
                 "modifiés, ni mis à la corbeille, ni détruits, même arrivés à échéance, jusqu'à la levée du gel.",
         'gestes': [aller('c5-gel'), anneau('#c5-gsb-1', d=1.2, decale=0.3), anneau('#c5-motif', d=1.0), anneau('#c5-perim', d=1.8)]},
        {'qui': 'Étape 3 · Le manager', 'titre': "Le bordereau d'élimination",
         'texte': "Préparé par l'archiviste, validé par le manager, puis exécuté : rien ne disparaît sans trace.",
         'voix': "Les documents échus sont rassemblés dans un bordereau d'élimination. L'archiviste le prépare, le manager le valide, "
                 "et seulement ensuite l'élimination est exécutée. Rien ne disparaît sans décision tracée.",
         'gestes': [aller('c5-bord'), anneau('#c5-b0', d=1.2, decale=0.2), clic('#c5-valider'), classe('#c5-bsb-1', retirer=['actif']),
                    classe('#c5-bsb-2', ajouter=['actif'], avec=True), texte('#c5-valpar', MANAGER[0], avec=True),
                    cacher('#c5-bb-a', d=0.2), montrer('#c5-bb-b', y=0, avec=True), anneau('#c5-exec', d=1.3)]},
        {'qui': "Étape 4 · L'archiviste", 'titre': 'Les archives physiques',
         'texte': "Chaque boîte a son emplacement, son contenu et ses prêts, avec la date de retour.",
         'voix': "Les originaux papier ne sont pas oubliés : chaque boîte d'archives a son emplacement, son contenu, "
                 "et ses sorties en prêt, avec l'emprunteur et la date de retour prévue.",
         'gestes': [aller('c5-boite'), anneau('#c5-empl', d=1.4, decale=0.2), anneau('#c5-xsb-2', d=1.2), anneau('#c5-retour', d=1.2)]},
    ],
}


# ================================================================ chapitre 6
def ecran_6():
    evts = [('13/10/2026 09:36:02', 'DOC-2026-00001', 'v1', ASSIST[0], 'Notification_de_changement_de_RIB.pdf', '49e1719cd115bca84b400f8a705a56dd853afa9f'),
            ('13/10/2026 09:36:02', 'DOC-2026-00001', 'v2', ASSIST[0], 'Notification_de_changement_de_RIB_v2.pdf', '5ccc0955730fb26f27215543ed67db853945a9a9'),
            ('13/10/2026 09:36:03', 'DOC-2026-00002', 'v1', AGENT[0], 'Demande_de_rendez-vous.pdf', '7b36600b8b85ea800a0b39de7d8270b80f48768f'),
            ('13/10/2026 09:36:03', 'DOC-2026-00003', 'v1', ASSIST[0], 'Mise_en_demeure_facture.pdf', 'e74c06c6008d18ad4ccc45e1e17fd4492e19b7fb'),
            ('13/10/2026 09:36:03', 'DOC-2026-00004', 'v1', ASSIST[0], 'Plainte_pour_nuisance_sonore.pdf', '284b59263bd97964ce6364bc4ffbaf9954fd2ba0'),
            ('13/10/2026 09:36:03', 'DOC-2026-00005', 'v1', ASSIST[0], 'Rappel_de_cotisations_sociales.pdf', 'f226119be9cb726afa3eb8f01c12f14b6301afdf'),
            ('13/10/2026 09:36:03', 'DOC-2026-00005', 'v2', ASSIST[0], 'Rappel_de_cotisations_sociales_v2.pdf', 'c02a64bab3eb474444430ee4b2f0b4174f01500d'),
            ('13/10/2026 09:36:04', 'DOC-2026-00007', 'v1', AGENT[0], 'Candidature_spontanee_comptable.pdf', 'b097727dbf5ebb03702cba493f2f510d6fdf8de6'),
            ('13/10/2026 09:36:04', 'DOC-2026-00008', 'v1', AGENT[0], 'Annexe_1.pdf', 'd4c24d79bbc2db711a6b69f3f57546308850a028'),
            ('13/10/2026 09:36:04', 'DOC-2026-00009', 'v1', AGENT[0], 'Mise_en_demeure_REF-2025-0240.pdf', 'a24d8c04f860b31aecde2118cf15e01968e98e62'),
            ('13/10/2026 09:36:04', 'DOC-2026-00009', 'v2', AGENT[0], 'Mise_en_demeure_REF-2025-0240_v2.pdf', '8f1c0c7ea592c92587257d50cf48095f4d96b3a6'),
            ('13/10/2026 09:36:04', 'DOC-2026-00010', 'v1', ASSIST[0], 'Candidature_spontanee.pdf', '4792e551a9e0e0c2446de50f1ed80165e412d3a5'),
            ('13/10/2026 09:36:04', 'DOC-2026-00011', 'v1', AGENT[0], 'Demande_de_partenariat.pdf', '5f35f43047591eb6a2d8ad7ffb666c50bd40aef2'),
            ('13/10/2026 09:36:04', 'DOC-2026-00012', 'v1', AGENT[0], 'Annexe_1.pdf', 'fed24dc4dad9b53c7181e72e4bd8084333c0afab'),
            ('13/10/2026 09:36:04', 'DOC-2026-00013', 'v1', ASSIST[0], 'Demande_de_devis_pour_travaux.pdf', '940dc543ede66713d2165a06ac02bc66646604fe'),
            ('13/10/2026 09:36:04', 'DOC-2026-00014', 'v1', AGENT[0], 'Demande_de_copie_de_contrat.pdf', '850cbcd9714e7ea4c2e21f42170643ced5e52be9'),
            ('13/10/2026 09:36:05', 'DOC-2026-00016', 'v1', ASSIST[0], 'Reclamation_sur_livraison.pdf', '1d22f46d1249e0cb2890cd8e87509ed331591160'),
            ('13/10/2026 09:36:05', 'DOC-2026-00017', 'v1', ASSIST[0], 'Annexe_1.pdf', '345ba0f96f5f985621f73d495a8d4a3fa31580a9')]
    journal = vue('c6-journal', panneau_liste('Journal de preuve', '1-80 / 481', nouveau=False)
                  + liste([('Horodatage', '128px'), ('Référence', '110px'), ('Événement', '108px'), ('Version', '48px'), ('Par', '100px'),
                           ('Détail', '1fr'), ('Empreinte du sceau', '260px')],
                          [{'id': 'c6-l%d' % i, 'cellules': [h, r, c_puce('Dépôt d\'une version'), ve, p, d, c_html('<span class="ell" style="font-family:monospace;font-size:11px">%s…</span>' % s)]}
                           for i, (h, r, ve, p, d, s) in enumerate(evts)]), initiale=True)
    sceau_corps = (grille2([champ('Référence', v('DOC-2026-00001')), champ('Document', v('Notification de changement de RIB', True)),
                            champ('Événement', v("Dépôt d'une version")), champ('Version', v('v1')), champ('Par', v(ASSIST[0], True))],
                           [champ('Horodatage', v('13/10/2026 09:36:02')), champ('Source', v('Interne (clé du serveur)')),
                            champ('Empreinte du sceau précédent', v('—'), 'c6-prec'),
                            champ('Empreinte du sceau', '<span style="font-family:monospace;font-size:11px;word-break:break-all">49e1719cd115bca84b400f8a705a56dd853afa9f4307999cc5feff8a2e85f4d4</span>', 'c6-emp')])
                   + sec_titre('Détail') + '<div>Notification_de_changement_de_RIB.pdf</div>'
                   + sec_titre('Données scellées')
                   + '<div style="font-family:monospace;font-size:11px;line-height:1.5" id="c6-donnees">{"detail": "Notification_de_changement_de_RIB.pdf", "document_id": 1, '
                     '"event": "version", "previous_hash": "", "reference": "DOC-2026-00001", "timestamp": "2026-10-13 09:36:02", "version": "v1"}</div>'
                   + sec_titre("Jeton d'horodatage") + '<div style="font-family:monospace;font-size:11px">16eace824f46c848147cb5d0ba8b35b3cd27a80c202cd11ca69fdd74ed9d9d29</div>')
    sceau = vue('c6-sceau', panneau_fiche('Journal de preuve', 'Sceau n° 1', '1 / 80', nouveau=False)
                + '<div class="o-corps"><div class="o-gauche" style="padding-top:12px">%s</div></div>' % feuille(sceau_corps))
    preuve = ('<div id="c6-preuve">' + grille2(
        [champ('Intégrité', puce('Non vérifiée', 'gris', 'c6-integ')), champ('Vérifiée le', v('', identifiant='c6-quand')),
         champ('Dernier sceau', '<span style="font-family:monospace;font-size:11px;word-break:break-all">4fa54b121540b539aa1a527695af5247790c09c41eb1d922e3fddb380c5cb0d3</span>')],
        [champ('Copie de préservation (PDF/A)', '')])
        + '<div style="margin:8px 0;display:flex;gap:6px">%s%s</div></div>' % (
            bouton('c6-verif', "Vérifier l'intégrité", 'prim'), bouton('c6-attest', "Attestation d'intégrité", 'second', 'pdf')))
    doc_corps = ('<div class="ref-l">Référence</div><div class="ref-v moyen">DOC-2026-00360</div>'
                 '<div class="titre-doc">Procédure de traitement du courrier entrant</div>'
                 + grille2([champ('Type', v('Procédure / instruction')), champ('Dossier de classement', v('Qualité et procédures')),
                            champ('Confidentialité', v('Interne'))], [champ('Propriétaire', v(ARCHI[0]))])
                 + onglets(ONGLETS_DOC, 4) + preuve)
    doc = vue('c6-doc', panneau_fiche('Documents', 'Procédure de traitement du courrier entrant', '1 / 80', boutons_stat=bouton_stat('Sceaux', '2', 'sceau'))
              + '<div class="o-corps"><div class="o-gauche">%s%s</div>%s</div>' % (
                  doc_bande('c6'), feuille(doc_corps),
                  chatter([message(ARCHI[0], ARCHI[2], 'Document ECM créé', '10:31'),
                           message(ARCHI[0], ARCHI[2], "Vérification d'intégrité : document intègre, chaîne de preuve cohérente.", '10:36',
                                   'c6-mv', masque=True)])))
    return fenetre('ECM', MENUS_ECM, [journal, sceau, doc], AUDIT[1], AUDIT[2], ident='app-6')


CH6 = {
    'titre': 'La valeur probante', 'qui': 'Audit, archiviste',
    'sous': "Chaque dépôt est scellé et horodaté ; l'intégrité se vérifie à tout moment.",
    'roles': ['Audit', 'Archiviste'],
    'voix': "Sixième chapitre : la valeur probante. Prouver qu'un document n'a pas changé depuis son dépôt.",
    'ecran': ecran_6(), 'vue_initiale': 'c6-journal',
    'etapes': [
        {'qui': "Étape 1 · L'auditeur", 'titre': 'Le journal de preuve',
         'texte': "Chaque événement est scellé : qui, quand, quel fichier, et l'empreinte du sceau.",
         'voix': "Le journal de preuve enregistre chaque événement du fonds : le dépôt d'une version, qui l'a fait, quand, sur quel "
                 "fichier. Chaque ligne est un sceau, avec son empreinte numérique.",
         'gestes': [anneau('#c6-l1', d=1.8, decale=0.2), survol('#c6-l0'), clic('#c6-l0', fx=0.4), aller('c6-sceau')]},
        {'qui': "Étape 2 · L'auditeur", 'titre': 'Une chaîne de sceaux',
         'texte': "Chaque sceau reprend l'empreinte du précédent et porte un jeton d'horodatage.",
         'voix': "Chaque sceau reprend l'empreinte du sceau précédent : les sceaux forment une chaîne, et la moindre retouche la "
                 "romprait. Les données scellées et le jeton d'horodatage sont conservés avec lui.",
         'gestes': [anneau('#c6-emp', d=1.6, decale=0.2), anneau('#c6-prec', d=1.4), anneau('#c6-donnees', d=1.6)]},
        {'qui': "Étape 3 · L'archiviste", 'titre': "Vérifier l'intégrité",
         'texte': "Un clic recalcule les empreintes : document intègre, chaîne cohérente ; une attestation se télécharge.",
         'voix': "Sur le document, l'onglet Preuve. Un clic sur Vérifier l'intégrité recalcule les empreintes : le document est "
                 "intègre, la chaîne de preuve est cohérente. Une attestation d'intégrité peut être remise à un tiers.",
         'gestes': [aller('c6-doc'), anneau('#c6-preuve', d=1.2, decale=0.2), clic('#c6-verif'), etat('#c6-integ', 'Intègre', 'vert', decale=0.2),
                    texte('#c6-quand', '13/10/2026 10:36:57', avec=True), montrer('#c6-mv', y=10), anneau('#c6-integ', d=1.0),
                    anneau('#c6-attest', d=1.2)]},
    ],
}


# ================================================================ chapitre 7
def ecran_7():
    pieces = table([('Pièce', '150px'), ('Type attendu', '1fr'), ('Obligatoire', '70px'), ('Document fourni', '1fr'), ('Validée', '60px'),
                    ('État', '90px'), ('', '70px')],
                   [{'id': 'c7-p0', 'cellules': [c_html('<span class="ell" style="color:#1E7E44">Pièce d\'identité</span>'), 'Pièce du dossier du personnel',
                                                 c_html(case(True)), 'Pièce d\'identité — A. Nkodo', c_html(interrupteur(True)), c_puce('Validée', 'vert'),
                                                 c_html('<span class="lien">◉ Ouvrir</span>')]},
                    {'id': 'c7-p1', 'cellules': [c_html('<span class="ell" style="color:#DC3545">Diplômes et attestations</span>'), 'Pièce du dossier du personnel',
                                                 c_html(case(True)), '', c_html(interrupteur(False)), c_puce('Manquante', 'rouge', 'c7-manq'),
                                                 c_html('<span class="lien">⤒ Fournir</span>')]},
                    {'id': 'c7-p2', 'cellules': ['Contrat de travail signé', 'Contrat', c_html(case(True)), 'Contrat de travail signé — A. Nkodo',
                                                 c_html(interrupteur(False)), c_puce('Fournie', 'info'), c_html('<span class="lien">◉ Ouvrir</span>')]},
                    {'id': 'c7-p3', 'cellules': ['Certificat médical d\'aptitude', 'Pièce du dossier du personnel', c_html(case(False)),
                                                 'Certificat médical — A. Nkodo', c_html(interrupteur(False)), c_puce('Fournie', 'info'),
                                                 c_html('<span class="lien">◉ Ouvrir</span>')]}], identifiant='c7-pieces')
    dos_corps = ('<div class="ref-l">Référence</div><div class="ref-v moyen">DOS-2026-0040</div>'
                 '<div class="titre-doc">Dossier du personnel — Armel Nkodo</div>'
                 + grille2([champ('Type de dossier', v('Dossier du personnel')), champ('Tiers concerné', v('Armel Nkodo')),
                            champ('Responsable', v(COMPTA[0]))],
                           [champ('Échéance du dossier', v('20/10/2026')), champ('Complétude (%)', barre(75), 'c7-compl'),
                            champ('Pièces obligatoires manquantes', v('1')), champ('Circuit — statut', v('Non lancé'))])
                 + sec_titre('Métadonnées') + grille2([champ('Matricule', v('MAT-1991')), champ("Date d'embauche", v('03/02/2019'))],
                                                      [champ('Poste', v('Technicien réseau'))])
                 + onglets(['Pièces', 'Circuit', 'Description']) + pieces)
    dossier = vue('c7-dossier', panneau_fiche('Dossiers métier', 'Dossier du personnel — Armel Nkodo', '1 / 40', boutons_stat=bouton_stat('Documents', '3'))
                  + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                      bande([bouton('c7-ouvrir', 'Ouvrir le dossier', 'prim'), bouton('c7-ann', 'Annuler', 'second'),
                             bouton('c7-regen', 'Régénérer les pièces', 'second')],
                            statusbar(['Brouillon', 'En cours', 'Clôturé'], 0, 'c7-sb'), 'c7-b'), feuille(dos_corps)), initiale=True)
    part_corps = (grille2([champ('Libellé', v('Contrat à signer — Groupe Horizon Services')),
                           champ('Document', v('Contrat de partenariat — Groupe Horizon Services')),
                           champ('Destinataire (info)', v(demo.TIERS_COURRIEL)),
                           champ('Lien', '<span class="entree" style="border:1px solid #DEE2E6;border-radius:4px;padding:0 6px;font-size:11.5px" id="c7-lien">'
                                         'https://courrier.aite-demo.test/ecm/share/UXM0cocIvy5YvvYULGRepP3p</span>')],
                          [champ('Expire le', v('31/10/2026'), 'c7-exp'), champ('Téléchargements max.', v('3'), 'c7-max', aide=True),
                           champ('Consultation seule', case(False), aide=True), champ('Filigrane', case(True), 'c7-fil', aide=True),
                           champ('Texte du filigrane', v('Diffusion contrôlée — AITE Démo'))])
                  + sec_titre('Suivi') + champ('Accès', v('1')) + champ('Dernier accès', v('13/10/2026 10:00:30')) + champ('Valide', case(True)))
    partage = vue('c7-partage', panneau_fiche('Partages externes', 'Contrat à signer — Groupe Horizon Services', '1 / 28')
                  + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                      bande([bouton('c7-desact', 'Désactiver', 'rouge')], '', 'c7-pb'), feuille(part_corps)))
    return fenetre('ECM', MENUS_ECM, [dossier, partage], COMPTA[1], COMPTA[2], ident='app-7')


CH7 = {
    'titre': 'Dossiers métier et partages', 'qui': 'Comptabilité, manager',
    'sous': "Des dossiers qui savent ce qui leur manque ; des liens externes sous contrôle.",
    'roles': ['Comptabilité', 'Manager'],
    'voix': "Septième chapitre : les dossiers métier, et le partage de documents avec l'extérieur.",
    'ecran': ecran_7(), 'vue_initiale': 'c7-dossier',
    'etapes': [
        {'qui': 'Étape 1 · La comptabilité', 'titre': 'Un dossier qui se sait incomplet',
         'texte': "Le type de dossier fixe les pièces attendues ; la complétude se calcule, la pièce manquante ressort.",
         'voix': "Un dossier métier, ici un dossier du personnel, connaît les pièces qu'il doit contenir. Sa complétude se calcule "
                 "toute seule : soixante-quinze pour cent, et la pièce obligatoire manquante ressort en rouge, prête à être fournie.",
         'gestes': [anneau('#c7-compl', d=1.6, decale=0.3), anneau('#c7-pieces', d=1.6), anneau('#c7-manq', d=1.4), pause(0.4)]},
        {'qui': 'Étape 2 · Le manager', 'titre': 'Partager sans perdre le contrôle',
         'texte': "Un lien qui expire, un nombre de téléchargements limité, un filigrane, et une désactivation en un clic.",
         'voix': "Pour envoyer un document à l'extérieur, on crée un partage : un lien qui expire, un nombre de téléchargements limité, "
                 "un filigrane sur le document. Chaque accès est compté, et le lien se désactive en un clic.",
         'gestes': [aller('c7-partage'), anneau('#c7-lien', d=1.4, decale=0.3), anneau('#c7-exp', d=1.0), anneau('#c7-max', d=1.0),
                    anneau('#c7-fil', d=1.0), anneau('#c7-desact', d=1.2)]},
    ],
}


# ================================================================ chapitre 8
def ecran_8():
    compte = '<div class="p-vue initiale" id="c8-compte">%s</div>' % (
        '<div class="p-titre">Mon compte</div>'
        '<div class="p-carte"><b>Connexion et sécurité</b><i>Configurez vos paramètres de connexion</i></div>'
        '<div class="p-carte" id="c8-mes"><b>Mes courriers</b><i>3 demande(s) suivie(s) — déposez-en une nouvelle</i></div>')
    lignes = [('COUR-2026-0009', CLOS['objet'], '05/10/2026', 'Traitée'), ('COUR-2026-0098', 'Réclamation sur la facture de août', '28/09/2026', 'En traitement'),
              ('COUR-2026-0071', 'Demande de copie de contrat', '12/09/2026', 'Traitée')]
    liste_p = '<div class="p-vue" id="c8-liste">%s</div>' % (
        p_fil('Courriers') + p_entete()
        + '<div style="display:flex;align-items:center;margin:14px 0 8px"><div class="p-titre" style="margin:0">Mes courriers</div>'
          '<span class="bt prim" id="c8-nouvelle" style="margin-left:auto;background:#714B67">+ Nouvelle demande</span></div>'
        + '<div class="p-liste"><div class="tt"><span>Référence</span><span>Objet</span><span></span><span>Date</span><span>Statut</span></div>%s</div>'
        % ''.join('<div class="tl" id="c8-l%d"><span class="lien">%s</span><span class="ell">%s</span><span></span><span>%s</span><span>%s</span></div>'
                  % (i, e(r), e(o), e(d), puce(s, 'vclair' if s == 'Traitée' else 'bleu')) for i, (r, o, d, s) in enumerate(lignes)))
    form = '<div class="p-vue" id="c8-form">%s</div>' % (
        p_fil('Courriers', 'Nouvelle demande') + p_entete()
        + '<div class="p-titre" style="margin:12px 0 2px">Nouvelle demande</div>'
          '<div style="font-size:11.5px;color:#495057">Les champs marqués d\'une étoile sont obligatoires</div>'
        + '<div class="p-form"><div class="pl">Objet <em>*</em></div>%s<div class="pl">Nature de la demande <em>*</em></div>%s'
          '<div class="pl">Votre message</div><div class="zone" id="c8-msg"><span class="ph" id="c8-msg-ph">Décrivez votre demande…</span>'
          '<span class="val" id="c8-msg-val"></span></div><div class="pl">Pièces jointes</div>'
          '<div class="p-depot" id="c8-depot">%s<span id="c8-pj"><span class="ph" id="c8-pj-ph">Glissez vos fichiers ici, ou cliquez pour les choisir — <b>plusieurs à la fois</b>.</span><span class="val" id="c8-pj-val"></span></span></div>'
          '<div class="p-bts"><span class="bt prim" id="c8-envoyer">%s Envoyer la demande</span><span class="bt second">Annuler</span></div></div>'
        % (entree('c8-objet', "En quelques mots, l'objet de votre demande"), entree('c8-nature', '— Choisir —'),
           ICONES['nuage'], '<span class="ic" style="display:inline-flex;width:12px">%s</span>' % ICONES['envoi']))
    recue = '<div class="p-vue" id="c8-recue">%s</div>' % (
        p_fil('Courriers', 'Réclamation sur la facture de septembre') + p_entete()
        + bandeau('✓ Votre demande a bien été reçue. Sa référence vous sera communiquée dès sa prise en charge ; vous la retrouverez sur cette page.', 'vert', 'c8-ok')
        + '<div class="p-suivi"><div class="sh">Demande reçue %s</div><div class="sc"><b>Objet :</b> Réclamation sur la facture de septembre<br>'
          '<b>Nature :</b> Courrier entrant</div></div>' % puce('Reçue', 'gris'))
    suivi = '<div class="p-vue" id="c8-suivi">%s</div>' % (
        p_fil('Courriers', CLOS['reference']) + p_entete()
        + '<div class="p-suivi"><div class="sh">%s %s</div><div class="sc"><b>Objet :</b> %s<br><b>Nature :</b> Courrier entrant'
          '<div style="font-size:14px;margin:10px 0 2px">Avancement</div><div class="p-av" id="c8-av">%s</div>'
          '<div style="font-size:14px;margin:10px 0 2px">Cachet de traitement</div><div class="cachet" id="c8-cachet"><div class="ch"><span>● DEMANDE TRAITÉE</span><span>11/10/2026</span></div>'
          '<div class="l"><b>Réception</b><span>Agent courrier</span><span>05/10/2026</span></div>'
          '<div class="l"><b>Archivage</b><span>Archiviste</span><span>11/10/2026</span></div></div>'
          '<div style="font-size:14px;margin:10px 0 4px">Pièces du dossier</div>'
          '<span class="stat" style="border-radius:4px">%s Demande_de_devis_pour_travaux.pdf</span></div></div>'
        % (CLOS['reference'], puce('Traitée', 'vclair'), CLOS['objet'],
           ''.join('<div><i></i>%s</div>' % n for n in ETAPES[:4]) + '<div class="cours"><i></i>Archivage <span class="ec">Étape en cours</span></div>',
           ICONES['trombone'].replace('<svg', '<svg width="12" height="12"')))
    return portail([compte, liste_p, form, recue, suivi], demo.TIERS, ident='app-8')


CH8 = {
    'titre': 'Le portail des tiers', 'qui': 'Tiers externe',
    'sous': "Vos correspondants déposent leurs demandes en ligne et suivent leur traitement.",
    'roles': ['Tiers externe (portail)'],
    'voix': "Huitième chapitre : le portail. Vos correspondants externes déposent leurs demandes en ligne, et en suivent le traitement.",
    'ecran': ecran_8(), 'vue_initiale': 'c8-compte',
    'etapes': [
        {'qui': 'Étape 1 · Le tiers', 'titre': 'Son espace, ses courriers',
         'texte': "Depuis son compte, le tiers retrouve toutes ses demandes et leur statut, dans un vocabulaire clair.",
         'voix': "Depuis son espace personnel, le tiers ouvre Mes courriers. Il y retrouve toutes ses demandes, avec un statut "
                 "rédigé pour lui : reçue, en traitement, traitée.",
         'gestes': [anneau('#c8-mes', d=1.2, decale=0.3), clic('#c8-mes', fx=0.3), aller('c8-liste'), anneau('#c8-l1', d=1.4)]},
        {'qui': 'Étape 2 · Le tiers', 'titre': 'Déposer une demande',
         'texte': "Objet, nature, message et pièces jointes, plusieurs à la fois ; puis Envoyer la demande.",
         'voix': "Il dépose une nouvelle demande : l'objet, la nature, son message, et ses pièces jointes, plusieurs à la fois. "
                 "À l'envoi, la demande arrive directement dans le courrier entrant de l'organisation.",
         'gestes': [clic('#c8-nouvelle'), aller('c8-form'), clic('#c8-objet', fx=0.2), saisir('c8-objet', 'Réclamation sur la facture de septembre', d=1.5),
                    clic('#c8-nature', fx=0.2), choisir('c8-nature', 'Courrier entrant'), clic('#c8-msg', fx=0.2, fy=0.3),
                    saisir('c8-msg', 'Le montant facturé ne correspond pas au devis accepté.', d=1.6),
                    clic('#c8-depot'), choisir('c8-pj', 'Facture_septembre.pdf'), clic('#c8-envoyer'), aller('c8-recue'),
                    anneau('#c8-ok', d=1.4)]},
        {'qui': 'Étape 3 · Le tiers', 'titre': 'Suivre, jusqu\'au cachet',
         'texte': "L'avancement étape par étape, puis le cachet de traitement et les pièces du dossier.",
         'voix': "Il suit ensuite l'avancement, étape par étape. Une fois sa demande traitée, il voit le cachet de traitement, "
                 "avec les visas et leurs dates, et les pièces du dossier.",
         'gestes': [aller('c8-suivi'), anneau('#c8-av', d=1.8, decale=0.3), anneau('#c8-cachet', d=2.0)]},
    ],
}


# ================================================================ chapitre 9
def ecran_9():
    lignes = [('13/10/2026 10:31:07', ARCHI[0], 'Création document', ('Information', 'gris'), 'DOC-2026-00360', 'Interface', 'Type : Procédure / instruction'),
              ('13/10/2026 10:29:41', MANAGER[0], 'Transmettre', ('Succès', 'vert'), 'COUR-2026-0014', 'Interface', 'Vers l\'étape « Traitement ».'),
              ('13/10/2026 10:29:01', AGENT[0], 'Création courrier', ('Information', 'gris'), 'COUR-2026-0141', 'Interface', 'Lancement du circuit « Courrier entrant standard ».'),
              ('13/10/2026 10:25:50', demo.TIERS, 'Demande déposée', ('Information', 'gris'), 'Réclamation sur la facture…', 'Système', 'Tiers : %s — Objet : Réclamation sur la facture de septembre' % demo.TIERS),
              ('13/10/2026 10:21:12', AGENT[0], 'Tentative non autorisée', ('Erreur', 'rouge'), 'COUR-2026-0016', 'Interface', 'Action « Transmettre » refusée.'),
              ('13/10/2026 10:19:02', MANAGER[0], 'Soumettre direction', ('Succès', 'vert'), 'COUR-2026-0081', 'Interface', 'Vers l\'étape « Validation direction ».'),
              ('13/10/2026 10:04:46', ARCHI[0], 'Archiver', ('Succès', 'vert'), 'COUR-2026-0011', 'Interface', 'Vers l\'étape « Archivage ».'),
              ('13/10/2026 10:00:30', 'Utilisateur public', 'Accès par lien de partage', ('Information', 'gris'), 'DOC-2026-00251', 'Système', 'Lien UXM0cocI — accès n°1'),
              ('13/10/2026 10:00:30', ARCHI[0], 'Ajout de version', ('Information', 'gris'), 'DOC-2026-00357', 'API', 'v2 — recette_v2.pdf — sha256 7a7eab677175…'),
              ('13/10/2026 10:00:29', ARCHI[0], 'Ajout de version', ('Information', 'gris'), 'DOC-2026-00257', 'WebDAV', 'v2 — Attestation ANR.pdf — sha256 38487076acc4…'),
              ('13/10/2026 09:58:33', demo.TIERS, 'Demande déposée', ('Information', 'gris'), 'Réclamation sur la facture…', 'Système', 'Tiers : %s' % demo.TIERS),
              ('13/10/2026 09:53:14', ARCHI[0], 'Création document', ('Information', 'gris'), 'DOC-2026-00356', 'Interface', 'Type : Procédure / instruction'),
              ('13/10/2026 09:51:45', MANAGER[0], 'Transmettre', ('Succès', 'vert'), 'COUR-2026-0011', 'Interface', 'Vers l\'étape « Traitement ».'),
              ('13/10/2026 09:44:10', ASSIST[0], 'Affecter', ('Succès', 'vert'), 'COUR-2026-0014', 'Interface', 'Vers l\'étape « Affectation ».'),
              ('13/10/2026 09:40:02', AGENT[0], 'Qualifier', ('Succès', 'vert'), 'COUR-2026-0140', 'Interface', 'Vers l\'étape « Qualification ».'),
              ('13/10/2026 09:36:56', ARCHI[0], 'Archiver', ('Succès', 'vert'), 'COUR-2026-0009', 'Interface', 'Vers l\'étape « Archivage ».'),
              ('13/10/2026 09:30:41', AGENT[0], 'Création courrier', ('Information', 'gris'), 'COUR-2026-0139', 'Interface', 'Lancement du circuit « Courrier entrant standard ».'),
              ('13/10/2026 09:22:18', ASSIST[0], 'Transmettre', ('Succès', 'vert'), 'COUR-2026-0005', 'Interface', 'Vers l\'étape « Traitement ».')]
    audit = vue('c9-audit', panneau_liste("Journal d'audit", '1-80 / 1 639', nouveau=False)
                + liste([('Date/heure', '120px'), ('Utilisateur', '110px'), ('Action', '120px'), ('Type', '80px'), ('Objet', '120px'),
                         ('Source', '64px'), ('Détails', '1fr')],
                        [{'id': 'c9-l%d' % i, 'cellules': [d, c_html('<span class="ell">%s</span>' % e(u)), a, c_puce(t[0], t[1]), o, s, det]}
                         for i, (d, u, a, t, o, s, det) in enumerate(lignes)]), initiale=True)
    vide = ('<div class="o-vide" id="c9-vide"><div class="ill"><i></i></div><div class="vt">Créez votre premier courrier</div>'
            '<div class="vs">Utilisez le panneau latéral pour filtrer par catégorie<br>(entrants / sortants / internes) ou par statut (brouillons, …).</div></div>')
    lst = vue('c9-agent', panneau_liste('Courriers', '0 / 0', ident='c9', recherche_id='c9-rech')
              + lat_courriers(None) + liste(COL_COURRIERS, [], vide=vide)).replace('class="vue"', 'class="vue avec-lateral"', 1)
    return fenetre('Courrier', MENUS_COURRIER + ['Audit'], [audit, lst], AUDIT[1], AUDIT[2], ident='app-9')


CH9 = {
    'titre': 'Sécurité et traçabilité', 'qui': 'Audit, agent courrier',
    'sous': "Huit rôles, une confidentialité respectée partout, et la trace de chaque action.",
    'roles': ['Audit', 'Agent courrier'],
    'voix': "Neuvième chapitre : la sécurité et la traçabilité. Qui a fait quoi, et qui peut voir quoi.",
    'ecran': ecran_9(), 'vue_initiale': 'c9-audit',
    'etapes': [
        {'qui': "Étape 1 · L'auditeur", 'titre': "Le journal d'audit",
         'texte': "Chaque action, son auteur, son objet et sa source : interface, système, API ou lecteur réseau.",
         'voix': "Le journal d'audit trace chaque action : création, transition, dépôt de version, accès par un lien de partage. "
                 "On y lit l'auteur, l'objet et la source : l'interface, le portail, l'A P I ou le lecteur réseau. "
                 "Les refus y figurent aussi.",
         'gestes': [anneau('#c9-l1', d=1.4, decale=0.2), anneau('#c9-l4', d=1.6), anneau('#c9-l8', d=1.2), anneau('#c9-l9', d=1.2)]},
        {'qui': "Étape 2 · Un agent courrier", 'titre': 'Le cloisonnement',
         'texte': "Un agent cherche un courrier « Secret » d'un autre service : il n'apparaît tout simplement pas.",
         'voix': "Le cloisonnement, maintenant. Un agent courrier cherche un courrier confidentiel destiné à un autre service. "
                 "Le résultat est vide : un courrier secret n'apparaît qu'aux personnes autorisées, dans les listes comme dans les recherches.",
         'gestes': [aller('c9-agent'), clic('#c9-rech', fx=0.4), saisir('c9-rech-q', 'Secret', d=0.6), pause(0.4),
                    anneau('#c9-vide', d=2.0)]},
    ],
}


# =============================================================== chapitre 10
def ecran_10():
    tuiles = ''.join(tuile(*t) for t in [('c10-t0', '0', 'En cours', '#3B66E0', 'boite'), ('c10-t1', '0', 'En retard (SLA)', '#E5484D', 'alerte'),
                                         ('c10-t2', '0', 'Reçus ce mois', '#1E9E52', 'telecharge'), ('c10-t3', '0', 'Archivés ce mois', '#14A39A', 'archive'),
                                         ('c10-t4', '0 %', 'Taux de rejet', '#F0A020', 'croix'), ('c10-t5', '0 j', 'Délai moyen de traitement', '#6A5BD6', 'montre')])
    br = barres([('c10-b%d' % i, l, str(n), n / 12.0) for i, (l, n) in enumerate([
        ('Qualification', 12), ('Diffusion', 10), ('Réception (Courrier entrant)', 8), ('Contrôle', 4), ('Validation', 4),
        ('Accusé réception', 4), ('Analyse commerciale', 4), ('Affectation', 3), ('Contrôle administratif', 3), ('Comptabilité', 3),
        ('Validation direction', 3), ('Traitement', 2), ('Signature', 2), ('Visa DG', 1)])])
    tb = ('<div class="tb"><div class="tb-h">◔ Tableau de bord — Courrier<span class="d"><span class="bt second petit">↻ Actualiser</span>'
          '<span class="bt prim petit">▥ Analyse détaillée</span></span></div><div class="tuiles">%s</div>'
          '<div class="tb-bas"><div class="tb-carte" id="c10-charge"><div class="ct">Charge par étape (en cours)</div>%s</div>'
          '<div class="tb-carte" id="c10-rep"><div class="ct">Répartition par catégorie</div><div class="rep"><span>Entrant</span><b>56</b></div>'
          '<div class="rep"><span>Sortant</span><b>56</b></div><div class="rep"><span>Interne</span><b>28</b></div></div></div></div>' % (tuiles, br))
    return fenetre('Courrier', MENUS_COURRIER, [vue('c10-tb', tb, initiale=True)], MANAGER[1], MANAGER[2], ident='app-10')


CH10 = {
    'titre': "Piloter l'activité", 'qui': 'Manager',
    'sous': "Le tableau de bord du courrier : volumes, retards, délais, charge par étape.",
    'roles': ['Manager', 'Administrateur'],
    'voix': "Dixième chapitre : piloter l'activité.",
    'ecran': ecran_10(), 'vue_initiale': 'c10-tb',
    'etapes': [
        {'qui': 'Étape 1 · Le manager', 'titre': "L'activité d'un coup d'œil",
         'texte': "Courriers en cours, en retard sur leur délai, reçus, archivés, taux de rejet et délai moyen.",
         'voix': "Le tableau de bord donne l'essentiel d'un coup d'œil : les courriers en cours, ceux qui dépassent leur délai, "
                 "les reçus et les archivés du mois, le taux de rejet et le délai moyen de traitement.",
         'gestes': [compter('#c10-t0-n', 0, 77, d=1.0), compter('#c10-t1-n', 0, 23, d=0.9, avec=True, decale=0.15),
                    compter('#c10-t2-n', 0, 21, d=0.9, avec=True, decale=0.15), compter('#c10-t3-n', 0, 52, d=0.9, avec=True, decale=0.15),
                    compter('#c10-t4-n', 0, 17.5, d=0.9, decimales=1, apres=' %', avec=True, decale=0.15),
                    compter('#c10-t5-n', 0, 6.1, d=0.9, decimales=1, apres=' j', avec=True, decale=0.15),
                    anneau('#c10-t1', d=1.6, decale=0.3)]},
        {'qui': 'Étape 2 · Le manager', 'titre': 'Où le courrier attend',
         'texte': "La charge par étape montre les goulots ; la répartition, l'équilibre entre entrants, sortants et internes.",
         'voix': "La charge par étape montre où les courriers attendent, et donc où renforcer l'équipe. À droite, la répartition "
                 "entre courriers entrants, sortants et internes. Analyse détaillée ouvre l'analyse complète.",
         'gestes': [animer('#c10-charge .piste i', {'scaleX': 0, 'transformOrigin': '0% 50%'},
                           {'scaleX': 1, 'stagger': 0.06, 'immediateRender': True}, d=0.6),
                    anneau('#c10-b0', d=1.4, decale=0.6), anneau('#c10-rep', d=1.6)]},
    ],
}


SCENARIO = {
    'slug': '00-presentation',
    'profil': 'presentation',
    'titre_page': 'AITE Courrier — présentation de la solution',
    'ouverture': {
        'sous': 'Courrier · GED · Archives · Odoo 18',
        'kicker': 'Présentation de la solution',
        'titre': 'Le courrier, du *dépôt* à *l\'archive.*',
        'mission': "Enregistrer, faire circuler, traiter, prouver et conserver chaque courrier et chaque document de votre organisation.",
    },
    'cartes_intro': [
        {'kicker': 'En une minute', 'titre': 'Une solution, deux applications',
         'sous': "Dans Odoo 18, AITE Courrier et AITE ECM partagent les mêmes rôles, les mêmes circuits et le même journal d'audit.",
         'cartes': [('AITE Courrier', 'Le courrier', "Enregistrement, circuits paramétrables, traitement, réponses, cachet de traitement, portail des tiers."),
                    ('AITE ECM', 'Le fonds documentaire', "Documents typés et versionnés, plan de classement, dossiers métier, partages externes."),
                    ('Conservation et preuve', "L'archive", "Règles de conservation, gels juridiques, éliminations, journal de preuve scellé, archives physiques.")],
         'voix_cle': 'intro-1',
         'voix': "Aïte Courrier tient en deux applications d'Odoo dix-huit, qui partagent les mêmes rôles, les mêmes circuits et le même "
                 "journal d'audit : Aïte Courrier pour le courrier, Aïte E C M pour tout le fonds documentaire, avec la conservation "
                 "et la preuve pour l'archive."},
    ],
    'parcours': {
        'kicker': 'Le parcours', 'titre': "Cinq étapes, cinq rôles, un délai pour chacune",
        'etapes': [('Réception', 'Agent courrier', '4'), ('Qualification', 'Agent courrier · Assistante', '8'),
                   ('Affectation', 'Assistante · Manager', '4'), ('Traitement', 'Manager', '48'), ('Archivage', 'Archiviste', '24')],
        'note': "Le circuit <b>Courrier entrant standard</b>, livré avec la solution. Les circuits se <b>paramètrent sans développement</b> : "
                "étapes, rôles habilités, délais et transitions, par type de courrier.",
    },
    'roles': {
        'kicker': 'Les rôles', 'titre': 'Huit rôles, chacun son périmètre',
        'sous': "Chaque utilisateur reçoit un ou plusieurs rôles ; les écrans, les boutons et les données suivent.",
        'liste': [('Agent courrier', "Enregistre et qualifie le courrier reçu."), ('Assistant(e)', "Qualifie, affecte, gère les pièces."),
                  ('Manager', "Traite, valide, pilote son service."), ('Comptabilité', "Suit factures et dossiers comptables."),
                  ('Signataire', "Vise et signe les courriers sortants."), ('Archiviste', "Classe, conserve, archive, élimine."),
                  ('Audit', "Consulte la preuve et le journal d'audit."), ('Administrateur', "Paramètre circuits, types et droits.")],
    },
    'sommaire_titre': 'Dix chapitres, une journée de courrier',
    'chapitres': [CH1, CH2, CH3, CH4, CH5, CH6, CH7, CH8, CH9, CH10],
    'cartes_fin': [
        {'kicker': 'Ouvert sur vos outils', 'titre': 'Au-delà du navigateur',
         'cartes': [('Lecteur réseau et Office', 'Le fonds dans l\'Explorateur', "Un lecteur réseau WebDAV : ouvrir dans Word, Excel ou PowerPoint, enregistrer, et chaque enregistrement crée une version."),
                    ('API REST', 'Vos logiciels connectés', "Rechercher, créer, déposer une version, télécharger : une API documentée en OpenAPI, protégée par clé."),
                    ('Liens de partage', 'Vos correspondants', "Une page publique par lien, sans compte, avec expiration, quota et filigrane.")],
         'voix_cle': 'fin-1',
         'voix': "La solution s'ouvre aussi à vos outils : un lecteur réseau pour travailler depuis l'Explorateur et dans Word, Excel ou "
                 "PowerPoint, où chaque enregistrement crée une version ; une A P I Rest documentée pour vos logiciels ; et des liens de "
                 "partage pour vos correspondants."},
        {'kicker': 'Et aussi', 'titre': 'Les modules complémentaires',
         'cartes': [('Capture et OCR', 'Le courrier qui arrive seul', "Une boîte e-mail dédiée : chaque message devient un courrier ; le texte des pièces numérisées devient cherchable."),
                    ('Réponses et signature', 'Le courrier sortant', "Modèles de réponse liés au courrier d'origine, et signature électronique des courriers, sur Community comme sur Enterprise."),
                    ('Nextcloud et édition en ligne', 'Le travail partagé', "Miroir Nextcloud, édition dans le navigateur avec Collabora ou OnlyOffice, ouverture dans Google Docs.")],
         'voix_cle': 'fin-2',
         'voix': "Des modules complémentaires vont plus loin : la capture des e-mails, la reconnaissance de texte des pièces numérisées, "
                 "les modèles de réponse, la signature électronique, le miroir Nextcloud et l'édition des documents en ligne."},
    ],
    'recette': {
        'kicker': 'Éprouvée', 'titre': 'Dix-huit scénarios de recette, tous conformes',
        'scenarios': [('SC01', 'Enregistrer un courrier'), ('SC02', "Faire avancer le circuit"), ('SC03', 'Pièces et versions'),
                      ('SC04', 'Explorateur ECM'), ('SC05', 'Créer un document'), ('SC06', 'Conservation et gel'),
                      ('SC07', "Bordereau d'élimination"), ('SC08', 'Journal de preuve'), ('SC09', 'Archives physiques'),
                      ('SC10', 'Partages externes'), ('SC11', 'Dossiers métier'), ('SC12', 'Tableau de bord'),
                      ('SC13', "Journal d'audit"), ('SC14', 'Cloisonnement'), ('SC15', 'Portail des tiers'),
                      ('SC16', 'Vérifier l\'intégrité'), ('SC17', 'Nouvelle version'), ('SC18', 'Cachet de traitement')],
        'chiffres': [('18 / 18', 'scénarios de recette conformes'), ('18 / 18', "contrôles d'interfaces"),
                     ('349', 'tests automatisés, 0 échec')],
    },
    'retenir': {
        'regle': 'Chaque courrier a un <b>circuit</b>, chaque document une <b>histoire</b>, chaque action une <b>trace</b>.',
        'cartes': [('Circuler', "Des circuits paramétrables, des rôles habilités, un délai par étape."),
                   ('Prouver', "Versions conservées, sceaux chaînés, intégrité vérifiable, journal d'audit."),
                   ('Conserver', "Règles de conservation, gels juridiques, éliminations validées, archives physiques.")],
    },
    'fin': {'sous': 'Courrier · GED · Archives · Odoo 18', 'pied': 'AITE Consulting · www.aite-consulting.com'},
    'voix': {
        'ouverture': "Aïte Courrier : le courrier de votre organisation, du dépôt jusqu'à l'archive. Enregistrer, faire circuler, "
                     "traiter, prouver et conserver.",
        'parcours': "Prenons un courrier entrant. Il suit un circuit en cinq étapes : réception, qualification, affectation, traitement "
                    "et archivage. Chaque étape a ses rôles habilités et son délai. Et chaque circuit se paramètre sans développement.",
        'roles': "Huit rôles se partagent le travail, de l'agent courrier à l'administrateur. Chacun ne voit que les écrans, "
                 "les boutons et les données de son périmètre.",
        'sommaire': "Suivons maintenant une journée de courrier, en dix chapitres, sur les écrans de l'application.",
        'recette': "Tout ce que vous venez de voir a été éprouvé : dix-huit scénarios de recette joués dans un vrai navigateur, "
                   "dix-huit contrôles d'interfaces, et trois cent quarante-neuf tests automatisés, sans un seul échec.",
        'retenir': "À retenir : avec Aïte Courrier, chaque courrier a un circuit, chaque document une histoire, et chaque action une trace.",
        'fin': "Aïte Courrier, par Aïte Consulting. Merci de votre attention.",
    },
    'vignette': {'chapitre': 2, 'etape': 2, 'apres': 4.0},
}
