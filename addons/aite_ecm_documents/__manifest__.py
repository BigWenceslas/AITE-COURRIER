# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Explorateur Documents',
    'summary': "Fait de l'app Documents d'Odoo l'explorateur de fichiers de "
               "l'ECM : espaces de travail = plan de classement, une carte par "
               "document (dernière version, vignette), étiquettes synchronisées, "
               "fichiers déposés dans Documents adoptés comme documents ECM.",
    'description': """
AITE ECM - Explorateur Documents
================================

L'application **Documents** d'Odoo Enterprise (espaces de travail, cartes
avec vignettes, étiquettes, glisser-déposer, demandes de documents, partage)
devient l'**explorateur de fichiers** de l'ECM ; la fiche ECM reste la vue
« métier » (métadonnées, versions, réservation, relations, circuits).

* **Plan de classement = espaces de travail** : chaque dossier ECM possède
  son dossier Documents (créé à l'installation et à chaque création), les
  déplacements sont répercutés.
* **Une carte par document** : les versions successives mettent à jour la
  même carte (Documents conserve l'historique), plus de carte par fichier ;
  titre, dossier et étiquettes synchronisés ; « Attaché à » ouvre la fiche ECM.
* **Adoption** : un fichier déposé dans Documents sous l'espace « ECM »
  (bouton *Charger*, glisser-déposer, réponse à une *Demande*) devient
  automatiquement un document ECM classé dans le dossier correspondant ;
  un fichier remplacé dans Documents crée une nouvelle version ECM.
* Menu **ECM › Documents › Explorateur de fichiers**, bouton
  **Explorateur** sur la fiche, vignette Documents dans le kanban ECM.
* Un fichier géré par l'ECM ne se supprime pas depuis Documents : la
  corbeille ECM reste le point de passage (traçabilité).
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document', 'documents'],
    'data': [
        'data/aite_ecm_documents_data.xml',
        'views/aite_ecm_documents_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': True,
}
