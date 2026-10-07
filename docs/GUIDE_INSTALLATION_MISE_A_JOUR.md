# Guide d'installation et de mise à jour — suite AITE 2.1.17

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

**2.1.17** (7 octobre 2026) — une mise à jour qui aboutit :

| Module | Version | Changement |
| --- | --- | --- |
| `aite_courrier_base` | 18.0.1.2.1 | **correctif** : Paramètres s'ouvre même si la base n'a pas encore été mise à niveau, et le journal d'Odoo nomme la vue en retard |

La procédure du §3 est corrigée. Le guide précédent indiquait le
dossier `C:\Program Files\Odoo 18`, alors que l'installateur Windows
installe dans `Odoo 18.0.<date>`. Sa commande de mise à jour échouait donc,
souvent sans message visible. Désormais :

- le dossier d'Odoo est trouvé automatiquement ;
- la base se met à niveau en un clic depuis Odoo ;
- les dossiers à remplacer sont nommés un par un. Vos autres modules
  `aite_*`, comme ceux de Core Banking, ne sont plus concernés.

Les tutoriels de signature, de capture et de WebDAV sont corrigés de la
même façon. Leurs commandes tiennent maintenant sur une ligne de PDF :
copiées depuis le PDF, elles ne se coupent plus en deux.

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

Trois temps, tous indispensables :

1. remplacer les dossiers des modules ;
2. redémarrer Odoo ;
3. **mettre la base à niveau**.

Copier les dossiers ne suffit pas : tant que l'étape 3.5 n'est pas faite,
la base garde les écrans de l'ancienne version.

> **Signature déjà installée (2.1.15 ou 2.1.16) ?** Les étapes 3.0 et 3.6
> sont faites : suivez 3.1 à 3.5, puis 3.7.

### 3.0 Débloquer `aite_courrier_sign`

Si `aite_courrier_sign` est resté bloqué « à installer » (Applications,
filtre retiré, bouton **Annuler l'installation** visible), cliquez
**Annuler l'installation**. Sinon l'installation de la signature Community
(§3.6) est refusée :

```
Les modules "AITE Courrier - Signature électronique (OCA)" et
"AITE Courrier - Signature électronique" sont incompatibles.
```

Ce refus débloque d'ailleurs le module : il suffit alors de relancer la
commande.

### 3.1 Sauvegarder la base

`http://localhost:8069/web/database/manager` › **Backup**, format zip.
Le mot de passe maître est `admin_passwd` dans `odoo.conf`.

### 3.2 Repérer le dossier d'Odoo et celui des modules

L'installateur Windows place Odoo dans `C:\Program Files\Odoo 18.0.<date>`,
par exemple `Odoo 18.0.20251006`. Ouvrez un PowerShell **administrateur**
et gardez-le ouvert jusqu'à la fin de la mise à jour :

```powershell
$odoo = (Get-ItemProperty "HKLM:\SOFTWARE\Odoo 18.0").Install_dir
$py = "$odoo\python\python.exe"
$bin = "$odoo\server\odoo-bin"
$cfg = "$odoo\server\odoo.conf"
$odoo
$conf = Get-Content $cfg
$conf -match "^\s*(addons_path|db_name)\s*="
```

Ces commandes affichent le dossier d'Odoo, les dossiers de modules
(`addons_path`) et la base (`db_name`). Les variables `$py`, `$bin` et
`$cfg` servent aux commandes suivantes. Pour lister les modules de la suite
qu'Odoo voit, avec leur version :

```powershell
$ligne = ($conf -match "^\s*addons_path\s*=")[0]
$dossiers = (($ligne -replace "^[^=]*=", "") -split ",").Trim()
Get-ChildItem $dossiers -Directory -ErrorAction SilentlyContinue |
  Where-Object Name -Match "^(aite_courrier|aite_ecm|sign_oca$)" |
  Sort-Object Name |
  ForEach-Object {
    $f = "$($_.FullName)\__manifest__.py"
    $v = Select-String -Path $f -Pattern "version.\s*:\s*.\d+\.\d+"
    "{0,-12} {1}" -f ($v[0].Line -replace "[^\d.]", ""), $_.FullName
  }
```

Chaque module doit apparaître **une seule fois**. Le dossier qui les
contient est celui de l'étape 3.3 ; avec l'installateur, c'est souvent
`…\server\odoo\addons`. La liste ne montre que la suite Courrier et ECM.
Vos autres modules `aite_*`, par exemple `aite_core_banking`, n'y figurent
pas et ne doivent pas être touchés.

### 3.3 Arrêter le service et remplacer les modules

```powershell
net stop odoo-server-18.0
```

Puis, dans l'Explorateur, dans le dossier repéré au §3.2 :

1. supprimez les dossiers dont le nom commence par `aite_courrier` ou
   `aite_ecm`, ainsi que `sign_oca`, **et eux seuls** ;
2. ouvrez le dossier `addons\` du paquet, sélectionnez les **26 dossiers**
   qu'il contient (pas le dossier `addons` lui-même) et collez-les ;
3. collez de même le dossier `oca\sign_oca`.

Ne copiez ni `enterprise\`, ni le dossier du paquet tel quel
(`aite-suite-18.0-…`). Odoo ne lit que les dossiers de modules posés
directement dans un dossier de l'`addons_path`.

### 3.4 Redémarrer et contrôler

```powershell
net start odoo-server-18.0
```

Dans Odoo, ouvrez **Applications**. Retirez le filtre *Apps* de la barre de
recherche, cherchez `AITE` et passez en **vue liste**. La colonne
*Dernière version* donne la version des fichiers qu'Odoo a lus :

| Nom de module | Dernière version |
| --- | --- |
| AITE Courrier - Socle | 18.0.1.2.1 |
| AITE ECM - Édition Office et Google Docs | 18.0.2.0.4 |

Une version plus ancienne signifie que les nouveaux dossiers ne sont pas au
bon endroit, ou qu'un ancien exemplaire est resté. Relancez le contrôle du
§3.2.

### 3.5 Mettre la base à niveau

**Depuis Odoo**, sans ligne de commande :

1. dans **Applications**, filtre *Apps* retiré, cherchez
   `aite_courrier_base` ;
2. sur la carte *AITE Courrier - Socle*, cliquez **⋮ › Mettre à niveau**.

Tous les modules AITE Courrier et AITE ECM installés suivent, car ils
dépendent tous de ce module. Comptez une quinzaine de secondes sur une base
de test, puis la page se recharge. En cas d'échec, Odoo affiche l'erreur :
envoyez-la nous.

Sur un serveur Linux configuré avec des workers, préférez la ligne de
commande pour une grosse base. Une requête du navigateur y est interrompue
au-delà de `limit_time_real`, 120 secondes par défaut.

**Ou en ligne de commande**, dans le PowerShell du §3.2. Remplacez
`ma_base` par le nom de votre base : la valeur `db_name` affichée au §3.2,
ou le nom visible sur `/web/database/manager`.

```powershell
$base = "ma_base"
net stop odoo-server-18.0
& $py $bin -c $cfg -d $base --stop-after-init --logfile= -u aite_courrier_base
net start odoo-server-18.0
```

`--logfile=` affiche le journal dans la fenêtre, au lieu de l'écrire dans
`odoo.log`. Il ne doit contenir aucune ligne `ERROR`. Comme le bouton,
`-u aite_courrier_base` met à niveau toute la suite.

### 3.6 Installer la signature Community

À faire une seule fois, dans le PowerShell du §3.2, avec le nom de votre
base comme au §3.5 :

```powershell
$base = "ma_base"
net stop odoo-server-18.0
& $py $bin -c $cfg -d $base --stop-after-init --logfile= -i aite_courrier_sign_oca
net start odoo-server-18.0
```

`sign_oca` s'installe avec, ainsi que deux modules standard d'Odoo
(`base_sparse_field`, `web_editor`). Aucune bibliothèque Python à ajouter.

### 3.7 Vérifier

Appuyez sur **Ctrl+F5**, puis ouvrez **Paramètres**. La page doit
s'afficher. Dans l'onglet *AITE ECM*, avec son icône, le bloc
*Office et Google Docs* présente deux points à contrôler :

- l'adresse WebDAV de l'ECM s'affiche, par exemple
  `http://localhost:8069/webdav/aite_ecm/` sur une instance locale ;
- l'aide du réglage *Word, Excel, PowerPoint, LibreOffice* se termine par
  « HKCU › Software › Policies › … ».

Si elle montre encore « HKCU⧵Software⧵… », la page tient grâce à la
protection de la 2.1.17, mais la base n'est pas à niveau : reprenez le
§3.5.

Signature, dans **Applications** en vue liste :

| Nom de module | Dernière version | Statut |
| --- | --- | --- |
| AITE Courrier - Signature électronique (OCA) | 18.0.1.0.0 | Installé |
| Sign Oca | 18.0.1.4.3 | Installé |
| AITE Courrier - Signature électronique | — | **non installé** |


---

## 4. Installation neuve

**Prérequis** : Odoo 18 Community (l'installateur Windows convient) et
PostgreSQL. Aucune bibliothèque Python à ajouter.

**Copier les modules** : les 26 dossiers de `addons\` et `oca\sign_oca`,
dans un dossier déclaré par `addons_path` (§3.2 pour le trouver). Sur
**Enterprise** seulement, copiez aussi `enterprise\aite_*`, et utilisez
`aite_courrier_sign` au lieu de `aite_courrier_sign_oca` : les deux
s'excluent.

**Compléter `odoo.conf`** :

```ini
db_name = ma_base           ; indispensable au WebDAV
proxy_mode = True           ; si Odoo est derrière un reverse proxy
```

**Installer**, dans un PowerShell administrateur, en remplaçant `ma_base`
par le nom choisi dans `odoo.conf` :

```powershell
$odoo = (Get-ItemProperty "HKLM:\SOFTWARE\Odoo 18.0").Install_dir
$py = "$odoo\python\python.exe"
$bin = "$odoo\server\odoo-bin"
$cfg = "$odoo\server\odoo.conf"
$base = "ma_base"
$modules = "aite_courrier,aite_courrier_base,aite_courrier_capture," +
  "aite_courrier_core,aite_courrier_ecm,aite_courrier_ged,aite_courrier_ocr," +
  "aite_courrier_portal,aite_courrier_reponse,aite_courrier_sign_oca," +
  "aite_courrier_validation,aite_courrier_webdav,aite_courrier_workflow," +
  "aite_ecm,aite_ecm_api,aite_ecm_document,aite_ecm_dossier," +
  "aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_ecm_office," +
  "aite_ecm_records,aite_ecm_sae,aite_ecm_share,aite_ecm_webdav," +
  "aite_ecm_workflow"
$options = "--load-language=fr_FR", "--without-demo=all", "--stop-after-init"
net stop odoo-server-18.0
& $py $bin -c $cfg -d $base --logfile= $options -i $modules
net start odoo-server-18.0
```

Jeu de données de démonstration : ajoutez `aite_ecm_demo` à `$modules`.
Sans signature : retirez-en `aite_courrier_sign_oca`.

**Poursuivre** avec `TUTORIEL_WEBDAV_HTTPS.pdf`, §3.

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
$cle = "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity"
reg add $cle /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

Remplacer `localhost` par le nom du serveur chez un client, ou déployer la
stratégie de groupe *Allow specified hosts to show Basic Authentication
prompts to Office apps*. Détail : `DEPLOIEMENT_WEBDAV_WINDOWS.pdf`, §3.

---

## 7. En cas de problème

| Symptôme | Remède |
| --- | --- |
| Paramètres : *UncaughtPromiseError > OwlError … Octal escape sequences are not allowed in template strings* | Odoo lit encore les anciens fichiers. Contrôlez la colonne *Dernière version* (§3.4), puis faites le §3.5 et **Ctrl+F5**. Avec la 2.1.17 en place, la page s'ouvre dès le redémarrage |
| *Dernière version* inchangée après la copie | Cause possible : dossiers collés hors de l'`addons_path`, ou dossier parent collé (`…\addons\addons\…`, `…\aite-suite-18.0-…\…`) ; contrôle du §3.2 |
| *Dernière version* inchangée, contrôle du §3.2 correct | Cause possible : ancien exemplaire resté ailleurs, ou service non redémarré ; contrôle du §3.2, puis §3.4 |
| Paramètres s'ouvre, mais l'aide affiche « HKCU⧵Software⧵… » | base non mise à niveau : §3.5 |
| `odoo.log` : *Page Paramètres : antislash remplacé à l'affichage (…)* | même cause : §3.5 ; le message nomme la vue en retard |
| PowerShell : *Le terme « C:\Program Files\Odoo 18\… » n'est pas reconnu* | chemin des guides antérieurs à la 2.1.17 : le dossier est `Odoo 18.0.<date>`, utilisez `$odoo` (§3.2) |
| PowerShell : *L'opérateur « < » est réservé à un usage futur* | `<votre_base>` des guides antérieurs laissé tel quel : `$base = "ma_base"` (§3.5) |
| *Les modules … sont incompatibles* | §3.0, puis relancer §3.6 |
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

Vérifié sur Odoo 18.0 Community et PostgreSQL 16, avec le code de ce
paquet, sous Python 3.12 et reportlab 4.1.0, les versions de l'installateur
Windows d'Odoo 18 :

- **campagne complète, signature comprise** : 26 modules, 349 tests,
  0 échec.
- **base antérieure à la 2.1.16**, en français, avec l'aide fautive, sur
  une copie :
  - avec les nouveaux fichiers et un simple redémarrage, Paramètres s'ouvre
    dans Chromium sans erreur, et `odoo.log` nomme la vue en retard ;
  - le bouton **Mettre à niveau** de *AITE Courrier - Socle* (§3.5),
    actionné dans le navigateur, met les 26 modules à la version du disque
    en 13 secondes ;
  - Paramètres affiche ensuite la nouvelle aide, sans message au journal.
- **ligne de commande du §3.5**, sur une autre copie et avec un `odoo.conf`
  qui désigne un fichier journal comme celui de l'installateur : le journal
  s'affiche à l'écran, aucune erreur, la suite entière est à niveau.
- **blocs PowerShell du guide**, exécutés sous PowerShell 7 sur une
  installation simulée :
  - le contrôle du §3.2 signale un doublon et un ancien exemplaire ;
  - il ignore un module Core Banking et un dossier de paquet collé tel
    quel ;
  - les commandes transmettent leurs arguments intacts, chemins avec
    espaces compris ;
  - non vérifié sur un poste Windows, ni sous Windows PowerShell 5.1.
- **test ajouté** (`test_settings_page_survives_stale_view`) : il échoue
  sans la protection et passe avec elle.

Repris de la 2.1.15, dont le code de la signature n'a pas changé : tests de
`sign_oca` sous Python 3.12 ; parcours réel de signature dans Chromium ;
installation sur la copie d'une base où `aite_courrier_sign` était bloqué
« à installer » (refus attendu, puis installation sans erreur une fois le
blocage levé).

Non vérifié dans cet environnement : l'envoi réel des e-mails (pas de
serveur SMTP) et l'autorisation Office d'un poste Windows (§6).

---

*AITE Consulting — www.aite-consulting.com*
