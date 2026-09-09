# Spécification de tests — aite_ecm_office

(l'arborescence WebDAV, les verrous et les déplacements sont couverts par `aite_ecm_webdav`.)

| Cas | Attendu |
|---|---|
| T03 LOCK ↔ réservation | LOCK réserve le document pour l'utilisateur ; LOCK par un autre → 423 ; UNLOCK libère ; PUT par un autre pendant la réservation → 423 |
| T04 MOVE | Renommage → titre modifié ; déplacement vers un autre dossier ; « enregistrer puis déplacer » (temporaire → cible) → version sur la cible, temporaire à la corbeille |
| T05 URI Office | `office_uri` = `ms-word:ofe|u|<base>/webdav/aite_ecm/…docx` ; Excel / PowerPoint selon l'extension ; PDF → aucun URI |
| T06 Google (simulé) | `action_open_google` sans jeton → redirection OAuth ; avec jeton → dépôt Drive, URL d'édition, réservation ; modification côté Google → `_gdrive_pull` crée v2 ; `action_google_finish` supprime la copie et libère |
| T07 WOPI (simulé) | Découverte simulée : `_editor_urlsrc('docx','edit')` renvoie l'URL Writer ; `_issue` crée un jeton, `_resolve` le retrouve (et refuse un jeton expiré) ; `check_file_info` expose nom, taille, version, `UserCanWrite` ; `get_file` renvoie le contenu ; LOCK réserve le document, LOCK d'un autre utilisateur → 409 avec `X-WOPI-Lock` ; `put_file` crée v2 ; UNLOCK libère ; `wopi_available` vrai pour docx, faux pour pdf sans serveur |
