# -*- coding: utf-8 -*-
"""La série des tutoriels marketing : une vidéo par fonctionnalité.

Chaque module définit ``TUTO`` ; ``SERIE`` les range dans l'ordre de
publication. Les écrans sont ceux de la présentation (thème MuK : le
producteur ``tutoriels.py`` pose ``ecrans.THEME = 'muk'`` avant l'import),
complétés dans les modules des tutoriels quand un écran manque.
"""

SERIE = [
    # AITE Courrier
    ('01', 't01_enregistrer'),          # enregistrer un courrier et lancer son circuit
    ('02', 't02_traiter'),              # traiter, rejeter, commenter
    ('03', 't03_circuits'),             # circuits et délais : SLA, relances, escalade
    ('04', 't04_cachet'),               # le cachet de traitement
    ('05', 't05_pieces'),               # les pièces et leurs versions
    ('06', 't06_capture'),              # capture automatique des e-mails
    ('07', 't07_recherche'),            # recherche plein texte (OCR)
    ('08', 't08_repondre'),             # répondre avec un modèle
    ('09', 't09_signature'),            # signature électronique
    ('10', 't10_portail'),              # le portail des tiers
    ('11', 't11_tableau_de_bord'),      # le tableau de bord
    ('12', 't12_securite'),             # confidentialité et journal d'audit
    # AITE ECM
    ('13', 't13_documents'),            # explorateur et document ECM
    ('14', 't14_travailler'),           # réservation, Office, versions, corbeille
    ('15', 't15_numeriser'),            # numériser ses documents
    ('16', 't16_dossiers'),             # les dossiers métier
    ('17', 't17_partager'),             # partager en toute sécurité
    ('18', 't18_conservation'),         # conservation et gels juridiques
    ('19', 't19_elimination'),          # élimination et archives physiques
    ('20', 't20_preuve'),               # la valeur probante
    ('21', 't21_circuit_document'),     # circuit de validation d'un document
]

COURRIER = {'produit': 'AITE Courrier', 'marque': ('AITE', 'Courrier'), 'icone': 'aite_courrier.png'}
ECM = {'produit': 'AITE ECM', 'marque': ('AITE', 'ECM'), 'icone': 'aite_ecm.png'}
ADRESSE = 'courrier.aite-demo.test/odoo/%s'
# aite-consulting.com ouvre directement la prise de rendez-vous (/appointment).
CTA_COURRIER = {'sous': 'AITE Courrier · le courrier et ses documents dans Odoo 18',
                'voix': "Prenez rendez-vous pour une démonstration sur Aïte Consulting point com."}
CTA_ECM = {'sous': 'AITE ECM · la gestion documentaire dans Odoo 18',
           'voix': "Prenez rendez-vous pour une démonstration sur Aïte Consulting point com."}
MOTS_CLES = ['AITE Consulting', 'Odoo 18', 'Odoo Cameroun', 'GED', 'dématérialisation', 'gestion du courrier',
             'gestion documentaire', 'tutoriel Odoo', 'Douala']


def etape(ch, i, titre, texte, voix, avant=(), apres=(), inserer=None, retirer=()):
    """Une étape de tutoriel tirée de l'étape ``i`` d'un chapitre de la
    présentation : mêmes gestes (dont on peut retirer des indices),
    avec des gestes insérés avant l'indice k (``inserer`` = {k: [...]}),
    au début (``avant``) ou à la fin (``apres``)."""
    gestes = [g for k, g in enumerate(ch['etapes'][i]['gestes']) if k not in retirer]
    if inserer:
        bruts = list(ch['etapes'][i]['gestes'])
        gardes = [k for k in range(len(bruts)) if k not in retirer]
        for k in sorted(inserer, reverse=True):
            pos = sum(1 for x in gardes if x < k)
            gestes[pos:pos] = list(inserer[k])
    return {'titre': titre, 'texte': texte, 'voix': voix, 'gestes': list(avant) + gestes + list(apres)}


def cta(produit, titre, voix_debut):
    base = CTA_COURRIER if produit == 'courrier' else CTA_ECM
    return {'titre': titre, 'sous': base['sous'], 'voix': voix_debut + ' ' + base['voix']}


def youtube(titre, description, mots=()):
    return {'titre': titre, 'description': description, 'mots_cles': list(mots) + MOTS_CLES}


def initiale(ecran, vue_html_id, ancienne=None):
    """Fait d'une autre vue la vue affichée au départ."""
    if ancienne:
        ecran = ecran.replace('class="vue initiale avec-lateral" id="%s"' % ancienne, 'class="vue avec-lateral" id="%s"' % ancienne, 1)
        ecran = ecran.replace('class="vue initiale" id="%s"' % ancienne, 'class="vue" id="%s"' % ancienne, 1)
    return ecran.replace('class="vue" id="%s"' % vue_html_id, 'class="vue initiale" id="%s"' % vue_html_id, 1)
