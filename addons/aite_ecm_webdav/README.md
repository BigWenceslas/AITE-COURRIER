# AITE ECM — Lecteur réseau et ouverture dans Office

> **AITE Consulting · Tutoriel**
> Module `aite_ecm_webdav` — « AITE ECM - Lecteur réseau et ouverture dans
> Office ». Odoo 18 Community et Enterprise.
> Septembre 2026.

---

## 1. Ce que fait ce module

Le module publie le plan de classement de l'ECM à l'adresse
`https://<votre-odoo>/webdav/aite_ecm` en **WebDAV** — le protocole que
Windows, macOS et Linux savent monter comme un disque, et que Word, Excel et
PowerPoint savent ouvrir directement, à condition, sous Windows, que le poste
autorise le serveur à leur demander des identifiants (§3, *Prérequis*).

Il apporte deux gestes, pour deux besoins différents :

| Geste | Pour qui | Ce qui se passe |
|---|---|---|
| Bouton **Ouvrir dans Office** sur la fiche d'un document | tout le monde, au cas par cas | Word (ou Excel, PowerPoint) s'ouvre sur le fichier ; le document est **réservé** à votre nom ; chaque *Enregistrer* crée une **nouvelle version** dans l'ECM |
| **Lecteur réseau** monté une fois pour toutes | personnes qui manipulent beaucoup de fichiers, migrations | le plan de classement apparaît comme des dossiers ; on ouvre, dépose, renomme, déplace et supprime comme sur un serveur de fichiers |

Dans les deux cas, **rien ne contourne l'ECM** : les droits, la confidentialité,
les réservations, les versions et le journal d'audit s'appliquent exactement
comme dans l'application.

---

## 2. Installation et vérification

Le module dépend uniquement de `aite_ecm_document` : il s'installe sur
Community comme sur Enterprise, sans configuration.

```powershell
& "..\python\python.exe" odoo-bin -c odoo.conf -d <base> -i aite_ecm_webdav --stop-after-init
```

Deux points à vérifier côté serveur, une seule fois :

- **`web.base.url`** (Paramètres › Technique › Paramètres système) doit
  contenir l'adresse publique d'Odoo en **https** : c'est elle qui construit
  les liens envoyés à Word.
- **Reverse proxy** : autoriser les méthodes WebDAV et les corps de requête
  jusqu'à 100 Mo. Sur nginx, dans le bloc du site :

```nginx
client_max_body_size 100m;
location /webdav/ {
    proxy_pass http://127.0.0.1:8069;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
}
```

Pour vérifier que le service répond, depuis n'importe quel poste :

```bash
curl -u mon.login -X PROPFIND https://<votre-odoo>/webdav/aite_ecm/ -H "Depth: 1"
```

La réponse est un XML `multistatus` listant vos dossiers de classement.

---

## 3. Ouvrir un document dans Word (le geste le plus simple)

C'est la façon la plus directe : aucun lecteur à connecter.

**Prérequis, une fois par poste Windows : autoriser le serveur dans Office.**
Depuis la version 2311 (Current Channel, décembre 2023 ; Monthly Enterprise
Channel, janvier 2024 ; Semi-Annual Enterprise Channel 2402, juillet 2024 ;
Office 2016, 2019 et 2021 vendus au détail, au rythme du Current Channel),
Word, Excel et PowerPoint sous Windows bloquent par défaut les demandes
d'identifiants en authentification **Basic** — la seule que propose le serveur
WebDAV d'Odoo. Au lieu de demander vos identifiants, Word affiche « Microsoft
Office a bloqué l'accès aux … car la source utilise une méthode de connexion
qui peut être non sécurisée ». Le blocage porte sur la **méthode**, pas sur le
transport : il s'applique en `https` comme en `http`, au bouton *Ouvrir dans
Office* comme à un fichier ouvert depuis le lecteur réseau (§4). Les versions
d'Office en licence en volume (LTSC) ne sont pas concernées.

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
   reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
   ```

3. Rouvrir Word : il **demande des identifiants** au lieu de bloquer.

- **Hôtes.** `/d` liste des noms d'hôtes séparés par `;`, sans `https://`.
  `localhost;localhost:8069` vaut pour un poste de test ; en production,
  mettre le nom du serveur (par exemple `ecm.client.fr`). La forme
  `hôte:port` s'ajoute par prudence : aucune source ne dit si le port compte.
  Garder les **guillemets** : en PowerShell, `;` sépare deux instructions et
  la liste serait tronquée. `/f` remplace une valeur existante : en reprendre
  d'abord les hôtes (`reg query` sur la même clé).
- **Sur un parc**, poser la même liste par stratégie de groupe (*User
  Configuration › Policies › Administrative Templates › Microsoft Office 2016
  › Security Settings*, modèles d'administration Office 5359.1000 ou plus
  récents) ou par Cloud Policy.
- **Limites.** Selon son libellé, la stratégie ne s'applique qu'aux versions
  d'Office sur abonnement. Une Cloud Policy du tenant Microsoft 365
  (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`) ou le Baseline
  Security Mode peuvent primer sur la valeur locale. Microsoft ne recommande
  cette autorisation qu'à titre transitoire.
- **Instance de test en `http`.** L'ancienne clé d'Office
  `HKCU\Software\Microsoft\Office\16.0\Common\Internet\BasicAuthLevel` à
  `2` (Basic autorisé hors SSL), distincte de celle du service WebClient
  (§4.1), y reste utile, mais **ne suffit plus** depuis la version 2311 ; en
  `https`, elle est inutile.
- **HTTPS** reste recommandé — il protège le mot de passe — mais ne dispense
  pas de cette valeur.

Puis, à chaque document :

1. Ouvrez le document dans l'ECM (fiche ou explorateur).
2. Cliquez **Ouvrir dans Office** — le bouton n'apparaît que pour les formats
   bureautiques (Word, Excel, PowerPoint et leurs équivalents OpenDocument).
3. À la première utilisation, Word demande vos **identifiants Odoo** (login et
   mot de passe, ou clé d'API — §7) et les mémorise. S'il affiche à la place
   « …méthode de connexion qui peut être non sécurisée », le prérequis
   ci-dessus manque.
4. Travaillez, puis **Enregistrer** : une nouvelle version apparaît dans
   l'ECM, à votre nom.
5. Fermez Word : la réservation est libérée.

![](w02_bouton_office.png)

| Extension | Application lancée | Si vous n'avez pas le droit d'écriture |
|---|---|---|
| docx, doc, rtf, odt | Microsoft Word | ouverture en **lecture seule** |
| xlsx, xls, csv, ods | Microsoft Excel | ouverture en lecture seule |
| pptx, ppt, odp | Microsoft PowerPoint | ouverture en lecture seule |
| pdf, images, autres | — | utiliser *Prévisualiser* ou *Télécharger* |

> **Réservation automatique.** Ouvrir en écriture réserve le document : vos
> collègues le voient marqué « Réservé par … » et ne peuvent pas y déposer de
> version tant que vous n'avez pas fermé le fichier. C'est ce qui évite les
> versions concurrentes.

---

## 4. Connecter le lecteur réseau

### 4.1 Windows

1. Explorateur de fichiers → clic droit sur **Ce PC** → *Connecter un lecteur
   réseau*.
2. Lecteur : `E:` ; Dossier : `https://<votre-odoo>/webdav/aite_ecm/` ;
   cochez *Se connecter à l'aide d'informations d'identification différentes*.
3. Saisissez votre **login Odoo** et votre **mot de passe Odoo**.

![](w01_lecteur_reseau.png)

> **HTTPS obligatoire.** Windows refuse d'envoyer un mot de passe sur une
> connexion non chiffrée. Sur un poste de test uniquement, un administrateur
> peut passer la clé
> `HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters\BasicAuthLevel`
> à `2` puis redémarrer le service *WebClient*. HTTPS ne lève pas, en
> revanche, le blocage d'Office décrit au §3.

> **Ouvrir un fichier du lecteur dans Word, Excel ou PowerPoint** suppose le
> même prérequis que le bouton (§3, *Prérequis*) : Word ne réutilise pas la
> connexion du lecteur, il convertit le chemin `E:\…` en adresse `http(s)` et
> télécharge lui-même le fichier. Les gestes de l'Explorateur, eux, n'en
> dépendent pas : copier, renommer, créer un dossier ou un fichier
> fonctionnent même quand Word refuse d'ouvrir.

> **Fichiers de plus de 50 Mo.** Le client WebDAV de Windows limite les
> transferts à 50 Mo : augmentez `FileSizeLimitInBytes` (même emplacement,
> par exemple `4294967295`). La limite de l'ECM est de 100 Mo.

### 4.2 macOS

Finder → **Aller › Se connecter au serveur** (⌘K) →
`https://<votre-odoo>/webdav/aite_ecm/` → *Se connecter* → identifiants Odoo.
Le volume apparaît dans la barre latérale.

### 4.3 Linux

- Fichiers (GNOME) → *Autres emplacements* →
  `davs://<votre-odoo>/webdav/aite_ecm/`
- En ligne de commande :
  `sudo mount -t davfs https://<votre-odoo>/webdav/aite_ecm/ /mnt/ecm`

---

## 5. Ce que l'on voit, et comment c'est nommé

```
/webdav/aite_ecm/
├── Direction générale/
│   └── DOC-2026-00045 - PV conseil du 12 mars.pdf
├── Juridique et contrats/
│   ├── Contrats fournisseurs/
│   ├── Baux et immobilier/
│   └── DOC-2026-00128 - Contrat de maintenance groupe électrogène.docx
├── Ressources humaines/
└── Sans classement/
```

- **Un dossier par dossier de classement**, avec la hiérarchie de l'ECM ; les
  documents sans dossier sont regroupés sous **« Sans classement »**.
- **Un fichier par document**, nommé `RÉFÉRENCE - Titre.extension` et
  correspondant toujours à la **dernière version**. Les versions antérieures
  restent dans Odoo.
- Un document sans fichier n'apparaît pas ; les caractères interdits par
  Windows (`\ / : * ? " < > |`) sont remplacés par `_` et le titre est tronqué
  à 80 caractères.
- Un document **finalisé, archivé ou réservé par un autre** apparaît en
  lecture seule.

---

## 6. Les gestes du quotidien

| Dans l'Explorateur ou l'application | Effet dans l'ECM |
|---|---|
| Ouvrir un fichier | lecture, si vos droits le permettent |
| Ouvrir dans Word ou LibreOffice (Word sous Windows : poste préparé, §3 *Prérequis*) | **réservation** à votre nom |
| Enregistrer | **nouvelle version**, empreinte SHA-256, audit source « WebDAV » |
| Fermer l'application | **libération** de la réservation |
| Copier un nouveau fichier dans un dossier | **nouveau document ECM**, titre = nom du fichier sans extension |
| Renommer un fichier | le **titre** du document change (la référence, jamais) |
| Déplacer vers un autre dossier | le document est **reclassé** |
| Supprimer un fichier | le document part à la **corbeille** (restaurable) |
| Créer un dossier | un **dossier de classement** est créé (managers, archivistes, administrateurs) |
| Renommer ou déplacer un dossier | le dossier est **renommé** ou **reclassé**, avec toute sa branche |
| Supprimer un dossier | le dossier est **archivé** s'il est vide ; refusé s'il contient encore des documents |
| Fichiers `~$…`, `.~lock…`, `.tmp` | ignorés : ce sont les verrous temporaires des suites bureautiques |

Deux comportements méritent une explication :

- **« Enregistrer sous » de Word.** Word écrit d'abord un fichier temporaire
  puis le renomme sur l'original. Le service reconnaît ce schéma : la version
  est créée sur le bon document, sans document fantôme.
- **Document verrouillé.** Si le document est finalisé, archivé, réservé par
  un collègue ou sous gel juridique, l'enregistrement est refusé avec un code
  *423 Verrouillé* ; Word propose alors d'enregistrer une copie locale.

---

## 7. Sécurité

- **Authentification** : HTTP Basic vers un compte Odoo, en HTTPS. Les
  utilisateurs *portail* n'ont pas accès. Word, Excel et PowerPoint sous
  Windows bloquent par défaut cette méthode, en HTTPS aussi : chaque poste
  doit autoriser le serveur (§3, *Prérequis*).
- **Droits** : identiques à ceux de l'ECM — rôle, droits du dossier (groupes
  et personnes nommées), confidentialité, partage nominatif, réservation, gel
  juridique. Un document que vous ne voyez pas dans Odoo n'apparaît pas dans
  le lecteur.
- **Traçabilité** : lecture, dépôt, version, renommage, reclassement,
  réservation et mise à la corbeille sont journalisés avec la source
  **WebDAV**.
- **Authentification déléguée (SSO)** : créez une **clé d'API** Odoo
  (Préférences › Sécurité du compte) et utilisez-la comme mot de passe.

---

## 8. Dépannage

| Symptôme | Cause probable | Remède |
|---|---|---|
| Windows : « Le nom du dossier n'est pas valide » | URL en `http://`, ou service *WebClient* arrêté | passer en HTTPS ; démarrer le service *WebClient* (services.msc) |
| Demande de mot de passe en boucle | `BasicAuthLevel` à 1, ou mot de passe incorrect | vérifier les identifiants ; voir §4.1 |
| Word : « Microsoft Office a bloqué l'accès… car la source utilise une méthode de connexion qui peut être non sécurisée » (bouton ou lecteur réseau, `http` ou `https`) | le poste n'autorise pas le serveur : Office bloque l'authentification Basic | §3, *Prérequis* : valeur `basichostallowlist`, toutes applications Office fermées, puis rouvrir Word |
| Même message, valeur pourtant posée | Office pas entièrement fermé ; valeur posée dans la session d'un autre compte Windows ; Cloud Policy du tenant ou Baseline Security Mode prioritaire ; Office hors abonnement | §3, *Prérequis* (*Limites*) ; voir avec l'administrateur Microsoft 365 |
| Word ouvre en lecture seule | document finalisé, archivé, réservé par un autre, ou droits insuffisants | consulter le bandeau de la fiche ECM |
| Enregistrement refusé (« fichier verrouillé ») | réservation d'un collègue ou gel juridique | attendre la libération ; un manager peut libérer |
| Fichier volumineux refusé | limite Windows de 50 Mo | augmenter `FileSizeLimitInBytes` |
| Le bouton *Ouvrir dans Office* est absent | le document n'a pas de fichier, ou le format n'est pas bureautique | déposer un fichier ; utiliser *Prévisualiser* pour les PDF |
| Lecteur lent à l'ouverture | arborescence volumineuse, Windows interroge chaque dossier | connecter le lecteur directement sur un sous-dossier |
| `curl` renvoie 401 | identifiants ou clé d'API erronés | vérifier le login Odoo |

---

## 9. Pour l'administrateur et l'intégrateur

**Architecture.** Le module fournit un **service** (`aite.ecm.webdav`,
`models/aite_ecm_webdav.py`) qui traduit les chemins WebDAV en enregistrements
ECM, et un **contrôleur** (`controllers/webdav.py`, route
`/webdav/aite_ecm`) qui parle le protocole : `OPTIONS`, `PROPFIND`, `GET`,
`PUT`, `DELETE`, `MOVE`, `MKCOL`, `LOCK`, `UNLOCK`, `HEAD`. Toutes les
opérations passent par l'ORM sous l'identité de l'utilisateur authentifié —
c'est ce qui garantit que les règles ECM s'appliquent sans code de sécurité
dupliqué.

Le service expose un contrat simple (`propfind`, `read_file`, `put_file`,
`lock`, `unlock`, `delete`, `move`, `mkcol`) : pour publier un autre modèle
versionné en WebDAV, il suffit de réimplémenter ces méthodes et de déclarer
une nouvelle route.

**Correspondance des erreurs.** `WebdavNotFound` → 404, `WebdavForbidden` →
403, `WebdavLocked` → 423, `WebdavConflict` → 409 : les clients WebDAV
affichent alors un message compréhensible plutôt qu'une erreur générique.

**Tests.** `--test-tags /aite_ecm_webdav` — 22 cas : arborescence, lecture avec
ETag, enregistrement (version et nouveau document), verrou et conflit entre
utilisateurs, déplacement, construction de l'URI Office (modes `url` et `unc`),
sécurité (401 et documents confidentiels absents du listing), clé d'API,
création depuis l'Explorateur, `HEAD`, dossiers (création, renommage,
déplacement, suppression, droits).

**Modules voisins.** `aite_courrier_webdav` publie de la même façon les pièces
de courrier sur `/webdav/aite_courrier` ; `aite_ecm_office` ajoute l'édition
dans le navigateur (Collabora / OnlyOffice) et l'aller-retour Google Docs. Les
lecteurs peuvent être connectés en parallèle.

---

*© AITE Consulting — Tutoriel « Lecteur réseau et ouverture dans Office ».*
