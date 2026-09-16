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

> **En production, exposer Odoo en HTTPS** derrière un reverse proxy : le
> montage fonctionne alors sans toucher au registre. Prévoir
> `client_max_body_size 100m;` et le passage des verbes WebDAV.

### Monter le lecteur

Explorateur → clic droit sur **Ce PC** → *Connecter un lecteur réseau* :

- Lecteur : `W:`
- Dossier : `http://localhost:8069/webdav/aite_courrier`
- cocher **Se connecter à l'aide d'informations d'identification différentes**
- login et mot de passe **Odoo** (une clé d'API fait office de mot de passe :
  Préférences → Sécurité du compte)

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
| Fichier > 50 Mo refusé par Windows | limite du client WebDAV | `FileSizeLimitInBytes`, §3 |
| Lecteur lent à l'ouverture | arborescence volumineuse | monter directement un sous-dossier |

---

## 6. Pour aller plus loin

- [`addons/aite_ecm_webdav/README.md`](../addons/aite_ecm_webdav/README.md) —
  tutoriel utilisateur ECM : lecteur réseau, *Ouvrir dans Office*, réservations.
- [`addons/aite_courrier_webdav/docs/WEBDAV.md`](../addons/aite_courrier_webdav/docs/WEBDAV.md) —
  verbes pris en charge, hooks GED, exemples `rclone` et `cadaver`.

---

*AITE Consulting — déploiement WebDAV sur Odoo 18 Windows.*
