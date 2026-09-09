# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Valeur probante (SAE)',
    'summary': "Scellement SHA-256, journal de preuve chaîné et horodaté, "
               "vérification d'intégrité, attestation, copies de préservation "
               "PDF/A et export de paquets d'archives (SEDA / OAIS).",
    'description': """
AITE ECM - Valeur probante
==========================

Ce qui transforme une GED en **système d'archivage à valeur probante**,
dans l'esprit de NF Z42-013 / ISO 14641 :

* **Scellement** : chaque dépôt de version, finalisation, archivage,
  vérification, élimination ou export produit un **sceau** — une empreinte
  SHA-256 qui couvre le contenu, l'événement et **l'empreinte du sceau
  précédent**. Le journal est **inaltérable** (ni modification ni suppression).
* **Horodatage** : jeton interne signé avec la clé de la base ; en option,
  jeton **RFC 3161** d'une autorité tierce (repli automatique).
* **Vérification** : à la demande sur un document, et par tâche planifiée sur
  tout le fonds — chaîne recalculée, empreintes des fichiers recontrôlées,
  anomalies journalisées.
* **Attestation d'intégrité** : PDF reprenant l'identité du document, ses
  versions, leurs empreintes et la chaîne de preuve.
* **Copie de préservation PDF/A** (LibreOffice), manuelle ou automatique pour
  les documents archivés à conservation longue ou définitive.
* **Export de paquets d'archives** : ZIP avec bordereau ``manifest.xml``
  (structure SEDA 2.1), fichiers, journal de preuve et mode d'emploi —
  réversibilité vers un SAE tiers ou les Archives.
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
        'data/ir_cron_data.xml',
        'report/proof_report.xml',
        'views/aite_ecm_seal_views.xml',
        'views/aite_ecm_document_views.xml',
        'wizard/aite_ecm_seda_export_views.xml',
        'views/aite_ecm_sae_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
