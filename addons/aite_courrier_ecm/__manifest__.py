# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Pont Courrier',
    'summary': "Les pièces de courrier deviennent des documents ECM : mêmes "
               "métadonnées, mêmes droits, mêmes circuits, même explorateur ; "
               "reprise des pièces existantes à l'installation.",
    'description': """
AITE ECM - Pont Courrier
========================

Le courrier devient la première **application de contenu** de la plateforme :

* chaque pièce de courrier (``aite.courrier.document``) est **reflétée** par
  un document ECM rattaché au courrier (``res_model='aite.courrier'``), avec
  les mêmes versions (fichiers non dupliqués : la pièce jointe est partagée),
  la confidentialité du courrier et un classement automatique
  ``Courrier/<année>/<référence>`` ;
* le miroir suit les versions, le renommage, la finalisation et la corbeille ;
* les documents de courrier apparaissent dans l'**explorateur ECM**, la
  recherche plein texte, l'analyse du fonds, les partages, l'API et — avec
  ``aite_ecm_records`` — la politique de conservation ;
* un bouton **Documents ECM** sur le courrier, un lien retour sur le document.

Installé automatiquement quand la GED courrier et l'ECM sont présents.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': ['aite_courrier_ged', 'aite_ecm_document'],
    'data': [
        'data/aite_courrier_ecm_data.xml',
        'views/aite_courrier_ecm_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': True,
}
