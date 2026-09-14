# Anomalies relevées et corrigées — campagne de recette

Toutes les anomalies listées ici ont été **reproduites, corrigées et
re-testées** ; chacune est désormais verrouillée par un test.

Gravité : **bloquante** (la fonction ne marche pas), **majeure** (résultat
faux ou protection inopérante), **mineure** (gêne, qualité).

---

## Socle et droits

### A-01 · Les rôles AITE ne faisaient pas un utilisateur interne — **bloquante**
`aite_courrier_base`

Aucun des 8 rôles (Agent, Assistant(e), Manager, Comptabilité, Signataire,
Archiviste, Audit, Administrateur) n'impliquait « Utilisateur interne ». Un
compte à qui l'on n'attribuait qu'un rôle AITE n'avait accès ni aux menus,
ni aux séquences (`COUR-…`, `DOC-…`), ni au chatter : 35 tests échouaient sur
`AccessError` et l'application était inutilisable pour ce compte.

*Correction* : chaque rôle implique `base.group_user` ; les séquences sont
lues en `sudo` (modèle technique). *Test* : `aite_ecm.test_02_roles_are_internal_users`.

### A-02 · Une opération métier échouait faute d'adresse e-mail — **majeure**
`aite_courrier_base`, 5 modèles

Poser un gel juridique, lancer un circuit ou déposer une version échouait
avec « Unable to send message… » quand l'utilisateur agissant n'avait pas
d'adresse e-mail — cas courant des comptes à identifiant technique.

*Correction* : mixin `aite.chatter.mixin` — adresse d'expédition de repli
(société, puis paramètres de messagerie) ; à défaut le message reste au
chatter, seule la notification par e-mail est omise. Portée limitée aux
modèles AITE.

---

## Cycle de vie et circuits

### A-03 · Le statut d'un courrier ne suivait pas son circuit — **majeure**
`aite_courrier_core`

`_enter_step` ne posait que l'état « Archivé », sur l'étape finale. Un
courrier restait donc « Nouveau » de bout en bout : les filtres « en cours »,
le tableau de bord et le suivi portail ne voyaient jamais de courrier « En
traitement ». Relevé en recette (SC02) : aucun groupe « En traitement » dans
la liste alors que 62 courriers circulaient.

*Correction* : passage à « En traitement » dès que le courrier quitte son
étape d'arrivée. L'aide du champ documente désormais chaque état, dont
« Validé », réservé aux circuits qui distinguent validation et archivage.
*Test* : `aite_courrier_validation.test_tc01b_state_follows_the_circuit`.

### A-04 · Un document finalisé restait modifiable par un manager — **majeure**
`aite_ecm_document`

Le contrôle d'accès accordait un accès total aux Manager et Administrateur
**avant** de vérifier le verrou de cycle de vie : une nouvelle version
pouvait être déposée sur un document finalisé ou archivé, alors que les
pièces de courrier appliquent la règle inverse et que le scellement repose
sur ce figement.

*Correction* : le verrou s'applique à tous les utilisateurs ; seuls les
traitements système en `sudo` (copie PDF/A, miroir de courrier) restent
autorisés. *Test* : `aite_ecm_document.test_06_locked_when_final`.

---

## Conservation et valeur probante

### A-05 · Un gel posé sur un dossier ne gelait rien — **majeure**
`aite_ecm_records`

`legal_hold_active` est un champ **stocké** qui ne dépend que des documents
nommés et du dossier de classement : un gel posé sur un *dossier* ne
déclenchait aucun recalcul. Les documents visés restaient modifiables,
supprimables et éliminables — la protection juridique était inopérante.

*Correction* : recalcul explicite à la pose et à la levée du gel.
*Test* : `aite_ecm_records.test_03_legal_hold`, `aite_ecm_demo.test_06`.

### A-06 · La durée de conservation glissait à chaque modification — **majeure**
`aite_ecm_document`, `aite_ecm_records`

Le point de départ d'une DUA déclenchée par la finalisation ou l'archivage
était lu sur `write_date` : toute retouche ultérieure du document repoussait
l'échéance d'autant. Une pièce comptable annotée chaque année n'arrivait
jamais à échéance.

*Correction* : nouvelles dates `final_date` / `archived_date`, figées à la
transition et remises à zéro par un retour en brouillon.
*Test* : `aite_ecm_records.test_02b_start_does_not_drift`.

### A-07 · La purge nocturne de la corbeille s'interrompait — **majeure**
`aite_ecm_document`

Le module records passait la liste des documents protégés via
`purge_skip_ids`, que la purge de base n'a jamais lue : la première pièce
sous conservation levait une erreur et **toute** la purge s'arrêtait.

*Correction* : la purge honore `purge_skip_ids`.
*Test* : `aite_ecm_document.test_07_trash_and_purge`.

### A-08 · Le détachement d'un sceau violait une contrainte de base — **bloquante**
`aite_ecm_sae`

L'élimination d'un document tentait de mettre `document_id` à NULL par SQL
direct sur un champ obligatoire : violation de contrainte, élimination
impossible alors même que le journal doit survivre au document.

*Correction* : le lien devient facultatif (`ondelete='set null'`) ; le sceau
conserve référence, empreinte et place dans la chaîne.
*Test* : `aite_ecm_records.test_05_protection`.

### A-09 · Vérifier l'intégrité d'un document gelé était impossible — **majeure**
`aite_ecm_records`, `aite_ecm_sae`

Le gel juridique interdisait toute écriture, y compris celle de l'état
d'intégrité : l'audit réclamé par le gel lui-même ne pouvait pas être
conduit.

*Correction* : la liste des champs qu'un gel laisse écrire devient
extensible (`_records_free_fields`) ; le scellement y ajoute les siens.
*Test* : `aite_ecm_sae.test_07_verify_under_legal_hold`.

---

## Interfaces

### A-10 · WebDAV ECM : toute lecture répondait 500 — **bloquante**
`aite_ecm_webdav`

Les dates HTTP étaient produites par `format_datetime(..., usegmt=True)` sur
un `datetime` Odoo naïf, ce que Python refuse : **tout** PROPFIND et **tout**
GET tombaient en erreur 500. Le lecteur réseau était inutilisable.

*Correction* : helper `_http_date` (UTC explicite), comme le module courrier.
*Test* : `aite_ecm_webdav.test_01_propfind`, `test_02_get`.

### A-11 · WebDAV : la base n'était pas résolue sans cookie — **bloquante**
`aite_ecm_webdav`

Un client réseau (Explorateur Windows, Finder, `davfs`) se présente sans
session : la base ne pouvait pas être déterminée et l'authentification
échouait.

*Correction* : repli sur la base configurée puis sur la base unique de
l'instance, comme le WebDAV courrier.

### A-12 · Routes non authentifiées jouées deux fois — **majeure**
`aite_ecm_webdav`, `aite_courrier_webdav`, `aite_ecm_api`, `aite_ecm_office`,
`aite_ecm_nextcloud`

Odoo 18 ouvre par défaut un curseur **en lecture seule** pour les routes
`auth='none'`. Toutes ces routes écrivent (dernière connexion, verrous, dépôt
de version) : chaque requête était exécutée une première fois en lecture
seule, échouait, puis était rejouée en écriture.

*Correction* : `readonly=False` déclaré sur les routes concernées.

### A-13 · Un refus de droits WebDAV répondait 500 — **mineure**
`aite_ecm_webdav`, `aite_courrier_webdav`

*Correction* : `AccessError` traduit en 403.

### A-14 · Google Docs : consentement appelé sur un enregistrement vide — **bloquante**
`aite_ecm_office`

`action_open_google` appelait le consentement sur `self.env['res.users']`
(vide) au lieu de l'utilisateur courant : `Expected singleton`. La première
ouverture d'un document dans Google Docs échouait toujours.

*Correction* : `self.env.user._google_authorize_action(...)`.
*Test* : `aite_ecm_office.test_06_google_round_trip`.

### A-15 · Webhook Nextcloud : 500 au lieu de 403 — **mineure**
`aite_ecm_nextcloud`

Le code HTTP était passé en position d'en-têtes
(`make_json_response(data, 403)`), d'où `TypeError`.

*Correction* : `status=403`. *Test* : `aite_ecm_nextcloud.test_10_webhook`.

---

## Portail

### A-16 · Le formulaire de dépôt n'avait pas de champ message — **bloquante**
`aite_courrier_portal`

`t-out` porté par la balise `<textarea>` supprime l'élément quand la valeur
est vide : le tiers voyait l'intitulé « Votre message » **sans zone de
saisie**. Relevé en recette (SC15).

*Correction* : la valeur par défaut passe dans le corps de la balise.
*Test* : `aite_courrier_portal.test_06_deposit_creates_a_courrier` (le
commentaire déposé est vérifié dans le chatter).

### A-17 · Une référence promise mais absente — **mineure**
`aite_courrier_portal`

Après dépôt, le message annonçait « conservez sa référence » alors que la
référence n'est attribuée qu'à l'enregistrement par le service.

*Correction* : le message n'annonce la référence que lorsqu'elle existe.

---

## Pont courrier ↔ ECM

### A-18 · Supprimer une pièce de courrier violait l'intégrité — **bloquante**
`aite_courrier_ecm`

Le fichier est **partagé** entre la version courrier et la version ECM
(`ondelete='restrict'`). Supprimer la pièce détruisait la pièce jointe et la
base rejetait l'opération.

*Correction* : les versions miroir sont retirées avant la suppression.
*Test* : `aite_courrier_ecm.test_05_unlink_to_trash`,
`aite_courrier_webdav.test_delete_document`.

---

## Jeu de données de test

### A-19 · Les 150 courriers du jeu de données n'étaient jamais créés — **majeure**
`aite_ecm_demo`

Quand la suite s'installe en une commande, les modèles du courrier ne sont
pas encore au registre au moment du crochet d'installation : les 150 unités
« courriers » étaient toutes ignorées — tout en étant **comptées comme
créées** dans le résumé.

*Correction* : le premier lot est différé à la tâche planifiée, qui travaille
sur un registre complet ; les modèles optionnels sont testés avant usage ;
les compteurs d'une unité annulée sont défaits.
*Tests* : `aite_ecm_demo.test_03`, `test_04`.

### A-20 · La purge échouait sur un gel actif — **majeure**
`aite_ecm_demo`

*Correction* : gels, bordereaux et boîtes supprimés en premier, marqueur
« sous gel » recalculé. *Test* : `aite_ecm_demo.test_07_purge_removes_everything`.

---

## Qualité et cohérence

### A-21 · Avertissements Odoo à l'installation — **mineure**

* paramètre `unaccent` invalide sur `aite.ecm.folder.parent_path` ;
* quatre paires de champs aux libellés identiques (`Fichier`, `Réponses`,
  `Version`) ;
* `legal_hold_active` (stocké) et `legal_hold_names` (non stocké) calculés
  par la même méthode ;
* deux `xpath` filtrant sur `@class` au lieu de `hasclass()` ;
* icônes décoratives sans intitulé accessible ;
* comparaison d'un enregistrement à une chaîne dans le plan de classement
  WebDAV.

*Correction* : tous traités. L'installation complète de la suite ne produit
plus aucun avertissement Odoo imputable aux modules AITE.

---

## Désinstallation

### A-22 · La désinstallation du jeu de données déversait des erreurs — **majeure**
`aite_ecm_demo`

Odoo supprime les enregistrements par identifiant externe, sans ordre
métier : dossiers avant documents, tiers avant comptes, comptes avant le
journal de preuve qui les référence. Une quarantaine d'erreurs d'intégrité
au journal serveur, et des données laissées derrière — alors que le manifeste
promet « désinstaller le module supprime tout le jeu de données ».

*Correction* : crochet de désinstallation qui lance d'abord la purge du
module (ordre métier connu) ; les comptes et les tiers qui leur sont
rattachés sont désactivés plutôt que détruits, puisque les journaux
inaltérables y font référence ; les miroirs ECM des courriers disparus et
leurs dossiers vides sont nettoyés. Vérifié : **0 erreur**, 150 courriers,
349 documents, 40 dossiers, 30 partages et 0 identifiant externe restants.
*Test* : `aite_ecm_demo.test_08_purge_removes_bridge_leftovers`.

---

## Robustesse des données

### A-23 · Un marqueur de gel périmé figeait un document pour toujours — **majeure**
`aite_ecm_records`

`legal_hold_active` est stocké. Après une restauration, un import ou la
suppression directe d'un gel, il pouvait rester à vrai sans qu'aucun gel ne
le justifie : le document devenait immodifiable et indestructible, avec un
message ne citant **aucun** gel (« Gel juridique actif () »).

*Correction* : le marqueur est revérifié contre les gels réels avant tout
refus, et corrigé s'il est périmé.
*Test* : `aite_ecm_records.test_08_stale_hold_flag_is_corrected`.

---

## Anomalies des tests eux-mêmes

Les tests des modules ECM n'avaient jamais été exécutés avec succès. Outre
les défauts produit ci-dessus, ont été corrigés : utilisateurs de test sans
adresse e-mail, doublure Google Drive écrite sur une API imaginaire, ETag de
dossier du faux Nextcloud ne changeant pas au bon moment, champ d'audit
`res_model` au lieu de `model_name`, `context_today` appelé sur le cas de
test, comptages absolus sur une base contenant déjà des données, lecteur PDF
imposé alors qu'Odoo en embarque deux selon la distribution.
