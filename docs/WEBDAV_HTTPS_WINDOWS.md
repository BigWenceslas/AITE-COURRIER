# WebDAV en HTTPS — poste ou serveur Windows

> Pourquoi le chiffrement n'est pas un luxe pour l'espace documentaire, et
> comment le mettre en place devant Odoo 18 sur Windows, en quelques minutes
> pour un poste de test, proprement pour une mise en production.

---

## 1. Ce que HTTPS débloque

Sur une instance en `http://`, trois obstacles apparaissent l'un après
l'autre — tous côté client, tous levés d'un coup par le chiffrement :

| Obstacle | En `http` | En `https` |
| --- | --- | --- |
| Montage du lecteur réseau | refusé, sauf clé de registre `BasicAuthLevel` sur chaque poste | fonctionne sans réglage |
| **Ouvrir dans Word / Excel** | **bloqué par Office** : « la source utilise une méthode de connexion qui peut être non sécurisée » | fonctionne |
| Fichiers de plus de 50 Mo | limite du client Windows, clé `FileSizeLimitInBytes` | limite du serveur seulement |
| Mot de passe sur le réseau | **en clair à chaque requête** | chiffré |

Ce dernier point suffirait : un client WebDAV présente ses identifiants à
*chaque* requête. En clair, sur un réseau d'entreprise, ce n'est pas tenable
au-delà d'un poste de test isolé.

Odoo ne sait pas servir HTTPS lui-même : on place un **reverse proxy** devant.

---

## 2. Poste de test ou instance interne : Caddy

Caddy tient en un exécutable, émet son propre certificat et sait l'installer
dans le magasin de la machine — ce qui est exactement ce qui manque avec un
certificat auto-signé posé à la main : sans autorité de confiance, Word le
refuse comme il refusait le `http`.

1. Télécharger l'exécutable depuis <https://caddyserver.com/download> et le
   renommer, car il arrive sous le nom de sa plateforme :

```powershell
Rename-Item .\caddy_windows_amd64.exe caddy.exe
```

2. Copier [`exemples/Caddyfile`](./exemples/Caddyfile) à côté.
3. **Démarrer Caddy**, en PowerShell **administrateur**, dans ce dossier :

```powershell
.\caddy.exe run --config .\Caddyfile
```

Au premier démarrage sur `localhost`, Caddy crée son autorité interne et
l'installe dans le magasin de certificats de la machine — c'est pour cela
qu'il faut être administrateur. Laisser cette fenêtre ouverte : Caddy tourne
tant qu'elle vit.

4. Si le journal n'annonce pas l'installation de l'autorité, la forcer depuis
   une **seconde** fenêtre administrateur, dans le même dossier :

```powershell
.\caddy.exe trust
```

> **`caddy trust` s'adresse à une instance qui tourne déjà**, par son API
> d'administration (port 2019). Lancé en premier, il échoue sur
> `dial tcp [::1]:2019 … connexion refusée`. Toujours démarrer avant de faire
> confiance.

Odoo est alors servi sur `https://localhost`. Pour un service permanent,
`caddy.exe start` ou l'installation en service Windows.

---

## 3. Production : nginx

[`exemples/nginx-aite-webdav.conf`](./exemples/nginx-aite-webdav.conf) est prêt
à adapter — `server_name` et chemins des certificats. Les trois réglages qui
comptent pour le WebDAV y sont déjà :

- `client_max_body_size 100m;` — sinon les dépôts sont tronqués ;
- `proxy_buffering off;` sur `/webdav/` — sinon les gros transferts patinent ;
- **aucun filtrage par méthode HTTP** — `PROPFIND`, `MKCOL`, `MOVE`, `LOCK` et
  `UNLOCK` doivent passer ; un pare-feu applicatif qui ne connaît que
  `GET`/`POST` casse le lecteur réseau sans message clair.

Le certificat vient de l'autorité interne de l'organisation ou de Let's Encrypt
selon l'exposition.

---

## 4. Côté Odoo

Dans `odoo.conf`, deux lignes :

```ini
; Odoo est derrière un proxy : faire confiance aux en-têtes X-Forwarded-*
proxy_mode = True

; Toujours indispensable au WebDAV, quel que soit le protocole
db_name = <votre_base>
```

Puis **Paramètres → Technique → Paramètres système**, `web.base.url` :

```
https://localhost        (ou https://ecm.exemple.fr)
```

C'est cette valeur qui construit les adresses envoyées à Word : tant qu'elle
reste en `http://`, le bouton *Ouvrir dans Office* continuera d'être bloqué,
même si l'instance répond en HTTPS.

Redémarrer Odoo.

---

## 5. Remonter le lecteur réseau

L'ancien montage pointe sur le port en clair : le supprimer d'abord.

```
net use W: /delete
net use X: /delete

net use W: \\localhost@SSL\webdav\aite_courrier /user:<login>
net use X: \\localhost@SSL\webdav\aite_ecm      /user:<login>
```

`@SSL` remplace `@8069` : c'est ainsi que le client Windows désigne un serveur
WebDAV chiffré. Avec un port non standard, la forme devient
`\\serveur@SSL@8443\webdav\aite_ecm`.

Dans l'Explorateur, le champ *Dossier* accepte directement
`https://localhost/webdav/aite_ecm/`.

---

## 6. Vérifier

```powershell
curl.exe -s -i -X OPTIONS https://localhost/webdav/aite_ecm | Select-Object -First 6
python docs\recette\test_webdav.py --url https://localhost --login <login> --password <clé d'API>
```

Attendu : `200` avec `DAV: 1, 2`, puis 34 contrôles verts. Si `curl` se plaint
du certificat, c'est que `caddy trust` n'a pas été joué, ou que l'autorité de
l'organisation n'est pas déployée sur le poste.

Puis, dans Odoo, le bouton **Ouvrir dans Office** sur une fiche document : Word
doit s'ouvrir sur le fichier, en écriture.

---

## 7. Retirer les contournements

Une fois HTTPS en place, les réglages de registre posés pour survivre au `http`
n'ont plus lieu d'être. Les laisser, c'est garder ouverte l'autorisation
d'envoyer un mot de passe en clair :

```powershell
# Autorisation Basic sur HTTP — client WebDAV de Windows (administrateur)
reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
  /v BasicAuthLevel /t REG_DWORD /d 1 /f
Restart-Service WebClient

# Autorisation Basic sur HTTP — Office (session utilisateur)
reg add HKCU\Software\Microsoft\Office\16.0\Common\Internet `
  /v BasicAuthLevel /t REG_DWORD /d 1 /f
```

`1` est la valeur par défaut de Windows : Basic accepté, mais sur connexion
chiffrée uniquement.

Et si le paramètre système `aite_ecm.office_uri_mode` avait été mis à `unc`
pour contourner le blocage d'Office, le remettre à `url` : en HTTPS, l'URL
fonctionne et vaut pour tous les systèmes, pas seulement Windows.

---

*AITE Consulting — WebDAV en HTTPS sur Windows.*
