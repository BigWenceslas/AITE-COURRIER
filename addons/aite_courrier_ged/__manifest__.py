# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - GED',
    'summary': "Gestion documentaire : pièces jointes versionnées, classement "
               "par dossiers et étiquettes, auto-classement, confidentialité héritée.",
    'description': """
AITE Courrier - Gestion documentaire (ged)
===========================================

Couche documentaire rattachée aux courriers :

* ``aite.courrier.document``         - document (conteneur de versions) ;
* ``aite.courrier.document.version`` - versions immuables des pièces jointes ;
* ``aite.courrier.folder``           - dossiers de classement (arborescence) ;
* ``aite.courrier.document.tag``     - étiquettes transversales.

Classement à deux axes : **arborescence de dossiers** (couleur, description,
compteur) et **étiquettes** colorées, avec **auto-classement** (dossier par
défaut déduit du type de courrier, surchargeable).

Confidentialité héritée du courrier, versionnage automatique (v1, v2, …),
verrouillage des versions finales/archivées, contrôle de format et de taille.

Compatible Odoo Community. Sur Enterprise, le module passerelle
``aite_courrier_ged_documents`` (installé automatiquement) reflète les pièces
dans l'app **Documents** : un espace « Courrier » contenant un dossier par
courrier, sans duplication des fichiers.

Conçu pour être **WebDAV-ready** sans code WebDAV (cf.
docs/WEBDAV_READINESS.md) : la méthode ``_check_document_access`` et l'indicateur
``is_locked`` sont les points d'accroche du module ``aite_courrier_webdav``.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_core',
        # GED native Odoo (Enterprise) : la couche documentaire du courrier
        # s'appuie dessus (espace « Courrier », un dossier par courrier) au lieu
        # de réimplémenter une GED parallèle.
    ],
    'data': [
        # Sécurité
        'security/ir.model.access.csv',
        'security/aite_courrier_ged_security.xml',
        # Données : espace documentaire natif « Courrier »
        # Données : dossiers, étiquettes et auto-classement par type
        'data/aite_courrier_folder_data.xml',
        'data/aite_courrier_tag_data.xml',
        'data/aite_courrier_type_data.xml',
        # Vues, actions et menus
        'views/aite_courrier_type_views.xml',
        'views/aite_courrier_folder_views.xml',
        'views/aite_courrier_document_views.xml',
        'views/aite_courrier_views.xml',
        'views/aite_courrier_ged_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
