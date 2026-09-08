# -*- coding: utf-8 -*-
{
    # Nom fonctionnel affiché dans la liste des applications Odoo.
    'name': 'AITE Courrier - Courrier',

    # Résumé court (une ligne) visible dans l'app store interne.
    'summary': "Objet métier Courrier et son cycle de vie : brouillon, "
               "instanciation du circuit, étape courante, référence unique.",

    # Description longue (affichée sur la fiche du module).
    'description': """
AITE Courrier - Objet métier Courrier (core)
============================================

Modèle central ``aite.courrier`` et son cycle de vie :

* brouillon sans référence ni circuit ;
* lancement du circuit : référence unique ``COUR-AAAA-NNNN``, instanciation
  du circuit actif du type, positionnement sur l'étape initiale, audit ;
* suivi de l'étape courante et historique des étapes ;
* listes filtrables (entrants / sortants / internes / brouillons) ;
* confidentialité appliquée par règle d'enregistrement.

L'exécution des transitions est pilotée par ``aite_courrier_validation``.
""",

    # Versionnage Odoo : <serie_odoo>.<major>.<minor>.<patch>.<build>
    'version': '18.0.1.1.0',

    # Catégorie de classement dans Odoo.
    'category': 'AITE/Courrier',

    # Métadonnées éditeur.
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',

    # Licence : Odoo Enterprise Edition License v1.0.
    'license': 'OEEL-1',

    # Dépendances : socle, moteur de workflow, et hr pour les services
    # (hr.department) référencés par le service destinataire.
    'depends': [
        'aite_courrier_base',
        'aite_courrier_workflow',
        'hr',
    ],

    # Données chargées à l'installation/mise à jour.
    # Ordre important : séquence et sécurité d'abord, puis vues et menus.
    'data': [
        # Séquence de référence
        'data/ir_sequence_data.xml',
        # Sécurité
        'security/ir.model.access.csv',
        'security/aite_courrier_security.xml',
        # Vues, actions et menus
        'views/aite_courrier_views.xml',
        'views/aite_courrier_type_views.xml',
        'views/aite_courrier_menus.xml',
        # Accusé de réception + cron SLA (après les vues : références au modèle)
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
    ],

    # Données de démonstration (chargées seulement si demo activé).
    'demo': [],

    # Brique métier : l'application affichée est le module chapeau
    # « aite_courrier » (application=True).
    'installable': True,
    'application': False,
    'auto_install': False,
}
