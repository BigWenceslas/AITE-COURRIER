# Spécification de tests — aite_ecm_webdav

| Cas | Attendu |
|---|---|
| T01 Arborescence | PROPFIND racine → dossiers racine + « Sans classement » ; PROPFIND d'un dossier → sous-dossiers et fichiers `REF - Titre.ext` |
| T02 Lecture | GET d'un fichier → contenu de la dernière version, ETag = SHA-256 |
| T03 Enregistrement | PUT sur un fichier existant → nouvelle version attribuée à l'utilisateur ; PUT d'un fichier inconnu → nouveau document dans le dossier |
| T04 Verrou | LOCK → document réservé par l'utilisateur ; PUT par un autre utilisateur → 423 ; UNLOCK → libéré |
| T05 Déplacement | MOVE vers un autre dossier avec nouveau nom → dossier et titre mis à jour |
| T06 URI Office | `office_uri` = `ms-word:ofe|u|…/webdav/aite_ecm/Juridique et contrats/DOC-… - Contrat.docx` ; PDF → pas d'URI |
| T07 Sécurité | Sans authentification → 401 ; document confidentiel d'un autre → absent du listing |
