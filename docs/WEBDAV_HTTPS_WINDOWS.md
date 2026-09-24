# WebDAV en HTTPS — poste ou serveur Windows

> Pourquoi le chiffrement n'est pas un luxe pour l'espace documentaire, et
> comment le mettre en place devant Odoo 18 sur Windows, en quelques minutes
> pour un poste de test, proprement pour une mise en production.
>
> **Pour une installation de bout en bout**, du premier module au lecteur
> monté, suivre plutôt [`TUTORIEL_WEBDAV_HTTPS.md`](./TUTORIEL_WEBDAV_HTTPS.md) :
> chaque étape y porte sa vérification, et les douze obstacles rencontrés en
> conditions réelles y sont annotés là où ils surviennent. Le présent document
> reste la référence sur le reverse proxy lui-même.

---

## 1. Ce que HTTPS débloque

Sur une instance en `http://`, trois obstacles apparaissent l'un après
l'autre, tous côté client. Le chiffrement ne lève que le premier, et met fin au
mot de passe en clair ; le blocage d'Office et la limite de taille demeurent en
`https` :

| Obstacle | En `http` | En `https` |
| --- | --- | --- |
| Montage du lecteur réseau | refusé, sauf clé de registre `BasicAuthLevel` sur chaque poste | fonctionne sans réglage |
| **Ouvrir dans Word / Excel** | **bloqué par Office** : « la source utilise une méthode de connexion qui peut être non sécurisée » | **bloqué aussi** : Office vise la méthode (Basic), pas le transport. Autoriser l'hôte par `basichostallowlist` (§6), comme en `http` |
| Fichiers de plus de 50 Mo | limite du client Windows, clé `FileSizeLimitInBytes` | **même limite** : elle tient au client WebClient, pas au protocole ; même clé |
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
refuse. Un certificat approuvé ne suffit pas pour autant : Word exige aussi que
l'hôte soit autorisé par `basichostallowlist` (§6).

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

> **« listening on :80 … interdit par ses autorisations d'accès »** : le port
> 80 est déjà retenu — sous Windows, `http.sys`, IIS ou un autre service le
> réservent souvent. Caddy ne le voulait que pour rediriger HTTP vers HTTPS ;
> le `Caddyfile` fourni désactive cette redirection (`auto_https
> disable_redirects`), et seul le port 443 est alors utilisé. Pour savoir qui
> occupe le port : `Get-NetTCPConnection -LocalPort 80 | Select-Object OwningProcess`
> puis `Get-Process -Id <numéro>`.

Les deux avertissements au démarrage — `Unnecessary header_up
X-Forwarded-Proto` et `Caddyfile input is not formatted` — visaient la
première version de cet exemple ; ils ont disparu.

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
reste en `http://`, le bouton *Ouvrir dans Office* envoie Word sur le port en
clair, même si l'instance répond en HTTPS. En `https://`, Word atteint bien
Caddy, mais il bloque encore l'authentification Basic tant que l'hôte n'est
pas autorisé par `basichostallowlist` (§6).

> **Odoo réécrit `web.base.url` tout seul.** À chaque connexion d'un
> administrateur, Odoo y recopie l'adresse par laquelle il a été atteint. Une
> seule visite sur `http://localhost:8069/web` suffit donc à annuler le
> réglage — silencieusement. Pour le figer, ajouter un second paramètre
> système :
>
> | Clé | Valeur |
> | --- | --- |
> | `web.base.url.freeze` | `True` |
>
> Et n'accéder à Odoo que par `https://localhost/web`.

**Vérification immédiate**, sans même lancer Word : ouvrir une fiche document
et regarder le champ **Adresse WebDAV**. Il doit commencer par `https://`. S'il
est encore en `http://`, le paramètre n'a pas pris — inutile d'aller plus loin.

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

## 6. Autoriser l'hôte dans Office

HTTPS ne suffit pas à Word. Depuis la version 2311 (Current Channel, décembre
2023 ; Monthly Enterprise, janvier 2024 ; Semi-Annual 2402, juillet 2024),
Word, Excel et PowerPoint sous Windows bloquent **par défaut** les invites
d'authentification Basic :

> Microsoft Office a bloqué l'accès aux … car la source utilise une méthode de
> connexion qui peut être non sécurisée

Office 2016, 2019 et 2021 achetés au détail suivent le calendrier du Current
Channel ; les versions LTSC en licence en volume ne sont pas concernées. Le
blocage vise la méthode, pas le transport : il s'applique en `https` comme en
`http` — constaté derrière Caddy, sur `https://localhost/webdav/aite_ecm/…`.
Le serveur WebDAV d'Odoo n'offrant que Basic, chaque poste doit autoriser
l'hôte.

Passer par le lecteur réseau n'y change rien : ouvert depuis `X:`, un fichier
est converti par Word en adresse `http(s)`, et Word le télécharge lui-même. Le
lecteur, en revanche, n'est pas concerné : l'Explorateur et `net use` créent
dossiers et fichiers dans `X:` même quand Word refuse de les ouvrir.

Fermer **toutes** les applications Office, puis, dans la session du compte
Windows qui utilise Word — PowerShell « en tant qu'administrateur » si ce
compte est administrateur du poste, les sources consultées indiquant que des
droits d'administration sont requis :

```powershell
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

- `/f` remplace une valeur `basichostallowlist` existante (posée par l'administrateur, ou pour un autre serveur) : la lire d'abord avec `reg query "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist` et reprendre ses hôtes dans `/d`.
- les hôtes se donnent par leur nom, sans `https://`, séparés par `;` ; en
  production, le nom du serveur (`ecm.client.fr`) ;
- `localhost:8069` s'ajoute par prudence : aucune source ne dit si le port
  compte ;
- les guillemets sont obligatoires en PowerShell, où le `;` sépare les
  instructions ;
- jamais depuis un autre compte, même administrateur : `HKCU` désignerait
  alors le profil de ce compte, et Word n'en verrait rien.

Rouvrir Office : au lieu du blocage, Word demande un identifiant et un mot de
passe — le login Odoo et son mot de passe, ou une clé d'API.

Sur un parc, la stratégie *Allow specified hosts to show Basic Authentication
prompts to Office apps* (Configuration utilisateur › Stratégies › Modèles
d'administration › Microsoft Office 2016 › Security Settings, modèles ADMX
Office 5359.1000 ou ultérieurs) pose la même valeur ; une Cloud Policy aussi.
Microsoft ne recommande cette autorisation qu'à titre transitoire (voir la
[page Microsoft Learn](https://learn.microsoft.com/microsoft-365-apps/security/basic-authentication-prompts-blocked)).

> **Si Word bloque encore.** Selon sa description, la stratégie ne s'applique
> qu'aux versions d'Office sur abonnement. Une Cloud Policy du tenant
> (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`) ou le Baseline
> Security Mode de Microsoft 365 peuvent aussi primer sur la valeur locale :
> voir avec l'administrateur Microsoft 365.

---

## 7. Vérifier

```powershell
curl.exe -i -X OPTIONS --ssl-no-revoke https://localhost/webdav/aite_ecm
python docs\recette\test_webdav.py --url https://localhost --login <login> --password <clé d'API> --no-verify
```

Attendu : `200` avec `DAV: 1, 2`, puis 34 contrôles verts.

> **`--ssl-no-revoke` et `--no-verify` ne sont pas des aveux d'échec.** Une
> autorité interne — celle de Caddy, ou un certificat auto-signé — n'a ni
> liste de révocation ni répondeur OCSP. `curl.exe` sous Windows exige cette
> vérification et refuse la connexion avec
> `CRYPT_E_NO_REVOCATION_CHECK (0x80092012)`, *alors même que la chaîne est
> approuvée* : un certificat non reconnu donnerait `CERT_E_UNTRUSTEDROOT`. Le
> navigateur, l'Explorateur et Word ne sont pas si stricts. Avec un
> certificat d'une autorité publique ou d'une PKI d'entreprise, les deux
> options deviennent inutiles.

Vérification complémentaire, plus parlante : ouvrir `https://localhost/web`
dans le navigateur. Le cadenas et l'écran de connexion Odoo suffisent à
confirmer que le proxy et le certificat tiennent.

Puis, dans Odoo, le bouton **Ouvrir dans Office** sur une fiche document, une
fois l'hôte autorisé (§6) : Word doit demander les identifiants Odoo, puis
s'ouvrir sur le fichier, en écriture. S'il affiche « Microsoft Office a bloqué
l'accès aux "https://localhost/webdav/aite_ecm/…" », l'hôte n'est pas
autorisé : revenir au §6.

---

## 8. Retirer les contournements

Une fois HTTPS en place, les clés `BasicAuthLevel` posées pour survivre au
`http` n'ont plus lieu d'être. Les laisser, c'est garder ouverte l'autorisation
d'envoyer un mot de passe en clair :

```powershell
# Autorisation Basic sur HTTP — client WebDAV de Windows (administrateur)
reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
  /v BasicAuthLevel /t REG_DWORD /d 1 /f
Restart-Service WebClient

# Autorisation Basic sur HTTP — ancienne clé Office (session utilisateur),
# seulement si elle avait été posée : inutile en HTTPS, et insuffisante
# depuis la version 2311
reg add HKCU\Software\Microsoft\Office\16.0\Common\Internet `
  /v BasicAuthLevel /t REG_DWORD /d 1 /f
```

`1` est la valeur par défaut de Windows : Basic accepté, mais sur connexion
chiffrée uniquement.

**À ne pas retirer** : la valeur `basichostallowlist` sous
`HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity` (§6). Ce n'est
pas un contournement du `http` : tant que le serveur n'offre que Basic, c'est
elle qui permet à Word de demander les identifiants, HTTPS compris. De même,
une clé `FileSizeLimitInBytes` relevée reste utile : la limite tient au client
WebClient, pas au protocole.

Et si le paramètre système `aite_ecm.office_uri_mode` avait été mis à `unc`,
le remettre à `url`. Le mode `unc` ne contournait pas le blocage d'Office :
Word convertit le chemin du lecteur en adresse `http(s)` et s'authentifie
lui-même ; la spécification Office URI Schemes n'accepte d'ailleurs, après
`ms-word:ofe|u|`, que des adresses `http` ou `https`. L'URL, elle, vaut pour
tous les systèmes, pas seulement Windows ; sous Windows, elle suppose l'hôte
autorisé (§6).

---

*AITE Consulting — WebDAV en HTTPS sur Windows.*
