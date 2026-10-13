# -*- coding: utf-8 -*-
"""Le chapitre propre à la vidéo d'AITE ECM : travailler sur un document.

Sources : aite_ecm_document/views/aite_ecm_document_views.xml (boutons de
l'en-tête et leurs conditions : Réserver / Libérer, Corbeille et son message
de confirmation, Restaurer ; bandeau « Réservé par … jusqu'au … »),
aite_ecm_document/models/aite_ecm_document.py (réservation de 48 h par
défaut, écriture refusée à un autre que le titulaire, libération par le
titulaire ou un manager), aite_ecm_webdav (« Ouvrir dans Office », « Adresse
WebDAV »), aite_ecm_share (« Partager ») ; recette des interfaces
(enregistrement depuis le lecteur réseau, journal d'audit source WebDAV).
"""

import demo
from ecrans import (assistant, bande, bandeau, bouton, case, champ, entree, fenetre, feuille, grille2, onglets, panneau_fiche,
                    sec_titre, statusbar, table, v, vue, c_html, c_num)
from moteur import anneau, cacher, clic, fermer, montrer, ouvrir, pause, texte

P = demo.PERSONNES
ASSIST = P['assistante']
MENUS_ECM = ['Documents', 'Dossiers métier', 'Plan de classement', 'Conservation', 'Preuve et archivage', 'Analyse']
NOM_DOC = 'Contrat de maintenance — climatisation'


def _bande():
    def b(*cles):
        tous = {'circ': bouton('c11-circ%s', 'Lancer le circuit', 'prim', 'lecture'),
                'fin': bouton('c11-fin%s', 'Finaliser', 'prim'),
                'res': bouton('c11-res%s', 'Réserver', 'second', 'cadenas'),
                'lib': bouton('c11-lib%s', 'Libérer', 'orange', 'cadenas'),
                'prev': bouton('c11-prev%s', 'Prévisualiser', 'second', 'oeil'),
                'corb': bouton('c11-corb%s', 'Corbeille', 'second', 'corbeille'),
                'rest': bouton('c11-rest%s', 'Restaurer', 'vert'),
                'part': bouton('c11-part%s', 'Partager', 'second'),
                'off': bouton('c11-off%s', 'Ouvrir dans Office', 'second', 'document')}
        return [tous[c] for c in cles]
    a = [x % '' for x in b('circ', 'fin', 'res', 'prev', 'corb', 'part', 'off')]
    reserve = [x % '2' for x in b('circ', 'fin', 'lib', 'prev', 'corb', 'part', 'off')]
    libere = [x % '3' for x in b('circ', 'fin', 'res', 'prev', 'corb', 'part', 'off')]
    corbeille = [x % '4' for x in b('circ', 'fin', 'res', 'prev', 'rest', 'off')]
    return bande(a, statusbar(['Brouillon', 'Finalisé', 'Archivé'], 0, 'c11-sb'), 'c11-b', [reserve, libere, corbeille])


def ecran_travail():
    reserve = bandeau('🔒 Réservé par <b>%s</b> jusqu\'au 15/10/2026 10:42' % ASSIST[0], 'jaune', 'c11-resa', masque=True)
    corps = (reserve
             + '<div class="ref-l">Référence</div><div class="ref-v moyen">DOC-2026-00341</div><div class="titre-doc">%s</div>' % NOM_DOC
             + grille2([champ('Type', v('Contrat')), champ('Dossier de classement', v('Juridique et contrats / Contrats fournisseurs')),
                        champ('Étiquettes', v('À renouveler')), champ('Confidentialité', v('Confidentiel'))],
                       [champ('Propriétaire', v(P['manager'][0])), champ('Fichier', v('Contrat_maintenance_climatisation.docx')),
                        champ('Adresse WebDAV', '<span class="entree" style="border:1px solid #DEE2E6;border-radius:4px;padding:0 6px;font-size:11px">'
                                                'https://courrier.aite-demo.test/webdav/aite_ecm/Juridique et contrats/…</span>', 'c11-webdav')])
             + sec_titre('Métadonnées') + grille2([champ('Parties', v('AITE Démo — ' + demo.FOURNISSEUR)),
                                                   champ('Objet du contrat', v('Maintenance des climatiseurs')),
                                                   champ("Date d'effet", v('02/01/2026')), champ('Date de fin', v('31/12/2026'))],
                                                  [champ('Montant', v('4 800 000')), champ('Devise', v('FCFA')),
                                                   champ('Tacite reconduction', case(True))])
             + onglets(['Versions', 'Relations', 'Accès', 'Conservation', 'Preuve', 'Circuit', 'Description'])
             + table([('Version', '60px'), ('Nom du fichier', '1fr'), ('Commentaire de version', '1fr'), ('Taille (octets)', '100px'),
                      ('Téléversé par', '120px'), ('Date', '130px')],
                     [{'id': 'c11-v3', 'masque': True, 'cellules': ['v3', 'Contrat_maintenance_climatisation.docx', 'Enregistré depuis Word',
                                                                    c_num('48 902'), ASSIST[0], '13/10/2026 10:55']},
                      {'id': 'c11-v2', 'cellules': ['v2', 'Contrat_maintenance_climatisation.docx', 'Avenant n° 1', c_num('47 310'),
                                                    P['manager'][0], '02/10/2026 16:20']},
                      {'id': 'c11-v1', 'cellules': ['v1', 'Contrat_maintenance_climatisation.docx', 'Version signée', c_num('45 118'),
                                                    P['manager'][0], '02/01/2026 09:12']}], identifiant='c11-versions', ajouter=False))
    confirm = assistant('c11-conf', 'Confirmation',
                        '<div style="font-size:13px">Mettre ce document à la corbeille ? Il pourra être restauré avant purge automatique.</div>',
                        [('c11-ok', 'Ok', 'prim'), ('c11-non', 'Annuler', 'second')], haut=230, largeur=560)
    fiche = vue('c11-doc', panneau_fiche('Documents', NOM_DOC, '5 / 257')
                + '<div class="o-corps"><div class="o-gauche">%s%s</div></div>' % (
                    _bande(), feuille(corps, ruban=('CORBEILLE', 'rouge'), ruban_id='c11-ruban').replace(
                        'class="ruban rouge"', 'class="ruban rouge masque"')), initiale=True)
    return fenetre('ECM', MENUS_ECM, [fiche], ASSIST[1], ASSIST[2], calques=confirm, ident='app-11')


CH_TRAVAIL = {
    'titre': 'Travailler sur un document', 'qui': 'Assistante',
    'sous': "Réserver, modifier dans Word, versionner, et ne rien perdre.",
    'roles': ['Assistante', 'Tous les rôles selon leurs droits'],
    'voix': "travailler sur un document, au quotidien.",
    'ecran': ecran_travail(), 'vue_initiale': 'c11-doc',
    'etapes': [
        {'qui': "Étape 1 · L'assistante", 'titre': 'Réserver avant de modifier',
         'texte': "Quarante-huit heures par défaut ; pendant ce temps, personne d'autre ne peut le modifier.",
         'voix': "Avant de modifier un contrat, l'assistante le réserve. La réservation dure quarante-huit heures par défaut : "
                 "pendant ce temps, personne d'autre ne peut le modifier. Seule elle, ou un manager, peut le libérer.",
         'gestes': [anneau('#c11-res', d=1.0, decale=0.3), clic('#c11-res'), cacher('#c11-b-a', d=0.2),
                    montrer('#c11-b-b', y=0, avec=True), montrer('#c11-resa', y=10), anneau('#c11-resa', d=1.8), anneau('#c11-lib2', d=1.2)]},
        {'qui': "Étape 2 · L'assistante", 'titre': 'Ouvrir dans Office',
         'texte': "Word s'ouvre sur le document, par le lecteur réseau ; chaque enregistrement crée une version.",
         'voix': "Ouvrir dans Office lance Word sur le document, à travers le lecteur réseau, dont l'adresse se copie aussi pour "
                 "l'Explorateur. À chaque enregistrement dans Word, une nouvelle version entre dans le fonds, tracée au journal d'audit.",
         'gestes': [anneau('#c11-webdav', d=1.6, decale=0.2), clic('#c11-off2'), pause(1.2), montrer('#c11-v3', y=10),
                    anneau('#c11-versions', d=2.2)]},
        {'qui': "Étape 3 · L'assistante", 'titre': 'Libérer, et la corbeille sans risque',
         'texte': "Un document supprimé part à la corbeille : il se restaure avant la purge automatique.",
         'voix': "Son travail fini, elle libère le document. Et un document supprimé part d'abord à la corbeille, après confirmation : "
                 "il se restaure d'un clic, avant la purge automatique. Un document sous gel juridique, lui, ne peut même pas y aller.",
         'gestes': [clic('#c11-lib2'), cacher('#c11-resa', d=0.3), cacher('#c11-b-b', d=0.2, avec=True), montrer('#c11-b-c', y=0, avec=True),
                    pause(0.4), clic('#c11-corb3'), ouvrir('c11-conf'), pause(0.8), clic('#c11-ok'), fermer('c11-conf'),
                    cacher('#c11-b-c', d=0.2), montrer('#c11-b-d', y=0, avec=True), montrer('#c11-ruban', y=0, avec=True),
                    anneau('#c11-rest4', d=1.4)]},
    ],
}
