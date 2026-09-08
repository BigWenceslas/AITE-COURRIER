# Spécification de tests — explorateur natif (aite_ecm_document)

| Cas | Attendu |
|---|---|
| T01 Métadonnées | `explorer_meta` renvoie dossiers (avec compteurs et droit d'écriture), étiquettes, types, statuts, corbeille |
| T02 Recherche | filtre par dossier (sous-dossiers inclus), par étiquette, par texte (titre / référence / nom de fichier), tri, pagination, corbeille |
| T03 Vignette image | version PNG → vignette serveur (`thumbnail_status = present`) ; PDF → `client` ; PDF puis `explorer_set_thumbnail` → `present` |
| T04 Actions groupées | `explorer_bulk` finalise deux documents ; l'erreur d'un troisième (sans fichier) est renvoyée sans bloquer les autres |
| T05 Dossier | `explorer_create_folder` sous un parent ; agent sans droit → AccessError |
| T06 Droits | un agent ne voit pas dans `explorer_search` un document Confidentiel d'un autre propriétaire |
