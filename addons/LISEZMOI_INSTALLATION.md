# AITE ECM & AITE Courrier — 29 modules Odoo 18

Archive unique contenant **tous les modules** de la suite, prêts à être copiés
dans le dossier `addons` d'Odoo 18 (Community ou Enterprise).

Version 2.1 · Septembre 2026 · AITE Consulting

---

## 1. Installation

**1. Copier les modules.** Décompressez cette archive dans le dossier des
modules de votre instance. Sous Windows, avec l'installateur officiel :

```
C:\Program Files\Odoo 18.0.<version>\server\odoo\addons\
```

Vous devez y retrouver les dossiers `aite_*` : 26 sur Odoo Community, 29 sur
Enterprise. Les trois modules Enterprise — `aite_courrier_sign`,
`aite_courrier_ged_documents`, `aite_ecm_documents` — ne se copient **que sur
Enterprise** : sur Community, *Activer* les laisse bloqués « à installer »
(voir `docs/TUTORIEL_SIGNATURE.md` §2). Si vous utilisez un dossier
personnalisé déclaré dans `addons_path`, copiez-les là — mais **à un seul
endroit** : deux exemplaires du même module provoquent des erreurs.

Pour la **signature électronique sur Community** (`aite_courrier_sign_oca`),
copiez aussi, au même endroit, le dossier `oca\sign_oca` du paquet : c'est
le module communautaire OCA sur lequel elle s'appuie
(`docs/TUTORIEL_SIGNATURE_COMMUNITY.md`).

**2. Redémarrer le service Odoo**, puis, dans Apps, cliquer
**Mettre à jour la liste des Apps**.

**3. Installer.** Un seul module suffit : **AITE ECM** (`aite_ecm`) installe
la suite Courrier et la Fondation ECM avec leurs dépendances.

Nous recommandons la ligne de commande plutôt que le bouton de l'interface :
l'installation peut dépasser la limite de temps des workers HTTP, et le
journal affiche l'erreur exacte en cas de problème.

```powershell
net stop odoo-server-18.0
cd "C:\Program Files\Odoo 18.0.<version>\server"
& "..\python\python.exe" odoo-bin -c odoo.conf -d <base> -i aite_ecm --stop-after-init
net start odoo-server-18.0
```

Sous Linux : `./odoo-bin -c odoo.conf -d <base> -i aite_ecm --stop-after-init`

---

## 2. Les 29 modules

### Socle et courrier

| Module | Rôle |
|---|---|
| `aite_courrier_base` | Rôles (8 groupes), confidentialité, journal d'audit — socle commun |
| `aite_courrier_workflow` | Moteur de circuits : étapes, rôles habilités, délais, transitions |
| `aite_courrier_core` | Courriers : types, références, services, priorités, SLA |
| `aite_courrier_validation` | Runtime des circuits sur le courrier (transitions, rejets, historique) |
| `aite_courrier_ged` | Pièces versionnées, dossiers, étiquettes, confidentialité |
| `aite_courrier_capture` | Boîte e-mail dédiée : les messages deviennent des courriers |
| `aite_courrier_ocr` | Reconnaissance de texte des pièces numérisées |
| `aite_courrier_reponse` | Modèles de réponse, courrier sortant lié |
| `aite_courrier_webdav` | Pièces de courrier en lecteur réseau |
| `aite_courrier` | **Chapeau Courrier** + tableau de bord |
| `aite_courrier_portal` | Dépôt et suivi par les tiers *(optionnel)* |
| `aite_courrier_sign_oca` | Signature électronique via le module OCA `sign_oca` *(optionnel, **Community**)* |
| `aite_courrier_sign` | Signature via Odoo Sign *(optionnel, **Enterprise**)* |

### Fondation ECM

| Module | Rôle |
|---|---|
| `aite_ecm_document` | **Application ECM** : documents, types et métadonnées, plan de classement, versions, réservation, relations, corbeille, explorateur de fichiers, numérisation |
| `aite_ecm_workflow` | Circuits polymorphes : documents ECM et dossiers métier |
| `aite_ecm_dossier` | Dossiers métier : pièces attendues, complétude, circuit |
| `aite_ecm_share` | Partage externe : lien expirant, quota, filigrane |
| `aite_ecm_api` | API REST `/api/ecm/v1` + OpenAPI |
| `aite_courrier_ecm` | **Pont** : les pièces de courrier deviennent des documents ECM *(auto)* |
| `aite_ecm` | **Chapeau ECM** : installe Courrier + Fondation ECM |

### Conservation et preuve (v2.1)

| Module | Rôle |
|---|---|
| `aite_ecm_records` | Durées de conservation, sort final, cycle de vie, gel juridique, bordereaux d'élimination, archives physiques |
| `aite_ecm_sae` | Scellement, journal de preuve chaîné, horodatage, vérification d'intégrité, attestation, PDF/A, export SEDA |

### Bureautique et interopérabilité

| Module | Rôle |
|---|---|
| `aite_ecm_webdav` | Lecteur réseau `/webdav/aite_ecm` + ouverture dans Word, Excel, PowerPoint |
| `aite_ecm_office` | Ajoute LibreOffice, l'édition dans le navigateur (Collabora / OnlyOffice) et Google Docs *(requiert `aite_ecm_webdav`)* |
| `aite_ecm_nextcloud` | Miroir Nextcloud : synchronisation, webhooks, liens publics |
| `aite_ecm_nextcloud_courrier` | Étend le miroir Nextcloud aux pièces de courrier *(auto)* |
| `aite_ecm_documents` | Passerelle vers l'app Documents *(auto, **Enterprise**)* |
| `aite_courrier_ged_documents` | Pièces de courrier dans l'app Documents *(auto, **Enterprise**)* |

### Divers

| Module | Rôle |
|---|---|
| `aite_ecm_demo` | Jeu de données de test (profils léger / standard / complet) |

---

## 3. Community ou Enterprise

Toute la suite s'installe sur **Odoo 18 Community**. Trois modules requièrent
Enterprise et restent simplement non installés sinon :
`aite_courrier_sign` (Odoo Sign), `aite_ecm_documents` et
`aite_courrier_ged_documents` (app Documents). Les deux derniers s'installent
d'eux-mêmes quand l'app Documents est présente.

La signature électronique existe dans les deux éditions : sur Community,
`aite_courrier_sign_oca` (module OCA `sign_oca`, livré dans `oca\`) ; sur
Enterprise, `aite_courrier_sign` (Odoo Sign). Les deux s'excluent.

---

## 4. Après l'installation

1. **Jeu de données de test** (recommandé pour découvrir et former) :
   ECM › Configuration › *Jeu de données de test* → **Démarrer**, puis
   **Tout générer maintenant**.
2. **Adapter les référentiels** : plan de classement, types de documents et
   de courrier, circuits, règles de conservation — tout est modifiable sans
   développement.
3. **Ouvrir la plateforme** selon vos besoins : lecteur réseau, édition en
   ligne, Google Docs, Nextcloud, API. Voir les `README.md` des modules
   concernés.

Documentation fournie séparément : *Manuel utilisateur AITE ECM & AITE
Courrier* (32 pages), *Tutoriel lecteur réseau et ouverture dans Office*,
*Roadmap produit v4*.

---

## 5. Mise à jour d'une instance existante

```powershell
net stop odoo-server-18.0
REM remplacer les dossiers aite_* par ceux de cette archive
cd "C:\Program Files\Odoo 18.0.<version>\server"
& "..\python\python.exe" odoo-bin -c odoo.conf -d <base> -u aite_ecm --stop-after-init
net start odoo-server-18.0
```

Videz ensuite le cache du navigateur (Ctrl+F5) : les gabarits d'interface font
partie des ressources compilées côté client.

---

*© AITE Consulting — www.aite-consulting.com — info@aite-consulting.com*
