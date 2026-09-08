# -*- coding: utf-8 -*-
{
    # Nom fonctionnel affiché dans la liste des applications Odoo.
    'name': 'AITE Courrier - Socle',

    # Résumé court (une ligne) visible dans l'app store interne.
    'summary': "Socle transverse de la solution de gestion du courrier AITE "
               "(référentiels, groupes de sécurité, audit).",

    # Description longue (affichée sur la fiche du module).
    'description': """
AITE Courrier - Module socle (base)
===================================

Module de fondation de la suite AITE Courrier. Il ne contient pas encore de
modèle métier : il pose l'ossature commune (groupes de sécurité, catégorie de
module, et plus tard les référentiels et l'audit transverse) sur laquelle
s'appuient les autres modules :

* aite_courrier_workflow  - circuits de traitement
* aite_courrier_core      - objets métier du courrier
* aite_courrier_ged       - gestion électronique des documents
* aite_courrier_validation- validation / signature

Principe directeur : paramétrage > code spécifique.
""",

    # Versionnage Odoo : <serie_odoo>.<major>.<minor>.<patch>.<build>
    'version': '18.0.1.0.0',

    # Catégorie de classement dans Odoo.
    'category': 'AITE/Courrier',

    # Métadonnées éditeur.
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',

    # Licence : Odoo Enterprise Edition License v1.0.
    # (LGPL-3 possible si le module doit rester librement redistribuable.)
    'license': 'OEEL-1',

    # Dépendances minimales : noyau Odoo, messagerie/chatter et couche web.
    'depends': [
        'base',
        'mail',
        'web',
    ],

    # Données chargées à l'installation/mise à jour.
    # Ordre important : sécurité d'abord, puis référentiels, vues et menus.
    'data': [
        # Sécurité
        'security/groups.xml',
        'security/ir.model.access.csv',
        # Référentiels par défaut
        'data/aite_courrier_type_data.xml',
        'data/aite_courrier_priority_data.xml',
        'data/aite_courrier_confidentiality_data.xml',
        # Vues
        'views/aite_courrier_referentiel_views.xml',
        'views/aite_courrier_audit_log_views.xml',
        'views/aite_courrier_menus.xml',
    ],

    # Données de démonstration (chargées seulement si demo activé).
    'demo': [],

    # Brique technique : l'application affichée est le module chapeau
    # « aite_courrier » (application=True).
    'installable': True,
    'application': False,
    'auto_install': False,
}
