# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - Capture e-mail',
    'summary': "Création automatique de courriers depuis une boîte e-mail "
               "dédiée (alias / passerelle mail) avec archivage des pièces "
               "jointes dans la GED.",
    'description': """
AITE Courrier - Capture e-mail (passerelle entrante)
====================================================

Standard du marché GEC (cf. benchmark : MailFeeder d'Elise, capture
multicanale de Maarch) : tout e-mail envoyé à l'alias dédié (par défaut
``courrier@<domaine>``) crée automatiquement un **courrier en brouillon** :

* objet du courrier = sujet de l'e-mail ;
* expéditeur (nom, e-mail) extrait de l'en-tête ``From`` ; le contact
  ``res.partner`` est lié s'il est reconnu ;
* type par défaut : le type marqué « Type par défaut (capture e-mail) »,
  sinon le premier type de catégorie « Entrant » ;
* les pièces jointes aux formats autorisés par la GED deviennent des
  **documents versionnés** du courrier (v1) — les petites images
  (signatures, logos) sont ignorées ;
* le corps de l'e-mail reste consultable dans le fil de discussion ;
* chaque capture est tracée dans le journal d'audit (source « Système »).

L'agent courrier n'a plus qu'à qualifier le brouillon puis lancer le circuit.

Configuration : Paramètres > Technique > E-mail > Alias (``courrier``) ;
serveur entrant (fetchmail) à configurer selon l'hébergement.
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
        'data/mail_alias_data.xml',
        'views/aite_courrier_type_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
