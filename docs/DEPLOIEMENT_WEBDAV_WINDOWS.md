# WebDAV AITE — déploiement sur une instance Odoo 18 Windows

> Installer, configurer, utiliser et vérifier l'accès WebDAV sur un poste
> Windows 10 exécutant Odoo 18 **Community** en local.
>
> **Nouvelle installation ?** Suivre [`TUTORIEL_WEBDAV_HTTPS.md`](./TUTORIEL_WEBDAV_HTTPS.md),
> qui déroule le parcours complet en HTTPS — la configuration où le client
> WebDAV de Windows se passe de `BasicAuthLevel` et où le mot de passe ne
> circule plus en clair. Office, lui, bloque l'authentification Basic en
> `http` **comme en** `https` : quel que soit le protocole, chaque poste doit
> autoriser l'hôte par la valeur `basichostallowlist` (§3, *Autoriser Word,
> Excel et PowerPoint*). Le présent document décrit le cas `http`, ses
> réglages de registre et leurs limites.

---

## 1. Ce que font les modules

Deux modules publient un espace documentaire en **WebDAV**, servi par Odoo
lui-même : même port, même authentification, aucune brique externe. Le
protocole est celui que Windows sait monter comme un lecteur réseau et que
Word, Excel et PowerPoint savent ouvrir directement — à condition, depuis la
version 2311 de Microsoft 365, que le poste autorise l'hôte à leur demander
des identifiants Basic (§3, *Autoriser Word, Excel et PowerPoint*).

| Module | Racine | Arborescence exposée |
| ------ | ------ | -------------------- |
| `aite_courrier_webdav` | `/webdav/aite_courrier` | un dossier par courrier enregistré, contenant ses pièces |
| `aite_ecm_webdav` | `/webdav/aite_ecm` | le plan de classement ECM, ses sous-dossiers, et « Sans classement » |

**Rien ne contourne l'application.** Toutes les opérations passent par l'ORM
sous l'identité du compte authentifié : rôles, confidentialité, droits de
dossier, verrouillage des pièces finalisées et journal d'audit s'appliquent
exactement comme dans l'interface. Un document invisible dans Odoo n'apparaît
pas dans le lecteur réseau.

### Ce que chaque geste produit

| Geste dans l'Explorateur | Effet dans l'application |
| ------------------------ | ------------------------ |
| Ouvrir un fichier | lecture, si les droits le permettent |
| Enregistrer depuis Word / Excel | **nouvelle version** (v1, v2, …), à votre nom, audit source « webdav » |
| Copier un fichier dans un dossier | **nouveau document** ; titre = nom du fichier sans extension |
| Renommer un fichier | le **titre** du document change (jamais sa référence) |
| Déplacer vers un autre dossier | document **reclassé** (ECM uniquement) |
| Supprimer un fichier | **corbeille** côté ECM, suppression côté courrier |
| Créer un dossier | dossier de classement ECM ; **refusé** côté courrier (`403`) |
| Renommer ou déplacer un dossier | dossier de classement **renommé** ou **reclassé**, avec toute sa branche (ECM) |
| Supprimer un dossier | dossier **archivé** s'il est vide (ECM) ; **refusé** (`409`) s'il contient encore des documents |

> Ouvrir ou enregistrer un fichier **dans Word, Excel ou PowerPoint** suppose
> la valeur `basichostallowlist` sur le poste (§3) : sans elle, Office bloque
> l'ouverture, même d'un fichier pris dans le lecteur réseau. Les gestes de
> l'Explorateur, eux, n'en dépendent pas : copier, renommer, créer un dossier
> ou un fichier fonctionnent même quand Word refuse d'ouvrir.

### Nommage et limites

| | `aite_courrier_webdav` | `aite_ecm_webdav` |
| --- | --- | --- |
| Nom de fichier exposé | `<nom du document>.<ext>` | `<RÉFÉRENCE> - <titre>.<ext>` |
| Formats acceptés | PDF, DOCX, XLSX, JPG, JPEG, PNG, TIF, TIFF, EML, MSG | + DOC, XLS, PPT(X), ODT, ODS, ODP, TXT, CSV, RTF, GIF, ZIP, XML, JSON |
| Taille maximale | 50 Mo | 100 Mo |
| `MKCOL` (créer un dossier) | `403` | `201` |
| `LOCK` | consultatif (jeton non persisté) | pose une **réservation** ECM |
| `DELETE` | suppression du document | mise à la **corbeille** |

### Codes d'erreur

`401` authentification manquante ou refusée · `403` droits insuffisants ou
opération interdite · `404` ressource inconnue · `409` format ou taille refusés
· `423` document verrouillé (finalisé, archivé, ou réservé par un collègue).

---

## 2. Installation

Les chemins ci-dessous supposent l'installateur Windows standard
(`C:\Program Files\Odoo 18`) : adapter à votre installation.

### 2.1 Copier les modules

Décompresser l'archive et copier les **7 dossiers de modules** dans le
répertoire d'addons personnalisé déclaré par `addons_path` :

```powershell
Copy-Item -Recurse -Force .\addons\* "C:\Program Files\Odoo 18\server\custom_addons\"
```

Les 7 modules sont la fermeture complète des dépendances des deux modules
WebDAV — rien d'autre n'est requis côté AITE :

```
aite_courrier_base       socle : groupes, référentiels, audit
aite_courrier_workflow   moteur de circuits
aite_courrier_core       objet métier Courrier, référence COUR-AAAA-NNNN
aite_courrier_ged        pièces versionnées du courrier
aite_courrier_webdav     racine /webdav/aite_courrier
aite_ecm_document        documents ECM, plan de classement, réservations
aite_ecm_webdav          racine /webdav/aite_ecm
```

Côté Odoo natif, seuls des modules **Community** sont requis : `base`, `web`,
`mail`, `contacts`, `hr`.

> Pour n'installer que l'un des deux accès : `aite_courrier_webdav` a besoin de
> `aite_courrier_base`, `aite_courrier_workflow`, `aite_courrier_core` et
> `aite_courrier_ged` ; `aite_ecm_webdav` a besoin de `aite_courrier_base` et
> `aite_ecm_document`.

### 2.2 Configurer `odoo.conf`

```ini
[options]
addons_path = C:\Program Files\Odoo 18\server\odoo\addons,C:\Program Files\Odoo 18\server\custom_addons

; INDISPENSABLE au WebDAV : le contrôleur s'authentifie hors session et ne
; peut pas deviner la base. Sans db_name, un serveur qui héberge plusieurs
; bases répond 401 quels que soient les identifiants.
db_name = <votre_base>
```

### 2.3 Installer les modules

Arrêter le service, puis :

```powershell
net stop odoo-server-18.0

& "C:\Program Files\Odoo 18\python\python.exe" `
  "C:\Program Files\Odoo 18\server\odoo-bin" `
  -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
  -i aite_courrier_webdav,aite_ecm_webdav --stop-after-init

net start odoo-server-18.0
```

Par l'interface : **Applications → Mettre à jour la liste des applications**,
puis installer « AITE Courrier - WebDAV » et « AITE ECM - Lecteur réseau ».
**Redémarrer Odoo dans tous les cas** : les routes HTTP ne sont publiées qu'au
démarrage du serveur.

### 2.4 Vérifier

```powershell
curl.exe -s -i -X OPTIONS http://localhost:8069/webdav/aite_courrier
```

Attendu : `200` avec `DAV: 1, 2` et un en-tête `Allow`. Un `404` signifie que le
module n'est pas installé ou qu'Odoo n'a pas redémarré.

---

## 3. Autoriser le client WebDAV de Windows

Le service **WebClient** de Windows refuse par défaut d'envoyer un mot de passe
en clair sur `http://`. Sur un poste local, en PowerShell **administrateur** :

```powershell
Set-Service -Name WebClient -StartupType Automatic
Start-Service WebClient

reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
  /v BasicAuthLevel /t REG_DWORD /d 2 /f
reg add HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters `
  /v FileSizeLimitInBytes /t REG_DWORD /d 1073741824 /f

net stop WebClient
net start WebClient
```

`BasicAuthLevel = 2` autorise l'authentification Basic sur HTTP — **réglage de
poste de test**. `FileSizeLimitInBytes` lève la limite de 50 Mo du client
Windows (elle est indépendante de celle du module).

### Autoriser Word, Excel et PowerPoint

> **Office bloque l'authentification Basic, en `http` comme en `https`.**
> Depuis la version 2311 (Current Channel, décembre 2023 ; Monthly Enterprise
> Channel, janvier 2024 ; Semi-Annual Enterprise Channel 2402, juillet 2024 ;
> Office 2016, 2019 et 2021 vendus au détail, au rythme du Current Channel),
> Word, Excel et PowerPoint sous Windows n'affichent plus d'invite
> d'identifiants Basic. Ils répondent « Microsoft Office a bloqué l'accès aux
> … car la source utilise une méthode de connexion qui peut être non
> sécurisée ». Le blocage porte sur la **méthode** d'authentification, pas sur
> le transport : HTTPS n'y change rien. Il vaut pour le bouton *Ouvrir dans
> Office* comme pour un fichier ouvert depuis le lecteur réseau : Word traduit
> le chemin du lecteur en adresse `http(s)` et télécharge lui-même le fichier.
> Les versions d'Office en licence en volume (LTSC) ne sont pas concernées.

Les applications Office ont **leur propre** client HTTP et leur propre
politique d'authentification, distincts du service WebClient. Le serveur
WebDAV d'Odoo n'offre que Basic : chaque poste doit donc **autoriser l'hôte**,
par la stratégie *Allow specified hosts to show Basic Authentication prompts
to Office apps*. Sur un poste, son équivalent registre s'écrit dans la
**session du compte Windows qui utilise Word** : PowerShell *en tant
qu'administrateur* si ce compte est administrateur du poste, mais jamais avec
un autre compte — `HKCU` désignerait alors le profil de cet autre compte.
**Fermer d'abord toutes les applications Office** (Word, Excel, PowerPoint,
Outlook). Si le poste porte déjà une valeur `basichostallowlist` (`reg query`
ci-dessous), reprendre ses hôtes dans `/d` : `/f` la remplace. Puis :

```powershell
# Indispensable, en http comme en https : autoriser l'hôte à demander des identifiants
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f

# En http seulement : ancienne clé, qui autorise Basic hors SSL
reg add HKCU\Software\Microsoft\Office\16.0\Common\Internet `
  /v BasicAuthLevel /t REG_DWORD /d 2 /f
```

Vérifier :

```powershell
reg query "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist
```

Attendu : `basichostallowlist    REG_EXPAND_SZ    localhost;localhost:8069`.
Rouvrir ensuite Word et le document : Word **demande des identifiants** au
lieu de bloquer. Saisir le login Odoo et son mot de passe, ou une clé d'API.

- **Hôtes.** `basichostallowlist` liste des noms d'hôtes séparés par `;`,
  sans `http://` ni `https://`. En production, y mettre le nom du serveur
  (par exemple `ecm.client.fr`). La forme `hôte:port` (`localhost:8069`)
  s'ajoute par prudence : aucune source ne dit si le port compte.
- **Guillemets obligatoires** en PowerShell, où `;` sépare deux instructions :
  sans eux, la liste d'hôtes est tronquée.
- **Ancienne clé `BasicAuthLevel` d'Office.** Elle autorise Office à
  s'authentifier en Basic sur une connexion non SSL. Elle reste utile sur une
  instance en `http`, mais **ne suffit plus** depuis la version 2311 ; en
  `https`, elle est inutile. `16.0` couvre Office 2016, 2019, 2021 et
  Microsoft 365.
- **Sur un parc**, poser la même liste par stratégie de groupe : *User
  Configuration › Policies › Administrative Templates › Microsoft Office 2016
  › Security Settings*, modèles d'administration Office 5359.1000 ou plus
  récents ; ou par Cloud Policy.
- **Limites.** Selon son libellé, la stratégie ne s'applique qu'aux versions
  d'Office sur abonnement : pour Office 2016, 2019 ou 2021 vendus au détail,
  bloqués eux aussi, aucune source ne montre que la valeur lève le blocage.
  Une Cloud Policy du tenant Microsoft 365
  (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`) ou le Baseline
  Security Mode peuvent primer sur la valeur locale : si Word bloque encore,
  voir avec l'administrateur Microsoft 365. Microsoft ne recommande cette
  autorisation qu'à titre transitoire.

> **En production, exposer Odoo en HTTPS** derrière un reverse proxy : le
> lecteur se monte alors sans `BasicAuthLevel`, et le mot de passe ne circule
> plus en clair. La valeur `basichostallowlist`, elle, **reste nécessaire** —
> Office bloque l'invite Basic en HTTPS aussi — avec le nom public du serveur.
> Prévoir `client_max_body_size 100m;` et le passage des verbes WebDAV.

### Monter le lecteur

Explorateur → clic droit sur **Ce PC** → *Connecter un lecteur réseau* :

- Lecteur : `W:`
- Dossier : `http://localhost:8069/webdav/aite_courrier`
- cocher **Se connecter à l'aide d'informations d'identification différentes**
- login Odoo et, **de préférence, une clé d'API** (Préférences → Sécurité
  du compte → Nouvelle clé d'API) à la place du mot de passe : elle se
  vérifie cent fois plus vite, se révoque seule, et c'est la seule voie pour
  un compte à double authentification. Le mot de passe du compte fonctionne
  aussi ; les vérifications réussies sont gardées cinq minutes en cache.

En ligne de commande : `net use W: http://localhost:8069/webdav/aite_courrier /user:<login> <motdepasse>`

---

## 4. Vérification automatisée

```powershell
python docs\recette\test_webdav.py --url http://localhost:8069 --login admin --password admin
```

34 contrôles, des en-têtes de découverte au cycle de vie complet d'un fichier.
Détail, options et dépannage : [`recette/GUIDE_TEST_WEBDAV.md`](./recette/GUIDE_TEST_WEBDAV.md).
Scénario manuel pas à pas : [`recette/SCENARIO_WEBDAV.md`](./recette/SCENARIO_WEBDAV.md).

---

## 5. Dépannage

| Symptôme | Cause probable | Remède |
| -------- | -------------- | ------ |
| `OPTIONS` → `404` | module non installé, ou Odoo non redémarré | §2.3 |
| `401` avec des identifiants corrects | `db_name` absent et plusieurs bases | §2.2 |
| `401` en boucle | compte *portail*, ou `BasicAuthLevel` à 1 | compte interne ; §3 |
| « Le nom du dossier n'est pas valide » | service WebClient arrêté, ou Basic refusé sur HTTP | §3 |
| Racine vide côté courrier | aucun courrier enregistré | créer un courrier et **Lancer le circuit** |
| `409` au dépôt | format hors liste, ou fichier trop gros | §1, tableau des limites |
| `423` au dépôt | document finalisé, archivé, ou réservé | libérer la réservation dans l'UI |
| Word ouvre en lecture seule | droits insuffisants, ou document verrouillé | consulter le bandeau de la fiche |
| *Ouvrir dans Office* affiche une page 404 d'Odoo | module antérieur à 18.0.2.3.0 | mettre à jour `aite_ecm_webdav` |
| Word se lance puis affiche « Microsoft Office a bloqué l'accès… car la source utilise une méthode de connexion qui peut être non sécurisée » (bouton ou lecteur réseau, `http` ou `https`) | hôte absent de `basichostallowlist` : Office bloque l'invite Basic | fermer toutes les applications Office, poser la valeur (§3, *Autoriser Word, Excel et PowerPoint*), puis rouvrir Word |
| Même message, valeur pourtant posée | Office pas entièrement fermé ; valeur écrite dans le profil d'un autre compte Windows ; Cloud Policy du tenant ou Baseline Security Mode prioritaire ; Office hors abonnement | §3 : fermer toutes les applications Office, reposer la valeur dans la session de l'utilisateur de Word ; sinon *Limites* |
| `reg add … basichostallowlist` répond « Accès refusé » | compte Windows sans droits d'administration | faire poser la valeur par l'administrateur (stratégie de groupe ou Cloud Policy, §3) ; ne pas lancer PowerShell sous un autre compte, dont `HKCU` serait le profil |
| Fichier > 50 Mo refusé par Windows | limite du client WebDAV | `FileSizeLimitInBytes`, §3 |
| Lecteur lent à l'ouverture | arborescence volumineuse | monter directement un sous-dossier |

---

## 6. Quand Office bloque l'ouverture

Word, Excel et PowerPoint peuvent refuser d'ouvrir le fichier alors que le
lecteur réseau, lui, fonctionne dans l'Explorateur : on y crée dossiers et
fichiers sans difficulté. Les deux n'utilisent pas le même client :
l'Explorateur passe par le service WebClient de Windows, Word par sa propre
pile HTTP. C'est vrai **même pour un fichier ouvert depuis le lecteur** : Word
traduit son chemin en adresse (`X:\…\ODOO45.docx` devient
`http://localhost:8069/webdav/aite_ecm/…/ODOO45.docx`) et télécharge lui-même
le fichier. Or Microsoft 365 bloque par défaut toute invite d'authentification
Basic, en `http` comme en `https`. Le remède, côté poste, est la valeur
`basichostallowlist` décrite au §3 (*Autoriser Word, Excel et PowerPoint*),
applications Office fermées pendant qu'on la pose.

### 6.1 HTTPS — recommandé, mais sans effet sur ce blocage

HTTPS ne lève pas le blocage d'Office : le même message apparaît derrière
Caddy, sur `https://localhost/webdav/aite_ecm/…`. HTTPS reste la
configuration cible pour le reste : le lecteur réseau se monte sans
`BasicAuthLevel`, et le mot de passe cesse de circuler en clair à chaque
requête. Un reverse proxy suffit ; comptez quelques minutes sur un poste de
test : [`WEBDAV_HTTPS_WINDOWS.md`](./WEBDAV_HTTPS_WINDOWS.md). La valeur
`basichostallowlist` (§3) reste nécessaire, avec le nom public du serveur.

### 6.2 Le mode `unc` — sans effet sur ce blocage

Le paramètre `aite_ecm.office_uri_mode = unc` fait désigner au bouton le
**chemin UNC** du lecteur au lieu de l'URL. On l'a cru capable de contourner
le blocage, Windows s'authentifiant à la place de Word. Ce n'est pas le cas :
Word traduit le chemin en adresse `http(s)`, télécharge lui-même le fichier et
bute sur le même blocage de l'authentification Basic — précédé, pour un
chemin `\\hôte@port\…`, du message de zone décrit plus bas. La spécification
des schémas d'URI d'Office
(*Office URI Schemes*) n'admet d'ailleurs, derrière `ms-word:ofe|u|`, que des
adresses `http` ou `https`. **Ce mode n'est plus recommandé** : laisser
`aite_ecm.office_uri_mode` à `url` (valeur par défaut) et autoriser l'hôte par
`basichostallowlist` (§3). Sa description suit pour mémoire ; tout ce qui
concerne la zone « Sites sensibles » ne vaut que pour lui.

**Paramètres → Technique → Paramètres système**, créer ou modifier :

| Clé | Valeur |
| --- | --- |
| `aite_ecm.office_uri_mode` | `unc` |

Le bouton sert alors `\\localhost@8069\webdav\aite_ecm\…`
au lieu de l'URL. L'adresse WebDAV affichée sur la fiche, elle, reste l'URL.

**Si Office répond « ce fichier provient d'un site de la zone Sites
sensibles »** : Windows lit `localhost@8069` comme un `utilisateur@hôte` et
relègue le chemin en zone restreinte. Deux remèdes à ce message-là, au
choix — aucun ne lève le blocage de l'authentification Basic.

*Désigner le lecteur monté* — ajouter un second paramètre système :

| Clé | Valeur |
| --- | --- |
| `aite_ecm.office_unc_root` | `Z:` |

Le bouton sert alors `Z:\Juridique et contrats\DOC-… .docx`. Word ne s'en
tient pas à ce chemin de lecteur : il le traduit en adresse WebDAV
(`http://localhost:8069/webdav/aite_ecm/…`), télécharge lui-même le fichier et
bute sur le blocage de l'authentification Basic tant que l'hôte n'est pas dans
`basichostallowlist` (§3). Le lecteur doit en outre porter cette lettre sur le
poste, ce qui limite ce réglage aux parcs où le montage est homogène.

*Ou classer le site en intranet local* — Options Internet → Sécurité →
**Intranet local** → *Sites* → *Avancé*, ajouter `http://localhost`. En
PowerShell utilisateur :

```powershell
$r = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains\localhost"
New-Item -Path $r -Force | Out-Null
New-ItemProperty -Path $r -Name http -Value 1 -PropertyType DWord -Force | Out-Null
```

`1` désigne la zone *Intranet local*. Fermer puis rouvrir Word.

> **Mode `unc` : à ne plus utiliser pour Office.** Il ne lève pas le blocage
> de l'authentification Basic, en `http` comme en `https` : Word traduit le
> chemin en adresse et s'authentifie lui-même. Un chemin UNC ne veut en outre
> rien dire sur macOS ou Linux, et LibreOffice, qui n'a pas le blocage
> d'Office, ouvre l'URL. Laisser `aite_ecm.office_uri_mode` à `url` et
> autoriser l'hôte par `basichostallowlist` (§3).

---

## 7. Pour aller plus loin

- [`WEBDAV_HTTPS_WINDOWS.md`](./WEBDAV_HTTPS_WINDOWS.md) — mettre l'espace
  documentaire en HTTPS : Caddy pour un poste, nginx pour la production.
- [`addons/aite_ecm_webdav/README.md`](../addons/aite_ecm_webdav/README.md) —
  tutoriel utilisateur ECM : lecteur réseau, *Ouvrir dans Office*, réservations.
- [`addons/aite_courrier_webdav/docs/WEBDAV.md`](../addons/aite_courrier_webdav/docs/WEBDAV.md) —
  verbes pris en charge, hooks GED, exemples `rclone` et `cadaver`.

---

*AITE Consulting — déploiement WebDAV sur Odoo 18 Windows.*
