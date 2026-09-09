# AITE ECM — Tutoriel WebDAV : l'ECM comme lecteur réseau

> **AITE Consulting · Tutoriel**
> Module `aite_ecm_office` — service WebDAV du plan de classement
> (`/webdav/aite_ecm`), ouverture directe dans Word, Excel, PowerPoint et
> LibreOffice. Odoo 18 Community et Enterprise.
> Septembre 2026.

---

## 1. À quoi ça sert

WebDAV est le protocole qui permet à un ordinateur de voir un serveur web
comme un **disque réseau**. Le module expose le plan de classement de l'ECM à
l'adresse `https://<votre-odoo>/webdav/aite_ecm/` : dans l'Explorateur
Windows, le Finder ou une suite bureautique, l'ECM apparaît comme des dossiers
et des fichiers ordinaires, alors que chaque geste passe par Odoo — droits,
réservation, versions, journal d'audit.

Trois usages concrets :

| Usage | Ce que fait l'utilisateur | Ce que fait l'ECM |
|---|---|---|
| **Ouvrir dans Word** (bouton de la fiche ou de l'explorateur) | Word s'ouvre directement sur le fichier ; il travaille, enregistre, ferme | réservation à l'ouverture, **nouvelle version** à chaque enregistrement, libération à la fermeture |
| **Lecteur réseau** | parcourt `E:\Juridique et contrats\`, ouvre, copie, dépose des fichiers | applique les droits de dossier et de confidentialité ; un fichier déposé devient un **document ECM** |
| **Migration / dépôt en masse** | copie un dossier entier depuis l'ancien serveur de fichiers | crée un document par fichier, dans le bon dossier de classement |

---

## 2. Ce que l'on voit dans le lecteur

```
/webdav/aite_ecm/
├── Direction générale/
│   └── DOC-2026-00045 - PV conseil du 12 mars.pdf
├── Juridique et contrats/
│   ├── Contrats fournisseurs/
│   │   └── DOC-2026-00128 - Contrat de maintenance groupe électrogène.docx
│   └── DOC-2026-00121 - Bail commercial agence de Bonabéri.docx
├── Ressources humaines/
│   └── Dossiers du personnel/ …
└── Sans classement/
    └── DOC-2026-00133 - Procédure d'achat v3.docx
```

Règles de représentation :

- **un dossier par dossier de classement**, avec la même hiérarchie que dans
  l'ECM ; les documents sans dossier sont sous **« Sans classement »** ;
- **un fichier par document** : `RÉFÉRENCE - Titre.extension`, toujours la
  **dernière version** ; les versions précédentes restent consultables dans
  Odoo ;
- un document sans fichier n'apparaît pas ;
- les caractères interdits dans les noms de fichiers (`\ / : * ? " < > |`)
  sont remplacés par `_` ;
- un fichier verrouillé dans l'ECM (finalisé, archivé ou réservé par un autre)
  apparaît en **lecture seule**.

---

## 3. Se connecter

### 3.1 Windows (Explorateur)

1. Explorateur de fichiers → clic droit sur *Ce PC* → **Connecter un lecteur
   réseau**.
2. Lettre : `E:` (par exemple) ; Dossier : `https://<votre-odoo>/webdav/aite_ecm/`
   ; cochez *Se connecter à l'aide d'informations d'identification différentes*.
3. Identifiants : votre **login Odoo** et votre **mot de passe Odoo**.

Le lecteur apparaît dans *Ce PC* ; les dossiers se parcourent comme sur un
serveur de fichiers.

> **HTTPS obligatoire.** Windows refuse d'envoyer un mot de passe en clair :
> l'URL doit être en `https://`. En environnement de test sans certificat, un
> administrateur peut autoriser HTTP via la clé de registre
> `HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters\BasicAuthLevel = 2`
> (puis redémarrer le service *WebClient*) — à réserver à un poste de test.

> **Fichiers de plus de 50 Mo.** Le client WebDAV de Windows limite les
> transferts à 50 Mo par défaut : la clé `FileSizeLimitInBytes` (même
> emplacement) permet d'augmenter cette limite (par exemple `4294967295`).

### 3.2 macOS (Finder)

Finder → menu **Aller → Se connecter au serveur** (⌘K) → adresse
`https://<votre-odoo>/webdav/aite_ecm/` → **Se connecter** → identifiants Odoo.
Le volume est monté sur le Bureau et dans la barre latérale.

### 3.3 Linux

- Fichiers (GNOME) : *Autres emplacements* → `davs://<votre-odoo>/webdav/aite_ecm/`.
- En ligne de commande : `davfs2` (`sudo mount -t davfs https://<votre-odoo>/webdav/aite_ecm/ /mnt/ecm`).

### 3.4 Sans rien connecter : ouvrir depuis Odoo

Sur la fiche d'un document ou dans l'explorateur, les boutons **Ouvrir dans
Word / Excel / PowerPoint** et **LibreOffice** lancent l'application du poste
directement sur le fichier (protocoles `ms-word:ofe|u|…` et
`vnd.libreoffice.command:ofe|u|…`). À la première utilisation, l'application
demande les identifiants Odoo et les mémorise. Aucun lecteur n'a besoin d'être
connecté.

---

## 4. Au quotidien

| Geste dans l'Explorateur / l'application | Effet dans l'ECM |
|---|---|
| Ouvrir un fichier | lecture, si vos droits le permettent (dossier, confidentialité, partage nominatif) |
| Ouvrir dans Word / LibreOffice | **réservation** du document à votre nom (verrou WebDAV) ; les collègues le voient réservé |
| Enregistrer | **nouvelle version** (v2, v3…), empreinte SHA-256, audit « WebDAV » |
| Fermer l'application | **libération** de la réservation |
| Copier un nouveau fichier dans un dossier | **nouveau document** (titre = nom du fichier sans extension) dans ce dossier de classement, classé « Interne » ou selon le type par défaut du dossier |
| Renommer un fichier | le **titre** du document change (la référence, elle, ne change jamais) |
| Déplacer un fichier vers un autre dossier | le document est **reclassé** (si vous avez le droit d'écriture sur la destination) |
| Supprimer un fichier | le document part à la **corbeille** ECM (restaurable, purge après 30 jours) |
| Créer un dossier | un **dossier de classement** est créé, s'il vous est permis d'écrire dans le dossier parent |
| Fichiers `~$xxx.docx`, `.~lock.xxx#` | ignorés : ce sont les verrous temporaires des suites bureautiques |

Deux cas particuliers à connaître :

- **« Enregistrer puis remplacer »** : Word et LibreOffice enregistrent
  souvent dans un fichier temporaire puis le déplacent sur l'original. Le
  service reconnaît ce schéma : la version est créée sur le bon document et le
  temporaire est écarté — vous ne verrez ni doublon ni document fantôme.
- **Document finalisé ou archivé** : le fichier est en lecture seule ; pour le
  modifier, remettez-le en brouillon dans Odoo (managers).

---

## 5. Sécurité

- **Authentification** : HTTP Basic vers un compte Odoo (login + mot de
  passe), toujours en HTTPS. Les utilisateurs *portail* n'ont pas accès.
- **Droits** : exactement ceux de l'ECM — rôle, droits du dossier (groupes et
  personnes nommées), confidentialité, partage nominatif, réservation. Un
  document invisible dans Odoo l'est aussi dans le lecteur.
- **Traçabilité** : chaque lecture, dépôt, version, renommage, réservation et
  mise à la corbeille est journalisé avec la source **WebDAV**.
- **Mot de passe d'application** : si l'instance utilise une authentification
  déléguée (SSO), créez pour l'utilisateur une **clé d'API** Odoo et
  utilisez-la comme mot de passe.

---

## 6. Dépannage

| Symptôme | Cause probable | Remède |
|---|---|---|
| Windows : « Le nom du dossier n'est pas valide » ou demande de mot de passe en boucle | URL en `http://` ou service *WebClient* arrêté | passer en HTTPS ; démarrer le service *WebClient* (services.msc) |
| Word ouvre le fichier en lecture seule | document finalisé / archivé, ou réservé par un collègue | vérifier le bandeau de la fiche ; attendre la libération ou demander à un manager |
| Enregistrement refusé (« fichier verrouillé ») | vous n'avez pas le droit d'écriture sur le dossier, ou le document est réservé par un autre | onglet **Accès** de la fiche ; réservation |
| Fichier volumineux refusé sous Windows | limite `FileSizeLimitInBytes` (50 Mo) | augmenter la clé de registre ; la limite ECM est de 100 Mo |
| Le lecteur est lent à l'ouverture | Windows interroge chaque dossier ; grande arborescence | connecter le lecteur sur un sous-dossier (`…/webdav/aite_ecm/Juridique%20et%20contrats/`) |
| Un fichier déposé n'apparaît pas dans l'ECM | dépôt à la racine (interdit) ou nom commençant par `~$` | déposer dans un dossier ; les temporaires sont ignorés |

---

## 7. Pour l'administrateur et l'intégrateur

**Activation.** Installer `aite_ecm_office` ; aucune configuration n'est
requise pour le WebDAV. L'adresse à communiquer aux utilisateurs est affichée
dans ECM › Configuration › Paramètres › *Édition Office*.

**Reverse proxy.** Autoriser les méthodes WebDAV (`PROPFIND`, `PROPPATCH`,
`MKCOL`, `MOVE`, `COPY`, `LOCK`, `UNLOCK`) et des corps de requête jusqu'à
100 Mo ; sur nginx : `client_max_body_size 100m;` et ne pas filtrer les
méthodes. Ne pas mettre de cache sur `/webdav/`.

**Architecture.** Le module réutilise le serveur WebDAV du courrier
(`aite_courrier_webdav`) — protocole RFC 4918, authentification Basic,
formatage des réponses — et branche dessus un **service** propre à l'ECM :

```
aite_ecm_office/
├── controllers/webdav.py      route /webdav/aite_ecm, verrous ↔ réservations,
│                              création de dossiers, MOVE, index HTML
└── models/aite_ecm_webdav.py  service : résolution des chemins, descripteurs,
                               propfind / read_file / put_file / lock_resource /
                               unlock_resource / delete_resource / move_resource /
                               make_collection
```

Le contrat du service (mêmes méthodes que `aite.courrier.webdav`) permet
d'exposer n'importe quel autre modèle versionné de la même manière :
implémenter les méthodes ci-dessus et sous-classer le contrôleur avec une
nouvelle route.

**Tests.** `--test-tags /aite_ecm_office` : arborescence, PUT (version,
nouveau document, temporaires ignorés), verrous ↔ réservations (423 pour un
autre utilisateur), MOVE (renommage, reclassement, « enregistrer puis
déplacer »), URI Office.

**Lien avec le courrier.** Le lecteur du courrier reste disponible sur
`/webdav/aite_courrier/` (un dossier par courrier, ses pièces) ; les deux
lecteurs peuvent être connectés en parallèle.

---

*© AITE Consulting — Tutoriel WebDAV AITE ECM.*
