# -*- coding: utf-8 -*-
{
    # Application « chapeau » : installer ce seul module installe toute la
    # suite AITE Courrier (socle, workflow, courrier, GED, validation).
    'name': 'AITE Courrier',
    'summary': "Suite complète de gestion du courrier AITE : référentiels, "
               "circuits, courriers, documents, validation et tableau de bord.",
    'description': """
AITE Courrier — Application complète
====================================

Module « chapeau » de la suite AITE Courrier. L'installer installe
automatiquement tous les modules connexes :

* aite_courrier_base       — socle (groupes, référentiels, audit) ;
* aite_courrier_workflow   — moteur de circuits + 5 circuits de base ;
* aite_courrier_core       — objet métier Courrier, cycle de vie, SLA
  (relances + escalade), accusé de réception automatique ;
* aite_courrier_ged        — gestion documentaire versionnée + classement ;
* aite_courrier_validation — exécution des transitions (actions) ;
* aite_courrier_webdav     — accès WebDAV à l'espace documentaire ;
* aite_courrier_capture    — capture e-mail (alias → courrier + pièces GED) ;
* aite_courrier_ocr        — indexation plein texte des pièces (OCR) ;
* aite_courrier_reponse    — modèles de réponse + génération PDF en GED.

Modules optionnels (non installés par le chapeau) :

* aite_courrier_sign       — signature électronique via Odoo Sign ;
* aite_courrier_portal     — portail externe de dépôt / suivi des demandes.

Ajoute un **tableau de bord** d'indicateurs (graphiques et tableaux croisés)
et le logo de l'application.
""",
    'version': '18.0.1.2.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_base',
        'aite_courrier_workflow',
        'aite_courrier_core',
        'aite_courrier_ged',
        'aite_courrier_validation',
        'aite_courrier_webdav',
        'aite_courrier_capture',
        'aite_courrier_ocr',
        'aite_courrier_reponse',
    ],
    'data': [
        'views/aite_courrier_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'aite_courrier/static/src/scss/dashboard.scss',
            'aite_courrier/static/src/js/dashboard.js',
            'aite_courrier/static/src/xml/dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
