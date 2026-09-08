# -*- coding: utf-8 -*-
{
    # Nom fonctionnel affiché dans la liste des applications Odoo.
    'name': 'AITE Courrier - Workflow',

    # Résumé court (une ligne) visible dans l'app store interne.
    'summary': "Moteur de circuits de traitement du courrier AITE : étapes, "
               "transitions et habilitations, configurable et livré avec les "
               "5 circuits de base.",

    # Description longue (affichée sur la fiche du module).
    'description': """
AITE Courrier - Moteur de workflow (workflow)
=============================================

Moteur de circuits CONFIGURABLE pour la suite AITE Courrier. Il fournit :

* ``aite.workflow.circuit``    - un circuit par type de courrier ;
* ``aite.workflow.step``       - les étapes (rôles, utilisateurs, SLA) ;
* ``aite.workflow.transition`` - les transitions dirigées entre étapes.

Les 5 circuits de base (entrant standard, sortant, interne, facture
fournisseur, devis commercial) sont livrés en données et prêts à l'emploi dès
l'installation. Principe directeur : paramétrage > code spécifique.

L'exécution effective d'un circuit sur un courrier relève des modules
``core`` et ``validation`` ; ce module se limite au paramétrage et aux
méthodes moteur (pures, testables).
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
    'license': 'OEEL-1',

    # Dépend du socle (groupes de sécurité, référentiel des types de courrier).
    'depends': [
        'aite_courrier_base',
    ],

    # Données chargées à l'installation/mise à jour.
    # Ordre important : sécurité d'abord, puis circuits de base, puis l'UI.
    'data': [
        # Sécurité
        'security/ir.model.access.csv',
        # Circuits de base (noupdate=1 : non écrasés aux mises à jour)
        'data/workflow_circuits.xml',
        # Vues, actions et menus
        'views/aite_workflow_views.xml',
        'views/aite_workflow_menus.xml',
    ],

    # Données de démonstration (chargées seulement si demo activé).
    'demo': [],

    # Module installable, listé comme application.
    'installable': True,
    'application': False,
    'auto_install': False,
}
