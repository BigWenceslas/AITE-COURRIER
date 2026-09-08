# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Connecteur Nextcloud (pièces de courrier)',
    'summary': "Étend le connecteur Nextcloud aux pièces de courrier "
               "(arborescence Courrier/<année>/<référence>).",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_nextcloud', 'aite_courrier_ged'],
    'data': ['views/aite_courrier_document_views.xml'],
    'installable': True,
    'auto_install': True,
}
