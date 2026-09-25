# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - Signature électronique (OCA)',
    'summary': "Signature des courriers sur Odoo Community, via le module "
               "OCA sign_oca : demande depuis le courrier, étapes « Signature "
               "requise », PDF signé versé en GED, audit.",
    'description': """
AITE Courrier - Signature électronique (OCA)
============================================

Signature des courriers sur **Odoo Community**, via le module communautaire
OCA ``sign_oca`` (livré dans le dossier ``oca`` du paquet de la suite).

* Case **Signature requise** sur une étape de circuit ; bouton **Demander la
  signature** pour qui peut agir sur l'étape.
* Le responsable du courrier signe depuis un lien reçu par e-mail, sans
  compte Odoo ; le PDF signé devient une nouvelle version de la pièce.
* Aucune transition en avant sans la signature du passage en cours sur
  l'étape ; chaque refus est tracé au journal d'audit.
* Accès aux demandes, aux jetons de signature et au téléchargement
  restreints par rapport à ``sign_oca``.

Exclut ``aite_courrier_sign`` (variante Enterprise, Odoo Sign). Voir le
README du module et ``docs/TUTORIEL_SIGNATURE_COMMUNITY.md``.
""",
    'version': '18.0.1.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    # Hérite du code de sign_oca (AGPL-3) : même licence.
    'license': 'AGPL-3',
    'depends': [
        'aite_courrier_core',
        'aite_courrier_workflow',
        'aite_courrier_ged',
        'aite_courrier_validation',
        'sign_oca',
    ],
    # Même champ require_signature, même garde : jamais les deux ensemble.
    'excludes': ['aite_courrier_sign'],
    'data': [
        'security/sign_oca_rules.xml',
        'views/aite_workflow_views.xml',
        'views/aite_courrier_views.xml',
        'views/sign_oca_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
