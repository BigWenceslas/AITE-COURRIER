# AITE Courrier & AITE ECM — Fiche avant-vente technique (DSI)

> Synthèse technique à destination des DSI et des architectes : architecture, sécurité, intégration bureautique, prérequis, qualité et limites connues.  
> Suite de 28 modules Odoo 18, installable sur Community comme sur Enterprise.  
> Version 2.1, septembre 2026 — AITE Consulting.

### Positionnement technique

**AITE Courrier & AITE ECM** est une suite de **28 modules Odoo 18** (licence OEEL-1) qui s'exécutent dans le serveur Odoo lui-même : circuits de traitement, gestion documentaire, lecteur réseau WebDAV, API REST, journal de preuve. Aucun serveur documentaire tiers n'est requis ; la seule bibliothèque Python externe déclarée est `requests` (connecteurs Office en ligne, Google et Nextcloud).

- **Community ou Enterprise** : 25 modules ne dépendent que d'apps Community (`base`, `mail`, `web`, `hr`, `contacts`, `portal`). Trois compléments optionnels s'appuient sur des apps Enterprise : `aite_courrier_sign` (app Sign) et les deux passerelles vers l'app Documents (`aite_courrier_ged_documents`, `aite_ecm_documents`), ces deux dernières s'installant d'elles-mêmes lorsque Documents est présent. Ces trois compléments n'ont pas été recettés (aucune instance Enterprise dans la campagne, voir *Qualité*).
- **Gestion documentaire propre à la suite** : les modèles `aite.courrier.document` et `aite.ecm.document` portent versions, verrous et droits ; l'ECM y ajoute l'empreinte SHA-256 de chaque version. L'app Documents d'Enterprise n'est qu'un explorateur de plus, jamais le socle.
- **Rien ne contourne l'application** : lecteur réseau et API passent par l'ORM sous l'identité de l'utilisateur ; le portail lit sous l'identité du tiers (droits et règle d'enregistrement) et dépose par un contrôleur dédié qui trace l'auteur au journal d'audit ; rôles, confidentialité et règles d'enregistrement s'appliquent partout.

### Architecture modulaire

| Groupe | Modules | Édition |
|---|---|---|
| Socle courrier | `aite_courrier_base` (8 rôles, référentiels, journal d'audit, authentification WebDAV), `aite_courrier_workflow` (circuits, étapes, transitions), `aite_courrier_core` (objet `aite.courrier`, SLA, cachet de traitement), `aite_courrier_validation` (exécution contrôlée des transitions), `aite_courrier_ged` (pièces versionnées, dossiers, étiquettes) | Community |
| Canaux courrier | `aite_courrier_capture` (alias e-mail), `aite_courrier_ocr` (indexation plein texte), `aite_courrier_reponse` (modèles de réponse, PDF), `aite_courrier_portal` (portail des tiers), `aite_courrier_webdav` (lecteur réseau), `aite_courrier_ecm` (pont vers l'ECM, auto) | Community |
| Compléments courrier | `aite_courrier_sign` (signature par Odoo Sign), `aite_courrier_ged_documents` (passerelle vers l'app Documents, auto) | Enterprise, optionnels |
| Fondation ECM | `aite_ecm_document` (application ECM), `aite_ecm_workflow` (circuits polymorphes), `aite_ecm_dossier` (dossiers métier), `aite_ecm_share` (partage externe), `aite_ecm_api` (API REST), `aite_ecm_demo` (jeu de données) | Community |
| Bureautique | `aite_ecm_webdav` (lecteur réseau, *Ouvrir dans Office*), `aite_ecm_office` (LibreOffice, WOPI, Google), `aite_ecm_nextcloud` (miroir Nextcloud), `aite_ecm_nextcloud_courrier` (extension du miroir aux pièces de courrier, auto) | Community |
| Complément ECM | `aite_ecm_documents` (passerelle vers l'app Documents, auto) | Enterprise, optionnel |
| Conservation et preuve | `aite_ecm_records` (records management), `aite_ecm_sae` (valeur probante) | Community |
| Chapeaux | `aite_courrier` (installe la suite Courrier et le tableau de bord), `aite_ecm` (installe Courrier et la Fondation ECM) | Community |

« auto » : module installé de lui-même dès que ses dépendances sont présentes. Le chapeau `aite_ecm` n'entraîne ni la bureautique, ni la conservation, ni le portail, ni la démo : on les nomme à l'installation (voir *Prérequis et déploiement*).

### Gestion du courrier

- **Référentiels** livrés : 5 types de courrier (entrant, sortant, interne, facture, devis), 3 priorités, 4 niveaux de confidentialité (Public, Interne, Confidentiel, Secret), services destinataires.
- **Circuits** : 5 circuits livrés (27 étapes, 37 transitions), entièrement paramétrables par l'administrateur : rôles et personnes habilités par étape, SLA en heures, commentaire obligatoire, transitions avant et arrière, un seul circuit actif par type.
- **Cycle de vie** : référence `COUR-AAAA-NNNN` attribuée au lancement du circuit ; états brouillon → nouveau → en traitement → archivé / rejeté ; champs métier verrouillés après archivage.
- **Exécution** : *valider*, *retourner*, *rejeter*, *commenter* depuis la fiche ou l'activité « À faire » créée pour les acteurs de l'étape ; l'habilitation est **vérifiée côté serveur** (refus `AccessError` tracé au journal d'audit).
- **SLA** : échéance par étape, indicateur de retard, cron horaire de relance (message aux habilités) puis d'escalade (activité au manager du service destinataire, à défaut aux Managers courrier ; `aite_courrier.sla_escalation_hours`, 24 h par défaut) ; accusé de réception automatique à l'expéditeur, activable par type.
- **Cachet de traitement** : dès que le circuit atteint son étape finale, le courrier reçoit un ruban « Traité » et un onglet *Cachet* listant les visas (étape, intervenant, fonction, date, transition, retours compris) ; un filtre « Traités » les regroupe dans les listes ; sur le portail, le tiers voit les **fonctions et les dates, jamais les noms**. Rien n'est saisi ni dupliqué : l'historique des étapes reste la source.
- **Canaux d'entrée** : alias e-mail `courrier@` (objet, expéditeur reconnu comme contact, pièces jointes aux formats admis versionnées, images de signature ignorées) ; portail `/my/courriers/new` (dépôt multi-fichiers, formats refusés signalés au tiers et tracés) ; saisie guidée.
- **Réponses** : 3 modèles livrés (réponse standard, demande de pièces complémentaires, notification de clôture), champs de fusion `{{ object.champ }}`, PDF à l'en-tête de la société versé comme version de la pièce, envoi à l'expéditeur, création du courrier sortant lié.
- **Recherche plein texte** : extraction en tâche de fond (cron 10 min) de la couche texte des PDF (`pypdf`, embarqué avec Odoo) et, si Tesseract est installé, OCR des scans et images (≤ 10 pages par défaut, `aite_courrier.ocr_max_pages`) ; champ de recherche « Contenu des pièces ».
- **Tableau de bord** (Manager, Audit, Administrateur) : en cours, en retard, reçus dans le mois, archivés (d'après la date de dernière modification), taux de rejet, délai moyen, répartition par étape et par catégorie.

### Gestion documentaire

| | GED courrier (`aite.courrier.document`) | ECM (`aite.ecm.document`) |
|---|---|---|
| Identifiant | rattaché au courrier `COUR-AAAA-NNNN` | `DOC-AAAA-NNNNN`, rattachable à tout enregistrement Odoo (`res_model` / `res_id`) |
| Formats | 25 extensions par défaut (bureautique, images dont HEIC / WEBP, EML / MSG), liste remplaçable par le paramètre `aite_courrier.allowed_extensions` | 24 extensions par défaut (bureautique, images, EML / MSG, ZIP / XML / JSON), restreignable par type de document |
| Taille maximale | 50 Mo par pièce | 100 Mo par fichier |
| Versions | v1, v2… conservées, audit à chaque dépôt | versions immuables avec **empreinte SHA-256**, auteur et commentaire ; détection de doublons (avertissement) |
| Classement | 8 dossiers et 7 étiquettes livrés, auto-classement par type de courrier | plan de classement hiérarchique (7 dossiers livrés), **droits de lecture / écriture par groupes et personnes, hérités du parent** |
| Types et métadonnées | 5 types de courrier, 3 priorités, 4 niveaux de confidentialité | 6 types et 20 métadonnées livrés (champs *Properties* Odoo 18) ; 4 types de relations entre documents |
| Verrous | pièce verrouillée si finalisée / archivée ou si le courrier est archivé | cycle brouillon → finalisé → archivé ; **réservation** (check-out) exclusive, expirant après 48 h (`aite_ecm.checkout_hours`) |
| Corbeille | non (suppression définitive ; seule la suppression d'une version isolée est tracée au journal d'audit, voir *Limites connues*) | oui : restauration, purge après 30 jours (`aite_ecm.trash_retention_days`) |
| Confidentialité | héritée du courrier | 4 niveaux, règles d'enregistrement par dossier et par confidentialité ; cloisonnement multi-société |

Le **pont `aite_courrier_ecm`** reflète chaque pièce de courrier en document ECM pointant vers le **même fichier** (aucune copie), classé `Courrier/<année>/<référence>` avec la confidentialité du courrier : les pièces de courrier bénéficient ainsi de l'explorateur, de la recherche, des partages, de l'API et de la politique de conservation.

L'ECM apporte en outre son propre **explorateur de fichiers**, disponible en Community comme en Enterprise (espaces, vignettes, glisser-déposer, aperçu, inspecteur, actions groupées), une **recherche facettée** (dossiers, types, étiquettes, état), un onglet « Documents » sur les contacts (mixin applicable à tout modèle), et trois voies de **numérisation** : photos prises au mobile assemblées en PDF, dossier surveillé alimenté par le scanner réseau (`aite_ecm.hotfolder_path`, cron 5 min), alias e-mail `ecm-scan@`.

**Circuits sur les documents et dossiers métier** : le moteur de circuits est réutilisable sur tout objet (`aite.workflow.mixin`) ; un circuit « Procédure » (rédaction → vérification → approbation) est livré, avec finalisation automatique du document en fin de circuit si son type le prévoit. Les **dossiers métier** `DOS-AAAA-NNNN` regroupent des pièces attendues (obligatoires ou non) avec complétude calculée, métadonnées propres et circuit dédié ; 2 types livrés (agrément fournisseur, dossier du personnel) et un circuit d'instruction.

### WebDAV et bureautique

**Deux racines servies par Odoo** (même port, même authentification, aucun serveur WebDAV tiers) :

| | `/webdav/aite_courrier` | `/webdav/aite_ecm` |
|---|---|---|
| Arborescence | un dossier par courrier référencé, dernière version de chaque pièce | le plan de classement, plus « Sans classement » ; fichiers `RÉFÉRENCE - Titre.ext` |
| Lecture / dépôt | lecture ; `PUT` = nouvelle version, ou nouveau document sur un nom libre | idem ; création depuis l'Explorateur Windows prise en charge (verrou posé sur un nom encore inexistant, conformément à la RFC 4918) |
| Renommage / déplacement | renommage au sein du courrier | renommage = titre, déplacement = reclassement |
| Dossiers (`MKCOL`, `MOVE`, `DELETE`) | création refusée (`403`) | création, renommage et déplacement (Manager, Archiviste, Administrateur) ; suppression = archivage d'un dossier vide |
| Suppression (`DELETE`) | définitive (voir *Limites connues*) | corbeille |
| Verrou (`LOCK`) | consultatif | devient une **réservation** ECM, libérée à l'`UNLOCK` ou à l'expiration |
| Métadonnées | `getlastmodified` sur fichiers et dossiers ; `HEAD` annonce la taille réelle | idem, plus `ETag` |

**Authentification.** HTTP Basic résolu en compte Odoo par le **mot de passe** ou par une **clé d'API** Odoo (révocable, liée au compte utilisateur ; seule voie pour un compte à double authentification). Une vérification réussie est mise en cache 5 minutes par processus (empreinte salée par le secret de la base ; l'état actif du compte est recontrôlé à chaque requête), ce qui évite de recalculer le hachage du mot de passe à chaque requête de l'Explorateur Windows ; une clé ou un mot de passe révoqués restent donc acceptés au plus 5 minutes sur un processus, alors que la désactivation du compte prend effet immédiatement. Audit `source = webdav` sur les dépôts, réservations et mises à la corbeille.

**Ouvrir dans Office / LibreOffice** : la fiche ECM remet au navigateur une URI `ms-word:` / `ms-excel:` / `ms-powerpoint:` (`ofe|u|` pour l'édition, `ofv|` en lecture seule lorsque l'utilisateur n'a pas le droit d'écrire) ; `aite_ecm_office` ajoute LibreOffice. En écriture directe, chaque enregistrement crée une version et le verrou posé par Office devient une réservation ; l'enregistrement par fichier temporaire puis renommage n'est pas encore pris en charge (voir *Limites connues*). Sous Windows, Word, Excel et PowerPoint exigent un réglage de poste (voir *Office et l'authentification Basic* ci-dessous). Deux modes d'adresse (`aite_ecm.office_uri_mode`) : `url` par défaut, ou `unc` (`\\hôte@port\webdav\aite_ecm\…`, `hôte@SSL` en HTTPS, racine imposable par `aite_ecm.office_unc_root`, par exemple la lettre du lecteur monté). Le mode `unc` ne contourne pas le blocage de l'authentification Basic par Office : Word convertit le chemin du lecteur en adresse `http(s)` et télécharge lui-même le fichier ; la spécification des URI Office n'admet d'ailleurs, après `ofe|u|`, que des adresses `http` ou `https`. Il n'est plus recommandé.

**Office et l'authentification Basic : prérequis de poste.** Depuis la version 2311 (Current Channel, décembre 2023 ; Monthly Enterprise Channel, janvier 2024 ; Semi-Annual Enterprise Channel 2402, juillet 2024 ; Office 2016, 2019 et 2021 vendus au détail, au rythme du Current Channel), Word, Excel et PowerPoint sous Windows bloquent par défaut les invites d'authentification Basic : « Microsoft Office a bloqué l'accès aux … car la source utilise une méthode de connexion qui peut être non sécurisée ». Le blocage porte sur la **méthode**, pas sur le transport : il s'applique **en HTTPS comme en HTTP**, au bouton *Ouvrir dans Office* comme à un fichier ouvert depuis le lecteur réseau. Les versions en licence en volume (LTSC) ne sont pas concernées. Le lecteur réseau lui-même (Explorateur, `net use`) échappe à ce blocage : on y crée dossiers et fichiers même quand Word refuse d'ouvrir. Le serveur WebDAV d'Odoo n'offrant que Basic, chaque poste doit **autoriser l'hôte** : sur un parc, par la stratégie de groupe *Allow specified hosts to show Basic Authentication prompts to Office apps* (*User Configuration › Policies › Administrative Templates › Microsoft Office 2016 › Security Settings*, modèles d'administration Office 5359.1000 ou plus récents) ou par Cloud Policy ; sur un poste, par son équivalent registre :

```powershell
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

- **Valeur existante** : `/f` remplace une valeur `basichostallowlist` existante (posée par l'administrateur, ou pour un autre serveur) : la lire d'abord avec `reg query "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist` et reprendre ses hôtes dans `/d`.
- **Hôtes** séparés par `;`, sans `https://` : en production, le nom du serveur (par exemple `ecm.client.fr`) ; la forme `hôte:port` s'ajoute par prudence, aucune source ne disant si le port compte. Guillemets obligatoires en PowerShell, où `;` sépare deux instructions.
- **Compte** : exécuter la commande dans la session du compte Windows qui utilise Word (PowerShell *en tant qu'administrateur* si ce compte est administrateur du poste), jamais avec un autre compte : `HKCU` désignerait alors le profil de cet autre compte.
- **Prise en compte** : fermer toutes les applications Office avant, puis les rouvrir ; Word demande alors des identifiants (login Odoo et mot de passe, ou clé d'API).
- **Réserves** : selon son libellé, la stratégie ne s'applique qu'aux versions d'Office sur abonnement (pour Office 2016, 2019 ou 2021 vendus au détail, bloqués eux aussi, aucune source ne montre que la valeur lève le blocage) ; une Cloud Policy du tenant (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`) ou le Baseline Security Mode peuvent primer sur la valeur locale ; Microsoft ne recommande cette autorisation qu'à titre transitoire (voir *Limites connues*).

Sur une instance en HTTP, l'ancienne clé Office `BasicAuthLevel` (`HKCU\Software\Microsoft\Office\16.0\Common\Internet`, valeur 2), qui autorise Basic hors SSL, reste utile, mais ne suffit plus depuis la version 2311 ; en HTTPS, elle est inutile. Pas-à-pas dans `docs/DEPLOIEMENT_WEBDAV_WINDOWS.md` (*Autoriser Word, Excel et PowerPoint*).

**HTTPS et mandataire inverse.** Le client WebDAV de Windows (Explorateur, `net use`) refuse par défaut l'authentification Basic en clair : **HTTPS est la configuration cible**, qui le dispense de tout réglage `BasicAuthLevel` et chiffre le mot de passe présenté à chaque requête. HTTPS ne lève pas, en revanche, le blocage d'Office décrit ci-dessus : `basichostallowlist` reste requis. Odoo se place derrière un mandataire inverse (*reverse proxy*), avec `proxy_mode = True`, `web.base.url` en HTTPS, `web.base.url.freeze = True` et `db_name` renseigné ; deux configurations sont livrées (`docs/exemples/Caddyfile`, `docs/exemples/nginx-aite-webdav.conf` : corps de requête 100 Mo, sans mise en tampon sur `/webdav/`). Le tutoriel `docs/TUTORIEL_WEBDAV_HTTPS.md` déroule le parcours complet, obstacles Windows compris.

**Édition en ligne, Google, Nextcloud** (`aite_ecm_office`, `aite_ecm_nextcloud`) :

- **WOPI** — Collabora Online ou OnlyOffice auto-hébergé : 12 formats bureautiques (Writer, Calc, Impress) et aperçu des PDF ; jetons limités à 8 h ; le verrou WOPI devient une réservation et chaque sauvegarde crée une version.
- **Google Docs / Sheets / Slides** — 10 formats ; autorisation OAuth par utilisateur (périmètre `drive.file`) ; copie déposée dans le Drive, rapatriée en version (manuellement, à la clôture ou par tâche planifiée) puis supprimée ; export en DOCX / XLSX / PPTX.
- **Nextcloud** — Odoo reste le référentiel, Nextcloud l'espace de travail : miroir du plan de classement par WebDAV (mode miroir seul ou bidirectionnel), retour des modifications en versions par webhook (Nextcloud 30+) ou sondage des ETags, conflit signalé sur un document finalisé, liens publics Nextcloud (mot de passe, expiration), extension aux pièces de courrier.

### API REST, partage externe, portail

- **API REST** `aite_ecm_api` : 9 routes sous `/api/ecm/v1` — `ping`, `types`, `folders`, recherche et lecture de documents, création de document et de version (fichier en base64 + métadonnées), téléchargement, `openapi.json` (OpenAPI 3.0). Authentification par **clé d'API Odoo** dans l'en-tête `X-API-Key`, exécution avec les droits de l'utilisateur titulaire de la clé, audit `source = api`. Périmètre volontairement limité à la lecture et à la création (pas de modification ni de suppression, pas de routes dossiers métier / partages / circuits).
- **Partage externe** `aite_ecm_share` : lien à jeton unique, date d'expiration, quota de téléchargements, désactivation à tout moment, mode consultation seule et **filigrane dynamique** sur les PDF (forcé pour Confidentiel / Secret), chaque accès journalisé. Le lien se transmet par le canal de votre choix (aucun e-mail envoyé par le module).
- **Portail** `aite_courrier_portal` : `/my/courriers` (courriers dont le tiers ou sa société est l'expéditeur), fiche avec parcours du circuit et cachet de traitement, pièces téléchargeables par lien à jeton, dépôt de demande avec pièces jointes multiples. Règle d'enregistrement en lecture seule, fil de discussion interne non exposé.

### Sécurité et gouvernance

- **8 rôles** (catégorie « AITE Courrier ») : Agent courrier, Assistant(e), Manager, Comptabilité, Signataire, Archiviste, Audit, Administrateur. Seuls Agent et Administrateur créent et modifient un courrier ; les autres agissent par les transitions du circuit. Groupes Odoo standard : combinables avec vos règles existantes.
- **Confidentialité** : 4 niveaux ; un courrier Confidentiel / Secret n'est visible que de son responsable, de son créateur, de son service et des managers ; règles d'enregistrement sur le courrier, ses pièces et les documents ECM ; réutilisées telles quelles par le WebDAV, l'API et le portail.
- **Journal d'audit** `aite.courrier.audit.log` en **ajout seul** (modification et suppression refusées au niveau ORM pour tout utilisateur, administrateur compris ; seuls les traitements en mode superutilisateur, comme les migrations, y échappent) : action, résultat, source (`ui`, `webdav`, `api`, `system`, `nextcloud`), auteur, horodatage ; lecture réservée aux rôles Audit et Administrateur.
- **Records management** (gestion des documents d'activité ; `aite_ecm_records`, dans l'esprit d'ISO 15489) : règles de conservation par type de document, dossier et niveau de confidentialité — durée, point de départ (création, finalisation, archivage, clôture du dossier, date de métadonnée), sort final (élimination, conservation définitive, revue) et base légale ; 5 règles livrées (pièces comptables OHADA 10 ans, contrats 10 ans, dossiers du personnel 5 ans, PV définitifs, procédures 3 ans) ; cycle de vie recalculé chaque nuit, activité de revue à l'échéance ; **gel juridique** posé et levé par un manager, bloquant modification, corbeille et destruction ; **bordereaux d'élimination** `BORD-AAAA-NNN` validés et exécutés par un manager (lignes conservant référence, titre et empreinte ; certificat PDF versé dans l'ECM) ; **archives physiques** (boîtes, emplacements, prêts) ; marquage des données personnelles.
- **Valeur probante** (`aite_ecm_sae`, dans l'esprit de NF Z42-013 / ISO 14641) : **sceau SHA-256** à chaque dépôt de version, finalisation, archivage, vérification, élimination et export, chaîné au sceau précédent ; horodatage interne (HMAC avec une clé conservée dans la base) ou **RFC 3161** par une autorité tierce (`aite_ecm_sae.tsa_url`) ; journal de preuve inaltérable au niveau ORM ; vérification à la demande par document et **contrôle hebdomadaire** de tout le fonds, toute anomalie étant consignée au journal d'audit ; **attestation d'intégrité** PDF ; copie de préservation **PDF/A** par LibreOffice ; **export de paquets d'archives** (ZIP : fichiers, `manifest.xml` inspiré du SEDA 2.1 — espace de noms SEDA, sans validation contre le schéma —, journal de preuve, mode d'emploi).

### Prérequis et déploiement

| Composant | Sert à | Statut |
|---|---|---|
| Odoo 18 Community **ou** Enterprise, PostgreSQL, Python 3.10+ | socle | requis (recette sous Odoo 18.0 Community, PostgreSQL 16, Python 3.11) |
| `db_name` dans `odoo.conf` ; `proxy_mode` et `web.base.url` derrière un mandataire inverse | WebDAV, liens Office, liens de partage | requis pour le lecteur réseau |
| Mandataire inverse HTTPS (Caddy ou nginx, exemples fournis) | lecteur réseau Windows sans réglage de registre ; chiffrement du mot de passe | recommandé ; en HTTP, réglages `BasicAuthLevel` documentés (postes de test) |
| Poste Windows avec Word, Excel, PowerPoint : hôte autorisé par `basichostallowlist` (stratégie *Allow specified hosts to show Basic Authentication prompts to Office apps*) | *Ouvrir dans Office*, documents Office ouverts depuis le lecteur réseau | requis à partir de la version 2311 (hors LTSC), en HTTP comme en HTTPS (voir *Office et l'authentification Basic*) |
| Poste Windows : service **WebClient** démarré | montage du lecteur | requis sur les postes concernés ; limite Windows de 50 Mo par fichier relevable (`FileSizeLimitInBytes`) |
| Serveur de messagerie entrant et domaine d'alias | capture `courrier@`, numérisation `ecm-scan@` | à configurer selon l'hébergement |
| `tesseract-ocr` (+ packs `fra`, `eng`), `poppler-utils`, `pytesseract`, `pdf2image`, `Pillow` | OCR des scans et images | optionnel ; sans eux, la couche texte des PDF est tout de même extraite |
| `wkhtmltopdf` | états PDF (réponse, bordereau, attestation) | requis pour ces états |
| LibreOffice (`soffice`) | copie de préservation PDF/A | optionnel |
| Collabora Online ou OnlyOffice | édition en ligne (WOPI) | optionnel |
| Projet Google Cloud (client OAuth) | Google Docs / Sheets / Slides | optionnel |
| Nextcloud 25+ (30+ pour le webhook) | miroir des fichiers | optionnel |
| `rfc3161ng` et URL d'autorité d'horodatage | horodatage externe | optionnel ; repli sur le jeton interne |

**Installation Community en une ligne** (les modules nommés entraînent l'installation des 24 modules Community hors démo) :

```
odoo-bin -c odoo.conf -d <base> -i aite_ecm,aite_ecm_webdav,aite_ecm_office,aite_ecm_records,aite_ecm_sae,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_courrier_portal --without-demo=all --stop-after-init
```

Ajouter `aite_ecm_demo` pour une base de formation : jeu de données réaliste généré par lots en arrière-plan, 3 profils (`leger` : 150 courriers / 60 documents / 40 dossiers ; `standard` : 300 / 120 / 100 ; `complet` : 500 / 200 / 200), génération reproductible (graine fixe), purge fournie (assistant ou script). Redémarrer Odoo après l'installation (les routes WebDAV sont publiées au démarrage). **Mise à jour** : recopier les modules, puis relancer Odoo avec `-u` suivi de la liste des modules ; sauvegarde `pg_dump` avant tout `-u all`.

**Documentation livrée** : `docs/DEPLOIEMENT.md` (installation, données de test, mise à jour), `docs/TUTORIEL_WEBDAV_HTTPS.md`, `docs/DEPLOIEMENT_WEBDAV_WINDOWS.md`, `docs/WEBDAV_HTTPS_WINDOWS.md`, `docs/TUTORIEL_CAPTURE_OCR.md`, `docs/TUTORIEL_SIGNATURE.md`, guides et scénarios de recette (`docs/recette/`), exemples `Caddyfile` et `nginx-aite-webdav.conf`. Interface en français (libellés natifs ; aucune autre langue livrée).

### Qualité

- **Tests automatisés** : 302 tests Odoo (`--test-enable`) exécutés lors de la campagne de recette du 16 septembre 2026 sur les 25 modules Community ; `run_tests.sh` rejoue base neuve, installation et tests, et échoue si aucun test n'a été exécuté. Les correctifs WebDAV livrés depuis (clés d'API et cache, création depuis l'Explorateur, `HEAD`, modes `url` / `unc`) sont couverts par des tests supplémentaires, à rejouer sur l'instance cible.
- **Recette applicative** : 18 scénarios joués dans un vrai navigateur (Playwright) sous l'identité des rôles, 49 captures, guide illustré régénérable ; 18 contrôles d'interfaces vus d'un client externe (6 WebDAV, 9 API REST, 3 liens de partage) ; 29 anomalies relevées et corrigées, la plupart couvertes par un test de non-régression.
- **Harnais WebDAV autonome** `docs/recette/test_webdav.py` : 34 contrôles sur les deux racines (découverte, authentification, listage, cycle complet d'un fichier, verrous, cas d'erreur), bibliothèque standard Python uniquement, utilisable sur n'importe quelle instance.
- **Hors couverture automatisée** : les 3 modules Enterprise (non installables sur la plateforme de recette, en Community), les serveurs WOPI, Google et Nextcloud réels (doublures en tests), l'OCR Tesseract, la conversion PDF/A, le rendu `wkhtmltopdf`, la montée en charge.

### Points d'extension

- **Paramétrage sans code** : circuits, étapes, transitions et habilitations ; types de documents et métadonnées *Properties* ; listes de formats ; paramètres système (`aite_courrier.sla_escalation_hours`, `aite_courrier.ocr_max_pages`, `aite_courrier.allowed_extensions`, `aite_ecm.checkout_hours`, `aite_ecm.trash_retention_days`, `aite_ecm.hotfolder_*`, `aite_ecm.office_uri_mode`, `aite_ecm.office_unc_root`, `aite_ecm_sae.tsa_url`) ; écrans *ECM › Configuration › Paramètres* pour Office en ligne, Google et Nextcloud.
- **Extension par le code** : mixin `aite.workflow.mixin` (circuits sur tout modèle), mixin `aite.ecm.document.mixin` (onglet Documents sur tout modèle), crochets GED (`_check_document_access`, `is_locked`, `add_version`), crochet `_version_registered` (scellement), contexte `audit_source`.
- **Intégration** : API REST décrite par OpenAPI, webhook Nextcloud, identifiants externes (XML-ID) du jeu de démonstration réutilisables par script.

### Limites connues et feuille de route

| Sujet | État actuel | Perspective |
|---|---|---|
| Authentification du lecteur réseau et d'*Ouvrir dans Office* | HTTP Basic seulement. Word, Excel et PowerPoint (version 2311 et suivantes) bloquent par défaut l'invite Basic, en HTTP comme en HTTPS : chaque poste doit autoriser l'hôte (`basichostallowlist`, voir *Office et l'authentification Basic*), autorisation que Microsoft ne recommande qu'à titre transitoire ; selon son libellé, la stratégie ne vaut que pour les versions sur abonnement, et une Cloud Policy du tenant peut primer | méthode d'authentification autre que Basic côté serveur, à étudier |
| Enregistrement Office par fichier temporaire | Word enregistre parfois via un temporaire renommé ; ces noms (`~$…`, `*.tmp`) sont refusés par le service ; seule l'écriture directe est prise en charge | prise en charge de l'enregistrement par fichier temporaire, en tête de la feuille de route du lecteur réseau |
| Verrous côté courrier | `LOCK` consultatif (non persisté) : deux agents peuvent écraser la même pièce ; l'ECM, lui, transforme le verrou en réservation, sans encore vérifier le jeton de verrou (`If:`) présenté par le client | verrous persistants côté courrier et validation du jeton sur les deux racines, planifiées |
| Noms de fichiers côté courrier | nom de la pièce servi tel quel (pas d'assainissement des caractères interdits) ; deux pièces homonymes dans un même courrier : seule la première est exposée | assainissement et désambiguïsation des noms, planifiés |
| Suppression WebDAV côté courrier | définitive, sans corbeille ; la suppression d'une pièce entière n'est pas tracée au journal d'audit (seule celle d'une version l'est) | corbeille et traçabilité de la suppression côté courrier, planifiées |
| Volumétrie de la racine courrier | tous les courriers accessibles sont chargés à chaque listage, sans structure par année | arborescence par année et filtrage en base, planifiés |
| *Ouvrir dans Office* sur les pièces de courrier | disponible sur les documents ECM seulement (les pièces de courrier y sont reflétées par le pont) | extension aux pièces de courrier, planifiée |
| Modules Enterprise | `aite_courrier_sign`, `aite_courrier_ged_documents`, `aite_ecm_documents` non recettés (aucune instance Enterprise dans la campagne) | à éprouver sur l'instance cliente |
| Moteur de circuits du courrier | le courrier conserve son moteur de circuits historique ; les documents ECM et les dossiers métier utilisent déjà le moteur générique (`aite.workflow.mixin`) | migration du courrier vers le moteur générique, planifiée |
| Cachet de traitement | cachet à l'écran et sur le portail, livré | cachet apposé sur le PDF, puis cachet vérifiable par un tiers (à l'étude) |
| Durcissement à l'installation | alias `courrier@` et `ecm-scan@` livrés ouverts à tout expéditeur ; clé d'API acceptée aussi en paramètre d'URL ; horodatage interne par défaut | restreindre les alias, imposer l'en-tête `X-API-Key`, configurer une autorité RFC 3161 |
| Montée en charge | aucun test de charge dans la campagne | à cadrer par projet |

### Versions des principaux modules

| Module | Version | Module | Version |
|---|---|---|---|
| `aite_courrier` | 18.0.1.2.0 | `aite_ecm` | 18.0.2.0.0 |
| `aite_courrier_base` | 18.0.1.1.0 | `aite_ecm_document` | 18.0.2.0.1 |
| `aite_courrier_core` | 18.0.1.1.1 | `aite_ecm_webdav` | 18.0.2.5.0 |
| `aite_courrier_webdav` | 18.0.1.1.1 | `aite_ecm_office` | 18.0.2.0.3 |
| `aite_courrier_portal` | 18.0.1.1.0 | `aite_ecm_records` | 18.0.2.1.1 |
| `aite_courrier_ged` | 18.0.2.0.1 | `aite_ecm_sae` | 18.0.2.1.1 |

### Services AITE Consulting

Cadrage et plan de classement · paramétrage des circuits, rôles et règles de conservation · déploiement (Community ou Enterprise, HTTPS, postes Windows) · reprise de données · formation par rôle · support et maintenance.

*AITE Consulting — www.aite-consulting.com*