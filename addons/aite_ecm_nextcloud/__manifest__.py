# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Connecteur Nextcloud',
    'summary': "Nextcloud comme espace de travail fichiers de l'ECM : miroir "
               "du plan de classement via WebDAV, retour des modifications en "
               "nouvelles versions (webhook ou sondage), édition en ligne, "
               "liens publics Nextcloud.",
    'description': """
AITE ECM - Connecteur Nextcloud
===============================

Odoo reste le **référentiel** (métadonnées, circuits, droits, audit,
versions) ; Nextcloud devient l'**espace de travail fichiers** : clients de
synchronisation bureau et mobile, édition en ligne (Collabora / OnlyOffice),
liens publics.

* **Miroir sortant (Odoo → Nextcloud)** par WebDAV : chaque document ECM —
  et, en option, chaque pièce de courrier — est écrit dans une arborescence
  qui reproduit le plan de classement
  (``AITE ECM/Juridique et contrats/DOC-2026-00128 - Contrat…/fichier.pdf``).
  Renommage ou reclassement dans Odoo → déplacement dans Nextcloud.
* **Retour entrant (Nextcloud → Odoo)** : une modification du fichier dans
  Nextcloud devient une **nouvelle version** du document, attribuée à
  l'utilisateur qui l'a réservé (ou au propriétaire). Détection en quasi
  temps réel par **webhook** (app *Webhook Listeners*, Nextcloud 30+) ou par
  **sondage périodique** des ETags (Nextcloud 25+). Un document finalisé ou
  archivé n'est jamais écrasé : **conflit** signalé au propriétaire.
* Boutons **Ouvrir dans Nextcloud** (édition en ligne), **Envoyer**,
  **Importer**, **Lien public Nextcloud** (mot de passe, expiration) sur les
  documents.
* Paramétrage dans ECM › Configuration › Paramètres : URL, compte de
  service (mot de passe d'application), dossier racine, mode (miroir seul ou
  bidirectionnel), sondage, secret du webhook, test de connexion,
  enregistrement du webhook, envoi initial du fonds.
* Journal d'audit : source « Nextcloud ».
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document'],   # Community-compatible ; courrier via aite_ecm_nextcloud_courrier
    'external_dependencies': {'python': ['requests']},
    'data': [
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/aite_ecm_document_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
