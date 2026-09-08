# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - GED dans l\'app Documents',
    'summary': "Reflète les pièces de courrier dans l'app Documents "
               "(Enterprise) : un espace « Courrier », un dossier par courrier, "
               "fichiers non dupliqués. Installé automatiquement avec Documents.",
    'description': """
AITE Courrier - GED dans l'app Documents
========================================

Passerelle Enterprise de la GED courrier : chaque pièce (``ir.attachment``)
ajoutée à un courrier apparaît dans l'app **Documents** sous l'espace
« Courrier », dans un dossier portant la référence du courrier (créé au
premier fichier, renommé avec la référence). Le socle ``aite_courrier_ged``
reste compatible Odoo Community.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'license': 'OEEL-1',
    'depends': ['aite_courrier_ged', 'documents'],
    'data': [
        'data/documents_workspace_data.xml',
        'views/aite_courrier_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': True,
}
