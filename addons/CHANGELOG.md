# Changelog — AITE Courrier / AITE ECM

## 18.0.2.1.2 — Lecteur réseau WebDAV opérationnel, banc de tests remis en état

Campagne de recette complète (dossier `docs/uat/DOSSIER_UAT.md`) : 9 anomalies
relevées, 9 corrigées et vérifiées. Suite automatisée à **0 échec sur 152
tests**, campagne protocolaire WebDAV à **32 exécutions sur 32**.

### Lecteur réseau WebDAV

- **fix(ecm_webdav): erreur 500 sur tout dossier contenant des documents**
  *(bloquante)* — les champs date d'Odoo sont naïfs ; `format_datetime(...,
  usegmt=True)` exige un fuseau explicite et levait `ValueError`. Une fonction
  `http_date()` rend la date explicitement UTC avant formatage. Le lecteur
  réseau était inutilisable au-delà de la racine.
- **fix(http): routes qui écrivent sans être déclarées comme telles** — Odoo 18
  sert les méthodes réputées de lecture sur un curseur en lecture seule
  (`Opening a read/write test cursor from a readonly one`). Sept routes
  reçoivent `readonly=False` : les deux points d'entrée WebDAV,
  `/api/ecm/v1/*`, les deux routes de partage externe, les deux routes WOPI,
  le retour OAuth Google et le webhook Nextcloud.
- **fix(webdav): un fichier déposé n'était pas relisible à son propre chemin**
  — le serveur expose `RÉFÉRENCE - Titre.ext` alors que le client emploie le
  nom qu'il a écrit : chaque `PUT` créait un document de plus.
  `_document_by_filename()` accepte désormais quatre clés de résolution (nom
  exposé, titre, nom de fichier de la dernière version, référence en tête).
  Corrige aussi la relecture après un `MOVE` avec renommage.
- **fix(webdav): perte de contenu silencieuse sur `PUT`** — un client annonçant
  un type de formulaire voyait son corps consommé par l'analyseur de
  formulaires : le fichier était enregistré **vide, sans erreur**. La requête
  est refusée en **415** avec l'en-tête à employer.
- **fix(webdav): `HEAD` annonçait une taille nulle** — vider le corps remet
  `Content-Length` à zéro, et werkzeug le recalcule à l'envoi. La taille est
  restaurée et le recalcul désactivé (RFC 7231). Corrigé sur les deux points
  d'entrée WebDAV.

### Cœur ECM et archivage

- **fix(ecm_document): un document finalisé acceptait une nouvelle version**
  — dans `_check_document_access()`, le raccourci manager était évalué avant le
  contrôle de verrouillage : un manager pouvait donc versionner un document
  finalisé ou archivé, ce qui ruinait la valeur probante. Le contrôle de
  verrou passe désormais en premier et s'applique à tous.
- **fix(courrier_ecm): suppression d'une pièce de courrier impossible** — la
  pièce et son jumeau ECM partagent les mêmes `ir.attachment` ; la suppression
  en cascade se heurtait au `ondelete='restrict'` des versions ECM
  (`ForeignKeyViolation`). Les pièces jointes partagées sont réattribuées au
  document ECM, qui en devient propriétaire, avant la suppression.
- **fix(records): un gel juridique posé sur un dossier ne protégeait rien** —
  `legal_hold_active` est stocké et ne dépend que de `legal_hold_ids` et
  `folder_id` : un gel visant un dossier ne déclenchait aucun recalcul. Le
  recalcul est explicite à la pose comme à la levée, sous contexte
  `records_bypass` — la protection refusait sinon l'écriture des champs de gel
  qu'elle vient elle-même d'activer.
- **fix(records): le point de départ de la conservation dérivait** — les
  déclencheurs « à la finalisation » et « à l'archivage » se fondaient sur
  `write_date`, qui bouge à chaque modification : l'échéance reculait donc
  indéfiniment. Deux horodatages dédiés, `date_final` et `date_archived`, sont
  posés par les transitions de cycle de vie ; `write_date` ne reste qu'un repli.
- **fix(ecm_document): un seul document protégé faisait échouer toute la purge**
  — nouveau point d'extension `_purgeable()` ; `aite_ecm_records` y écarte les
  documents sous gel ou sous conservation, la purge traite les autres et
  renvoie le nombre réellement détruit.
- **fix(sae): le journal de preuve ne survivait pas au document** —
  `aite.ecm.seal.document_id` était `required`, d'où un `NotNullViolation` à la
  destruction. Le champ devient facultatif ; référence et empreintes, elles,
  restent obligatoires.

### Courrier, connecteurs, bureautique

- **fix(courrier_core): statuts déclarés mais jamais atteints** — le champ
  `state` annonçait six valeurs, le moteur n'en écrivait que quatre : un
  courrier restait « Nouveau » de la première à l'avant-dernière étape.
  Le franchissement d'une étape positionne « En traitement » ; la valeur
  « Validé », que rien ne produisait, est retirée. Tableau de bord, vue liste
  et libellés du portail ajustés.
- **fix(nextcloud): webhook renvoyant 500 au lieu de 403** —
  `make_json_response(payload, 403)` passait le statut en position d'`headers`.
- **fix(office): `Expected singleton: res.users()`** — l'autorisation Google
  était demandée au modèle `res.users` au lieu de l'utilisateur courant.
- **fix(office): champ « Adresse WebDAV » affiché en double** sur la fiche
  document — reliquat de la séparation `aite_ecm_office` / `aite_ecm_webdav`
  du 18.0.2.1.1, le champ ayant été retiré du modèle mais pas de la vue.

### Banc de tests et recette

- **fix(tests): banc de tests des modules ECM inopérant** *(39 échecs sur 152)*
  — deux défauts systématiques du code de test masquaient les anomalies
  ci-dessus : utilisateurs créés sans le groupe *Utilisateur interne* (compte
  externe, `AccessError` sur `ir.sequence` dès la création d'un document) et
  sans adresse e-mail (tout `message_post` échoue). Nouveau socle partagé
  `aite_ecm_document/tests/common.py` (`EcmTransactionCase`, `EcmHttpCase`,
  `_make_user()`) dont héritent les 8 fichiers de test ECM.
- **docs(uat): dossier de recette réutilisable** — `docs/uat/DOSSIER_UAT.md`
  (34 scénarios, 36 captures étiquetées, 9 fiches d'anomalie avec cause racine
  et preuve de correction) et sa version PDF, grille de saisie vierge
  `GRILLE_RECETTE.md`, campagne WebDAV rejouable
  `scripts/campagne_webdav.sh` (32 cas) et générateur de PDF
  `scripts/generer_pdf.py`.


## 18.0.2.1.1 — Corrections

- **fix(dashboard): clé de boucle dupliquée** — le tableau de bord du courrier
  utilisait le *nom* de l'étape comme clé de rendu ; deux circuits ayant une
  étape homonyme (« Réception »), l'affichage échouait avec
  `Got duplicate key in t-foreach`. La clé est désormais l'identifiant de
  l'étape, et le libellé est complété par le nom du circuit quand le nom est
  ambigu (« Réception (Facture fournisseur) ») ; même correction pour la
  répartition par catégorie.
- **test(audit): contrôle des clés de boucle** — tout `t-foreach` d'un gabarit
  OWL sans `t-key`, ou dont la clé n'est pas manifestement unique, est
  désormais signalé avant livraison.

- **fix(office): collision entre `aite_ecm_office` et `aite_ecm_webdav`** —
  les deux modules définissaient le même service WebDAV (`aite.ecm.webdav`),
  la même route `/webdav/aite_ecm` et les mêmes champs (`webdav_url`,
  `office_app`, `office_uri`), `office_app` étant Selection dans l'un et Char
  dans l'autre : l'explorateur échouait avec
  `'Char' object has no attribute 'selection'`. `aite_ecm_office` dépend
  désormais de `aite_ecm_webdav` et ne conserve que ce qui lui est propre
  (LibreOffice, édition en ligne WOPI, Google Docs) ; service, contrôleur,
  champs Office et tests WebDAV supprimés du module Office.
- **test(audit): nouveau contrôle de collisions** — un champ défini sur le même
  modèle par deux modules avec des types différents, ou une route HTTP
  déclarée deux fois, sont désormais détectés avant livraison.


## 18.0.2.1.0 — Records management et valeur probante (v2.1)

### `aite_ecm_records` (nouveau)

- **feat(records): règles de conservation** — périmètre (types, dossiers,
  confidentialité), durée (DUA), **point de départ** (création, finalisation,
  archivage, clôture de l'objet lié, ou date portée par une métadonnée),
  **sort final** (élimination, conservation définitive, revue), base légale ;
  5 règles livrées (OHADA 10 ans, contrats, RH, PV définitifs, procédures).
- **feat(records): cycle de vie archivistique** calculé chaque nuit (utilité
  courante → intermédiaire → échue → définitive), activité de **revue** créée
  au responsable à l'échéance, filtres et regroupements dédiés.
- **feat(records): gel juridique** sur documents et dossiers entiers :
  modification, corbeille, purge et destruction bloquées tant qu'il est actif ;
  pose et levée motivées et tracées.
- **feat(records): bordereaux d'élimination** — constitution automatique des
  documents échus, validation manager, exécution tracée, **certificat de
  destruction** PDF déposé dans l'ECM, lignes conservant référence, titre et
  empreinte ; destruction directe refusée hors bordereau.
- **feat(records): archives physiques** (boîtes, emplacement, prêt/retour) et
  **données personnelles** (marquage et filtre) ; 6 tests.

### `aite_ecm_sae` (nouveau)

- **feat(sae): scellement et journal de preuve chaîné** — chaque version,
  finalisation, archivage, vérification, élimination ou export produit un
  sceau SHA-256 couvrant contenu, événement et **empreinte du sceau
  précédent** ; journal **inaltérable** (write et unlink refusés).
- **feat(sae): horodatage** interne signé (HMAC de la clé de base) ou **RFC
  3161** via une autorité tierce, avec repli automatique.
- **feat(sae): vérification d'intégrité** à la demande et par tâche
  hebdomadaire (chaîne recalculée, empreintes des fichiers recontrôlées,
  anomalies au journal d'audit) ; **attestation d'intégrité** PDF.
- **feat(sae): copie de préservation PDF/A** (LibreOffice), manuelle ou
  automatique pour les archives à conservation longue.
- **feat(sae): export de paquets d'archives** — ZIP avec bordereau
  ``manifest.xml`` (structure SEDA 2.1), fichiers, journal de preuve et mode
  d'emploi ; 6 tests.

### `aite_courrier_ecm` (nouveau, v2.0 GA)

- **feat(bridge): les pièces de courrier deviennent des documents ECM** —
  miroir avec **fichiers non dupliqués** (même `ir.attachment`), classement
  `Courrier/<année>/<référence>`, confidentialité et métadonnées du courrier,
  suivi des versions dans les deux sens, archivage et corbeille propagés,
  reprise des pièces existantes à l'installation et filet de sécurité horaire ;
  les pièces entrent ainsi dans l'explorateur, la recherche, les partages,
  l'API et la politique de conservation ; 6 tests.


## 18.0.2.0.0 — Fondation ECM (v2.0, sprint 1)

La suite devient une plateforme de gestion de contenu d'entreprise :
le document est libéré de l'objet courrier, le moteur de circuits devient
polymorphe, et la plateforme s'ouvre (partage, API). Les modules courrier
v1.2 restent inchangés et fonctionnels ; les référentiels communs (groupes,
confidentialité, audit) restent portés par `aite_courrier_base`.

### `aite_ecm_document` (nouveau, application « ECM »)

- **feat(ecm): document autonome** `aite.ecm.document` — référence
  `DOC-AAAA-NNNNN`, rattachable à tout enregistrement Odoo
  (`res_model`/`res_id`), cycle de vie brouillon → finalisé → archivé,
  propriétaire, société, description.
- **feat(ecm): types et métadonnées** — `aite.ecm.document.type` porte un
  **modèle de métadonnées** (`fields.PropertiesDefinition`) ; chaque document
  expose ses valeurs (`fields.Properties`) ; dossier et confidentialité par
  défaut, extensions autorisées par type ; 6 types livrés (contrat, procédure,
  facture fournisseur, pièce RH, PV, générique).
- **feat(ecm): plan de classement** `aite.ecm.folder` — arborescence
  (`_parent_store`), **droits de lecture/écriture hérités** (groupes
  effectifs calculés récursivement), miroir paresseux dans l'app Documents
  (espace racine « ECM »), 7 dossiers de départ.
- **feat(ecm): versions** avec **empreinte SHA-256**, commentaire de version,
  extensions étendues (Office, images, e-mails, archives), 100 Mo max ;
  **détection de doublons** (bouton « Doublons », message chatter).
- **feat(ecm): check-out / check-in** — réservation exclusive avec expiration
  (`aite_ecm.checkout_hours`, 48 h), bandeau, libération par le réservant ou
  un manager ; téléversement et modifications bloqués pour les autres.
- **feat(ecm): relations** typées et orientées entre documents
  (`aite.ecm.link.type` : annexe, remplace, référence, traduction) avec vue
  inverse.
- **feat(ecm): corbeille** — `active=False` + date/auteur, restauration,
  **purge automatique** (`aite_ecm.trash_retention_days`, 30 j) tracée.
- **feat(ecm): sécurité** — ACL des 8 rôles du socle ; règles combinant
  **droits de dossier ET confidentialité** pour les utilisateurs, accès total
  Manager/Admin, règle multi-société ; contrôle centralisé
  `_check_document_access` (UI, partage, API).
- **feat(ecm): mixin** `aite.ecm.document.mixin` — onglet « Documents » pour
  tout modèle, livré sur les **contacts**.
- **feat(ecm): recherche** — panneau de facettes (plan de classement
  hiérarchique, types, étiquettes), filtres (mes documents, réservés, sans
  type, sans fichier, corbeille), recherche sur le **contenu indexé** des
  pièces ; **analyse du fonds** (graphique et tableau croisé).
- **test:** 10 cas (`tests/test_01_ecm_document.py`).

### `aite_ecm_workflow` (nouveau)

- **feat(workflow): circuit polymorphe** — champ `res_model` (objet
  gouverné), type de courrier requis seulement pour les circuits de courrier,
  contrainte d'unicité réécrite.
- **feat(workflow): mixin** `aite.workflow.mixin` — lancement, transition
  contrôlée côté serveur (habilitations des étapes, managers), rejet motivé,
  réinitialisation manager, échéance SLA et retard (recherchable), activités
  planifiées aux habilités, **historique générique** `aite.workflow.history`
  (durées par étape), audit.
- **feat(workflow): assistant d'action** générique (transition ou rejet,
  commentaire obligatoire respecté).

### `aite_ecm_dossier` (nouveau)

- **feat(dossier): types de dossiers** avec **pièces attendues**
  (type de document, obligatoire), métadonnées, dossier de classement,
  circuit dédié (unicité du circuit actif par type).
- **feat(dossier): dossier métier** `aite.ecm.dossier` — référence
  `DOS-AAAA-NNNN`, tiers, responsable, échéance, checklist instanciée à la
  création, **complétude** en temps réel, clôture refusée si incomplet (sauf
  manager), **rattachement automatique** des documents créés depuis le
  dossier à la pièce attendue, clôture automatique en fin de circuit si
  complet.
- **data:** types « Agrément fournisseur » (5 pièces + circuit Instruction →
  Validation achats → Décision) et « Dossier du personnel » (4 pièces).
- **test:** 5 cas (`tests/test_01_dossier.py`).

### `aite_ecm_share` (nouveau)

- **feat(share): liens de partage** à jeton, expiration, quota d'accès,
  consultation seule, désactivation ; page publique `/ecm/share/<jeton>`.
- **feat(share): filigrane dynamique** (pypdf + reportlab) sur les PDF
  servis, forcé pour Confidentiel/Secret ; accès journalisés (audit
  « Système », compteur).

### `aite_ecm_api` (nouveau)

- **feat(api): API REST** `/api/ecm/v1` — clé d'API Odoo (`X-API-Key`),
  exécution avec les droits de l'utilisateur ; `ping`, `types`, `folders`,
  `documents` (recherche paginée, création avec fichier base64 et
  métadonnées), `documents/<id>` (détail, versions, relations),
  `documents/<id>/versions`, `documents/<id>/download`, `openapi.json`.
- **feat(audit):** nouvelle source d'événements « API ».

### `aite_ecm` (nouveau chapeau)

- Installe AITE Courrier + Fondation ECM en un clic.

### `aite_ecm_office` (nouveau, édition Office et Google Docs)

- **feat(office): WebDAV du plan de classement** (`/webdav/aite_ecm`) — dossiers,
  documents `REF - Titre.ext`, dépôt = nouveau document, verrous = réservations.
- **feat(office): ouverture de bureau** — Word / Excel / PowerPoint
  (`ms-word:ofe|u|`) et LibreOffice (`vnd.libreoffice.command`) depuis la fiche
  et l'explorateur ; enregistrer = version.
- **feat(office): édition dans le navigateur (WOPI)** — Collabora Online /
  OnlyOffice : jetons temporaires, CheckFileInfo / GetFile / PutFile / Lock,
  verrou = réservation, sauvegarde = version, page hôte, découverte en cache,
  bouton *Tester le serveur*.
- **feat(office): Google Docs / Sheets / Slides** — autorisation OAuth par
  utilisateur, copie dans Drive, rapatriement (manuel, clôture, tâche
  planifiée), suppression de la copie ; 7 tests.

### Droits, numérisation et circuits sur les documents (v2.0 sprint 3)

- **feat(ecm): droits par utilisateurs nommés** sur les dossiers de classement
  (lecteurs / rédacteurs, hérités comme les groupes) et **partage nominatif**
  sur les documents (lecture / écriture, prime sur dossier et confidentialité),
  résumé « qui peut accéder » sur dossiers et documents, onglet Accès, bloc
  Accès et partage rapide dans l'explorateur ; règles d'enregistrement et
  `_check_document_access` mis à jour ; 3 tests.
- **feat(ecm): numérisation** — bouton **Numériser** de l'explorateur (photos
  de l'appareil mobile assemblées en PDF multipage), **dossier de dépôt
  surveillé** pour les scanners réseau (tâche planifiée, sous-dossiers
  `traites`/`erreurs`), **scan vers e-mail** (alias `ecm-scan`) ; page
  ECM › Configuration › Paramètres (dépôt, alias, réservation, corbeille) dans
  laquelle Nextcloud insère son bloc.
- **feat(workflow): circuits sur les documents ECM** — un circuit actif par
  type de document, boutons Lancer / Traiter / Rejeter / Réinitialiser sur la
  fiche et dans l'explorateur, bandeau d'étape et échéance, historique, filtres
  « En circuit », « En retard », « À traiter par moi », versions réservées aux
  habilités de l'étape, **finalisation automatique** en fin de circuit (option
  du type) ; circuit « Procédure — rédaction, vérification, approbation »
  livré ; 4 tests ; jeu de données enrichi (circuits, partages).

### Compatibilité Odoo Community et explorateur natif

- **refactor(ged): la GED courrier ne dépend plus de l'app Documents** —
  `aite_courrier_ged` (pièces versionnées, dossiers, étiquettes,
  confidentialité, WebDAV) s'installe sur Community ; le miroir dans l'app
  Documents (espace « Courrier », un dossier par courrier) est porté par
  `aite_courrier_ged_documents`, auto-installé sur Enterprise avec migration
  de l'espace racine existant. Les chapeaux `aite_courrier` et `aite_ecm`
  s'installent donc sur Community ; seul `aite_courrier_sign` (Odoo Sign)
  reste Enterprise.

- **refactor(ecm): plus aucune dépendance Enterprise dans le socle** —
  `aite_ecm_document` ne dépend plus de l'app Documents ; le mixin, le miroir
  de dossiers et l'espace racine « ECM » sont portés par `aite_ecm_documents`
  (auto-installé sur Enterprise, migration de l'espace racine existant) ;
  `aite_ecm_nextcloud` ne dépend plus de la GED courrier (glue
  `aite_ecm_nextcloud_courrier`) ; `aite_ecm_demo` dépend des seuls modules
  ECM (courrier et RH exploités s'ils sont présents).
- **feat(ecm): explorateur de fichiers natif** (action cliente OWL,
  ECM › Documents › Explorateur) : panneau latéral (plan de classement
  dépliable, statuts, types, étiquettes, rattachements, corbeille), cartes à
  **vignettes** (images côté serveur, PDF via pdf.js) ou liste, recherche
  plein texte, tri, pagination, **Charger** et **glisser-déposer**, nouvelle
  version, création de dossier, aperçu intégré, inspecteur et actions
  groupées (finaliser, réserver, corbeille, déplacer, étiqueter, typer,
  partager) — mêmes règles d'accès que les vues classiques ; kanban ECM avec
  vignettes ; 6 tests serveur ; gabarits validés avec le compilateur OWL 2.

### `aite_ecm_documents` (nouveau, explorateur Documents — installé automatiquement)

- **feat(documents): l'app Documents devient l'explorateur de l'ECM** —
  plan de classement reflété intégralement (création, déplacement), une seule
  carte par document mise à jour à chaque version (historique Documents),
  étiquettes et propriétaire synchronisés, « Attaché à » vers la fiche ECM,
  menu ECM › Documents › Explorateur de fichiers, bouton Explorateur, kanban
  ECM avec vignettes Documents.
- **feat(documents): adoption** — un fichier déposé dans l'espace « ECM »
  (Charger, glisser-déposer, Demande) crée un document ECM sans dupliquer le
  fichier ; remplacement de fichier → nouvelle version (refusé si verrouillé) ;
  renommage/déplacement de carte → titre/dossier ECM ; suppression depuis
  Documents refusée (corbeille ECM) ; corbeille ↔ carte archivée.
- **fix(documents): fusion** des cartes héritées (une par version) à
  l'installation.

### `aite_ecm_nextcloud` (nouveau, connecteur Nextcloud)

- **feat(nextcloud): miroir sortant** — chaque document ECM (et, en option,
  chaque pièce de courrier) est écrit par WebDAV dans une arborescence
  Nextcloud qui reproduit le plan de classement ; renommage/reclassement →
  déplacement ; suppression définitive → retrait ; envoi immédiat ou par
  tâche planifiée ; envoi initial du fonds ; documents Confidentiel/Secret
  exclus par défaut.
- **feat(nextcloud): retour des modifications** — fichier modifié dans
  Nextcloud (ETag) importé comme nouvelle version attribuée au réservant ou
  au propriétaire ; contenu identique ignoré ; document verrouillé → conflit
  signalé ; détection par **webhook** (app Webhook Listeners, Nextcloud 30+,
  contrôleur `/ecm/nextcloud/webhook` à secret partagé) ou **sondage** des
  ETags avec court-circuit sur l'ETag racine.
- **feat(nextcloud): liens publics** Nextcloud (mot de passe, expiration,
  révocation) ; boutons Ouvrir dans Nextcloud / Envoyer / Importer.
- **feat(nextcloud): paramètres** dans ECM › Configuration › Paramètres :
  connexion, test, mode, sondage, courrier, confidentiels, webhook,
  envoi du fonds ; audit source « Nextcloud » ; client WebDAV/OCS sans
  dépendance ; 11 tests avec faux serveur.

### `aite_ecm_demo` (nouveau, jeu de données de test)

- **feat(demo): générateur déterministe** (graine 2026) passant par les
  méthodes métier : 12 utilisateurs de démonstration, 8 services, tiers,
  courriers de chaque type avec pièces PDF, circuits lancés, transitions
  avant/arrière, rejets, archivages, retards SLA et réponses liées ;
  documents ECM typés (métadonnées, versions, doublons, finalisés/archivés) ;
  dossiers métier et leurs pièces ; relations, partages (expirés, quotas,
  accès journalisés), réservations, corbeille ; dates réparties sur six mois.
- **feat(demo): installation instantanée et génération par lots** — le hook
  enregistre un plan, une tâche planifiée crée les données par lots de 40 s
  (reprise automatique, état dans `aite_ecm_demo.state`), compatible avec une
  instance à configuration de base ; trois **profils** (`leger` par défaut :
  150 courriers, 60 documents, 40 dossiers ; `standard` ; `complet` : 500
  courriers, 200 documents, 200 dossiers).
- **feat(demo): identifiants externes** `aite_ecm_demo.*` sur chaque
  enregistrement : la désinstallation (ou `scripts/purge_demo.py`) supprime
  tout ; `scripts/seed_demo.py` pour une génération synchrone via
  `odoo-bin shell`.

## 18.0.1.2.0 — Modèles de réponse & portail externe

### `aite_courrier_reponse` (nouveau)

- **feat(reponse): bibliothèque de modèles** — modèle
  `aite.courrier.reponse.template` (objet + corps HTML avec champs de fusion
  `{{ object.champ }}`, moteur `inline_template` des modèles d'e-mails),
  restreignable par type ; 3 modèles livrés (réponse standard, demande de
  pièces, notification de clôture) ; menu Configuration > Modèles de réponse.
- **feat(reponse): assistant « Répondre »** — fusion immédiate au choix du
  modèle, corps retouchable, génération **PDF sur en-tête société**
  (`web.external_layout`) versionnée en **GED** ; options : envoi e-mail à
  l'expéditeur (PDF joint) et **création du courrier sortant lié**
  (`reply_to_courrier_id`, boutons croisés « Réponses » / « Courrier
  d'origine ») ; traçabilité chatter + audit.

### `aite_courrier_portal` (nouveau, optionnel)

- **feat(portal): espace « Mes courriers »** — liste paginée des courriers
  dont le tiers connecté (ou sa société) est l'expéditeur ; libellés de
  statut publics (le vocabulaire interne n'est pas exposé).
- **feat(portal): suivi d'avancement** — fiche avec parcours du circuit,
  étape courante en évidence, pièces téléchargeables via **jetons d'accès**
  (aucune ACL élargie sur les attachements).
- **feat(portal): dépôt de demandes** — formulaire objet / nature (types
  « Entrant ») / message / pièces jointes → courrier en brouillon + documents
  GED versionnés (mêmes garde-fous que la capture e-mail) ; audit source
  « Système ».
- **sec(portal): périmètre strict** — ACL lecture seule sur `aite.courrier`
  uniquement + règle d'enregistrement dédiée (`sender_partner_id` = tiers ou
  sa société) ; relations lues côté serveur via le pattern
  `_document_check_access` ; fil de discussion interne non exposé.

### `aite_courrier` (chapeau, 1.1.0 → 1.2.0)

- **chore(chapeau): périmètre** — la suite installe désormais aussi
  `aite_courrier_reponse` (10 modules) ; `aite_courrier_portal` reste
  optionnel, comme `aite_courrier_sign`.

## 18.0.1.1.0 — Alignement benchmark GEC (Maarch / Elise / QALITEL)

Version issue du benchmark des solutions GEC du marché : chaque écart
identifié est comblé par une brique native Odoo, en conservant le principe
« paramétrage avant code ».

### `aite_courrier_core` (1.0.0 → 1.1.0)

- **feat(core): contact expéditeur** — nouveau champ `sender_partner_id`
  (res.partner) + `sender_email`, pré-remplissage par onchange, bouton
  « Historique expéditeur » (vue 360° des courriers d'un même tiers).
- **feat(core): accusé de réception automatique** — case « Accusé de
  réception automatique » sur le type de courrier ; au lancement du circuit,
  envoi du modèle `mail_template_courrier_ack` à l'e-mail de l'expéditeur.
  L'échec d'envoi ne bloque jamais le lancement (audit `err`, source
  `system`).
- **feat(core): relances et escalade SLA** — cron horaire
  `_cron_check_sla_overdue` : 1 relance des habilités à l'échéance dépassée,
  puis 1 escalade à la hiérarchie (manager du service destinataire, sinon
  Managers Courrier) après `aite_courrier.sla_escalation_hours` (24 h par
  défaut). Drapeaux `sla_reminder_sent` / `sla_escalated` réarmés à chaque
  changement d'étape.
- **feat(core): filtre « En retard »** — `is_overdue` devient filtrable
  (méthode `_search_is_overdue`) ; filtres « Mes courriers » et « Reçus ce
  mois » ajoutés à la recherche.

### `aite_courrier_ged` (1.0.0 → 1.1.0)

- **feat(ged): formats étendus** — images (JPG, JPEG, PNG, TIF, TIFF) et
  e-mails archivés (EML, MSG) acceptés en plus de PDF/DOCX/XLSX ; message
  d'erreur dynamique aligné sur `ALLOWED_EXTENSIONS`.

### `aite_courrier_capture` (nouveau)

- **feat(capture): passerelle e-mail** — alias `courrier@<domaine>` : chaque
  e-mail crée un courrier en brouillon pré-qualifié (objet, expéditeur,
  contact, type par défaut) ; les pièces jointes aux formats GED deviennent
  des documents versionnés (les petites images type signature sont
  ignorées) ; audit source `system`. Case « Type par défaut (capture
  e-mail) » sur le type.

### `aite_courrier_ocr` (nouveau)

- **feat(ocr): indexation plein texte asynchrone** — file d'attente à la
  création des versions PDF/image, cron par lots (10 min) : couche texte PDF
  native (pypdf) puis repli OCR Tesseract si installé ; texte recopié dans
  `ir.attachment.index_content` ; champ de recherche « Contenu des pièces »
  sur le courrier ; bouton « Réindexer » sur les versions. Dépendances
  externes **optionnelles** (repli propre si absentes).

### `aite_courrier_sign` (nouveau, optionnel)

- **feat(sign): signature électronique Odoo Sign** — action « Demander la
  signature » (dernière version PDF → modèle Sign avec zone pré-positionnée,
  demande envoyée au responsable) ; étapes de circuit « Signature requise »
  bloquant les transitions en avant côté serveur tant qu'aucune demande n'est
  complétée ; bouton statistique « Signatures » ; lien `courrier_id` sur
  `sign.request`.

### `aite_courrier` (chapeau, 1.0.0 → 1.1.0)

- **chore(chapeau): périmètre** — la suite installe désormais aussi
  `aite_courrier_capture` et `aite_courrier_ocr` (9 modules) ;
  `aite_courrier_sign` reste optionnel.
