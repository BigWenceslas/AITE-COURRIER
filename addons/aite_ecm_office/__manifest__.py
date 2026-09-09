# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Édition Office et Google Docs',
    'summary': "Ouvrir et modifier les documents ECM dans Word, Excel, "
               "PowerPoint ou LibreOffice (bureau, via WebDAV), dans le "
               "navigateur (Collabora Online / OnlyOffice via WOPI) ou dans "
               "Google Docs (aller-retour par Google Drive) : chaque "
               "enregistrement crée une version, la réservation protège "
               "l'édition.",
    'description': """
AITE ECM - Édition Office et Google Docs
========================================

Quatre façons d'ouvrir un document ECM dans une suite bureautique, toutes
compatibles Odoo Community :

* **Bureau et lecteur réseau** : fournis par ``aite_ecm_webdav`` (installé
  automatiquement) — boutons *Ouvrir dans Office*, plan de classement exposé
  en WebDAV sur ``/webdav/aite_ecm``. Ce module y ajoute l'ouverture dans
  **LibreOffice**.
* **Navigateur** : bouton *Modifier en ligne* — édition dans Collabora Online
  ou OnlyOffice (auto-hébergés, protocole **WOPI** ouvert) ; jetons d'accès
  limités dans le temps, verrou WOPI = réservation, chaque sauvegarde =
  version.
* **Google Docs / Sheets / Slides** : bouton *Ouvrir dans Google* — copie
  déposée dans le Drive de l'utilisateur (autorisation OAuth par personne),
  édition dans Google, rapatriement en version (manuel, à la clôture ou par
  tâche planifiée), suppression de la copie à la fin.

Paramétrage : ECM › Configuration › Paramètres › *Édition Office*.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document', 'aite_ecm_webdav'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/aite_ecm_document_views.xml',
        'views/res_config_settings_views.xml',
        'views/wopi_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'aite_ecm_office/static/src/explorer/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
