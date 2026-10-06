# Guide d'installation et de mise à jour — suite AITE 2.1.16

> AITE Courrier et AITE ECM pour Odoo 18 Community, signature électronique
> comprise. Ce guide accompagne le paquet `aite-suite-18.0-<commit>.zip` :
> mise à jour d'une instance en service, installation neuve, signature,
> ouverture dans Office et vérifications.

---

## 1. Contenu du paquet

| Dossier | Contenu | Sur Community |
| --- | --- | --- |
| `addons\` | les 26 modules Community, `CHANGELOG.md`, `LISEZMOI_INSTALLATION.md` | **à copier** |
| `oca\sign_oca` | module communautaire OCA (AGPL-3, 18.0.1.4.3) requis par la signature | **à copier** |
| `enterprise\` | `aite_courrier_sign`, `aite_courrier_ged_documents`, `aite_ecm_documents` | **ne pas copier** |
| `docs\pdf\` | les guides et tutoriels en PDF | à lire |
| `LISEZMOI.txt` | le présent guide, en texte brut | — |

Les trois modules Enterprise exigent les apps Sign ou Documents d'Odoo
Enterprise. Copiés sur Community, *Activer* les laisse bloqués « à
installer », ce qui suspend toutes les tâches planifiées de la base.

---

## 2. Dernières nouveautés

**2.1.16** (6 octobre 2026) — la page Paramètres :

| Module | Version | Changement |
| --- | --- | --- |
| `aite_ecm_office` | 18.0.2.0.4 | **correctif** : Paramètres ne s'ouvrait plus (*Octal escape sequences are not allowed in template strings*) ; l'adresse WebDAV et l'URI de redirection Google s'affichent |
| `aite_ecm_document` | 18.0.2.0.2 | l'adresse de scan vers e-mail s'affiche dans Paramètres |
| `aite_ecm` | 18.0.2.0.1 | l'onglet *AITE ECM* des Paramètres retrouve son icône |

**2.1.15** — la signature sur Community :

| Module | Version | Changement |
| --- | --- | --- |
| `aite_courrier_sign_oca` | 18.0.1.0.0 | **nouveau** : signature électronique des courriers sur Community (§5) |
| `aite_courrier_base` | 18.0.1.2.0 | les refus de transition restent tracés au journal d'audit |
| `aite_ecm_webdav` | 18.0.2.5.0 | dossiers créés, renommés, déplacés et supprimés depuis l'Explorateur |

Historique complet : `addons\CHANGELOG.md`.

---

## 3. Mettre à jour une instance en service

> **Déjà en 2.1.15, signature installée ?** Les étapes 3.0 et 3.5 sont
> faites : suivez 3.1 à 3.4, puis 3.6 et 3.7.

### 3.0 Débloquer `aite_courrier_sign`

Si `aite_courrier_sign` est resté bloqué « à installer » (Applications,
filtre retiré, bouton **Annuler l'installation** visible), cliquez
**Annuler l'installation**. Sinon l'installation de la signature Community
(§3.5) est refusée :

```
Les modules "AITE Courrier - Signature électronique (OCA)" et
"AITE Courrier - Signature électronique" sont incompatibles.
```

Cet échec débloque d'ailleurs le module : relancer la commande suffit alors.

### 3.1 Sauvegarder la base

`http://localhost:8069/web/database/manager` › **Backup**, format zip.
Le mot de passe maître est `admin_passwd` dans `odoo.conf`.

### 3.2 Arrêter le service

PowerShell **administrateur** :

```powershell
net stop odoo-server-18.0
```

### 3.3 Remplacer les modules

Dans le dossier des modules (celui qui contient déjà vos `aite_*`) :

1. **supprimer** tous les dossiers `aite_*` ;
2. copier les **26 dossiers** de `addons\` ;
3. copier le dossier **`oca\sign_oca`**.

Un seul exemplaire de chaque module dans tout l'`addons_path` ; ne pas
copier `enterprise\`.

### 3.4 Mettre la suite à jour

Une seule commande ; les modules que vous n'avez pas installés sont ignorés :

```powershell
& "C:\Program Files\Odoo 18\python\python.exe" `
  "C:\Program Files\Odoo 18\server\odoo-bin" `
  -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
  --stop-after-init `
  -u aite_courrier,aite_courrier_base,aite_courrier_capture,aite_courrier_core,aite_courrier_ecm,aite_courrier_ged,aite_courrier_ocr,aite_courrier_portal,aite_courrier_reponse,aite_courrier_validation,aite_courrier_webdav,aite_courrier_workflow,aite_ecm,aite_ecm_api,aite_ecm_demo,aite_ecm_document,aite_ecm_dossier,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_ecm_office,aite_ecm_records,aite_ecm_sae,aite_ecm_share,aite_ecm_webdav,aite_ecm_workflow
```

La commande doit se terminer sans ligne `ERROR`.

### 3.5 Installer la signature Community

```powershell
& "C:\Program Files\Odoo 18\python\python.exe" `
  "C:\Program Files\Odoo 18\server\odoo-bin" `
  -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
  --stop-after-init -i aite_courrier_sign_oca
```

`sign_oca` s'installe avec, ainsi que deux modules standard d'Odoo
(`base_sparse_field`, `web_editor`). Aucune bibliothèque Python à ajouter.

### 3.6 Redémarrer

```powershell
net start odoo-server-18.0
```

Puis **Ctrl+F5** dans le navigateur.

### 3.7 Vérifier

Applications, filtre retiré :

| Module | Version | État |
| --- | --- | --- |
| `aite_courrier_sign_oca` | 18.0.1.0.0 | installé |
| `sign_oca` | 18.0.1.4.3 | installé |
| `aite_courrier_base` | 18.0.1.2.0 | installé |
| `aite_ecm_office` | 18.0.2.0.4 | installé |
| `aite_courrier_sign` | — | **non installé** |

Puis ouvrez **Paramètres** : la page s'affiche, et l'onglet *AITE ECM*
(avec son icône) donne, sous *Office et Google Docs*, l'adresse WebDAV de
l'ECM — `http://localhost:8069/webdav/aite_ecm/` sur une instance locale.

---

## 4. Installation neuve

1. Odoo 18 Community (l'installateur Windows convient) et PostgreSQL.
2. Copier `addons\aite_*` (26 dossiers) et `oca\sign_oca` dans le dossier
   déclaré par `addons_path`. Sur **Enterprise** seulement, copier aussi
   `enterprise\aite_*`, et utiliser `aite_courrier_sign` au lieu de
   `aite_courrier_sign_oca` : les deux s'excluent.
3. Dans `odoo.conf` :

   ```ini
   db_name = <votre_base>      ; indispensable au WebDAV
   proxy_mode = True           ; si Odoo est derrière un reverse proxy
   ```

4. Installer, service arrêté :

   ```powershell
   net stop odoo-server-18.0

   & "C:\Program Files\Odoo 18\python\python.exe" `
     "C:\Program Files\Odoo 18\server\odoo-bin" `
     -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
     --load-language=fr_FR --without-demo=all --stop-after-init `
     -i aite_courrier,aite_courrier_base,aite_courrier_capture,aite_courrier_core,aite_courrier_ecm,aite_courrier_ged,aite_courrier_ocr,aite_courrier_portal,aite_courrier_reponse,aite_courrier_sign_oca,aite_courrier_validation,aite_courrier_webdav,aite_courrier_workflow,aite_ecm,aite_ecm_api,aite_ecm_document,aite_ecm_dossier,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_ecm_office,aite_ecm_records,aite_ecm_sae,aite_ecm_share,aite_ecm_webdav,aite_ecm_workflow

   net start odoo-server-18.0
   ```

   Jeu de données de démonstration : ajouter `aite_ecm_demo`. Sans
   signature : retirer `aite_courrier_sign_oca`.

5. Poursuivre avec `TUTORIEL_WEBDAV_HTTPS.pdf`, §3.

---

## 5. Mettre en service la signature électronique

Guide complet : `TUTORIEL_SIGNATURE_COMMUNITY.pdf`.

### 5.1 Prérequis

| À vérifier | Où |
| --- | --- |
| Le serveur de messagerie sortant fonctionne | Paramètres › Technique › Serveurs de messagerie sortants › *Tester la connexion* |
| `web.base.url` est l'adresse d'Odoo vue par le signataire | Paramètres › Technique › Paramètres système |
| Le responsable du courrier a une adresse e-mail | fiche contact de l'utilisateur |

Le lien de signature est construit sur `web.base.url` et envoyé par e-mail :
sans messagerie, le signataire ne reçoit rien.

### 5.2 Paramétrer le circuit

Courrier › Configuration › **Circuits de traitement** › ouvrir le circuit ›
cocher **Signature requise** sur l'étape voulue.

### 5.3 Le parcours

1. Sur l'étape cochée, le bouton orange **Demander la signature** (visible
   pour qui peut agir sur l'étape) envoie la dernière version PDF du courrier
   à son **responsable** : e-mail *Nouveau document à signer*.
2. Le responsable ouvre le lien — sans compte Odoo —, clique la zone en bas
   à droite de la page 1, **Adopter & Signer**, puis **Valider et envoyer le
   document**.
3. Le PDF signé devient la version suivante de la pièce
   (`<pièce>_signe.pdf`) ; l'original reste consultable.
4. Tant que la signature du passage en cours sur l'étape manque, *Traiter*
   est refusé et le refus est tracé au journal d'audit ; retourner et
   rejeter restent possibles. Un courrier revenu sur l'étape doit être signé
   de nouveau.

### 5.4 Ce qu'il faut savoir

- **Signature électronique simple** : image de la signature dans le PDF,
  journal horodaté (adresse IP, empreintes chaînées), sans certificat
  qualifié. Elle convient aux visas et validations internes.
- Un seul signataire (le responsable), PDF uniquement, zone de signature
  fixe.
- Les droits **Signature** de `sign_oca` permettent de signer à la place
  d'autrui : les réserver aux administrateurs de la signature. Les agents du
  courrier n'en ont pas besoin.
- `sign_oca` est au statut Beta à l'OCA, sous licence AGPL-3
  (`oca\LICENSE`).

---

## 6. Word, Excel et PowerPoint : une autorisation par poste

Depuis la version 2311, Microsoft 365 bloque par défaut l'authentification
du lecteur réseau (Basic), en http comme en https, y compris pour un fichier
ouvert depuis un lecteur `X:`.

Une fois par poste, Word, Excel, PowerPoint et Outlook **fermés**, dans un
PowerShell administrateur ouvert avec le compte Windows qui utilise Word :

```powershell
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

Remplacer `localhost` par le nom du serveur chez un client, ou déployer la
stratégie de groupe *Allow specified hosts to show Basic Authentication
prompts to Office apps*. Détail : `DEPLOIEMENT_WEBDAV_WINDOWS.pdf`, §3.

---

## 7. En cas de problème

| Symptôme | Remède |
| --- | --- |
| Paramètres : *UncaughtPromiseError > OwlError … Octal escape sequences are not allowed in template strings* | `aite_ecm_office` antérieur à 18.0.2.0.4 : §3.3, §3.4, puis redémarrer et **Ctrl+F5** (§3.6) |
| *Les modules … sont incompatibles* | §3.0, puis relancer §3.5 |
| `sign_oca` introuvable à l'installation | `oca\sign_oca` non copié, ou hors de l'`addons_path` (§3.3) |
| Journal : *Some modules have inconsistent states … ['aite_courrier_sign']* | §3.0 |
| Le bouton *Demander la signature* n'apparaît pas | étape non cochée (§5.2), ou vous n'êtes pas habilité à agir sur l'étape |
| Le signataire ne reçoit rien | messagerie sortante, `web.base.url` (§5.1) |
| Word : *Microsoft Office a bloqué l'accès…* | §6 |

---

## 8. Documents fournis

| Fichier (`docs\pdf\`) | Sujet |
| --- | --- |
| `GUIDE_INSTALLATION_MISE_A_JOUR.pdf` | ce guide |
| `TUTORIEL_SIGNATURE_COMMUNITY.pdf` | signature sur Community |
| `TUTORIEL_SIGNATURE.pdf` | signature sur Enterprise (Odoo Sign) |
| `TUTORIEL_WEBDAV_HTTPS.pdf` | parcours complet d'une instance neuve, HTTPS |
| `DEPLOIEMENT_WEBDAV_WINDOWS.pdf` | lecteur réseau et Office, cas http |
| `WEBDAV_HTTPS_WINDOWS.pdf` | reverse proxy (Caddy, nginx) |
| `SCENARIO_WEBDAV.pdf`, `GUIDE_TEST_WEBDAV.pdf` | recette du WebDAV |
| `TUTORIEL_CAPTURE_OCR.pdf` | capture e-mail et recherche plein texte |
| `DEPLOIEMENT.pdf` | déploiement Linux |
| `AITE_Courrier_fiche_commerciale.pdf`, `AITE_Courrier_fiche_avant_vente_technique.pdf` | offres |
| `AITE_Courrier_cachet_de_traitement.pdf` | le cachet de traitement |
| `ANALYSE_FLUX_WEBDAV_RESTANTS.pdf` | ce qui reste à développer |

---

## 9. Qualité de la version

Vérifié sur Odoo 18.0 Community et PostgreSQL 16, avec le code de ce paquet :

- campagne complète (`docs\recette\run_tests.sh`, avec la signature) sous
  Python 3.12 et reportlab 4.1.0, les versions de l'installateur Windows
  d'Odoo 18 : base neuve, 26 modules, 348 tests, 0 échec ;
- la page Paramètres dans un navigateur (Chromium), sur la copie d'une base
  touchée par le plantage, après la mise à jour du §3.4 : aucune erreur,
  les 4 applications de réglages s'affichent, avec l'adresse WebDAV, l'URI
  Google, l'adresse de scan et l'icône *AITE ECM* ;
- les 4 tests ajoutés (`test_web_client_views`) échouent sur la 2.1.15 et
  passent sur cette version ;
- installation depuis le paquet sur une base neuve, sans erreur.

Repris de la 2.1.15, dont le code de la signature n'a pas changé : tests de
`sign_oca` sous Python 3.12 ; parcours réel de signature dans Chromium ;
installation sur la copie d'une base où `aite_courrier_sign` était bloqué
« à installer » (refus attendu, puis installation sans erreur une fois le
blocage levé).

Non vérifié dans cet environnement : l'envoi réel des e-mails (pas de
serveur SMTP) et l'autorisation Office d'un poste Windows (§6).

---

*AITE Consulting — www.aite-consulting.com*
