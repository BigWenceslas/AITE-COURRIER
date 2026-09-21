# WebDAV AITE — déploiement sur une instance Odoo 18 Windows

> Installer, configurer, utiliser et vérifier l'accès WebDAV sur un poste
> Windows 10 exécutant Odoo 18 **Community** en local.

---

## 1. Ce que font les modules

Deux modules publient un espace documentaire en **WebDAV**, servi par Odoo
lui-même : même port, même authentification, aucune brique externe. Le
protocole est celui que Windows sait monter comme un lecteur réseau et que
Word, Excel et PowerPoint savent ouvrir directement.

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

> **Office bloque l'ouverture depuis une instance en `http`.** Le réglage
> ci-dessous ne suffit pas toujours : les versions récentes de Microsoft 365
> refusent l'authentification Basic en clair quoi qu'il arrive — « la source
> utilise une méthode de connexion qui peut être non sécurisée ». Deux issues,
> décrites au §7 : passer l'instance en **HTTPS** (la bonne), ou faire pointer
> le bouton vers le **lecteur réseau** plutôt que vers l'URL.

Les applications Office ont **leur propre** interdiction de l'authentification
Basic sur HTTP, distincte de celle du service WebClient. Sans ce réglage, le
bouton *Ouvrir dans Office* lance Word, qui échoue aussitôt. En PowerShell
**utilisateur** (la clé est propre à chaque compte Windows), applications
Office fermées :

```powershell
reg add HKCU\Software\Microsoft\Office\16.0\Common\Internet `
  /v BasicAuthLevel /t REG_DWORD /d 2 /f
```

`16.0` couvre Office 2016, 2019, 2021 et Microsoft 365.

> **En production, exposer Odoo en HTTPS** derrière un reverse proxy : le
> montage fonctionne alors sans toucher au registre, et cette clé Office
> devient elle aussi inutile. Prévoir `client_max_body_size 100m;` et le
> passage des verbes WebDAV.

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
| Word se lance puis échoue | clé Basic d'Office absente | §3, `HKCU\…\Office\16.0\Common\Internet` |
| Fichier > 50 Mo refusé par Windows | limite du client WebDAV | `FileSizeLimitInBytes`, §3 |
| Lecteur lent à l'ouverture | arborescence volumineuse | monter directement un sous-dossier |

---

## 7. Quand Office bloque l'ouverture en `http`

Sur une instance en clair, Word peut refuser d'ouvrir le fichier alors que le
lecteur réseau, lui, fonctionne : c'est Word qui parle HTTP dans le premier
cas, et Windows dans le second. Deux réponses.

### 7.1 HTTPS — la bonne

Elle lève d'un coup ce blocage, celui du client Windows et la limite de
taille, et cesse de promener le mot de passe en clair à chaque requête. Un
reverse proxy suffit ; comptez quelques minutes sur un poste de test :
[`WEBDAV_HTTPS_WINDOWS.md`](./WEBDAV_HTTPS_WINDOWS.md).

### 7.2 Passer par le lecteur réseau — le dépannage

Si l'instance doit rester en `http`, le bouton peut désigner le **chemin UNC**
du lecteur au lieu de l'URL. Word ne fait alors plus de requête HTTP : il ouvre
un fichier sur un lecteur, et c'est Windows qui s'authentifie — ce qui
fonctionne déjà.

**Paramètres → Technique → Paramètres système**, créer ou modifier :

| Clé | Valeur |
| --- | --- |
| `aite_ecm.office_uri_mode` | `unc` |

Le bouton sert alors `\\localhost@8069\DavWWWRoot\webdav\aite_ecm\…`
au lieu de l'URL. L'adresse WebDAV affichée sur la fiche, elle, reste l'URL.

> **À réserver aux parcs Windows.** Un chemin UNC ne veut rien dire sur macOS
> ou Linux, et LibreOffice n'a pas le blocage d'Office : pour eux, l'URL est la
> bonne réponse. C'est pourquoi ce mode se demande explicitement au lieu d'être
> déduit. Repasser à `url` dès que l'instance est en HTTPS.

---

## 6. Pour aller plus loin

- [`WEBDAV_HTTPS_WINDOWS.md`](./WEBDAV_HTTPS_WINDOWS.md) — mettre l'espace
  documentaire en HTTPS : Caddy pour un poste, nginx pour la production.
- [`addons/aite_ecm_webdav/README.md`](../addons/aite_ecm_webdav/README.md) —
  tutoriel utilisateur ECM : lecteur réseau, *Ouvrir dans Office*, réservations.
- [`addons/aite_courrier_webdav/docs/WEBDAV.md`](../addons/aite_courrier_webdav/docs/WEBDAV.md) —
  verbes pris en charge, hooks GED, exemples `rclone` et `cadaver`.

---

*AITE Consulting — déploiement WebDAV sur Odoo 18 Windows.*
