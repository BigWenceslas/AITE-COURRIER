# aite_ecm_document — socle ECM (Community et Enterprise)

Module application « ECM ». **Aucune dépendance Enterprise** : il s'installe
sur Odoo 18 Community comme sur Enterprise (dépendances : `aite_courrier_base`,
`mail`, `contacts`).

## Explorateur de fichiers natif

Menu **ECM › Documents › Explorateur** (action cliente OWL, `static/src/explorer`) :

* panneau latéral : espace de travail (plan de classement dépliable, compteurs
  cumulés), statut, mes documents, réservés, corbeille, types, étiquettes,
  « rattaché à » ;
* cartes à vignettes (images : générées côté serveur ; PDF : générées par le
  navigateur avec pdf.js livré par Odoo) ou vue liste, tri, recherche
  plein texte (titre, référence, nom de fichier, contenu indexé), pagination ;
* **Charger** (multi-fichiers) et **glisser-déposer** dans le dossier courant,
  nouvelle version depuis l'inspecteur, création de dossier ;
* inspecteur (sélection simple) : fiche, aperçu (PDF, images, texte),
  téléchargement, réserver / libérer, finaliser, partager, corbeille /
  restaurer ; sélection multiple : finaliser, corbeille, déplacer, étiqueter,
  typer ;
* toutes les règles ECM s'appliquent (dossiers, confidentialité, verrous) :
  le client ne fait qu'appeler `explorer_meta`, `explorer_search`,
  `explorer_bulk`, `explorer_create_folder`, `explorer_set_thumbnail` et le
  contrôleur `/ecm/explorer/upload`.

## Intégration Enterprise

Sur Enterprise, `aite_ecm_documents` (auto-installé avec l'app Documents)
ajoute le miroir dans l'app Documents (espaces de travail, adoption des
fichiers déposés, une carte par document). Les deux explorateurs coexistent.

## Tests

`--test-tags /aite_ecm_document` : 10 cas socle (`tests/test_01_ecm_document.md`)
et 6 cas explorateur (`tests/test_02_explorer.md`).
