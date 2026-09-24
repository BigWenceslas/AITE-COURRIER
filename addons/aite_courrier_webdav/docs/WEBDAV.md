# WebDAV — `aite_courrier_webdav`

Expose l'espace documentaire AITE Courrier (`aite_courrier_ged`) via **WebDAV**,
servi directement par le serveur Odoo (même port, même authentification, aucune
dépendance externe).

## À quoi sert le WebDAV ?

Le WebDAV permet de **monter l'espace documentaire des courriers comme un lecteur
réseau** : dossiers et fichiers apparaissent dans l'**Explorateur Windows** (ou le
Finder macOS), exactement comme un partage réseau. On peut **ouvrir, modifier et
enregistrer** une pièce directement depuis Word/Excel — l'enregistrement crée
automatiquement une **nouvelle version** côté GED. Sous Windows, Word, Excel et
PowerPoint exigent pour cela que le poste autorise le serveur (voir *Ouvrir une
pièce dans Word, Excel, PowerPoint*). C'est l'accès « bureautique »
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
Le serveur n'offre que Basic : Word, Excel et PowerPoint sous Windows bloquent
cette méthode par défaut, en HTTPS comme en HTTP (voir *Ouvrir une pièce dans
Word, Excel, PowerPoint*).

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
   reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
     /v BasicAuthLevel /t REG_DWORD /d 2 /f
   # Optionnel : lever la limite de taille de fichier (ex. 1 Go)
   reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
     /v FileSizeLimitInBytes /t REG_DWORD /d 1073741824 /f
   Restart-Service WebClient
   ```
   (En PowerShell, la ligne se continue par l'accent grave `` ` ``, en dernier
   caractère de la ligne ; le `^` et le `&&` de `cmd` n'y fonctionnent pas,
   `&&` n'existant qu'à partir de PowerShell 7.)
3. Reconnecter le lecteur réseau.

> **En production**, exposer Odoo en **HTTPS** (reverse proxy) : le montage Windows
> fonctionne alors sans le réglage `BasicAuthLevel`, et le mot de passe ne
> circule plus en clair. C'est la configuration recommandée. Elle ne lève pas,
> en revanche, le blocage d'Office (section suivante). macOS Finder : *Aller →
> Se connecter au serveur →* `https://host/webdav/aite_courrier`.
>
> Astuce de test rapide sans montage : `curl` (voir scénarios) valide que le
> service répond, indépendamment des restrictions du client Windows.

## Ouvrir une pièce dans Word, Excel, PowerPoint

Word ne s'appuie pas sur la connexion du lecteur réseau : il convertit le
chemin de la pièce en adresse `http(s)://…/webdav/aite_courrier/…` et
télécharge lui-même le fichier, avec sa propre authentification. Or, depuis la
version 2311 (Current Channel, décembre 2023 ; Monthly Enterprise Channel,
janvier 2024 ; Semi-Annual Enterprise Channel 2402, juillet 2024 ; Office
2016, 2019 et 2021 vendus au détail, au rythme du Current Channel), Word,
Excel et PowerPoint sous Windows bloquent par défaut les demandes
d'identifiants en authentification **Basic** — la seule que propose ce
serveur. Ils affichent « Microsoft Office a bloqué l'accès aux … car la source
utilise une méthode de connexion qui peut être non sécurisée ». Le blocage
porte sur la **méthode**, pas sur le transport : il s'applique en `https`
comme en `http`. Les versions d'Office en licence en volume (LTSC) ne sont pas
concernées. L'Explorateur, lui, n'est pas concerné : le lecteur se parcourt,
et l'on y copie ou renomme des fichiers, même quand Word refuse d'ouvrir.

Le remède est la stratégie *Allow specified hosts to show Basic
Authentication prompts to Office apps*. Sur un poste, son équivalent
registre :

1. Enregistrer puis **fermer toutes les applications Office** (Word, Excel,
   PowerPoint, Outlook).
2. Ouvrir PowerShell **dans la session du compte Windows qui utilise Word** —
   *en tant qu'administrateur* si ce compte est administrateur du poste (les
   sources Microsoft indiquent que des droits d'administration sont requis),
   mais jamais avec un autre compte : `HKCU` désignerait alors le profil de
   cet autre compte. Puis :
   ```powershell
   # Indispensable, en http comme en https : autoriser l'hôte à demander des identifiants
   reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f

   # En http seulement : ancienne clé d'Office, qui autorise Basic hors SSL
   reg add HKCU\Software\Microsoft\Office\16.0\Common\Internet `
     /v BasicAuthLevel /t REG_DWORD /d 2 /f
   ```
3. Rouvrir Word, puis la pièce : Word **demande des identifiants** au lieu de
   bloquer ; saisir le login Odoo et son mot de passe.

- **Hôtes.** `/d` liste des noms d'hôtes séparés par `;`, sans `http://` ni
  `https://`. La forme `hôte:port` s'ajoute par prudence, aucune source ne
  disant si le port compte. La commande reprend le port par défaut d'Odoo
  (`8069`) : pour l'instance de test de ce document (port `8169`), écrire
  `localhost;localhost:8169` ; en production, le nom du serveur (par exemple
  `ecm.client.fr`). Garder les **guillemets** : en PowerShell, `;` sépare deux
  instructions et la liste serait tronquée. `/f` remplace une valeur
  existante : en reprendre d'abord les hôtes (`reg query` sur la même clé).
- **Ancienne clé `BasicAuthLevel` d'Office** (`…\Common\Internet`, distincte
  de celle du service WebClient) : elle reste utile sur une instance en
  `http`, mais **ne suffit plus** depuis la version 2311 ; en `https`, elle
  est inutile.
- **Sur un parc**, poser la même liste par stratégie de groupe (*User
  Configuration › Policies › Administrative Templates › Microsoft Office 2016
  › Security Settings*, modèles d'administration Office 5359.1000 ou plus
  récents) ou par Cloud Policy.
- **Limites.** Selon son libellé, la stratégie ne s'applique qu'aux versions
  d'Office sur abonnement. Une Cloud Policy du tenant Microsoft 365
  (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`) ou le Baseline
  Security Mode peuvent primer sur la valeur locale. Microsoft ne recommande
  cette autorisation qu'à titre transitoire.

## Architecture

- `models/aite_courrier_webdav.py` — service `aite.courrier.webdav` (logique
  métier, **couverte par les tests**).
- `controllers/webdav.py` — adaptateur HTTP : authentification, mapping des
  verbes, formatage des réponses (XML multistatus, dates RFC 1123).

> La logique métier est testée au niveau ORM. La couche HTTP (dialogue réel avec
> un client WebDAV) se valide sur une instance Odoo lancée (port 8169) — voir le
> README et `docs/produits/AITE_Courrier_scenarios_test.md`.
