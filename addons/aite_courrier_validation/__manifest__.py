# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - Validation',
    'summary': "Exécution des transitions du workflow : valider, rejeter, "
               "retourner, commenter, avec permissions par rôle et audit.",
    'description': """
AITE Courrier - Validation et actions de workflow (validation)
==============================================================

Exécute les transitions du circuit sur un courrier :

* **Valider** (transition avant) : avance d'étape, notifie, audit ``ok`` ;
* **Rejeter** : passe en état rejeté (non archivé), motif obligatoire ;
* **Retourner** (transition arrière) : repositionne sur l'étape précédente ;
* **Commenter** : message d'historique sans changement d'étape.

Les actions disponibles sont les transitions sortantes de l'étape courante,
filtrées par ``can_user_act`` (règle role_ids/user_ids). Le contrôle
d'habilitation est **systématiquement vérifié côté serveur** (jamais seulement
dans la vue) : une tentative non autorisée lève une ``AccessError`` et trace un
audit ``err``.
""",
    'version': '18.0.1.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/aite_courrier_action_wizard_views.xml',
        'views/aite_courrier_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
