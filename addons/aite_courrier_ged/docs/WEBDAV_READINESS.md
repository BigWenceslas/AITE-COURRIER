# WebDAV readiness — `aite_courrier_ged`

> Ce module **n'implémente PAS** WebDAV : il fournit les points d'accroche.
> Le WebDAV est désormais implémenté dans le module **`aite_courrier_webdav`**
> (contrôleur Odoo intégré, cf. `aite_courrier_webdav/docs/WEBDAV.md`), qui
> consomme exactement les hooks ci-dessous. Aucun code WebDAV ne doit être
> ajouté ici.

## Points d'accroche prévus

### 1. `aite.courrier.document._check_document_access(operation, user=None)`
Contrat d'accès **unique** et déjà testé, à appeler tel quel depuis le provider :

- `operation='read'` → autorise la lecture selon la **confidentialité héritée**
  du courrier (délègue à `aite.courrier._check_courrier_access`, logique
  centralisée côté `core`).
- `operation='write'` / `'unlink'` → refuse si le document est **verrouillé**
  (`is_locked`), en plus du respect de la confidentialité.

Le provider WebDAV mappera :
- `GET` / `PROPFIND` → `_check_document_access('read')`
- `PUT` / `DELETE` / `MOVE` → `_check_document_access('write')`

### 2. `aite.courrier.document.is_locked`
Booléen stocké (vrai si version finale/archivée ou courrier archivé). Le
provider doit refuser toute écriture (`PUT`/`DELETE`) sur une ressource dont le
document est verrouillé → réponse `423 Locked` ou `403 Forbidden`.

### 3. `confidentiality_id` hérité
Champ `related` stocké recalculé automatiquement depuis le courrier. Le provider
n'a donc **aucune logique de confidentialité à dupliquer** : il s'appuie sur
`_check_document_access`.

### 4. Audit `source='webdav'`
Le journal d'audit (`aite.courrier.audit.log._log`) accepte un paramètre
`source` (`'ui'`, `'webdav'`, `'system'`). Le provider devra tracer ses
opérations avec `source='webdav'` (ex. « Ajout pièce jointe », « Suppression
pièce jointe ») pour distinguer les accès réseau des accès interface.

### 5. Versionnage
`aite.courrier.document.add_version(filename, datas)` crée une version
`v(n+1)` sans supprimer les précédentes, avec contrôle de format (PDF/DOCX/XLSX)
et de taille (≤ 50 Mo). Un `PUT` WebDAV se traduira par un appel à cette méthode.

## Implémenté dans `aite_courrier_webdav`
- Contrôleur Odoo intégré (arborescence de collections par courrier).
- Authentification HTTP Basic / mapping vers `res.users`.
- Mapping des verbes WebDAV vers les méthodes ci-dessus.
