# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - API REST',
    'summary': "API REST authentifiée par clé (X-API-Key) pour créer, "
               "rechercher, lire et verser des documents ECM ; spécification "
               "OpenAPI servie par le serveur.",
    'description': """
AITE ECM - API REST
===================

Ouverture de la plateforme aux applications tierces (portails métiers,
scanners, RPA, intégrations) :

* **Authentification** par clé d'API Odoo (``Paramètres > Sécurité > Clés
  d'API`` de l'utilisateur), en-tête ``X-API-Key`` ; toutes les opérations
  s'exécutent **avec les droits de l'utilisateur** (dossiers,
  confidentialité, verrous) ;
* ``GET  /api/ecm/v1/ping`` · ``GET /types`` · ``GET /folders`` ;
* ``GET  /api/ecm/v1/documents`` (recherche : ``q``, ``type``, ``folder``,
  ``state``, ``limit``, ``offset``) ;
* ``POST /api/ecm/v1/documents`` (création + fichier base64 + métadonnées) ;
* ``GET  /api/ecm/v1/documents/<id>`` · ``POST …/<id>/versions`` ·
  ``GET …/<id>/download`` ;
* ``GET  /api/ecm/v1/openapi.json`` : spécification OpenAPI 3.0.

Réponses JSON, codes HTTP explicites, audit source « API ».
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
