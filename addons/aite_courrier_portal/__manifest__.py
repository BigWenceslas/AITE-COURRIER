# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - Portail externe',
    'summary': "Portail natif Odoo : dépôt de demandes par les tiers, suivi "
               "de l'avancement (étapes du circuit) et accès aux pièces de "
               "leurs courriers.",
    'description': """
AITE Courrier - Portail externe (tiers / administrés)
=====================================================

Réponse aux portails citoyens du marché (Maarch, Cotranet) avec le portail
**natif** d'Odoo — cohérent avec le positionnement « sans brique externe ».

Fonctionnalités
---------------
* **Mes courriers** (`/my/courriers`) : chaque utilisateur portail voit les
  courriers dont il est l'expéditeur (lui-même ou sa société), avec
  référence, objet, date et statut public.
* **Déposer une demande** (`/my/courriers/new`) : objet, nature de la
  demande (types « Entrant »), description et pièces jointes ; la demande
  crée un courrier en brouillon (mêmes règles que la capture e-mail : les
  pièces deviennent des documents GED versionnés), que l'agent qualifie
  puis lance dans son circuit.
* **Suivi d'avancement** : la fiche affiche le parcours du circuit avec
  l'étape courante mise en évidence, et les pièces téléchargeables
  (jetons d'accès sécurisés).
* **Confidentialité** : règle d'enregistrement dédiée au portail (lecture
  seule, limitée aux courriers dont le tiers est l'expéditeur) ; le fil de
  discussion interne n'est PAS exposé.
* Chaque dépôt est tracé au journal d'audit (source « Système »).

Prérequis : inviter les tiers en tant qu'utilisateurs **Portail**
(Paramètres > Utilisateurs > Accorder l'accès au portail).
""",
    'version': '18.0.1.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_core',
        'aite_courrier_ged',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/aite_courrier_portal_security.xml',
        'views/portal_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
