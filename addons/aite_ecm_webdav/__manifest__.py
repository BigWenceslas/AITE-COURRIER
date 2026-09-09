# -*- coding: utf-8 -*-
{
    'name': 'AITE ECM - Lecteur réseau et ouverture dans Office',
    'summary': "Serveur WebDAV du plan de classement ECM : lecteur réseau, "
               "ouverture directe dans Word / Excel / PowerPoint (édition et "
               "enregistrement → nouvelle version), verrous Office ↔ réservation.",
    'description': """
AITE ECM - Lecteur réseau et ouverture dans Office
==================================================

* Le plan de classement ECM est servi en **WebDAV** (``/webdav/aite_ecm``) :
  montable comme lecteur réseau (Windows, macOS, Linux) ou dans l'explorateur
  de fichiers. Chaque fichier porte la référence et le titre du document.
* **Ouvrir dans Word / Excel / PowerPoint** depuis la fiche ou l'explorateur :
  l'application de bureau ouvre le fichier directement sur le serveur ;
  chaque enregistrement crée une **nouvelle version** ECM, attribuée à
  l'utilisateur ; le verrou posé par Office devient une **réservation**.
* Dépôt d'un fichier dans un dossier du lecteur → document ECM créé ;
  renommage / déplacement → titre / dossier mis à jour ; suppression →
  corbeille ; création de dossier → dossier de classement (managers).
* Mêmes droits que l'application (dossiers, confidentialité, verrous).

Compatible Odoo Community.
""",
    'version': '18.0.2.0.0',
    'category': 'AITE/ECM',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'license': 'OEEL-1',
    'depends': ['aite_ecm_document'],
    'data': ['views/aite_ecm_document_views.xml'],
    'installable': True,
    'auto_install': False,
}
