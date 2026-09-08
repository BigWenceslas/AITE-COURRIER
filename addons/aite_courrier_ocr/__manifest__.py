# -*- coding: utf-8 -*-
{
    'name': 'AITE Courrier - OCR & recherche plein texte',
    'summary': "Extraction du texte des pièces (PDF, images) en tâche de "
               "fond et recherche plein texte sur le contenu des courriers.",
    'description': """
AITE Courrier - OCR & recherche plein texte
===========================================

Standard du marché GEC (Elise, QALITEL, Maarch) : retrouver un courrier par
le **contenu** de ses pièces, pas seulement par ses métadonnées.

Fonctionnement
--------------
* À chaque téléversement d'une version PDF ou image, l'extraction est mise
  **en file d'attente** (état « En attente ») ; un cron la traite par lots
  toutes les 10 minutes — l'utilisateur n'attend jamais.
* PDF : le texte natif est extrait en priorité (pypdf, embarqué avec Odoo).
  Si la page est un scan sans couche texte, repli automatique sur l'OCR
  Tesseract (si installé).
* Images (JPG/PNG/TIFF) : OCR Tesseract (si installé).
* Le texte extrait alimente le champ ``index_content`` de la pièce jointe
  (recherche native Odoo) et un champ de recherche « Contenu des pièces »
  dans l'espace Courrier.

Dépendances **optionnelles** (repli propre si absentes — l'extraction PDF
native fonctionne sans elles) :

* binaires : ``tesseract-ocr`` (+ ``tesseract-ocr-fra``), ``poppler-utils`` ;
* python : ``pytesseract``, ``pdf2image``, ``Pillow``.

Paramètres système : ``aite_courrier.ocr_max_pages`` (défaut : 10 pages
OCRisées par PDF).
""",
    'version': '18.0.1.0.0',
    'category': 'AITE/Courrier',
    'author': 'AITE Consulting',
    'website': 'https://www.aite-consulting.com',
    'maintainer': 'AITE Consulting',
    'license': 'OEEL-1',
    'depends': [
        'aite_courrier_ged',
    ],
    'data': [
        'data/ir_cron_data.xml',
        'views/aite_courrier_document_views.xml',
        'views/aite_courrier_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
