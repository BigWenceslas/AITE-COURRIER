# AITE Courrier — Scénarios de test (base vierge)

> Document de recette fonctionnelle. À dérouler sur une **base de données vierge**.
> Objectif : valider le cycle de vie d'un courrier, la GED versionnée et son
> intégration à la **GED native Odoo (Documents)**.

---

## 0. Préparation de la base vierge

### 0.1 Architecture locale (rappel)

| Élément | Chemin / valeur |
|---|---|
| OS d'exécution | **WSL (Ubuntu)** |
| Odoo 18 Enterprise (binaire) | `/opt/odoo18e/extracted/usr/bin/odoo` |
| Environnement Python | `/opt/odoo18e/venv` |
| Bibliothèques Odoo (PYTHONPATH) | `/opt/odoo18e/extracted/usr/lib/python3/dist-packages` |
| Fichier de configuration | `/opt/odoo18e/conf/odoo18e.conf` |
| Dossier d'addons custom (dans `addons_path`) | `/opt/odoo18e/custom_addons` |
| Script de démarrage | `/opt/odoo18e/start.sh` |
| Port HTTP | **8169** |
| Dépôt Git (géré côté **Windows**) | `D:\Dev\Projects\Aite-Product-Courrier\aite-courrier` — vu depuis WSL : `/mnt/d/Dev/Projects/Aite-Product-Courrier/aite-courrier` |

> **Workflow** : le dépôt Git est cloné et mis à jour **sous Windows**. Pour
> tester, on **copie** les addons dans `custom_addons` (côté WSL), puis on lance
> Odoo. Toutes les commandes serveur (copie, install, démarrage) sont à exécuter
> **dans WSL**, instance 8169 **arrêtée** (Ctrl+C dans le terminal de `start.sh`).

### 0.2 Récupérer la dernière version du code (côté Windows)

Depuis **Git Bash sous Windows**, dans le dossier du dépôt
`D:\Dev\Projects\Aite-Product-Courrier\aite-courrier` :

```bash
git fetch origin claude/awesome-volta-7m8bo3
git checkout claude/awesome-volta-7m8bo3
git pull origin claude/awesome-volta-7m8bo3
```

> **Échec de `git clone` ?** (`fetch-pack: unexpected disconnect…`) → clone
> superficiel d'abord, puis la branche de travail (léger = fiable) :
> ```bash
> git clone --depth 1 git@github.com:BigWenceslas/aite-courrier.git
> cd aite-courrier
> git fetch --depth 1 origin claude/awesome-volta-7m8bo3
> git checkout -b claude/awesome-volta-7m8bo3 FETCH_HEAD
> ```
> Rappel : seul `git clone` crée un dossier ; `git fetch`/`pull` travaillent
> dans le dossier courant.

### 0.3 Copier les modules dans l'instance (côté WSL)

L'instance lit les modules depuis `custom_addons` (déjà dans l'`addons_path`). On
**copie** les addons du dépôt Windows vers WSL :

```bash
cp -r /mnt/d/Dev/Projects/Aite-Product-Courrier/aite-courrier/addons/* \
      /opt/odoo18e/custom_addons/

ls /opt/odoo18e/custom_addons | grep aite_courrier   # doit lister les 7 modules
```

> ⚠️ **À refaire après chaque modification du code** : la copie n'est pas un lien.
> Si tu as changé le code (ou fait un `git pull`), **re-copie** avant de
> réinstaller/mettre à niveau, sinon l'instance tourne sur l'ancienne version.

### 0.4 Créer la base vierge et installer la suite

```bash
DB=odoo18e_recette        # une seule base, qu'on garde pour toute la recette

source /opt/odoo18e/venv/bin/activate
export PYTHONPATH=/opt/odoo18e/extracted/usr/lib/python3/dist-packages:$PYTHONPATH

# Odoo crée la base si elle n'existe pas ; -i aite_courrier tire toute la suite
# (base, workflow, core, GED, validation, webdav) ET la GED native « documents ».
python3 /opt/odoo18e/extracted/usr/bin/odoo \
  -c /opt/odoo18e/conf/odoo18e.conf -d "$DB" \
  -i aite_courrier --without-demo=all --stop-after-init
deactivate
```

> Pour des **données d'exemple**, retirer `--without-demo=all`.

### 0.5 Démarrer l'instance et se connecter

```bash
/opt/odoo18e/start.sh
```

Ouvre **http://localhost:8169**, puis sélectionne/connecte-toi à la base **`odoo18e_recette`**.

### 0.6 Vérifications d'installation

- [ ] La sortie de l'étape 0.4 montre `Loading module documents (...)` **et** `Loading module aite_courrier_ged (...)`.
- [ ] L'app **Documents** est visible dans le menu principal.
- [ ] Un espace **« Courrier »** existe dans le panneau gauche de Documents.
- [ ] L'app **Courrier** est visible avec son tableau de bord.

> Contrôle rapide en ligne de commande (facultatif) :
> ```bash
> source /opt/odoo18e/venv/bin/activate
> export PYTHONPATH=/opt/odoo18e/extracted/usr/lib/python3/dist-packages:$PYTHONPATH
> python3 /opt/odoo18e/extracted/usr/bin/odoo shell \
>   -c /opt/odoo18e/conf/odoo18e.conf -d odoo18e_recette --no-http <<'PY'
> M = env['ir.module.module']
> for n in ('documents', 'aite_courrier', 'aite_courrier_ged', 'aite_courrier_webdav'):
>     print(n, ':', M.search([('name','=',n)]).state)
> PY
> deactivate
> ```
> Les quatre doivent être à l'état `installed`.

---

## Scénario 1 — Courrier avec 3 documents, du début à l'archivage

**But :** dérouler un courrier entrant complet, y attacher 3 documents, et le
mener jusqu'à l'archivage en vérifiant verrouillage et présence dans la GED native.

### 1.1 Création du courrier
1. **Courrier → Nouveau**.
2. Renseigner : **Objet** = « Demande de subvention 2026 », **Type** = *Courrier entrant*,
   **Priorité** = *Haute*, **Confidentialité** = *Interne*, **Service destinataire** au choix.
3. Enregistrer.

✅ **Attendu :** statut = **Brouillon**, pas encore de référence.

### 1.2 Lancement du circuit
4. Cliquer **Lancer le circuit** (circuit *Courrier entrant standard*).

✅ **Attendu :**
- Référence attribuée au format **`COUR-2026-NNNN`**.
- Statut passe à **Nouveau**, étape courante = **Réception**.
- Dans **Documents**, un **dossier portant la référence** apparaît sous l'espace « Courrier ».

### 1.3 Ajout des 3 documents
Pour chaque document, onglet **Documents** du courrier → **Ajouter une ligne** :

| # | Nom | Fichier | Dossier attendu |
|---|---|---|---|
| 1 | Lettre de demande | un **PDF** | auto-classé (dossier par défaut du type) |
| 2 | Budget prévisionnel | un **XLSX** | idem |
| 3 | Statuts association | un **DOCX** | idem |

Pour chacun : choisir le fichier dans **« Fichier à téléverser »** puis **cliquer « Téléverser »**.

✅ **Attendu par document :**
- Une version **v1** créée, horodatée, avec auteur.
- Le **même fichier apparaît dans Documents** → espace « Courrier » → dossier `COUR-2026-NNNN`.
- Un **auto-classement** dans le dossier par défaut du type de courrier.

### 1.4 Progression dans le circuit
5. Faire avancer le courrier étape par étape : **Réception → Qualification →
   Affectation → Traitement**. À chaque transition, **saisir un commentaire**
   distinct dans l'assistant (ex. « reçu le 21/06 », « pièces complètes », …).

✅ **Attendu :** statut **En traitement**, étape courante mise à jour à chaque transition.
- Onglet **Historique** : chaque commentaire apparaît **une seule fois, sur la
  ligne de l'étape où l'action a été faite** (plus de commentaire décalé/manquant).
- Le **fil de discussion** (chatter) liste également chaque action signée et horodatée.

### 1.5 Validation puis archivage
6. **Valider** le courrier → statut **Validé**.
7. **Archiver** le courrier (étape *Archivage*) → statut **Archivé**.

✅ **Attendu après archivage :**
- Les **champs métier** du courrier deviennent **non modifiables**.
- Les 3 documents passent **verrouillés** (`is_locked`) : plus d'ajout de version possible.
- Les 3 fichiers restent **consultables dans Documents**.

### Résultat attendu du scénario 1
- [ ] Référence `COUR-2026-NNNN` générée.
- [ ] Cycle complet Brouillon → … → Archivé.
- [ ] 3 documents (PDF/XLSX/DOCX) visibles dans la GED **et** dans Documents.
- [ ] Verrouillage effectif après archivage.

---

## Scénario 2 — Gestion documentaire à deux utilisateurs

**But :** démontrer les fonctionnalités utiles de la GED dans le module Courrier
à travers une **collaboration entre deux profils** : dépôt, **aperçu intégré**,
téléchargement, versionnage collaboratif, classement, confidentialité, finalisation,
et restitution dans la GED native (Documents).

### 2.0 Préparation des deux utilisateurs

Créer deux utilisateurs (**Paramètres → Utilisateurs**) et leur attribuer les
droits AITE Courrier (onglet *Autorisations*, section AITE Courrier) :

| Utilisateur | Rôle métier | Groupe AITE Courrier |
|---|---|---|
| **Alice** (agent) | Dépose et prépare les pièces | **Agent courrier** |
| **Bob** (manager) | Relit, corrige, finalise | **Manager** (+ Agent courrier) |

> Conseil : ouvre **deux navigateurs** (ou une fenêtre privée) pour être connecté
> simultanément en **Alice** et en **Bob**.

### 2.1 Alice — création du courrier et dépôt de 5 documents

*(connecté en **Alice**)*
1. **Courrier → Nouveau** : « Dossier marché public » (*Type* = Courrier entrant),
   **lancer le circuit** → référence `COUR-…` + dossier créé dans Documents.
2. Onglet **Documents** → créer **5 documents** et téléverser une pièce pour chacun
   (bouton **Ajouter la version**) :

| # | Nom | Fichier |
|---|---|---|
| 1 | CCTP | PDF |
| 2 | Bordereau prix | XLSX |
| 3 | Mémoire technique | DOCX |
| 4 | Acte engagement | PDF |
| 5 | Annexe financière | XLSX |

✅ **Attendu :** 5 documents en **v1**, tous présents dans le dossier `COUR-…` de Documents.

### 2.2 Bob — aperçu et téléchargement

*(connecté en **Bob**)*
3. Ouvrir le courrier d'Alice → onglet **Documents** → ouvrir le document **CCTP**.
4. Bloc **« Aperçu de la dernière version »** → le **PDF s'affiche dans la visionneuse intégrée**.
5. Onglet **Versions** → cliquer l'icône de **téléchargement** de la v1.

✅ **Attendu :**
- PDF **prévisualisé sans quitter le courrier** (visionneuse intégrée).
- Pour le DOCX/XLSX : pas d'aperçu PDF mais **lien de téléchargement** disponible.
- Le fichier se télécharge correctement.

### 2.3 Versionnage collaboratif

*(connecté en **Bob**)*
6. Sur **CCTP**, téléverser un PDF corrigé (**Ajouter la version**).

✅ **Attendu :** **v2** créée (auteur = **Bob**), **v1 conservée** ; l'aperçu montre la v2 ;
Documents reflète la dernière version. La colonne *Téléversé par* distingue Alice (v1) / Bob (v2).

### 2.4 Classement : dossiers et étiquettes

*(connecté en **Alice** ou **Bob**)*
7. Créer un dossier « Pièces administratives » et y **déplacer** 2 documents.
8. Poser des **étiquettes** (ex. « Urgent », « À viser ») sur 3 documents.

✅ **Attendu :** compteur du dossier mis à jour ; **filtrage** par dossier et par étiquette opérationnel.

### 2.5 Contrôles de format et de taille (cas d'erreur)

9. Téléverser un fichier **`.txt`** (ou `.png`). ✅ **Refus** — formats PDF/DOCX/XLSX uniquement.
10. Téléverser un fichier **> 50 Mo**. ✅ **Refus** — taille maximale 50 Mo.

### 2.6 Finalisation et verrouillage

*(connecté en **Bob**)*
11. Sur 2 documents, bouton **Finaliser**.

✅ **Attendu :** documents **verrouillés** (ruban « Verrouillé ») → re-téléversement
impossible ; seul un **Administrateur** peut **repasser en brouillon**.

### 2.7 Confidentialité entre deux utilisateurs

12. Créer un 3ᵉ utilisateur **Carole** *sans* droits AITE Courrier (ou agent d'un
    autre périmètre). Passer le courrier en **Confidentialité = Confidentiel**.

✅ **Attendu :** **Carole ne voit ni le courrier ni ses pièces** (ni dans la GED,
ni dans l'espace Documents) ; Alice et Bob continuent d'y accéder. La
confidentialité est **héritée** par les documents.

### 2.8 Restitution dans la GED native (Documents)

13. En **Alice** puis en **Bob** : **Documents → espace « Courrier » → dossier `COUR-…`**.

✅ **Attendu :** les 5 documents (CCTP en **v2**) y sont **visibles et gérables**
(aperçu natif, téléchargement, recherche), **sans duplication du binaire**.

### 2.9 Accès WebDAV (optionnel)

14. Depuis WSL ou Windows :
```bash
LOGIN='alice'; PASS='mot_de_passe_alice'; REF='COUR-2026-NNNN'
curl -s -i -X OPTIONS http://localhost:8169/webdav/aite_courrier
curl -s -u "$LOGIN:$PASS" -X PROPFIND -H "Depth: 1" http://localhost:8169/webdav/aite_courrier/$REF/
```
✅ **Attendu :** `DAV: 1` ; le PROPFIND du courrier liste ses documents. Avec les
identifiants de **Carole**, le courrier confidentiel **n'apparaît pas** (mêmes droits qu'en UI).

### Résultat attendu du scénario 2
- [ ] Dépôt par Alice, relecture/correction par Bob (collaboration 2 users).
- [ ] **Aperçu PDF intégré** au courrier + téléchargement des versions.
- [ ] Versionnage v1 (Alice) / v2 (Bob) avec historique et auteurs distincts.
- [ ] Classement par dossiers et étiquettes.
- [ ] Refus des formats non autorisés et des fichiers > 50 Mo.
- [ ] Verrouillage des documents finalisés.
- [ ] Confidentialité héritée : un tiers non habilité ne voit rien.
- [ ] Restitution dans Documents (sans duplication) + WebDAV cohérent avec les droits.

---

## Matrice de synthèse

| Fonction testée | Scénario | Statut |
|---|---|---|
| Cycle de vie courrier complet | S1 | ☐ |
| Commentaires d'étape visibles dans l'Historique | S1 | ☐ |
| Référence `COUR-AAAA-NNNN` | S1 | ☐ |
| Auto-classement documentaire | S1/S2 | ☐ |
| Collaboration à deux utilisateurs | S2 | ☐ |
| Aperçu PDF intégré + téléchargement | S2 | ☐ |
| Intégration GED native (Documents) | S1/S2 | ☐ |
| Versionnage v1/v2 (auteurs distincts) | S2 | ☐ |
| Contrôles format/taille | S2 | ☐ |
| Dossiers + étiquettes | S2 | ☐ |
| Confidentialité héritée (tiers non habilité) | S2 | ☐ |
| Verrouillage (finalisé/archivé) | S1/S2 | ☐ |
| Accès WebDAV | S2 | ☐ |

---

*AITE Consulting — recette fonctionnelle AITE Courrier.*
