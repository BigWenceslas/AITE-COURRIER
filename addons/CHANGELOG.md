# Changelog — AITE Courrier / AITE ECM

## 18.0.2.1.15 — Signature électronique sur Odoo Community

`aite_courrier_sign` exige l'app Sign d'Odoo Enterprise : sur Community, la
signature des courriers n'existait pas. Nouveau module
**`aite_courrier_sign_oca`** 18.0.1.0.0, adossé au module communautaire OCA
`sign_oca` (18.0.1.4.3, commit `2489814`, AGPL-3), livré dans le paquet sous
`oca/`. Il reprend le paramétrage de la variante Enterprise (case
*Signature requise* sur l'étape, bouton *Demander la signature*, garde
serveur) et va plus loin :

- **feat(sign_oca)** : le signataire (responsable du courrier) signe depuis le
  lien reçu par e-mail, sans compte Odoo ; le **PDF signé revient en GED**
  comme nouvelle version (`<pièce>_signe.pdf`, l'original reste), ou dans le
  fil du courrier si la pièce est verrouillée ou si le demandeur n'y a plus
  accès — les contrôles GED se font au nom du demandeur.
- **feat(sign_oca)** : la garde vaut **par passage sur l'étape** : un retour
  sur l'étape, ou une seconde étape à signer, exige une nouvelle signature
  (la variante Enterprise accepte toute signature complétée du courrier).
  Redemander remplace la demande en attente ; quitter l'étape l'annule.
- **feat(sign_oca)** : demander la signature est réservé à qui peut agir sur
  l'étape ; un refus est tracé « Tentative non autorisée ». Journal
  d'audit : *Demande de signature*, *Action bloquée*, *Signature complétée*.
- **fix(sign_oca)** : trois ouvertures de `sign_oca` refermées — lecture de
  toutes les demandes (PDF compris) par tout utilisateur interne ; lecture
  des lignes signataires, donc des jetons de signature, entre collègues
  rattachés à une même société partenaire ; téléchargement
  `/my/sign/<id>/download` de n'importe quelle demande par tout utilisateur
  connecté.
- **test(sign_oca)** : 12 tests (parcours, garde par passage, remplacement,
  annulation, pièce verrouillée, droits du demandeur, cloisonnement,
  téléchargement, signature anonyme par le lien). Campagne complète avec le
  module : 342 tests, 0 échec ; mêmes tests et ceux de `sign_oca` sous
  Python 3.12 et reportlab 4.1.0 (installateur Windows) : 0 échec ; parcours
  réel dans Chromium ; installation sur la copie d'une base où
  `aite_courrier_sign` était bloqué « à installer ».
- **docs** : `docs/TUTORIEL_SIGNATURE_COMMUNITY.md` ; renvois depuis le
  tutoriel Enterprise, `addons/LISEZMOI_INSTALLATION.md`, le plan de test et
  les fiches produit. `docs/recette/run_tests.sh` accepte `EXTRA_MODULES`.

## 18.0.2.1.14 — Journal d'audit : les refus restent tracés

Le moteur de validation écrit « Tentative non autorisée » ou « Action bloquée »
au journal d'audit, puis lève une exception. Sur un vrai serveur, l'exception
annule la transaction de la requête — et l'entrée d'audit avec elle : aucun
refus n'était jamais conservé, contrairement à ce qu'annonçaient la
documentation et les fiches produit. Les tests ne le voyaient pas : ils
partagent une seule transaction. Constaté sur Odoo 18.0 Community, serveur
démarré, par une tentative réelle : 0 entrée après le refus.

- **fix(base): les entrées « err » s'écrivent dans une transaction à part**
  (`aite.courrier.audit.log._log`), validée aussitôt, avec l'identité de
  l'utilisateur. Cela couvre les refus de `aite_courrier_validation` et la
  garde de signature. Pendant les tests, l'écriture reste dans la transaction
  partagée ; si l'écriture à part échoue, repli sur la transaction courante.
  `aite_courrier_base` 18.0.1.2.0.
- **test(base)** : le chemin d'exploitation passe par un curseur dédié, les
  autres types restent dans la transaction courante.
- **recette** : `docs/recette/verif_audit_refus.py` rejoue un refus par
  XML-RPC sur un serveur démarré et compte les entrées. Avant : 0 → 0 ;
  après : 0 → 1, puis 1 → 2.

## 18.0.2.1.13 — Community : les modules Enterprise à l'écart

Sur l'instance Windows (Odoo 18 Community), `aite_courrier_sign` restait
bloqué « à installer ». Community présente l'app Sign comme une offre
commerciale (module `sign` à l'état « non installable », bouton *Mettre à
niveau* vers odoo.com) : *Activer* passe sans erreur visible, puis Odoo ne
peut rien charger. Chaque démarrage écrit alors « Some modules have
inconsistent states, some dependencies may be missing: ['aite_courrier_sign'] ».
Les mises à jour des autres modules passent, mais **toutes les tâches
planifiées de la base sont suspendues** : Odoo n'exécute aucun cron tant
qu'un module est « à installer » (`ir.cron._check_modules_state`) — file
d'envoi des e-mails, relances SLA, capture, indexation, conservation —, et ne
remet lui-même les états à zéro qu'au bout de cinq heures. Reproduit sur Odoo 18.0
Community ; *Annuler l'installation* ramène le module à « non installé » et
fait disparaître la ligne.

- **paquet** : les trois modules Enterprise (`aite_courrier_sign`,
  `aite_courrier_ged_documents`, `aite_ecm_documents`) sont rangés dans
  `enterprise/`, hors du dossier `addons/` à copier sur Community.
- **docs** : le piège et son remède dans le tutoriel de signature (§2 et
  dépannage), le guide de déploiement et `addons/LISEZMOI_INSTALLATION.md`.

## 18.0.2.1.12 — Office bloque Basic en HTTPS aussi (documentation)

Sur l'instance Windows, un document Word créé dans le lecteur `X:` refusait
de s'ouvrir : « Microsoft Office a bloqué l'accès aux "http://localhost:8069/…"
car la source utilise une méthode de connexion qui peut être non sécurisée ».
Depuis la version 2311, Microsoft 365 bloque **par défaut** toute invite
d'authentification Basic — la seule que propose le serveur WebDAV —, en HTTP
comme en HTTPS, et Word convertit un chemin de lecteur réseau en adresse
`http(s)` avant de télécharger le fichier lui-même
([Microsoft Learn](https://learn.microsoft.com/microsoft-365-apps/security/basic-authentication-prompts-blocked)).

Les versions 18.0.2.1.9 et 18.0.2.1.10 affirmaient le contraire : que HTTPS
levait ce blocage, que le même fichier s'ouvrait depuis le lecteur réseau
« où c'est Windows qui s'authentifie », et que le mode `unc` le contournait.
Ces trois affirmations sont fausses ; les entrées ci-dessous restent en l'état
pour l'historique.

- **docs** : le remède est côté poste — la stratégie *Allow specified hosts to
  show Basic Authentication prompts to Office apps*, ou sa valeur de registre,
  posée dans la session du compte qui utilise Word, Office fermé :
  `reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f`.
  Décrit dans le guide de déploiement Windows, le tutoriel et le guide HTTPS,
  les README et la documentation des modules `aite_ecm_webdav`,
  `aite_ecm_office` et `aite_courrier_webdav`, le scénario de recette (étape
  0.5) et la fiche avant-vente technique. HTTPS reste recommandé — il protège
  le mot de passe et dispense le client WebDAV de Windows de `BasicAuthLevel`
  — mais ne dispense pas de cette valeur. L'ancienne clé Office
  `Common\Internet\BasicAuthLevel = 2` reste utile en HTTP, sans suffire.
- **ecm_webdav** : le mode `unc` (`aite_ecm.office_uri_mode`) est déclaré non
  recommandé — Word repasse par l'URL, et `ms-word:ofe|u|` n'admet que des
  adresses `http(s)`. Le comportement du code est inchangé ; docstrings,
  description du module et nom d'un test corrigés.

## 18.0.2.1.11 — WebDAV ECM : les dossiers depuis l'Explorateur

Sur l'instance Windows, créer un dossier dans le lecteur ECM échouait au
moment de le nommer : « Impossible de lire à partir du fichier ou de la
disquette source ». L'Explorateur crée toujours un dossier sous le nom
« Nouveau dossier » (`MKCOL`), puis le renomme (`MOVE`) — et le service ne
savait renommer, déplacer ou supprimer que des documents. Les tests ont été
joués pour la première fois sur un Odoo 18 réel, ce qui a mis au jour deux
défauts de plus.

- **fix(ecm_webdav): renommer, déplacer, supprimer un dossier.** `MOVE`
  renomme ou reclasse un dossier avec toute sa branche ; un nom déjà pris est
  refusé (`412`, jamais de fusion), un déplacement dans sa propre descendance
  aussi (`403`). `DELETE` **archive** un dossier vide — rien ne disparaît au
  lecteur réseau, comme un document part à la corbeille — et refuse (`409`)
  un dossier qui contient encore des documents, y compris ceux que
  l'utilisateur ne voit pas. `MKCOL` sur un nom déjà pris répond `405` au lieu
  de créer un homonyme inaccessible.
- **fix(ecm_webdav): chaque requête dans la langue du compte.** Odoo pose la
  langue de l'utilisateur quand il vérifie le mot de passe, pas quand
  l'identité vient du cache d'authentification (18.0.2.1.5) : les requêtes
  suivantes s'exécutaient en anglais. Les noms de dossiers étant
  traduisibles, un dossier renommé s'écrivait dans une langue et se relisait
  dans l'autre : l'application en français gardait « Nouveau dossier », et le
  lecteur réseau affichait tantôt l'un, tantôt l'autre nom.
- **fix(ecm_webdav): un refus ne laisse plus rien en base.** Les erreurs sont
  converties en réponses HTTP, si bien qu'Odoo validait la transaction : une
  écriture refusée par une contrainte restait enregistrée malgré le `403`.
  Chaque verbe s'exécute désormais dans un point de sauvegarde.
- **fix(ecm_webdav): chemin UNC sans `DavWWWRoot`.** Avec ce mot-clé, Windows
  interroge d'abord la racine du site — la page de connexion d'Odoo — et
  refuse le montage (« Erreur système 5 »), alors que
  `\\hôte@8069\webdav\aite_ecm` se monte. Le mode `unc` du bouton *Ouvrir
  dans Office* sert désormais cette forme.
- **test(ecm_webdav)** : création puis renommage d'un dossier comme le fait
  l'Explorateur, avec un compte en français et après expiration du cache ;
  déplacement et ses refus ; suppression d'une arborescence de bas en haut ;
  droits.
- **Première exécution réelle** (Odoo 18.0 Community, PostgreSQL 16) : les 57
  tests de `aite_courrier_base`, `aite_courrier_webdav` et `aite_ecm_webdav`
  passent — dont ceux des versions 18.0.2.1.4 à 18.0.2.1.10, jusqu'ici
  jamais joués. Le harnais `test_webdav.py` passe sur la racine ECM : 34
  contrôles, 36 avec `--strict`.
- **docs, recette** : gestes sur les dossiers, erreur 5 au montage, scénario
  manuel (4.9 – 4.11) ; `test_webdav.py --strict` renomme puis supprime le
  dossier qu'il crée. Après un renommage côté ECM, le harnais vérifie que
  l'ancien nom a disparu du listage, et non qu'il répond 404 : l'ECM retrouve
  un document par la référence en tête du nom, que l'ancien chemin porte.

## 18.0.2.1.10 — Mode UNC : racine personnalisable

Le mode `unc` levait bien le blocage de l'authentification, mais Office
refusait ensuite le fichier « car celui-ci provient d'un site de la zone Sites
sensibles » : en convertissant `\\hôte@8069\…` en URL pour déterminer la zone,
Windows y lit un `utilisateur@hôte` et relègue le chemin en zone restreinte.

- **feat(ecm_webdav): `aite_ecm.office_unc_root`** impose la racine servie en
  mode `unc`, au lieu de la déduire de `web.base.url`. Y mettre la lettre du
  lecteur monté (`Z:`) donne un chemin de lecteur ordinaire, que Windows ne
  convertit pas en URL — donc pas de zone restreinte. Utile aussi quand le
  partage porte un autre nom que l'URL publique.
- **docs** : le remède par les zones de sécurité (classer `http://localhost` en
  intranet local) est documenté à côté, pour les parcs où la lettre du lecteur
  n'est pas homogène.
- **test(ecm_webdav)** : racine imposée en mode `unc`, et ignorée en mode `url`.

## 18.0.2.1.9 — Office sur une instance en http : deux issues

Les versions récentes de Microsoft 365 refusent d'ouvrir un document servi en
`http` avec une authentification Basic — « la source utilise une méthode de
connexion qui peut être non sécurisée » — et la clé de registre `BasicAuthLevel`
ne lève plus ce refus. Le même fichier s'ouvre pourtant sans difficulté depuis
le lecteur réseau, où c'est Windows qui s'authentifie, et non Word.

- **feat(ecm_webdav): mode d'adresse pour les applications de bureau.** Le
  paramètre système `aite_ecm.office_uri_mode` accepte `url` (défaut,
  inchangé) ou `unc`. En `unc`, *Ouvrir dans Office* et *Ouvrir dans
  LibreOffice* désignent le chemin UNC du lecteur réseau
  (`\\hôte@8069\DavWWWRoot\webdav\aite_ecm\…`, `hôte@SSL` derrière HTTPS)
  au lieu de l'URL. L'adresse WebDAV affichée sur la fiche reste l'URL. Le
  mode se demande explicitement plutôt que de se déduire du protocole : un
  chemin UNC ne veut rien dire sur macOS ou Linux, et LibreOffice n'a pas ce
  blocage.
- **docs**: `WEBDAV_HTTPS_WINDOWS.md` — mettre l'instance en HTTPS, qui lève
  ce blocage et celui du client Windows, avec deux configurations prêtes
  (`docs/exemples/Caddyfile`, `docs/exemples/nginx-aite-webdav.conf`), le
  remontage du lecteur en `@SSL` et le retrait des contournements de registre.
- **test(ecm_webdav)** : mode `url` par défaut, rendu UNC en http et en https.

## 18.0.2.1.8 — WebDAV : HEAD annonçait un fichier vide

Word s'ouvrait sur une fenêtre sans document, sans message d'erreur. Il
interroge la taille du fichier avant de le charger, et le serveur lui
répondait **0 octet**.

- **fix(webdav, ecm_webdav): HEAD annonce la vraie taille.** Les deux
  contrôleurs répondaient à `HEAD` en reprenant les en-têtes du `GET` puis en
  vidant le corps par `set_data(b'')`. Or Werkzeug recalcule
  `Content-Length` à cette occasion : l'en-tête retombait à `0`. Un client
  qui interroge la taille avant de charger — Word systématiquement — en
  déduisait un document vide. La taille est désormais préservée.
- **test(ecm_webdav)** : `HEAD` annonce la taille du `GET` correspondant,
  corps vide. Le scénario autonome `docs/recette/test_webdav.py` couvrait
  déjà ce contrôle sur les deux racines.

## 18.0.2.1.7 — ECM : « Ouvrir dans Office » lance vraiment Word

Le bouton de la fiche document menait à une page 404 d'Odoo, l'adresse
`ms-word:ofe|u|http://…` s'affichant dans la barre du navigateur sous la forme
`localhost:8069/ms-word:ofe%7Cu%7Chttp:/…`.

- **fix(ecm_webdav, office): une URI de protocole ne passe plus par
  `ir.actions.act_url`.** Le client web normalise l'adresse de ce type
  d'action : les barres verticales deviennent `%7C` et le `//` du schéma
  imbriqué se réduit à `/`. Le navigateur ne reconnaît alors plus le
  protocole, résout l'adresse comme un chemin relatif d'Odoo et répond 404
  sans jamais lancer l'application. Une action cliente confie désormais l'URI
  au navigateur telle quelle — exactement ce que faisait déjà l'explorateur
  ECM, d'où la différence de comportement entre les deux. Même correction pour
  *Ouvrir dans LibreOffice*.
- **test(ecm_webdav)** : le bouton retourne une action cliente, l'URI conserve
  ses barres verticales et son schéma imbriqué.

## 18.0.2.1.6 — WebDAV ECM : créer un fichier depuis l'Explorateur

Les dossiers ECM s'ouvraient enfin, mais y créer un document Word échouait :
« Élément introuvable ». Deux refus du service, là où le lecteur du courrier
laissait passer — ce qui explique que seul l'ECM soit touché.

- **fix(ecm_webdav): un verrou sur un nom encore libre est accepté.** C'est
  ainsi que l'Explorateur Windows crée un fichier : il verrouille le nom,
  dépose le contenu, puis libère (ressource « lock-null » de la RFC 4918).
  `lock()` exigeait un document existant et répondait 404 : plus rien ne
  pouvait être créé depuis le lecteur. Le dossier d'accueil et le droit d'y
  écrire sont contrôlés, rien n'est créé — c'est le `PUT` qui crée. Le
  contrôleur répond alors 201, comme le veut la RFC. `UNLOCK` d'un nom resté
  libre (création abandonnée) n'est plus une erreur.
- **fix(ecm_webdav): un document se retrouve aussi par son titre.** L'ECM
  republie ses fichiers sous « RÉFÉRENCE - Titre.ext » ; le client, lui,
  redemande le fichier sous le nom qu'il vient de déposer. Ce nom résout
  désormais, après la correspondance exacte et la référence en tête.
- **test(ecm_webdav)** : la séquence complète de création par l'Explorateur
  (LOCK d'un nom libre, PUT, PROPFIND sous ce nom, UNLOCK), et le verrou
  refusé sans droit d'écriture sur le dossier.

## 18.0.2.1.5 — WebDAV : clés d'API et cache d'authentification

Mesuré sur une instance Windows : un simple `PROPFIND` de la racine du
courrier répondait en **2,8 s**. Un client WebDAV présente ses identifiants à
chaque requête, et Odoo 17/18 hache les mots de passe avec 600 000 itérations
de PBKDF2 : chaque listage, chaque lecture payait une seconde de calcul —
l'Explorateur en envoie des dizaines par dossier.

- **feat(base): aide d'authentification partagée** `tools/webdav_auth.py`,
  utilisée par les deux contrôleurs WebDAV. Les **clés d'API** Odoo sont
  acceptées comme mot de passe — hachage léger, révocables, seule voie pour un
  compte à double authentification, qu'une connexion Basic ne peut pas mener
  au bout. Les vérifications réussies sont mises en **cache** cinq minutes
  (empreinte salée par le secret de la base, compte revérifié actif à chaque
  coup). Ce que les README promettaient déjà devient vrai.
- **test(base)** : mot de passe vérifié une seule fois, mauvais mot de passe
  jamais mis en cache, expiration, compte désactivé évincé, clé d'API liée à
  son login. **test(ecm_webdav)** : `PROPFIND` avec une clé d'API → `207`,
  avec la clé d'un autre compte → `401`.

## 18.0.2.1.4 — WebDAV ECM : dossiers accessibles depuis Windows

- **fix(ecm_webdav): les dossiers s'ouvrent dans l'Explorateur Windows.**
  Le service ne servait de date de modification que sur les fichiers ; or le
  client WebDAV de Windows refuse d'ouvrir une collection sans
  `getlastmodified` — la racine, les dossiers de classement et « Sans
  classement » étaient déclarés inaccessibles, alors que le lecteur du
  courrier, qui date toutes ses collections, fonctionnait. Les dossiers
  portent désormais leurs dates de création et de modification, la racine et
  « Sans classement » l'instant courant, comme le courrier.
- **test(ecm_webdav)** : chaque entrée du `multistatus` de la racine porte
  un `getlastmodified`.

## 18.0.2.1.3 — WebDAV : recette autonome et correctif ECM

Le flux WebDAV n'était éprouvé que dans le cadre d'une campagne complète
(`uat_interfaces.py` : six contrôles sur la seule racine ECM, dépendant de
`requests` et d'une base ensemencée). Valider une installation locale — un
poste Windows, une instance de démonstration — demandait donc de tout monter.

### Correction

- **fix(ecm_webdav): un format refusé ne laisse plus de document vide.**
  `put_file` créait le document avant d'y attacher la première version : le
  contrôleur traduisant l'erreur en réponse `409`, la transaction était
  validée et un document sans version subsistait en base — invisible du
  lecteur réseau, mais bien présent. Création et première version sont
  désormais encadrées par un savepoint. `unlink` n'était pas la réponse :
  côté ECM il est réservé aux managers et aurait transformé le `409` en
  `500` pour un agent.

### Vérification

- **test(ecm_webdav): non-régression** sur le dépôt d'un format interdit —
  `409` renvoyé, et rien de créé en base.
- **test(recette): scénario WebDAV autonome** (`docs/recette/test_webdav.py`),
  34 contrôles sans aucune dépendance, sur les deux racines : découverte,
  authentification, listage, puis cycle de vie complet d'un fichier — dépôt,
  relecture à l'octet près, versionnage, renommage, verrous, formats refusés,
  suppression.

### Documentation

- `docs/DEPLOIEMENT_WEBDAV_WINDOWS.md` — installation sur Odoo 18 Windows,
  configuration du client WebDAV de Windows, usage, dépannage.
- `docs/recette/SCENARIO_WEBDAV.md` — parcours manuel de bout en bout,
  jusqu'à l'aller-retour Word.
- `docs/recette/GUIDE_TEST_WEBDAV.md` — prérequis, `curl` express, options du
  harnais. Y sont documentés les deux pièges d'une instance locale : module
  installé mais Odoo non redémarré, et serveur multi-base sans `db_name` —
  où le contrôleur ne peut deviner la base et répond `401` quels que soient
  les identifiants.

## 18.0.2.1.2 — Campagne de recette complète

Première campagne de recette de bout en bout sur Odoo 18 Community : les 25
modules installables ont été installés, testés, joués dans un navigateur
sous l'identité des rôles réels, et éprouvés par leurs interfaces
techniques. Le détail est dans `docs/recette/` (plan de test, guide
illustré, journal des anomalies).

### Vérification

- **test(suite): 295 tests** (contre 199 avant la campagne, dont 43
  échouaient), tous verts — les 8 modules sans couverture en ont désormais
  une : API REST, partage externe, portail, capture e-mail, OCR, réponses,
  pont Nextcloud du courrier, module chapeau.
- **test(ecm): parcours fonctionnel complet** — un courrier arrive, il est
  enregistré, son circuit se déroule jusqu'à l'archivage, sa pièce devient
  un document ECM scellé, partagé, exposé en WebDAV et retrouvé par l'API.
- **test(recette): 17 parcours utilisateur** joués dans un vrai navigateur
  avec les comptes du jeu de données, 45 captures d'écran, et 18 contrôles
  d'interfaces (WebDAV, API REST, lien de partage).
- L'installation complète de la suite ne produit plus aucun avertissement
  Odoo imputable aux modules AITE ; la désinstallation du jeu de données
  ne produit plus aucune erreur d'intégrité.

### Corrections bloquantes

- **fix(base): les 8 rôles AITE n'impliquaient pas « Utilisateur interne »** —
  un compte à qui l'on n'attribuait qu'un rôle AITE n'avait accès ni aux
  menus, ni aux séquences, ni au chatter.
- **fix(ecm_webdav): toute lecture répondait 500** — les dates HTTP étaient
  produites à partir d'un `datetime` Odoo naïf, refusé par Python. Le
  lecteur réseau ECM était inutilisable.
- **fix(ecm_webdav): base non résolue sans cookie de session** — cas normal
  d'un client réseau (Explorateur Windows, Finder, `davfs`).
- **fix(office): l'ouverture d'un document dans Google Docs échouait**
  toujours à la première demande (consentement appelé sur un enregistrement
  vide).
- **fix(sae): l'élimination d'un document violait une contrainte de base** —
  le lien du sceau vers le document devient facultatif ; le journal survit
  au document, comme prévu.
- **fix(portal): le formulaire de dépôt n'affichait aucune zone de saisie**
  pour le message ; le tiers voyait l'intitulé sans le champ.
- **fix(courrier_ecm): supprimer une pièce de courrier violait l'intégrité**
  du fichier partagé avec sa version ECM.

### Corrections majeures

- **fix(core): le statut ne suivait pas le circuit** — un courrier restait
  « Nouveau » de bout en bout ; « En traitement » n'apparaissait ni dans les
  filtres, ni sur le tableau de bord, ni au portail.
- **fix(records): un gel juridique posé sur un dossier ne gelait rien** — le
  marqueur stocké n'était jamais recalculé, la protection restait
  inopérante.
- **fix(records): la durée de conservation glissait** à chaque modification
  du document ; nouvelles dates `final_date` / `archived_date`, figées à la
  transition.
- **fix(ecm): un document finalisé restait modifiable par un manager** —
  le verrou du cycle de vie s'applique désormais à tous, comme côté
  courrier ; seuls les traitements système conservent leur accès.
- **fix(ecm): la purge nocturne de la corbeille s'interrompait** dès qu'une
  pièce sous conservation s'y trouvait.
- **fix(sae): impossible de vérifier l'intégrité d'un document gelé** —
  l'audit réclamé par le gel lui-même était bloqué.
- **fix(sae): les pièces de courrier n'étaient pas scellées** — le miroir
  ECM créait ses versions directement ; nouveau crochet
  `_version_registered`, appelé quelle que soit l'origine de la version.
- **fix(webdav/api/wopi/webhook): routes non authentifiées jouées deux
  fois** — Odoo 18 les ouvre en lecture seule par défaut alors qu'elles
  écrivent.
- **fix(demo): les 150 courriers du jeu de données n'étaient jamais créés**
  quand la suite s'installait en une commande — et étaient pourtant comptés
  comme créés.
- **fix(demo): la purge échouait sur un gel actif** et laissait derrière
  elle les miroirs ECM des courriers supprimés.

### Compléments

- **feat(demo): phases v2.1** — politique de conservation appliquée,
  documents à échéance ancienne, gels juridiques, boîtes d'archives avec
  prêt en cours, données personnelles, bordereau d'élimination prêt à
  valider, vérifications d'intégrité.
- **feat(demo): crochet de désinstallation** — la purge du module passe
  avant le nettoyage générique d'Odoo, qui déversait jusqu'ici une
  quarantaine d'erreurs d'intégrité et laissait des données derrière lui ;
  les miroirs ECM des courriers disparus et leurs dossiers vides sont
  nettoyés, les comptes référencés par les journaux inaltérables sont
  désactivés plutôt que détruits.
- **fix(records): un marqueur de gel périmé figeait un document pour
  toujours** — après une restauration ou la suppression directe d'un gel, le
  marqueur stocké pouvait rester à vrai sans qu'aucun gel ne le justifie. Il
  est désormais revérifié avant tout refus.
- **fix(divers)**: libellés de champs dupliqués, paramètre `unaccent`
  invalide, calculs mêlant champ stocké et non stocké, `xpath` sur `@class`,
  icônes sans intitulé accessible, statut HTTP en position d'en-têtes,
  erreur de droits WebDAV rendue en 500.


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
