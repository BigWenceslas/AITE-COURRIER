# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM',
    'summary': "Chapeau de la plateforme AITE ECM : installe en un clic la "
               "gestion du courrier (AITE Courrier) et la Fondation ECM "
               "(documents, workflow polymorphe, dossiers métier, partage "
               "sécurisé, API REST).",
    'description': """
AITE ECM — plateforme de gestion de contenu d'entreprise sur Odoo 18
====================================================================

Ce module chapeau installe l'ensemble de la suite :

* **AITE Courrier** (chapeau ``aite_courrier`` : base, workflow, core, GED,
  validation, WebDAV, capture, OCR, réponses) ;
* **Fondation ECM v2.0** : ``aite_ecm_document``, ``aite_ecm_workflow``,
  ``aite_ecm_dossier``, ``aite_ecm_share``, ``aite_ecm_api``.

Les modules optionnels ``aite_courrier_sign`` et ``aite_courrier_portal``
s'installent séparément.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier',
        'aite_ecm_document',
        'aite_ecm_workflow',
        'aite_ecm_dossier',
        'aite_ecm_share',
        'aite_ecm_api',
    ],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
