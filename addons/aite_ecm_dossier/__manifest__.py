# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Dossiers métier',
    'summary': "Gestion de dossiers (case management) : pièces requises et "
               "complétude, métadonnées, circuit de validation, documents "
               "ECM rattachés.",
    'description': """
AITE ECM - Dossiers métier
==========================

Un **dossier** regroupe des documents autour d'un objectif : agrément
fournisseur, dossier salarié, marché public, sinistre, demande d'autorisation…

* **Types de dossiers** avec **liste de pièces requises** (type de document
  attendu, obligatoire ou non), métadonnées propres (``Properties``), dossier
  de classement des pièces et **circuit de validation** dédié.
* **Complétude** calculée en temps réel : pièces fournies / attendues ;
  clôture refusée tant que les pièces obligatoires manquent (sauf manager).
* **Rattachement automatique** : un document ECM créé depuis le dossier
  avec le bon type vient remplir la première pièce manquante.
* **Circuit polymorphe** : lancement, transitions habilitées, SLA, historique
  et rejet motivé via ``aite.workflow.mixin``.
* Livré avec deux types de dossiers prêts à l'emploi (Agrément fournisseur,
  Dossier du personnel) et un circuit « Instruction → Validation ».
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_ecm_document',
        'aite_ecm_workflow',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/aite_ecm_dossier_security.xml',
        'data/ir_sequence_data.xml',
        'views/aite_ecm_dossier_views.xml',
        'views/aite_ecm_dossier_type_views.xml',
        'views/aite_ecm_dossier_menus.xml',
        'data/aite_ecm_dossier_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
