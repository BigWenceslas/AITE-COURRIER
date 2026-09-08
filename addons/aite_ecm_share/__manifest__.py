# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Partage sécurisé',
    'summary': "Liens de partage externes expirants (quota de téléchargements, "
               "consultation seule) avec filigrane dynamique sur les PDF et "
               "journalisation des accès.",
    'description': """
AITE ECM - Partage sécurisé
===========================

Partagez un document avec un tiers **sans compte** et sans e-mail lourd :

* lien à **jeton** unique, **date d'expiration**, **quota de
  téléchargements**, désactivation à tout moment ;
* mode **consultation seule** (PDF affiché dans le navigateur, pas de
  téléchargement) ;
* **filigrane dynamique** incrusté dans le PDF servi (mention, date,
  identifiant du lien) — activé d'office pour les documents Confidentiel /
  Secret ;
* chaque accès est **journalisé** (audit source « Système », compteur sur
  le lien) ; la dernière version au moment de l'accès est servie.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/aite_ecm_share_views.xml',
        'views/aite_ecm_share_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
