# Tutoriel — l'espace documentaire en lecteur réseau, en HTTPS

> Installer la suite AITE sur une instance Odoo 18 neuve, la servir en HTTPS, et
> monter l'espace documentaire comme un lecteur réseau sur un poste Windows.
> Chaque étape porte sa vérification : ne pas passer à la suivante sans elle.
> Comptez une heure la première fois.
>
> Ce tutoriel consigne les douze obstacles rencontrés lors d'une mise en place
> réelle. Ils sont tous annotés à l'endroit où ils surviennent.

---

## Pourquoi HTTPS, et pas « plus tard »

On peut servir le WebDAV en clair. Pendant une demi-journée, c'est même plus
rapide. Puis Windows et Office opposent, l'une après l'autre, quatre défenses
distinctes :

| Défense | Ce qu'on voit |
| --- | --- |
| Service WebClient | « Windows ne peut pas accéder à http://… » |
| Basic sur HTTP, côté Windows | boîte d'identifiants en boucle |
| Basic côté Office, en HTTP **comme en HTTPS** | « Microsoft Office a bloqué l'accès aux … car la source utilise une méthode de connexion qui peut être non sécurisée » |
| Zones de sécurité | « provient d'un site de la zone Sites sensibles » |

Chacune se lève par un réglage sur chaque poste (service, clé de registre ou
stratégie Office), et Microsoft en resserre régulièrement les vis. Surtout, un client WebDAV **présente ses
identifiants à chaque requête** — des dizaines par dossier ouvert. En clair,
sur un réseau d'entreprise, c'est intenable.

HTTPS dispense le client WebDAV de Windows de toute clé `BasicAuthLevel` et
chiffre le mot de passe. Il ne lève **pas** la défense d'Office : depuis la
version 2311, Word, Excel et PowerPoint bloquent par défaut toute invite
d'authentification Basic, chiffrée ou non, et le serveur WebDAV d'Odoo n'offre
que Basic. Le même message s'affiche derrière Caddy, sur
`https://localhost/webdav/aite_ecm/…`. Cette défense-là se lève sur chaque
poste, en autorisant l'hôte dans Office (§5), en `http` comme en `https`. Le
service WebClient, lui, se démarre dans tous les cas (§5). Pour le reste,
HTTPS est la route courte, pas la route longue.

### Ce qu'on installe

```
   Poste Windows                    Serveur
   ─────────────                    ───────────────────────────
   Explorateur  ──┐
   Word, Excel  ──┼── HTTPS 443 ──▶ Caddy ──── HTTP 8069 ──▶ Odoo
   Navigateur   ──┘                 (reverse proxy,          (WebDAV,
                                     certificat)              ECM, courrier)
```

Odoo ne sait pas servir HTTPS lui-même : un reverse proxy s'en charge. Caddy
tient en un exécutable et gère le certificat tout seul ; nginx convient mieux
en production (§11).

---

## 1. Installer les modules

Copier le contenu de `addons\` dans le répertoire déclaré par `addons_path`,
typiquement `C:\Program Files\Odoo 18\server\custom_addons\`.

```powershell
net stop odoo-server-18.0

& "C:\Program Files\Odoo 18\python\python.exe" `
  "C:\Program Files\Odoo 18\server\odoo-bin" `
  -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
  --load-language=fr_FR --without-demo=all --stop-after-init `
  -i aite_courrier_webdav,aite_ecm_webdav
```

Pour la suite complète, remplacer la dernière ligne par la liste des 24 modules
Community donnée dans le `LISEZMOI.txt` du paquet. **Ne pas sélectionner**
`aite_courrier_sign`, `aite_courrier_ged_documents` ni `aite_ecm_documents` :
ils dépendent de modules Odoo Enterprise et feraient échouer l'installation.

✅ **Vérification** — la sortie se termine sans `ERROR`, et
`Loading module aite_ecm_webdav` y figure.

---

## 2. Configurer Odoo

Dans `odoo.conf` :

```ini
; Le contrôleur WebDAV s'authentifie hors session et ne peut pas deviner la
; base : sans cette ligne, un serveur multi-base répond 401 à tout, quels que
; soient les identifiants.
db_name = <votre_base>

; Odoo sera derrière un proxy : faire confiance aux en-têtes X-Forwarded-*.
proxy_mode = True
```

```powershell
net start odoo-server-18.0
```

> **Obstacle 1 — `db_name` manquant.** C'est la première cause de `401`
> inexplicables. Les identifiants sont bons, le module est installé, et rien
> ne passe.

✅ **Vérification** — `curl.exe -s -i -X OPTIONS http://localhost:8069/webdav/aite_ecm`
renvoie `200` avec `DAV: 1, 2`.

> **Obstacle 2 — Odoo non redémarré.** Les routes HTTP ne sont publiées qu'au
> démarrage du serveur. Un `404` ici, alors que le module est installé, veut
> presque toujours dire que le service n'a pas été relancé.

---

## 3. Mettre en place HTTPS avec Caddy

Télécharger l'exécutable depuis <https://caddyserver.com/download>. Il arrive
sous le nom de sa plateforme :

```powershell
Rename-Item .\caddy_windows_amd64.exe caddy.exe
```

Copier `exemples\Caddyfile` à côté, puis, en PowerShell **administrateur**,
dans ce dossier :

```powershell
.\caddy.exe run --config .\Caddyfile
```

Laisser cette fenêtre ouverte : Caddy tourne tant qu'elle vit. Au premier
démarrage, il crée son autorité interne et l'installe dans le magasin de la
machine — d'où les droits administrateur.

Le journal doit contenir, dans l'ordre :

```
certificate installed properly in windows trusts
automatic HTTP->HTTPS redirects are disabled
certificate obtained successfully   {"identifier": "localhost", "issuer": "local"}
server running                      {"protocols": ["h1", "h2", "h3"]}
```

> **Obstacle 3 — `caddy trust` lancé en premier.** Cette commande s'adresse à
> une instance **déjà démarrée**, par son API d'administration (port 2019).
> Lancée avant, elle échoue sur `dial tcp [::1]:2019 … connexion refusée`. Si
> le journal n'annonce pas l'installation de l'autorité, lancer `.\caddy.exe
> trust` depuis une **seconde** fenêtre administrateur, Caddy tournant.

> **Obstacle 4 — le port 80 déjà pris.** `listening on :80 … interdit par ses
> autorisations d'accès` : sous Windows, `http.sys` ou IIS le réservent
> souvent. Caddy ne le voulait que pour rediriger HTTP vers HTTPS ; le
> `Caddyfile` fourni désactive cette redirection. Pour savoir qui l'occupe :
> `Get-Process -Id (Get-NetTCPConnection -LocalPort 80).OwningProcess`.

✅ **Vérification** — depuis une autre fenêtre :

```powershell
Invoke-WebRequest -Uri https://localhost/webdav/aite_ecm/ -Method Options
```

`StatusCode : 200`, et `Dav: 1, 2` dans `RawContent`. Cette commande passe par
.NET, donc par le magasin de certificats de Windows : si elle réussit, le
certificat est approuvé par le système.

> **Obstacle 5 — `curl.exe` refuse le certificat.**
> `CRYPT_E_NO_REVOCATION_CHECK (0x80092012)`. Une autorité interne n'a ni
> liste de révocation ni répondeur OCSP, et `curl.exe` sous Windows exige
> cette vérification. **Ce n'est pas un problème de confiance** : un
> certificat non reconnu donnerait `CERT_E_UNTRUSTEDROOT`. Ajouter
> `--ssl-no-revoke` pour curl ; les autres clients ne sont pas si stricts.

> **Obstacle 6 — `https://localhost:8069`.** Le port 8069 reste en clair :
> c'est Odoo en direct. HTTPS, c'est Caddy, sur le port 443 — donc
> `https://localhost`, **sans numéro de port**. L'erreur
> `ERR_SSL_PROTOCOL_ERROR` vient de là.

---

## 4. Déclarer l'adresse publique

**Paramètres → Technique → Paramètres système** :

| Clé | Valeur |
| --- | --- |
| `web.base.url` | `https://localhost` |
| `web.base.url.freeze` | `True` |

> **Obstacle 7 — Odoo réécrit `web.base.url`.** À chaque connexion d'un
> administrateur, Odoo y recopie l'adresse par laquelle il vient d'être
> atteint. Une seule visite sur `http://localhost:8069/web` annule le réglage,
> silencieusement. `web.base.url.freeze` le fige. À partir d'ici, n'accéder à
> Odoo que par **`https://localhost/web`**.

✅ **Vérification** — ouvrir une fiche document : le champ **Adresse WebDAV**,
sous le nom du fichier, doit commencer par `https://localhost/webdav/`. C'est
exactement l'adresse qui sera remise à Word. Tant qu'elle est en `http://` ou
qu'elle porte `:8069`, inutile d'aller plus loin. Une adresse en `https://` est
nécessaire, pas suffisante : Word exigera encore que l'hôte soit autorisé dans
Office (§5).

---

## 5. Préparer le poste Windows

Le client WebDAV de Windows est un service, arrêté par défaut. En PowerShell
**administrateur** :

```powershell
Set-Service -Name WebClient -StartupType Automatic
Start-Service WebClient
Get-Service WebClient
```

`Running` attendu. Le `StartupType Automatic` compte : sans lui, le service ne
redémarre pas après un redémarrage du poste, et le lecteur redevient
inaccessible.

> **Obstacle 8 — les espaces dans les commandes.** `Set-Service -Name WebClient`
> et non `Set-Service-Name WebClient`. Recopiée à la main, la commande perd
> ses espaces et PowerShell cherche une applet nommée `Set-Service-Name`.

**En HTTPS, le client WebDAV de Windows n'a besoin d'aucune clé
`BasicAuthLevel`** — seule `FileSizeLimitInBytes` reste utile pour les
fichiers de plus de 50 Mo. Les réglages `BasicAuthLevel` ne servaient qu'à survivre au `http`
(§12). Office, lui, en demande une, en `http` comme en `https`.

### Autoriser l'hôte dans Office

Depuis la version 2311 (Current Channel, décembre 2023 ; Monthly Enterprise,
janvier 2024 ; Semi-Annual 2402, juillet 2024), Word, Excel et PowerPoint sous
Windows bloquent **par défaut** les invites d'authentification Basic. Office
2016, 2019 et 2021 achetés au détail suivent le calendrier du Current Channel ;
les versions LTSC en licence en volume ne sont pas concernées. Le blocage porte
sur la méthode, pas sur le transport, et le serveur WebDAV d'Odoo n'offre que
Basic. Chaque poste doit donc autoriser l'hôte, **avant le premier essai dans
Word** (§8).

1. Enregistrer puis **fermer toutes** les applications Office.
2. Ouvrir PowerShell **dans la session du compte Windows qui utilise Word** —
   « en tant qu'administrateur » si ce compte est administrateur du poste :
   les sources consultées indiquent que des droits d'administration sont
   requis. Jamais avec un autre compte : `HKCU` désignerait alors le profil de
   cet autre compte, et Word n'en verrait rien. La fenêtre administrateur
   ouverte plus haut ne convient que si c'est le même compte.
3. Coller :

```powershell
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

   `/f` remplace une valeur `basichostallowlist` existante (posée par l'administrateur, ou pour un autre serveur) : la lire d'abord avec `reg query "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist` et reprendre ses hôtes dans `/d`.

4. Rouvrir Office. À la première ouverture d'un fichier du serveur, Word
   demande désormais un identifiant et un mot de passe : le login Odoo et son
   mot de passe, ou une clé d'API.

Les hôtes se donnent par leur nom, sans `https://`, séparés par `;`. En
production, mettre le nom du serveur (`ecm.client.fr`). `localhost:8069`
s'ajoute par prudence : aucune source ne dit si le port compte. Les guillemets
sont obligatoires en PowerShell, où le `;` sépare les instructions.

Sur un parc, la même valeur se pose par la stratégie *Allow specified hosts to
show Basic Authentication prompts to Office apps* (Configuration utilisateur ›
Stratégies › Modèles d'administration › Microsoft Office 2016 › Security
Settings, modèles ADMX Office 5359.1000 ou ultérieurs), ou par une Cloud
Policy. Microsoft ne recommande cette autorisation qu'à titre transitoire (voir la
[page Microsoft Learn](https://learn.microsoft.com/microsoft-365-apps/security/basic-authentication-prompts-blocked)).

> **Obstacle 9 — Office bloque, même en HTTPS.** « Microsoft Office a bloqué
> l'accès aux https://localhost/webdav/aite_ecm/… car la source utilise une
> méthode de connexion qui peut être non sécurisée » : Word ne demande même
> pas le mot de passe. Le certificat n'y est pour rien. Ouvrir le fichier
> depuis `X:` n'y change rien non plus : Word convertit le chemin du lecteur
> en adresse `http(s)` et télécharge le fichier lui-même. Le lecteur réseau,
> lui, n'est pas concerné : on peut créer dossiers et fichiers dans `X:` alors
> même que Word refuse de les ouvrir. Si le blocage persiste une fois l'hôte
> autorisé et Office relancé : la stratégie ne s'applique, selon sa
> description, qu'aux versions sur abonnement ; une Cloud Policy du tenant
> (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`) ou le Baseline
> Security Mode de Microsoft 365 peuvent primer sur la valeur locale.

✅ **Vérification** — dans la même session :

```powershell
reg query "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist
```

`basichostallowlist    REG_EXPAND_SZ    localhost;localhost:8069`.

---

## 6. Monter les lecteurs

```
net use X: \\localhost@SSL\webdav\aite_ecm      /user:<login Odoo>
net use W: \\localhost@SSL\webdav\aite_courrier /user:<login Odoo>
```

Le mot de passe est demandé au clavier. **`@SSL` remplace le numéro de port** :
c'est ainsi que le client Windows désigne un serveur WebDAV chiffré. Avec un
port non standard, la forme devient `\\serveur@SSL@8443\webdav\aite_ecm`.

L'identifiant est le champ **Identifiant** de l'utilisateur Odoo
(Paramètres → Utilisateurs), qui n'est pas forcément son adresse e-mail. Les
utilisateurs *portail* n'ont pas accès.

`net use` plutôt que la boîte de dialogue de l'Explorateur : en cas d'échec, il
donne un **numéro d'erreur** au lieu de boucler en silence.

| Erreur | Cause | Remède |
| --- | --- | --- |
| 1244 | identifiants non envoyés | service WebClient arrêté |
| 1326 | refusés par Odoo | mauvais identifiant, ou `db_name` absent (§2) |
| 5 | accès refusé | chemin avec `DavWWWRoot` : l'ôter (`\\localhost@SSL\webdav\aite_ecm`) ; sinon mot de passe refusé par Odoo (tester avec `test_webdav.py`, §7, ou `curl.exe -u <login> -X PROPFIND https://localhost/webdav/aite_ecm/`) |
| 67 | serveur non reconnu comme WebDAV | service WebClient arrêté, ou faute dans le chemin |
| 1219 | connexion déjà en mémoire | `net use X: /delete` puis recommencer |

✅ **Vérification** — `X:` et `W:` apparaissent dans *Ce PC*. Ouvrir `X:` :
les dossiers du plan de classement s'affichent, plus « Sans classement ».

---

## 7. Éprouver le service

```powershell
python test_webdav.py --url https://localhost --login <login> --password <mot de passe> --no-verify
```

34 contrôles sur les deux racines : découverte, authentification, listage, puis
cycle de vie complet d'un fichier — dépôt, relecture à l'octet près,
versionnage, renommage, verrous, formats refusés, suppression. Le script ne
crée ni courrier ni dossier : il travaille dans une collection existante et
nettoie derrière lui.

`--no-verify` n'est nécessaire qu'avec une autorité interne (obstacle 5) ;
avec un certificat d'une autorité publique ou d'une PKI d'entreprise, l'omettre.

✅ **Vérification** — `34 réussis, 0 échoués`.

> Côté courrier, la racine ne liste que les courriers **déjà enregistrés**,
> porteurs d'une référence `COUR-AAAA-NNNN`. Sur une base neuve, créer un
> courrier et **lancer son circuit**, sinon le lecteur `W:` paraît vide.

---

## 8. Le parcours réel

Dans `X:`, ouvrir un dossier de classement et déposer un PDF. Dans Odoo, le
document apparaît en **v1**, à votre nom, avec une entrée d'audit de source
*webdav*. Remplacer le fichier : **v2**, la v1 restant consultable.

Ouvrir un `.docx` depuis `X:` dans Word, modifier, `Ctrl+S` : une nouvelle
version doit apparaître dans l'ECM. Word ne réutilise pas la connexion du
lecteur : il traduit le chemin `X:\…` en adresse `https://localhost/webdav/…`
et s'authentifie lui-même. Il doit donc demander un identifiant et un mot de
passe. S'il affiche « Microsoft Office a bloqué l'accès… », l'hôte n'est pas
autorisé dans Office : revenir au §5 (obstacle 9).

Ce qu'il faut savoir en manipulant le lecteur :

| Geste | Effet dans l'application |
| --- | --- |
| Copier un fichier dans un dossier | nouveau document ; titre = nom du fichier sans extension |
| Enregistrer depuis Word | nouvelle version, à votre nom |
| Renommer | le titre change ; la référence, jamais |
| Déplacer vers un autre dossier | document reclassé (ECM) |
| Supprimer | corbeille (ECM), suppression (courrier) |
| Créer un dossier | dossier de classement (ECM) ; refusé côté courrier |
| Renommer ou déplacer un dossier | dossier renommé ou reclassé, avec sa branche (ECM) |
| Supprimer un dossier | archivé s'il est vide (ECM) ; refusé s'il contient des documents |

L'ECM republie chaque fichier sous `RÉFÉRENCE - Titre.ext`. Un fichier que vous
venez de déposer sous `contrat.docx` réapparaît donc en
`DOC-2026-00128 - contrat.docx` au rafraîchissement : c'est normal.

Formats acceptés : PDF, DOCX, XLSX, JPG, PNG, TIF, EML, MSG côté courrier
(50 Mo) ; la même liste étendue à DOC, XLS, PPT(X), ODT, ODS, ODP, TXT, CSV,
RTF, GIF, ZIP, XML, JSON côté ECM (100 Mo).

---

## 9. Ouvrir dans Office depuis la fiche

Sur la fiche d'un document ECM, le bouton **Ouvrir dans Office** lance Word,
Excel ou PowerPoint directement sur le fichier.

Il suppose l'hôte autorisé dans Office sur le poste (§5) : sans cela, en HTTPS
comme en HTTP, Word répond « Microsoft Office a bloqué l'accès… car la source
utilise une méthode de connexion qui peut être non sécurisée ». L'hôte autorisé
et Office relancé, Word demande les identifiants Odoo, puis ouvre le fichier.

Le module sait aussi faire pointer le bouton sur le lecteur monté plutôt que
sur l'URL :

| Clé | Valeur |
| --- | --- |
| `aite_ecm.office_uri_mode` | `unc` |
| `aite_ecm.office_unc_root` | `X:` |

Ce mode ne contourne **pas** le blocage d'Office : Word convertit le chemin du
lecteur en adresse `http(s)` et télécharge le fichier lui-même, avec la même
authentification Basic. La spécification Office URI Schemes n'accepte
d'ailleurs, après `ms-word:ofe|u|`, que des adresses `http` ou `https`. Ce mode
n'est plus recommandé : laisser `aite_ecm.office_uri_mode` à `url`, sa valeur
par défaut. Il supposait en outre que tous les postes montent le lecteur sur la
même lettre, et un chemin de lecteur ne veut rien dire sur macOS ou Linux.

> **Obstacle 10 — Word s'ouvre à vide.** Sans message. Vérifier que les modules
> sont à jour : une version antérieure à `aite_ecm_webdav 18.0.2.3.1`
> répondait `Content-Length: 0` aux requêtes `HEAD`, et Word en déduisait un
> document vide.

> **Obstacle 11 — une page 404 d'Odoo au lieu de Word.** L'adresse
> `localhost:8069/ms-word:ofe%7Cu%7C…` dans le navigateur : version antérieure
> à `18.0.2.3.0`. Après mise à jour, **Ctrl+F5** — le correctif ajoute un
> fichier JavaScript au client web.

> **Obstacle 12 — Word en mode lecture seule.** Regarder le titre de la
> fenêtre : « Échec de l'activation du produit » signale une licence Office
> non activée, sans rapport avec l'ECM. Sinon, vérifier sur la fiche que le
> document n'est ni *Finalisé*, ni *Archivé*, ni *Réservé* par un collègue.

---

## 10. Faire tourner Caddy en permanence

La fenêtre PowerShell ferme Caddy en se fermant. Pour un serveur :

```powershell
.\caddy.exe start        # détache le processus
.\caddy.exe stop
```

Pour un vrai service Windows, survivant au redémarrage, utiliser
[NSSM](https://nssm.cc/) ou le service officiel décrit dans la documentation de
Caddy. Ne pas oublier que le service doit démarrer **avant** que les
utilisateurs ne se connectent, sinon leurs lecteurs réseau échouent au
montage.

---

## 11. Production : nginx

`exemples\nginx-aite-webdav.conf` est prêt à adapter — `server_name` et chemins
des certificats. Trois réglages y sont indispensables, et souvent oubliés :

- `client_max_body_size 100m;` — sinon les dépôts sont tronqués ;
- `proxy_buffering off;` sur `/webdav/` — sinon les gros transferts patinent ;
- **aucun filtrage par méthode HTTP** — `PROPFIND`, `MKCOL`, `MOVE`, `LOCK` et
  `UNLOCK` doivent passer. Un pare-feu applicatif qui ne connaît que
  `GET`/`POST` casse le lecteur réseau sans message clair.

Le certificat vient de l'autorité interne de l'organisation ou de Let's
Encrypt. Avec un certificat public, `--ssl-no-revoke` et `--no-verify`
deviennent inutiles.

---

## 12. Retirer les contournements

Si le poste a d'abord servi en `http`, les clés `BasicAuthLevel` posées alors
autorisent encore l'envoi d'un mot de passe en clair. Les remettre à leur
valeur par défaut :

```powershell
# Client WebDAV de Windows (administrateur)
reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
  /v BasicAuthLevel /t REG_DWORD /d 1 /f
Restart-Service WebClient

# Ancienne clé Office (session utilisateur), seulement si elle avait été
# posée : inutile en HTTPS, et insuffisante depuis la version 2311
reg add HKCU\Software\Microsoft\Office\16.0\Common\Internet `
  /v BasicAuthLevel /t REG_DWORD /d 1 /f
```

`1` est la valeur par défaut : Basic accepté, mais sur connexion chiffrée
uniquement. Supprimer aussi les entrées de zone ajoutées pour `localhost`, et
repasser `aite_ecm.office_uri_mode` à `url` : le mode `unc` ne levait pas le
blocage d'Office (§9).

**Ne pas retirer** la valeur `basichostallowlist`
(`HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity`, §5). Ce n'est
pas un contournement du `http` : tant que le serveur n'offre que Basic, c'est
elle qui permet à Word, Excel et PowerPoint de demander les identifiants,
HTTPS compris. Ne pas toucher non plus à `FileSizeLimitInBytes`, si elle a été
relevée : c'est une limite du client WebClient, indépendante du protocole.

---

## Récapitulatif des vérifications

| § | Commande | Attendu |
| --- | --- | --- |
| 1 | installation des modules | pas d'`ERROR` |
| 2 | `curl.exe -i -X OPTIONS http://localhost:8069/webdav/aite_ecm` | `200`, `DAV: 1, 2` |
| 3 | `Invoke-WebRequest https://localhost/webdav/aite_ecm/ -Method Options` | `StatusCode : 200` |
| 4 | champ *Adresse WebDAV* d'une fiche | commence par `https://localhost/` |
| 5 | `Get-Service WebClient` | `Running` |
| 5 | `reg query "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist` (session de l'utilisateur de Word) | `REG_EXPAND_SZ    localhost;localhost:8069` |
| 6 | `net use X: \\localhost@SSL\webdav\aite_ecm` | « terminée correctement » |
| 7 | `test_webdav.py --no-verify` | `34 réussis, 0 échoués` |
| 8 | dépôt d'un fichier dans `X:` | v1 dans Odoo, audit *webdav* |
| 8 | `.docx` ouvert depuis `X:` dans Word, `Ctrl+S` | identifiants demandés, puis nouvelle version dans l'ECM |

---

*AITE Consulting — tutoriel WebDAV en HTTPS.*
