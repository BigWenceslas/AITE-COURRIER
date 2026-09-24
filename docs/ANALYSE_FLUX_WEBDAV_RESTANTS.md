# WebDAV — analyse des flux restant à développer

> État réel des deux serveurs WebDAV de la suite, ce que l'usage visé — Explorateur Windows et Word sur un poste Community — exige encore, et le backlog priorisé qui en découle. Analyse statique du code (branche `claude/amazing-brown-9qymkv`, commit `82f4400`), chaque constat renvoie à la ligne qui le fonde.

---

## 0. En deux mots

- **Ce qui marche** : deux serveurs WebDAV (`/webdav/aite_courrier`, `/webdav/aite_ecm`) servent lecture, dépôt, versionnage, renommage et listage sous les droits de l'utilisateur. Le `207` obtenu avec `curl` sur l'instance Windows le confirme : route, base, identifiants, droits — tout répond.
- **Ce qui manque pour l'usage visé** : quatre flux bloquent encore l'aller-retour « ouvrir dans Word, enregistrer, fermer » et le montage par des comptes réels — l'enregistrement Office par fichier temporaire, les verrous réels côté courrier, l'authentification par clé d'API (donc les comptes à double authentification), et l'assainissement des noms de fichiers côté courrier. S'y ajoute, côté poste et hors code, l'autorisation de l'hôte dans Office (`basichostallowlist`) : sans elle, Word refuse d'ouvrir, en HTTPS comme en HTTP (F14).
- **Une dette structurelle** : les deux contrôleurs sont des copies l'un de l'autre. Chaque correctif est à faire deux fois — le journal des anomalies en porte déjà la trace (A-10 : les dates HTTP corrigées côté courrier, puis à nouveau côté ECM).
- **Backlog** : 14 chantiers. Les 4 bloquants (P0) représentent 6 à 8 jours ; le socle commun (P1, 2 jours) doit passer **avant** pour que chaque correctif n'atterrisse qu'une fois.

---

## 1. Ce qui existe

| Capacité | `aite_courrier_webdav` | `aite_ecm_webdav` |
| --- | --- | --- |
| Arborescence | un dossier par courrier enregistré | plan de classement hiérarchique + « Sans classement » |
| Nom de fichier | `<nom>.<ext>` brut | `RÉFÉRENCE - Titre.ext`, caractères interdits remplacés |
| `OPTIONS`, `PROPFIND`, `GET`, `HEAD` | ✓ | ✓ avec `ETag` SHA-256 |
| `PUT` → nouvelle version / nouveau document | ✓ | ✓ |
| `MOVE` | renommage dans le même courrier | renommage et reclassement |
| `MKCOL` | refusé (`403`) — voulu | crée un dossier de classement |
| `COPY` | refusé | refusé |
| `LOCK` / `UNLOCK` | jeton **non persisté** | → **réservation** ECM, avec expiration |
| `DELETE` | suppression **définitive** | corbeille |
| `PROPPATCH` | acquitté sans effet | acquitté sans effet |
| Authentification | Basic, mot de passe seulement | Basic, mot de passe seulement |
| Audit `source='webdav'` | ✓ | ✓ |
| Bouton *Ouvrir dans Office*, adresse WebDAV sur la fiche | **absent** | ✓ (explorateur : avec `aite_ecm_office`) |
| Tests | 13 cas au niveau service, **couche HTTP non testée** | 8 cas `HttpCase` |
| Formats / taille | 10 extensions, 50 Mo | 23 extensions, 100 Mo |

Le connecteur Nextcloud (`aite_ecm_nextcloud`) est une **autre voie** vers le même besoin — Odoo pousse les fichiers dans Nextcloud, dont les clients de synchronisation font le lecteur réseau. Il n'est pas un manque du WebDAV, c'est un choix de déploiement.

---

## 2. Flux restants — analyse détaillée

Effort indicatif : **S** ≤ 1 jour · **M** 2 à 4 jours · **L** au-delà.

### 2.1 Bloquants pour l'usage Windows / Office — P0

#### F1 · Enregistrement Office par fichier temporaire — M

**Constat.** Word, Excel et LibreOffice n'écrasent pas le fichier ouvert : ils écrivent un temporaire (`~WRD0001.tmp`, `.~lock.x#`) dans le même dossier, puis le **déplacent** sur l'original. Le service ECM **refuse** ces temporaires au `PUT` (`aite_ecm_webdav/models/aite_ecm_webdav.py:222`, `403`) et au `MOVE` (`:288`) ; côté courrier, l'extension `tmp` n'est pas dans la liste et tombe en `409`. Le `MOVE` qui suit vise une ressource jamais stockée : `404`. Les deux tutoriels affirment pourtant que « le service reconnaît ce schéma » (`aite_ecm_webdav/README.md:177`, `aite_ecm_office/docs/WEBDAV.md:123`) : **ce n'est pas le cas.**

**Conséquence.** Selon la version d'Office, l'enregistrement échoue (« erreur d'autorisation de fichier ») ou se rabat sur une écriture directe. Dans les deux cas, le scénario documenté n'est pas celui joué, et l'utilisateur n'a aucun moyen de le savoir.

**À développer.** Un espace transitoire pour les temporaires (enregistrement `ir.attachment` sans `res_model`, purgé par cron après 24 h), servi par `PROPFIND`/`GET` le temps de la session ; au `MOVE` temporaire → nom existant, créer la **version** sur le document cible et jeter le temporaire ; reconnaître aussi la variante `PUT tmp` → `DELETE original` → `MOVE tmp→original` en différant la suppression quand un temporaire porte le même nom de base. Un test « séquence Office » commun aux deux racines (cf. F11).

#### F2 · Verrous réels côté courrier — M — *partiel : lock-null ECM livré en 18.0.2.1.6*

**Constat.** Le contrôleur courrier annonce la classe 2 (`DAV: 1, 2`) mais son `LOCK` « émet un jeton sans le persister » (`aite_courrier_webdav/controllers/webdav.py:257`). `aite.courrier.document` n'a **aucune notion de réservation** : pas de champ, pas de contrôle. L'en-tête `If:` des `PUT`/`MOVE`/`DELETE` n'est jamais lu, ni ici ni côté ECM.

**Conséquence.** Deux agents ouvrent la même pièce dans Word ; chacun croit détenir un verrou exclusif ; les deux enregistrements passent (v2, puis v3) — **le dernier écrit gagne, sans conflit signalé**. C'est précisément ce que le verrou doit empêcher.

**Livré en 18.0.2.1.6, côté ECM seulement** : un verrou sur un nom encore libre est accepté (ressource « lock-null » de la RFC 4918), sans quoi l'Explorateur Windows ne peut créer aucun fichier. Le reste tient.

**À développer.** Soit porter la réservation ECM (`checkout_user_id`, `checkout_expiry`, `_check_document_access` refusant l'écriture aux autres) sur la pièce de courrier, soit une table de verrous WebDAV (jeton, ressource, propriétaire, expiration) commune aux deux racines ; valider le jeton `If:` sur les écritures ; `423` pour les autres ; `lockdiscovery` avec propriétaire pour qu'Office affiche « verrouillé par … ». Harmoniser avec l'ECM : le `Timeout` du client y est renvoyé tel quel (`aite_ecm_webdav/controllers/webdav.py:244`) alors que la réservation dure `_checkout_hours()`, et un `UNLOCK` d'un autre utilisateur répond `204` sans rien faire.

#### F3 · Clé d'API et double authentification — S — **livré en 18.0.2.1.5**

**Constat.** Les deux contrôleurs authentifient par `request.session.authenticate(...)` (`aite_courrier_webdav/controllers/webdav.py:103`, `aite_ecm_webdav/controllers/webdav.py:95`), c'est-à-dire une connexion **interactive**. Dans Odoo 17/18, `res.users._check_credentials` n'accepte les clés d'API que pour les connexions non interactives ; et un compte à double authentification reste « en attente du code » — `session.uid` vide — donc `401`. Trois documents promettent pourtant la clé d'API comme mot de passe (`aite_ecm_webdav/README.md:197`, `aite_ecm_office/docs/WEBDAV.md:142`, et les miens, corrigés dans cette livraison). Vérifiable en dix secondes sur l'instance : `curl -u login:CLÉ_API -X PROPFIND …` → `401`.

**Conséquence.** Un compte avec 2FA — typiquement l'administrateur — ne peut pas monter le lecteur ; un poste qui mémorise le mot de passe du compte est une exposition inutile, là où une clé révocable était la bonne réponse.

**À développer.** Après l'échec du mot de passe, tenter `res.users.apikeys.sudo()._check_credentials(scope='rpc', key=…)` et, si l'identifiant correspond, `request.update_env(user=uid)` sans ouvrir de session. Commun aux deux racines (F5).

#### F4 · Noms de fichiers côté courrier — S

**Constat.** `_document_filename` sert `document.name` **brut** (`aite_courrier_webdav/models/aite_courrier_webdav.py:81`) : pas d'assainissement, alors que l'ECM remplace `\ / : * ? " < > |` (`aite_ecm_webdav/models/aite_ecm_webdav.py:26,57`). Et `_document_by_filename` renvoie le **premier** homonyme (`:115`).

**Conséquence.** Une pièce nommée « Facture 12/03 » produit un chemin à deux segments : introuvable (`404`). Deux pièces « Annexe.pdf » dans un même courrier : la seconde est invisible, et un `PUT` sur ce nom versionne la première.

**À développer.** Porter `sanitize` côté courrier ; désambiguïser les homonymes (`Annexe (2).pdf`, ou le schéma ECM `ID - nom.ext`) ; test de non-régression sur les deux cas.

### 2.2 Robustesse et performance — P1

#### F5 · Socle commun aux deux contrôleurs — M, **à faire en premier**

**Constat.** Authentification, résolution de base, dates HTTP, `multistatus`, `PROPPATCH`, corps de `LOCK` : ~80 % des deux contrôleurs sont identiques, copiés. La documentation Office affirme que l'ECM « réutilise le serveur WebDAV du courrier » (`aite_ecm_office/docs/WEBDAV.md:171`) : c'était le plan, pas le code. Le journal des anomalies montre le coût : A-10 (dates HTTP en `500`) corrigé dans l'un, puis redécouvert dans l'autre ; A-12 et A-13 appliqués aux deux, à la main.

**À développer.** `aite_courrier_webdav` fournit un contrôleur abstrait (verbes, formatage, authentification, erreurs) et le contrat de service ; l'ECM ne garde que son service et sa route. F1, F2, F3, F6, F7 n'atterrissent alors qu'une fois.

#### F6 · Coût de l'authentification à chaque requête — S — **livré en 18.0.2.1.5**

**Constat.** `save_session=False` + Basic : **chaque** requête rejoue la vérification du mot de passe — 600 000 itérations de PBKDF2 sous Odoo 17/18. **Mesuré sur l'instance Windows : 2,8 s pour un `PROPFIND` de la racine.** L'Explorateur émet 5 à 20 requêtes par dossier ouvert.

**Conséquence.** Un dossier met une demi-minute à s'ouvrir ; « l'accès aux fichiers est extrêmement lent » — c'était ce constat-là, pas le poste Windows.

**À développer.** Cache court (5 min) « empreinte des identifiants → uid » en mémoire du worker, invalidé par TTL et au changement de mot de passe.

#### F7 · ETag, requêtes conditionnelles, `Range` côté courrier — S à M

**Constat.** Le courrier ne renvoie pas d'`ETag` (l'ECM si) ; `If-Match` / `If-None-Match` sont ignorés des deux côtés ; `Range` n'est pas géré ; `Last-Modified` courrier suit `document.write_date`, qui bouge à la moindre étiquette.

**Conséquence.** Sans verrou (F2) ni `If-Match`, aucune protection contre l'écrasement croisé ; caches clients invalidés pour rien ; aperçus et gros fichiers rechargés en entier.

**À développer.** `ETag` depuis le `checksum` de l'`ir.attachment` ; `412 Precondition Failed` si `If-Match` ne correspond plus ; `Last-Modified` sur la date de la version ; `Range` sur `GET`.

#### F8 · Volumétrie de la racine courrier — M

**Constat.** `_accessible_courriers` charge **tous** les courriers enregistrés puis filtre en Python, courrier par courrier (`aite_courrier_webdav/models/aite_courrier_webdav.py:93`) ; la racine renvoie tout d'un bloc.

**Conséquence.** Sur une volumétrie de production (des milliers de courriers par an), ouvrir `W:\` déclenche un balayage complet à chaque `PROPFIND` ; le client Windows expire à 60 s.

**À développer.** Pousser le filtrage d'accès dans le domaine (règles d'enregistrement) ; structurer la racine par année puis mois (`/2026/09/COUR-2026-0412/`) ou par service ; même précaution pour « Sans classement » côté ECM.

#### F9 · `DELETE` courrier = suppression définitive — S

**Constat.** Supprimer un fichier dans l'Explorateur appelle `unlink()` (`aite_courrier_webdav/models/aite_courrier_webdav.py:264`). L'ECM, lui, met à la corbeille.

**Conséquence.** Une touche `Suppr` par erreur efface la pièce et toutes ses versions ; seul l'audit en garde trace.

**À développer.** Archivage (`active = False`) restaurable depuis la fiche, ou `DELETE` réservé aux managers ; aligner sur la corbeille ECM.

### 2.3 Produit et interface — P2

#### F10 · Exposition côté courrier — S à M

**Constat.** `aite_courrier_webdav` n'a **aucune vue** : ni adresse WebDAV sur la fiche courrier, ni bouton *Ouvrir dans Office* sur les pièces. L'ECM a les deux (`aite_ecm_webdav/models/aite_ecm_document.py`, `views/`), et ce code est générique.

**À développer.** Un mixin partagé (`webdav_url`, `office_uri`, `office_app`, `action_open_in_office`) appliqué aux deux modèles ; bouton sur les lignes de pièces et la fiche ; page *Paramètres › Lecteur réseau* avec l'adresse et la marche à suivre par système.

#### F11 · Tests HTTP courrier et séquence Office — M

**Constat.** La couche HTTP du courrier « se valide sur une instance lancée » (`aite_courrier_webdav/docs/WEBDAV.md`) : aucun `HttpCase`. Aucune racine ne teste la séquence réelle d'un client (`OPTIONS` → `PROPFIND 0` → `PROPFIND 1` → `LOCK` → `PUT` temporaire → `MOVE` → `UNLOCK`). Le harnais `docs/recette/test_webdav.py` couvre 34 contrôles mais hors intégration continue.

**À développer.** `HttpCase` courrier (401, 207, 409, 423, 403) ; un test « séquence Office » paramétré par racine, joué dans la suite.

#### F12 · Documentation à remettre d'équerre — S

Promesses non tenues par le code : clé d'API (×3), fichiers temporaires (×2), architecture Office (×1). Commentaires périmés : « futur provider WebDAV » (`aite_courrier_ged/models/aite_courrier_document.py:15`), « WebDAV hors périmètre V1 » (`aite_courrier_base/models/aite_courrier_audit_log.py:34`), « WebDAV à venir » (`aite_ecm_document/models/aite_ecm_document.py:337`). Fichiers morts : `aite_ecm_office/static/src/explorer_office.{js,xml}`, hors du motif d'assets du manifeste. À corriger au fil des chantiers ci-dessus ; mes trois documents le sont dans cette livraison.

### 2.4 Optionnel — P3

#### F13 · `COPY` et `MOVE` entre courriers — S chacun

Refusés partout (`aite_courrier_webdav/controllers/webdav.py:253`, service `:277`). `COPY` permettrait de créer un document à partir d'un modèle ; le déplacement d'une pièce vers un autre courrier est un reclassement rare. À arbitrer avec le métier.

#### F14 · Aide au montage — S — *partiellement traité*

**Livré en 18.0.2.1.9** : le mode `unc` et le guide HTTPS, présentés alors comme levant le blocage d'Office sur une instance en clair. **Constat du 24 septembre 2026 : ni l'un ni l'autre ne le lève.** Depuis la version 2311, Word, Excel et PowerPoint sous Windows bloquent par défaut l'invite d'authentification Basic — la seule que propose le serveur — en HTTPS comme en HTTP : le blocage porte sur la méthode, pas sur le transport (même message derrière Caddy, `https://localhost/…`). Un fichier pris dans le lecteur réseau n'y échappe pas : Word convertit le chemin `X:\…` en adresse `http(s)` et télécharge lui-même le fichier (constaté : `X:\…\ODOO45.docx` → `http://localhost:8069/webdav/aite_ecm/…/ODOO45.docx`, bloqué). Le mode `unc` (`aite_ecm.office_uri_mode = unc`, avec ou sans racine imposée par `aite_ecm.office_unc_root`) repasse donc par l'URL bloquée ; la spécification Office URI Schemes n'admet d'ailleurs pour `ms-word:ofe|u|` que des URI `http`/`https`. Ce mode n'est plus recommandé. Le remède est côté poste : la stratégie *Allow specified hosts to show Basic Authentication prompts to Office apps*, ou sa valeur de registre `basichostallowlist` (`REG_EXPAND_SZ`, stratégie Utilisateur) sous `HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity`, posée dans la session du compte Windows qui utilise Word, toutes applications Office fermées. HTTPS reste recommandé — il protège le mot de passe et dispense le client WebDAV de Windows de `BasicAuthLevel` — mais ne dispense pas de cette valeur. Reste la préparation du poste elle-même.

Le premier montage bute sur des réglages du **poste** (service WebClient, `BasicAuthLevel`, syntaxe `\\hôte@port\…` — sans `DavWWWRoot`) que l'utilisateur ne peut pas deviner — c'est exactement le parcours de cette semaine. La première ouverture dans Word bute en plus sur `basichostallowlist`. Générer depuis Odoo un script prêt à l'emploi et une page d'instructions par système réduirait ce coût à zéro — par exemple, sur le poste de test :

```powershell
net use X: \\localhost@8069\webdav\aite_ecm
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

(`\\localhost@SSL\webdav\aite_ecm` en HTTPS ; en production, le nom du serveur dans les deux commandes.) En production, HTTPS supprime le réglage `BasicAuthLevel` du client WebDAV de Windows, pas `basichostallowlist` : Office bloque l'invite Basic en HTTPS aussi. Microsoft ne recommande cette autorisation qu'à titre transitoire.

---

## 3. Backlog priorisé

| # | Chantier | Racines | Effort | Ce que ça débloque |
| --- | --- | --- | --- | --- |
| F5 | Socle commun aux deux contrôleurs | les deux | M | tous les correctifs suivants, une seule fois |
| F1 | Enregistrement Office par temporaire + `MOVE` | les deux | M | « Enregistrer » dans Word, tel que documenté |
| F2 | Verrous réels, `If:`, `lockdiscovery` | courrier (harmoniser ECM) | M | édition concurrente sûre |
| F3 | Clé d'API, comptes 2FA — **livré** | les deux | S | montage par l'administrateur, mot de passe jamais stocké |
| F4 | Assainissement et homonymes | courrier | S | toute pièce accessible, sans écrasement croisé |
| F6 | Cache d'authentification — **livré** | les deux | S | lecteur fluide, CPU serveur |
| F7 | `ETag`, `If-Match`, `Range`, `Last-Modified` | courrier surtout | S–M | caches clients, gros fichiers, anti-écrasement |
| F8 | Racine par année, filtrage SQL | courrier (ECM « Sans classement ») | M | volumétrie de production |
| F9 | `DELETE` → archivage | courrier | S | plus de perte par mauvaise touche |
| F10 | Adresse et *Ouvrir dans Office* sur les pièces | courrier | S–M | usage sans connaître l'URL |
| F11 | `HttpCase` courrier, séquence Office | les deux | M | non-régression en CI |
| F12 | Documentation et commentaires | les deux | S | promesses = code |
| F13 | `COPY`, `MOVE` entre courriers | les deux | S | à arbitrer |
| F14 | Aide au montage | les deux | S | premier montage et première ouverture dans Word sans support |

Ordre recommandé : F3 et F6 sont livrés (aide partagée dans `aite_courrier_base/tools/webdav_auth.py`, utilisée par les deux contrôleurs — un premier pas vers F5). Reste **F5 → F4 → F1 → F2** (le cœur de l'usage Windows/Office, ≈ 7 à 9 jours), puis F7–F9 en un lot « robustesse » (≈ 4 jours), puis F10–F12 (≈ 4 jours). F13 et F14 à la demande.

---

## 4. Hors WebDAV — ce que la campagne de recette déclare elle-même non couvert

Pour mémoire, `docs/recette/PLAN_DE_TEST.md §5` et l'inventaire des modules :

| Point | Pourquoi | État |
| --- | --- | --- |
| `aite_courrier_sign`, `aite_courrier_ged_documents`, `aite_ecm_documents` | Odoo Enterprise (`sign`, `documents`) | **0 test**, jamais installés en Community |
| Édition en ligne Collabora / OnlyOffice (WOPI) | serveur Office externe | protocole couvert unitairement, jamais éprouvé en réel |
| Google Docs, Nextcloud | client OAuth, instance Nextcloud | doublures en test unitaire seulement |
| OCR d'images, copie PDF/A, rendu PDF des états | Tesseract, LibreOffice, `wkhtmltopdf` sur le serveur | optionnels, à vérifier après installation |
| Montée en charge | hors périmètre | aucun test de charge |

Ces points sont des **vérifications** à mener sur une plateforme cible, pas des développements manquants — sauf ce qu'elles révéleront.

---

## 5. Méthode et limites

- Lecture intégrale des deux modules WebDAV, de leurs tests et de leurs documentations, des points d'accroche GED et ECM, du module Office, du plan de test, du journal des anomalies et des fiches produit. Aucune exécution : ce conteneur n'a ni Odoo ni PostgreSQL.
- Le serveur a été validé sur l'instance Windows par `curl` (`207`). Le montage dans l'Explorateur est en cours de diagnostic ; il relève du client Windows (F14), pas des flux ci-dessus — mais F1 et F2 se manifesteront dès la première sauvegarde depuis Word.
- Les efforts sont indicatifs, pour un développeur connaissant Odoo et la suite.

---

*AITE Consulting — analyse des flux WebDAV, septembre 2026.*
