# -*- coding: utf-8 -*-
"""Les données de démonstration de la vidéo : toutes fictives.

Les comptes et les tiers du jeu de recette (``aite_ecm_demo``) n'apparaissent
pas : noms, organisations, adresses et références sont inventés ici, et
repris d'un écran à l'autre pour qu'un même courrier traverse la vidéo.
"""

SOCIETE = 'AITE Démo'

# rôle : (nom, initiale, couleur de l'avatar)
PERSONNES = {
    'agent': ('Carine Mballa', 'C', '#B5404A'),
    'assistante': ('Estelle Nguema', 'E', '#1E8E8A'),
    'manager': ('Paul Ebogo', 'P', '#8E3A9D'),
    'archiviste': ('Jules Abena', 'J', '#2E8B57'),
    'audit': ('Sandrine Owona', 'S', '#C27A12'),
    'compta': ('Hervé Mvondo', 'H', '#3D63B8'),
    'signataire': ('Nicole Biyong', 'N', '#B5651A'),
    'admin': ('Martin Ekoto', 'M', '#5E5665'),
}

TIERS = 'Groupe Horizon Services'
TIERS_COURRIEL = 'contact@horizon-services.test'
FOURNISSEUR = 'Delta Équipements SARL'

# Le courrier enregistré au chapitre 1
NOUVEAU = {'reference': 'COUR-2026-0141', 'objet': 'Demande de partenariat — Groupe Horizon Services',
           'expediteur': 'Direction générale, Groupe Horizon Services', 'courriel': TIERS_COURRIEL,
           'date': '13/10/2026'}
# Le courrier qui avance au chapitre 2
EN_COURS = {'reference': 'COUR-2026-0014', 'objet': "Demande d'agrément fournisseur — Delta Équipements SARL",
            'expediteur': FOURNISSEUR, 'courriel': 'contact@delta-equipements.test', 'date': '22/09/2026',
            'service': 'Juridique', 'priorite': 'Haute', 'confidentialite': 'Interne'}
# Le courrier clos du cachet de traitement
CLOS = {'reference': 'COUR-2026-0009', 'objet': 'Demande de devis pour travaux', 'expediteur': TIERS,
        'courriel': TIERS_COURRIEL, 'date': '05/10/2026', 'service': 'Finance et comptabilité'}
