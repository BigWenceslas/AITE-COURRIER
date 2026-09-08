# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Documents',
    'summary': "Socle de gestion de contenu d'entreprise : documents "
               "autonomes, types et métadonnées, plan de classement avec "
               "droits hérités, versions, check-out/check-in, relations, "
               "corbeille, doublons, recherche facettée.",
    'description': """
AITE ECM - Documents (Fondation ECM v2.0)
=========================================

Le document est libéré de l'objet courrier : tout contenu (contrat,
procédure, dossier RH, PV, plan…) vit dans un **référentiel unique**, rattaché
ou non à un objet Odoo (partenaire, facture, employé, dossier métier…).

* **Types de documents** avec **modèle de métadonnées** (champs
  ``Properties`` natifs d'Odoo 18 : dates, montants, listes, liens…).
* **Plan de classement** hiérarchique avec **droits hérités** (groupes en
  lecture / écriture par dossier).
* **Explorateur de fichiers** natif (Community et Enterprise) : espaces de
  travail, cartes à vignettes, dépôt et glisser-déposer, aperçu, inspecteur,
  actions groupées.
* **Versions** (v1, v2…) avec empreinte SHA-256, **détection de doublons**.
* **Check-out / check-in** : verrou d'édition exclusif avec expiration.
* **Relations** entre documents (annexe, remplace, référence, traduction).
* **Cycle de vie** brouillon → finalisé → archivé (lecture seule) ;
  **corbeille** avec restauration et purge automatique.
* **Confidentialité** (4 niveaux du socle) et **journal d'audit** partagés
  avec la suite Courrier.
* Mixin ``aite.ecm.document.mixin`` : ajoute un onglet « Documents » à
  n'importe quel modèle (livré sur les contacts).
* Recherche facettée (panneau dossiers / types / étiquettes / état) et
  recherche sur le contenu indexé des pièces ; analyse du fonds.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_base',   # groupes, confidentialité, audit (socle)
        'mail',
        'contacts',
    ],
    # Compatible Odoo Community : aucune dépendance Enterprise. L'intégration à
    # l'app Documents (Enterprise) est portée par aite_ecm_documents.
    'data': [
        'security/ir.model.access.csv',
        'security/aite_ecm_security.xml',
        'data/ir_sequence_data.xml',
        'data/aite_ecm_data.xml',
        'data/ir_cron_data.xml',
        'data/aite_ecm_capture_data.xml',
        'views/aite_ecm_document_views.xml',
        'views/aite_ecm_folder_views.xml',
        'views/aite_ecm_config_views.xml',
        'views/res_partner_views.xml',
        'views/aite_ecm_explorer_views.xml',
        'views/res_config_settings_views.xml',
        'views/aite_ecm_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'aite_ecm_document/static/src/explorer/**/*',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
