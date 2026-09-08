# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Jeu de données de test',
    'summary': "Génère un jeu de données de test réaliste, par lots en arrière-"
               "plan (profils léger / standard / complet), en passant par les "
               "méthodes métier : courriers de chaque type avec circuits et "
               "pièces, documents ECM typés et versionnés, dossiers métier, "
               "partages, relations, réservations, corbeille.",
    'description': """
AITE ECM - Jeu de données de test
=================================

L'installation est **instantanée** : le module enregistre un plan de
génération, puis une **tâche planifiée** crée les données par lots de 40 s en
arrière-plan (état visible dans le journal serveur), sans jamais dépasser
les limites de temps d'une instance à configuration de base.

Trois **profils de volume** (paramètre système ``aite_ecm_demo.profile`` à
définir *avant* l'installation, ou argument du script ``shell``) :

* ``leger`` (défaut) : 12 utilisateurs, 8 services, 60 tiers, **150
  courriers** (30 par type), 60 documents ECM, 40 dossiers métier, 40
  relations, 30 partages, 12 réservations, 8 documents en corbeille ;
* ``standard`` : 100 tiers, 300 courriers, 120 documents, 100 dossiers… ;
* ``complet`` : 130 tiers, 500 courriers (100 par type), 200 documents, 200
  dossiers, 120 relations, 100 partages…

Dans tous les profils : circuits lancés et avancés (retours commentés,
rejets, archivages, retards SLA), pièces PDF versionnées, métadonnées
renseignées, doublons, réponses liées, accès journalisés. Aléa
**déterministe** (graine 2026). Chaque enregistrement porte un identifiant
externe ``aite_ecm_demo.*`` : **désinstaller le module supprime tout le jeu
de données**. Voir ``README.md``.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document', 'aite_ecm_workflow', 'aite_ecm_dossier',
                'aite_ecm_share'],   # courrier et RH exploités s'ils sont installés
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/aite_ecm_demo_wizard_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
