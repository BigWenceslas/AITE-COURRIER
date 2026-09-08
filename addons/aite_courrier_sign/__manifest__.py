# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - Signature électronique',
    'summary': "Intégration d'Odoo Sign : demandes de signature depuis un "
               "courrier et étapes de circuit exigeant une signature "
               "complétée avant validation.",
    'description': """
AITE Courrier - Signature électronique (Odoo Sign)
==================================================

Cohérent avec le positionnement « 100 % natif Odoo Enterprise » : le
parapheur électronique s'appuie sur l'app **Sign**, incluse dans l'offre
Enterprise — aucune brique externe (réponse au parapheur de Maarch / Elise).

Fonctionnalités
---------------
* **Demander la signature** depuis un courrier : la dernière version PDF est
  transformée en modèle Sign avec une zone de signature pré-positionnée, et
  une demande est envoyée au responsable du courrier (ou à l'utilisateur
  courant à défaut).
* **Étapes « Signature requise »** : une étape de circuit peut exiger qu'au
  moins une demande de signature rattachée au courrier soit **complétée**
  avant d'autoriser toute transition en avant — contrôle appliqué côté
  serveur, comme le reste du moteur.
* Suivi : bouton statistique « Signatures » sur le courrier, lien
  ``courrier_id`` sur les demandes Sign, journal d'audit.

Module **optionnel** : ne l'installer que si l'app Sign est déployée.
""",
    'version': '18.0.1.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_core',
        'aite_courrier_workflow',
        'aite_courrier_ged',
        'aite_courrier_validation',
        'sign',
    ],
    'data': [
        'views/aite_workflow_views.xml',
        'views/aite_courrier_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
