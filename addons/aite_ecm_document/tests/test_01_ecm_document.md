# Spécification de tests — aite_ecm_document

| Cas | Attendu |
|---|---|
| T01 Création avec type | Référence DOC-AAAA-NNNNN attribuée ; dossier et confidentialité par défaut du type appliqués |
| T02 add_version | v1 puis v2 créées ; SHA-256 calculé ; dernière version = v2 |
| T03 Extension refusée | `.exe` → ValidationError |
| T04 Doublon | Même contenu sur un second document → `duplicate_count == 1` de part et d'autre |
| T05 Check-out | Réservé par A : `add_version` par B → AccessError ; libération par B → UserError ; libération par manager → OK |
| T06 Verrou finalisé | Document finalisé : `add_version` → AccessError ; suppression d'une version → UserError |
| T07 Corbeille | `action_trash` → `active=False` ; restauration ; purge du cron après expiration |
| T08 Confidentialité | Document Confidentiel : lecture refusée à un agent non propriétaire, autorisée au manager |
| T09 Droits de dossier | Dossier réservé en écriture au groupe Manager : création par un agent → AccessError |
| T10 Mixin | `res.partner.ecm_document_count` reflète les documents rattachés |
| T11 Droits nominatifs (dossier) | Dossier réservé au groupe Manager + lectrice nommée : l'agent nommé lit, l'autre agent non ; rédacteur nommé → création possible |
| T12 Partage nominatif (document) | Document Confidentiel partagé en lecture avec un agent : lecture OK, `add_version` refusée ; partagé en écriture : `add_version` OK ; résumé d'accès renseigné |
| T13 Numérisation | Deux images → `_images_to_pdf` produit un PDF de 2 pages ; dépôt surveillé : fichier importé, déplacé dans `traites` |
