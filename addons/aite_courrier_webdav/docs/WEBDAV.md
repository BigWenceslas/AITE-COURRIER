# WebDAV — `aite_courrier_webdav`

Expose l'espace documentaire AITE Courrier (`aite_courrier_ged`) via **WebDAV**,
servi directement par le serveur Odoo (même port, même authentification, aucune
dépendance externe).

## À quoi sert le WebDAV ?

Le WebDAV permet de **monter l'espace documentaire des courriers comme un lecteur
réseau** : dossiers et fichiers apparaissent dans l'**Explorateur Windows** (ou le
Finder macOS), exactement comme un partage réseau. On peut **ouvrir, modifier et
enregistrer** une pièce directement depuis Word/Excel — l'enregistrement crée
automatiquement une **nouvelle version** côté GED. C'est l'accès « bureautique »
complémentaire à l'app Documents (navigateur).

Les droits sont identiques à ceux de l'interface : confidentialité héritée et
verrouillage des pièces finalisées sont respectés selon l'utilisateur connecté.

## Arborescence exposée

```
/webdav/aite_courrier/
  └── <référence courrier>/        une collection par courrier enregistré
        └── <document>.<ext>        dernière version de chaque document
```

- La **racine** liste les courriers déjà enregistrés (avec une référence) que
  l'utilisateur a le droit de voir (confidentialité héritée).
- Chaque **courrier** est une collection contenant ses documents.
- Chaque **document** est un fichier dont le contenu est sa dernière version.

## Verbes pris en charge

| Verbe | Effet | Hook GED |
| ----- | ----- | -------- |
| `OPTIONS` | Découverte des capacités (`DAV: 1, 2`) | — |
| `PROPFIND` | Lister racine / courrier / document | `_check_courrier_access`, `_check_document_access('read')` |
| `GET` / `HEAD` | Télécharger la dernière version | `_check_document_access('read')` |
| `PUT` | Déposer un fichier → nouvelle version (v1, v2, …) | `add_version` (format/taille) |
| `DELETE` | Supprimer un document | `_check_document_access('write')` |
| `MOVE` | Renommer un document (même courrier) | `_check_document_access('write')` |
| `LOCK` / `UNLOCK` | Verrou consultatif (jeton non persisté) | `is_locked` (vraie protection) |
| `MKCOL` / `COPY` | Non autorisés (`403`) | — |
| `PROPPATCH` | Acquitté sans effet (compat. clients) | — |

Codes d'erreur : `401` (auth manquante), `403` (accès refusé / opération
interdite), `404` (introuvable), `409` (format/taille refusés), `423` (document
verrouillé — finalisé/archivé ou courrier archivé).

## Authentification

**HTTP Basic** : identifiant + mot de passe d'un utilisateur Odoo. Toutes les
opérations s'exécutent ensuite avec les droits de cet utilisateur (la
confidentialité et le verrouillage sont donc respectés sans configuration
supplémentaire). Le serveur est supposé **mono-base** (`--database` / `db_name`).

## Traçabilité

Chaque opération réseau est journalisée dans l'audit AITE Courrier avec
`source='webdav'`, ce qui permet de distinguer les accès WebDAV des accès via
l'interface.

## Exemples clients

```bash
# rclone
rclone config create courrier webdav url=https://host/webdav/aite_courrier \
    vendor=other user=jdoe pass=$(rclone obscure '****')
rclone ls courrier:

# cadaver
cadaver https://host/webdav/aite_courrier
```

## Montage dans l'Explorateur Windows

> **Explorateur → Ce PC → Connecter un lecteur réseau → Dossier :**
> `http://localhost:8169/webdav/aite_courrier`
> (identifiants = login + mot de passe d'un utilisateur Odoo).

⚠️ **Important — pourquoi ça échoue souvent en local.** Le client WebDAV intégré
de Windows (service **WebClient** / mini-redirector) **refuse par défaut
l'authentification Basic sur une connexion HTTP non chiffrée** (cas de
`http://localhost:8169`). Pour que le montage fonctionne :

1. Démarrer le service **WebClient** (`services.msc` → WebClient → Démarrer ;
   le mettre en *Automatique*).
2. Autoriser l'auth Basic sur HTTP (PowerShell **administrateur**) :
   ```powershell
   reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters ^
     /v BasicAuthLevel /t REG_DWORD /d 2 /f
   # Optionnel : lever la limite de taille de fichier (ex. 1 Go)
   reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters ^
     /v FileSizeLimitInBytes /t REG_DWORD /d 1073741824 /f
   net stop WebClient && net start WebClient
   ```
3. Reconnecter le lecteur réseau.

> **En production**, exposer Odoo en **HTTPS** (reverse proxy) : le montage Windows
> fonctionne alors sans le réglage `BasicAuthLevel`. C'est la configuration
> recommandée. macOS Finder : *Aller → Se connecter au serveur →*
> `https://host/webdav/aite_courrier`.
>
> Astuce de test rapide sans montage : `curl` (voir scénarios) valide que le
> service répond, indépendamment des restrictions du client Windows.

## Architecture

- `models/aite_courrier_webdav.py` — service `aite.courrier.webdav` (logique
  métier, **couverte par les tests**).
- `controllers/webdav.py` — adaptateur HTTP : authentification, mapping des
  verbes, formatage des réponses (XML multistatus, dates RFC 1123).

> La logique métier est testée au niveau ORM. La couche HTTP (dialogue réel avec
> un client WebDAV) se valide sur une instance Odoo lancée (port 8169) — voir le
> README et `docs/produits/AITE_Courrier_scenarios_test.md`.
