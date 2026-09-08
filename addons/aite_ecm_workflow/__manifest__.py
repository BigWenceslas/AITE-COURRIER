# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Workflow polymorphe',
    'summary': "Rend le moteur de circuits (étapes, rôles, SLA, transitions) "
               "réutilisable sur tout objet via un mixin, avec historique "
               "générique et assistant d'action.",
    'description': """
AITE ECM - Workflow polymorphe
==============================

Le moteur de circuits de la suite Courrier (circuits, étapes habilitées,
délais SLA, transitions avant/arrière, commentaire obligatoire) devient une
brique de plateforme :

* un circuit déclare l'**objet cible** (``res_model``) : courrier, dossier
  métier… ; le type de courrier n'est plus obligatoire ;
* le mixin ``aite.workflow.mixin`` apporte à tout modèle le **runtime** :
  lancement, transition contrôlée côté serveur (``step.can_user_act``),
  rejet motivé, échéance SLA et indicateur de retard, activités planifiées,
  **historique générique** (``aite.workflow.history``) ;
* un **assistant d'action** unique (choix de la transition + commentaire)
  sert tous les objets.

* **Circuits sur les documents ECM** : un circuit actif par type de document
  (rédaction → vérification → approbation…), boutons Lancer / Traiter /
  Rejeter sur la fiche et dans l'explorateur, historique, échéances SLA ;
  en fin de circuit le document est **finalisé** automatiquement (option du
  type). Un circuit « Procédure » est livré.

Le courrier conserve son runtime v1 (même modèle de circuits, mêmes
habilitations) ; sa migration vers le mixin est planifiée en v2.1.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_workflow',
        'aite_ecm_document',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/aite_workflow_views.xml',
        'views/aite_ecm_document_views.xml',
        'wizard/aite_workflow_action_wizard_views.xml',
        'data/aite_ecm_document_circuit_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
