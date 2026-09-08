# Spécification de tests — aite_ecm_nextcloud (client Nextcloud simulé)

| Cas | Attendu |
|---|---|
| T01 Chemin cible | Document « Contrat de maintenance » dans « Juridique et contrats » → `Juridique et contrats/DOC-… - Contrat de maintenance/contrat.pdf` ; caractères interdits remplacés |
| T02 Envoi à la création de version | `add_version` (mode miroir, envoi immédiat) → `ensure_dir` + `upload` appelés ; `nc_path`, `nc_file_id`, `nc_etag` renseignés ; état `synced` ; audit source `nextcloud` |
| T03 Import d'une modification | ETag Nextcloud différent → `download` → nouvelle version v2 attribuée au réservant ; état `synced` ; ETag mis à jour |
| T04 ETag inchangé | `_nc_pull` sans changement → aucune version créée |
| T05 Conflit | Document finalisé modifié dans Nextcloud → pas de version, état `conflict`, message dans le fil |
| T06 Contenu identique | Fichier réenregistré sans changement (même SHA-256) → pas de version, ETag mis à jour |
| T07 Reclassement | Changement de dossier → état `todo` ; envoi suivant → `move` appelé vers le nouveau chemin |
| T08 Sondage | Listing du dossier avec ETag différent → import déclenché ; ETag racine inchangé → aucun appel |
| T09 Lien public | `action_nc_share` → `create_public_link` avec mot de passe et date d'expiration ; `nc_share_url` stocké ; révocation → `delete_share` |
| T10 Webhook | Requête sans secret → 403 ; avec secret et `event.node.id` connu → document marqué `pull` |
| T11 Connecteur désactivé | Mode `off` : `add_version` ne planifie rien, `action_nc_push` refuse |
