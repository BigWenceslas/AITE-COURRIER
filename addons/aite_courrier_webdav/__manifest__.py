# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - WebDAV',
    'summary': "Accès WebDAV à l'espace documentaire : monter les courriers et "
               "leurs pièces jointes comme un lecteur réseau.",
    'description': """
AITE Courrier - WebDAV
======================

Expose la GED (``aite_courrier_ged``) via le protocole **WebDAV**, directement
servi par le serveur Odoo (aucune dépendance externe). On peut ainsi monter
l'espace documentaire comme un lecteur réseau (Explorateur Windows, Finder
macOS, rclone, cadaver…).

Arborescence exposée sous ``/webdav/aite_courrier`` ::

    /webdav/aite_courrier/
      └── <référence courrier>/        (une collection par courrier)
            └── <document>.<ext>        (dernière version de chaque document)

Le module se branche sur les points d'accroche déjà prévus côté GED
(cf. ``aite_courrier_ged/docs/WEBDAV_READINESS.md``) :

* ``aite.courrier.document._check_document_access`` — droits read/write ;
* ``aite.courrier.document.is_locked`` — verrou → ``423 Locked`` ;
* confidentialité héritée via ``aite.courrier._check_courrier_access`` ;
* ``add_version`` — un ``PUT`` crée une nouvelle version (v1, v2, …) ;
* audit ``source='webdav'`` pour tracer les opérations réseau.

La logique (résolution de chemin, lecture/écriture/suppression) vit dans le
service ``aite.courrier.webdav`` (testable), le contrôleur HTTP n'étant qu'un
adaptateur des verbes WebDAV.
""",
    'version': '18.0.1.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_ged',
    ],
    'data': [],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
