# -*- coding: utf-8 -*-
"""La série des tutoriels marketing : une vidéo par fonctionnalité.

Chaque module définit ``TUTO`` ; ``SERIE`` les range dans l'ordre de
publication. Les écrans sont ceux de la présentation (thème MuK : le
producteur ``tutoriels.py`` pose ``ecrans.THEME = 'muk'`` avant l'import).
"""

SERIE = [
    ('01', 't01_enregistrer'),
]

COURRIER = {'produit': 'AITE Courrier', 'marque': ('AITE', 'Courrier'), 'icone': 'aite_courrier.png'}
ECM = {'produit': 'AITE ECM', 'marque': ('AITE', 'ECM'), 'icone': 'aite_ecm.png'}
ADRESSE = 'courrier.aite-demo.test/odoo/%s'
