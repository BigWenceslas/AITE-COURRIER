# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Records management',
    'summary': "Durées de conservation (DUA), sort final, cycle de vie "
               "archivistique, gel juridique, bordereaux d'élimination et "
               "archives physiques — conforme à l'esprit d'ISO 15489.",
    'description': """
AITE ECM - Records management
=============================

La couche de gouvernance des archives, au-dessus du socle documentaire :

* **Règles de conservation** : périmètre (types, dossiers, confidentialité),
  durée (DUA) et **point de départ** (création, finalisation, archivage,
  clôture du dossier, ou une date portée par une métadonnée), **sort final**
  (élimination, conservation définitive, revue) et **base légale** (OHADA,
  code du travail, fiscal…). Cinq règles livrées.
* **Cycle de vie** calculé chaque nuit : utilité courante → archive
  intermédiaire → échue → éliminée / conservation définitive ; activité de
  **revue** créée pour le responsable à l'échéance.
* **Gel juridique** : sur des documents ou des dossiers entiers ; tant qu'il
  est actif, aucune modification, corbeille ni destruction n'est possible.
* **Bordereaux d'élimination** : constitution automatique des documents échus,
  validation par un manager, exécution tracée, **certificat de destruction**
  déposé dans l'ECM ; les lignes conservent référence, titre et empreinte.
* **Archives physiques** : boîtes, emplacements, prêt/retour, lien avec le
  document numérique et indicateur « original papier ».
* **Données personnelles** : marquage, filtre et purge à échéance.
""",
    'version': '18.0.2.1.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document'],
    'data': [
        'security/ir.model.access.csv',
        'security/aite_ecm_records_security.xml',
        'data/ir_sequence_data.xml',
        'data/aite_ecm_records_data.xml',
        'data/ir_cron_data.xml',
        'report/disposition_report.xml',
        'views/aite_ecm_retention_views.xml',
        'views/aite_ecm_legal_hold_views.xml',
        'views/aite_ecm_disposition_views.xml',
        'views/aite_ecm_box_views.xml',
        'views/aite_ecm_document_views.xml',
        'views/aite_ecm_records_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
