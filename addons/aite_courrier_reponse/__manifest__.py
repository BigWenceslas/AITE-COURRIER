# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - Modèles de réponse',
    'summary': "Bibliothèque de modèles de courriers sortants avec champs de "
               "fusion, génération PDF à en-tête société versionnée en GED, "
               "envoi à l'expéditeur et création du courrier sortant lié.",
    'description': """
AITE Courrier - Modèles de réponse (courrier sortant)
=====================================================

Standard du marché GEC (bibliothèques de modèles de QALITEL / Maarch /
Elise) : répondre à un courrier en quelques clics, sans quitter l'application.

Fonctionnement
--------------
* **Bibliothèque de modèles** paramétrable (Configuration > Modèles de
  réponse) : objet et corps avec **champs de fusion** au format
  ``{{ object.champ }}`` (référence, expéditeur, service, dates…), modèles
  restreignables par type de courrier.
* **Assistant « Répondre »** depuis un courrier : choix du modèle, fusion
  immédiate, corps librement retouchable avant génération.
* **Génération PDF** sur l'en-tête société (mise en page standard Odoo
  ``web.external_layout``) ; le PDF devient une **version GED** du courrier
  (ou du courrier sortant lié).
* Options : **envoi par e-mail** à l'expéditeur (PDF joint) et **création du
  courrier sortant lié** (type « Sortant » au choix), prêt à suivre son
  circuit Préparation → … → Émission. Lien croisé « Réponse à / Réponses »
  entre les deux courriers.
* Chaque génération/envoi est tracé (chatter + journal d'audit).

3 modèles livrés : réponse standard, demande de pièces complémentaires,
notification de clôture.
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
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_reponse_templates.xml',
        'views/aite_courrier_reponse_template_views.xml',
        'views/aite_courrier_views.xml',
        'wizard/aite_courrier_reponse_wizard_views.xml',
        'data/reponse_template_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
