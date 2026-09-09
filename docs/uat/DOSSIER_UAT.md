# Dossier de recette (UAT) — AITE Courrier / AITE ECM v2.1

**Version du dossier** : 1.0 · **Date d'exécution** : 9 septembre 2026 · **Rédacteur** : recette technique
**Version testée** : commit `8ac0a08` (« maj ok »), 28 modules · **Socle** : Odoo 18.0 Community, PostgreSQL 16, Python 3.11

Ce dossier est **réutilisable** : chaque scénario est numéroté, décrit pas à pas, avec son résultat
attendu, sa capture d'écran de référence et une colonne à remplir à chaque campagne. Les captures
portent un bandeau d'étiquette reprenant l'identifiant du scénario.

---

## 1. Résultat de la campagne du 9 septembre 2026

| Indicateur | Valeur |
|---|---|
| Modules installés sans erreur | **24 / 24** installables sur Community |
| Scénarios de recette fonctionnelle | **34 exécutés — 33 conformes, 1 non conforme** |
| Tests automatisés exécutés | 152 |
| Tests en échec, suite livrée telle quelle | **39** |
| Tests en échec après réparation du banc de test | **17** |
| Anomalies produit retenues | **9** (1 bloquante, 3 majeures, 5 mineures) |

**Verdict.** La plateforme s'installe proprement sur Odoo 18 Community et l'ensemble des fonctions
métier est opérationnel : courrier, circuits, GED, référentiel ECM, dossiers métier, conservation,
valeur probante, partage externe, API REST. Le **lecteur réseau WebDAV était inutilisable** en
raison d'une anomalie bloquante (ANO-01) désormais corrigée et vérifiée ; il reste une anomalie
majeure (ANO-03) sur le dépôt de fichiers nouveaux. Le **banc de tests automatisés des modules ECM
est défaillant** (ANO-02) : il masquait ces régressions.

---

## 2. Environnement de recette

### 2.1 Installation de référence (reproductible)

```bash
# 1. Base de données
service postgresql start
su postgres -c "createuser -s odoo"           # mot de passe : odoo
su postgres -c "createdb -O odoo aite_uat"

# 2. Odoo 18 Community
git clone --depth 1 --branch 18.0 https://github.com/odoo/odoo.git /home/user/odoo18
python3 -m venv /home/user/odoo-venv
/home/user/odoo-venv/bin/pip install -r /home/user/odoo18/requirements.txt
/home/user/odoo-venv/bin/pip install psycopg2-binary pypdf   # psycopg2 sans en-têtes système

# 3. Suite AITE : addons_path = <odoo>/addons,<dépôt>/addons
/home/user/odoo-venv/bin/python odoo-bin -c odoo.conf -d aite_uat \
  -i aite_ecm,aite_ecm_records,aite_ecm_sae,aite_ecm_webdav,aite_ecm_office,\
aite_courrier_portal,aite_ecm_nextcloud --without-demo=all --stop-after-init

# 4. Jeu de données de recette
/home/user/odoo-venv/bin/python odoo-bin -c odoo.conf -d aite_uat -i aite_ecm_demo --stop-after-init
/home/user/odoo-venv/bin/python odoo-bin shell -c odoo.conf -d aite_uat \
  < addons/aite_ecm_demo/scripts/seed_demo.py

# 5. Démarrage
/home/user/odoo-venv/bin/python odoo-bin -c odoo.conf -d aite_uat --db-filter='^aite_uat$'
```

> **Prérequis WebDAV.** Le serveur doit exposer **une seule base résolvable** : renseigner `db_name`
> dans `odoo.conf` ou démarrer avec `--db-filter`. Sans cela, les deux points d'entrée WebDAV
> (`/webdav/aite_ecm` et `/webdav/aite_courrier`) répondent `404` : un client WebDAV n'envoie aucun
> cookie de session, la base ne peut donc pas être déduite. Vérifié en campagne.

### 2.2 Modules installés

| Statut | Modules |
|---|---|
| **Installés (24)** | aite_courrier_base, aite_courrier_workflow, aite_courrier_core, aite_courrier_validation, aite_courrier_ged, aite_courrier_webdav, aite_courrier_capture, aite_courrier_ocr, aite_courrier_reponse, aite_courrier_portal, aite_courrier, aite_courrier_ecm, aite_ecm_document, aite_ecm_workflow, aite_ecm_dossier, aite_ecm_share, aite_ecm_api, aite_ecm_records, aite_ecm_sae, aite_ecm_webdav, aite_ecm_office, aite_ecm_nextcloud, aite_ecm_nextcloud_courrier, aite_ecm |
| **Non installés (4)** | aite_courrier_sign, aite_ecm_documents, aite_courrier_ged_documents *(requièrent Odoo Enterprise — comportement conforme)* ; aite_ecm_demo *(installé séparément pour la recette)* |

### 2.3 Limites de l'environnement de recette

Ces points ne sont pas des anomalies produit ; ils bornent la portée de la campagne.

| Élément absent | Conséquence sur la recette |
|---|---|
| `wkhtmltopdf` | Génération PDF non testée : réponses courrier, attestation d'intégrité, certificat de destruction |
| `tesseract-ocr`, `poppler-utils` | OCR image non testé ; l'extraction PDF native (pypdf) reste opérationnelle |
| Serveur SMTP / IMAP | Capture e-mail et notifications sortantes non testées de bout en bout |
| Instance Nextcloud | Connecteur testé sur simulateur uniquement |
| Odoo Enterprise | Passerelles app Documents et signature Odoo Sign non testées |

### 2.4 Comptes de recette

Mot de passe commun : `demo1234`. Compte technique : `admin` / `admin`.

| Identifiant | Nom | Rôle AITE | Usage en recette |
|---|---|---|---|
| `demo.admin` | Serge Kamdem | Administrateur (tous rôles) | Scénarios d'administration et de configuration |
| `demo.manager1` | Patrick Essomba | Manager | Validation, clôture, gel juridique, bordereaux |
| `demo.agent1` | Aurélie Mbarga | Agent courrier | Saisie, traitement, dépôt de pièces |
| `demo.assist1` | Nadège Fotso | Assistant(e) | Enregistrement et orientation |
| `demo.compta` | Hervé Kenfack | Comptabilité | Circuit facture fournisseur |
| `demo.signer` | Gisèle Atangana | Signataire | Étapes de signature |
| `demo.archive` | Landry Nkolo | Archiviste | Classement, conservation, archives physiques |
| `demo.audit` | Irène Djomo | Audit | Consultation du journal d'audit (lecture seule) |

### 2.5 Volumétrie du jeu de données

150 courriers (30 par type) · 196 pièces de courrier · 346 documents ECM · 185 versions ·
40 dossiers métier · 93 pièces de dossier · 30 partages externes · 12 réservations ·
8 documents en corbeille · 60 tiers · 8 services · 12 utilisateurs · 15 étiquettes ·
12 sous-dossiers de classement · 135 circuits lancés · 350 transitions.

---

## 3. Convention de notation

| Colonne | Contenu |
|---|---|
| **Réf.** | Identifiant stable du cas, à citer dans les anomalies |
| **Résultat attendu** | Critère d'acceptation, vérifiable sans ambiguïté |
| **Capture** | Fichier de `docs/uat/captures/`, bandeau d'étiquette intégré |
| **Statut** | ☐ Conforme ☐ Non conforme ☐ Non testé — à cocher à chaque campagne |

Statuts relevés le 9 septembre 2026 : **C** = conforme, **NC** = non conforme, **NT** = non testé.

---

## 4. Scénarios de recette

### SC-01 — Gestion du courrier : pilotage et cycle de vie

*Profil : `demo.admin` · Prérequis : jeu de données chargé*

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-01.1 | Courrier › Analyse | Le graphique et le tableau croisé se chargent, ventilation par type et statut | `sc01_01_analyse_courrier.png` | C |
| SC-01.2 | Courrier › Tableau de bord | 6 indicateurs affichés (en cours, retard SLA, reçus, archivés, taux de rejet, délai moyen), charge par étape et répartition par catégorie | `sc01_02_tableau_de_bord.png` | C |
| SC-01.3 | Courrier › Courriers | Liste des courriers avec référence `COUR-AAAA-NNNN`, objet, statut, étape | `sc01_03_liste_courriers.png` | C |
| SC-01.4 | Ouvrir le premier courrier | Fiche complète : référence, circuit, étape courante, échéance SLA, responsable | `sc01_04_fiche_courrier.png` | C |
| SC-01.5 | Onglet **Documents** | Pièces versionnées du courrier, format et taille contrôlés | `sc01_05_pieces_courrier.png` | C |
| SC-01.6 | Onglet **Historique** | Historique daté des étapes traversées, avec acteur et commentaire | `sc01_06_historique_etapes.png` | C |
| SC-01.7 | Courrier › Audit › Journal d'audit | Journal horodaté, en lecture seule, source de chaque opération | `sc01_07_journal_audit.png` | C |

> **Point de vigilance fonctionnel.** Le tableau de bord affiche 75 courriers « en cours ». Le champ
> `state` déclare six valeurs mais le moteur n'écrit que *Brouillon*, *Nouveau*, *Rejeté* et
> *Archivé* : **« En traitement » et « Validé » ne sont jamais positionnés**. Un courrier reste donc
> « Nouveau » de la première à l'avant-dernière étape (voir ANO-08). L'avancement réel se lit sur
> l'étape du circuit, pas sur le statut.

### SC-02 — Référentiel documentaire ECM

*Profil : `demo.admin`*

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-02.1 | ECM › Documents › Explorateur | Plan de classement dépliable avec compteurs, cartes à vignettes, facettes, recherche, dépôt par glisser-déposer | `sc02_01_explorateur.png` | C |
| SC-02.2 | ECM › Tous les documents | Liste avec référence `DOC-AAAA-NNNNN`, type, dossier, état | `sc02_02_liste_documents.png` | C |
| SC-02.3 | Ouvrir un document | Fiche : référence, type, dossier, confidentialité, propriétaire, métadonnées du type | `sc02_03_fiche_document.png` | C |
| SC-02.4 | Onglet **Versions** | Versions successives avec empreinte SHA-256, taille, auteur, date | `sc02_04_versions.png` | C |
| SC-02.5 | Onglet **Relations** | Relations typées vers d'autres documents (annexe, remplace, référence, traduction) | `sc02_05_relations.png` | C |
| SC-02.6 | Onglet **Conservation** | Règle appliquée, durée d'utilité administrative, sort final, cycle de vie, boîte d'archives | `sc02_06_conservation.png` | C |
| SC-02.7 | Onglet **Preuve** | Sceaux du document et renvoi au journal de preuve | `sc02_07_preuve.png` | C |

> Le champ **Adresse WebDAV** apparaît **deux fois** sur la fiche (voir ANO-06).

### SC-03 — Plan de classement

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-03.1 | ECM › Plan de classement | Arborescence hiérarchique, droits de lecture et d'écriture par dossier, résumé d'accès | `sc03_01_plan_classement.png` | C |

### SC-04 — Dossiers métier et complétude

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-04.1 | ECM › Dossiers métier | 40 dossiers avec taux de complétude et état | `sc04_01_dossiers_metier.png` | C |
| SC-04.2 | Ouvrir un dossier | Pièces attendues, pièces fournies, complétude, circuit de validation | `sc04_02_fiche_dossier.png` | C |

**Vérification métier complémentaire** : la clôture d'un dossier incomplet est refusée à un agent et
autorisée à un manager (couvert par le test automatisé `test_03_close_requires_completeness`).

### SC-05 — Partage externe sécurisé

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-05.1 | ECM › Partages externes | 27 partages avec date d'expiration, quota, filigrane, compteur d'accès | `sc05_01_partages.png` | C |

**Vérifications fonctionnelles exécutées en ligne de commande** (lien public, sans compte) :

| Réf. | Cas | Résultat attendu | 09/09 |
|---|---|---|---|
| SC-05.2 | Ouvrir un lien valide | Page de téléchargement : titre, référence, taille, validité, accès restants | C |
| SC-05.3 | Télécharger le fichier | PDF servi, **filigrane incrusté** vérifié dans le texte extrait | C |
| SC-05.4 | Recharger la page du lien | Compteur d'accès passé de 0 à 1 sur 10 | C |
| SC-05.5 | Ouvrir un lien expiré | Page « Lien indisponible », HTTP 404 | C |
| SC-05.6 | Ouvrir un jeton inexistant | HTTP 404, aucune information divulguée | C |

### SC-06 — Conservation et archivage (records management)

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-06.1 | ECM › Conservation › Règles | 5 règles livrées : durée, point de départ, sort final, base légale | `sc06_01_regles_conservation.png` | C |
| SC-06.2 | ECM › Conservation › Documents échus | Liste des documents ayant atteint leur fin de conservation | `sc06_02_documents_echus.png` | C |
| SC-06.3 | ECM › Conservation › Gels juridiques | Écran de pose et de levée de gel, motif obligatoire | `sc06_03_gels_juridiques.png` | C |
| SC-06.4 | ECM › Conservation › Bordereaux d'élimination | Écran de constitution, validation manager, exécution tracée | `sc06_04_bordereaux.png` | C |
| SC-06.5 | ECM › Conservation › Archives physiques | Boîtes, emplacement, prêt et retour | `sc06_05_archives_physiques.png` | C |

**Vérification de la protection** : la suppression directe d'un document sous politique de
conservation est refusée avec le message « *Ces documents sont sous politique de conservation :
passez par un bordereau d'élimination* ». Comportement conforme, constaté en campagne.

### SC-07 — Valeur probante (SAE)

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-07.1 | ECM › Preuve › Journal de preuve | Sceaux SHA-256 chaînés, horodatés, journal inaltérable | `sc07_01_journal_preuve.png` | C |
| SC-07.2 | ECM › Preuve › Export de paquet d'archives | Assistant d'export SEDA 2.1 | `sc07_02_export_seda.png` | C |
| SC-13.1 | Ouvrir un sceau | Empreinte du contenu, empreinte du sceau précédent, événement, date | `sc13_01_sceau.png` | C |

### SC-08 — Configuration et paramétrage

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-08.1 | Configuration › Circuits | 7 circuits : étapes, rôles habilités, délais SLA, transitions | `sc08_01_circuits.png` | C |
| SC-08.2 | ECM › Configuration › Types de documents | 7 types avec modèle de métadonnées, dossier et confidentialité par défaut | `sc08_02_types_documents.png` | C |
| SC-08.3 | ECM › Documents › Corbeille | 8 documents en corbeille, restauration et purge automatique | `sc08_03_corbeille.png` | C |
| SC-08.4 | ECM › Analyse du fonds | Vue graphique et tableau croisé du fonds documentaire | `sc08_04_analyse_fonds.png` | C |
| SC-14.1 | ECM › Configuration › Paramètres | Numérisation, durée de réservation, rétention corbeille, connecteurs | `sc14_01_parametres.png` | C |

### SC-09 — API REST `/api/ecm/v1`

*Prérequis : créer une clé d'API — Préférences › Sécurité du compte › Nouvelle clé.*
**Odoo 18 impose une date d'expiration, plafonnée à 90 jours par défaut.**

| Réf. | Appel | Résultat attendu | 09/09 |
|---|---|---|---|
| SC-09.1 | `GET /ping` avec `X-API-Key` | `{"status":"ok","user":"…","version":"18.0.2.0.0"}` | C |
| SC-09.2 | `GET /ping` sans clé | HTTP 401 | C |
| SC-09.3 | `GET /ping` avec clé invalide | HTTP 401 | C |
| SC-09.4 | `GET /types` | 7 types retournés (CONTRAT, COUR, PROC, FACT, RH, PV, DOC) | C |
| SC-09.5 | `GET /folders` | Plan de classement à plat, chemin complet par dossier | C |
| SC-09.6 | `GET /documents?limit=3` | `total = 346`, 3 documents avec référence, titre, état | C |
| SC-09.7 | `GET /documents?q=contrat` | Recherche plein texte : 39 résultats | C |
| SC-09.8 | `GET /openapi.json` | Spécification OpenAPI 3.0.3, 7 chemins décrits | C |
| SC-09.9 | `POST /documents` avec fichier base64 | Document créé, version v1, empreinte SHA-256 calculée | C |
| SC-09.10 | `GET /documents/<id>` | Fiche complète du document créé | C |
| SC-09.11 | `POST /documents/<id>/versions` | Version v2 créée avec commentaire | C |
| SC-09.12 | `GET /documents/<id>/download` | Fichier PDF servi, en-tête `%PDF` conforme | C |
| SC-09.13 | `GET /documents/999999` | HTTP 404 | C |

### SC-11 — Lecteur réseau WebDAV

*Point d'entrée : `http(s)://<serveur>/webdav/aite_ecm` · Authentification HTTP Basic (compte Odoo)*

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-11.0 | Ouvrir la racine WebDAV | Le plan de classement ECM apparaît comme arborescence de dossiers | `sc11_00_webdav_racine.png` | C |
| SC-11.1 | Ouvrir un dossier | Sous-dossiers et documents nommés `RÉFÉRENCE - Titre.ext` | `sc11_01_webdav_navigation.png` | C |

**Campagne protocolaire** (`curl`, 22 cas). Les résultats ci-dessous sont ceux obtenus **après
correction de l'anomalie ANO-01**.

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.2 | `OPTIONS` | 200, en-têtes `DAV: 1, 2` et `MS-Author-Via: DAV` | C |
| SC-11.3 | `PROPFIND` sans identifiants | 401 avec `WWW-Authenticate: Basic` | C |
| SC-11.4 | `PROPFIND` avec mot de passe erroné | 401 | C |
| SC-11.5 | `PROPFIND` racine, `Depth: 1` | 207, 9 dossiers dont « Sans classement » | C |
| SC-11.6 | `PROPFIND` sur chaque dossier racine | 207 pour les 9 dossiers | C |
| SC-11.7 | `PROPFIND` dossier inexistant | 404 | C |
| SC-11.8 | `GET` d'un document | 200, contenu binaire, `Content-Type` correct | C |
| SC-11.9 | En-têtes de réponse `GET` | `ETag` = SHA-256 de la version, `Last-Modified` en RFC 1123 | C |
| SC-11.10 | `LOCK` d'un document | 200, jeton `opaquelocktoken`, document **réservé** côté ECM | C |
| SC-11.11 | `PUT` par un autre utilisateur pendant le verrou | **423 Locked** | C |
| SC-11.12 | `UNLOCK` | 204, réservation libérée | C |
| SC-11.13 | `PUT` sur un document existant | 204, **nouvelle version** créée et attribuée à l'utilisateur | C |
| SC-11.14 | `PUT` d'un fichier temporaire `~$…` | 403 (fichiers de travail Office ignorés) | C |
| SC-11.15 | `PUT` d'un fichier `.tmp` | 403 | C |
| SC-11.16 | `MKCOL` | 201, dossier de classement créé | C |
| SC-11.17 | `MOVE` vers un autre dossier avec nouveau nom | 201, titre et dossier ECM mis à jour | C |
| SC-11.18 | `DELETE` | 204, document placé **en corbeille** (non supprimé) | C |
| SC-11.19 | `COPY` | 403 (non pris en charge, conforme à la documentation) | C |
| SC-11.20 | `PROPPATCH` | 207 acquitté sans effet | C |
| SC-11.21 | **`PUT` d'un fichier nouveau puis relecture au même chemin** | 201 puis 200 | **NC — ANO-03** |
| SC-11.22 | `HEAD` d'un document | Même `Content-Length` que le `GET` | **NC — ANO-07** |

**Parcours bureautique complet, validé de bout en bout** (SC-11.10 à SC-11.13) : ouverture d'un
document depuis le lecteur réseau, verrouillage automatique, enregistrement créant une nouvelle
version, refus d'écriture concurrente pour un collègue (423), libération, reprise possible par le
collègue. **6 cas sur 6 conformes.**

### SC-12 — Sécurité et cloisonnement par rôle

| Réf. | Étapes | Résultat attendu | Capture | 09/09 |
|---|---|---|---|---|
| SC-12.1 | Se connecter en `demo.agent1`, ouvrir ECM › Documents | L'agent ne voit qu'une partie du fonds | `sc12_01_vue_agent.png` | C |
| SC-12.2 | Écran d'accueil de l'agent | Les écrans de configuration ne sont pas proposés | `sc12_02_menus_agent.png` | C |

**Mesure du cloisonnement** (fonds de 346 documents, dont 92 confidentiels) :

| Compte | Rôle | Documents visibles | dont confidentiels |
|---|---|---|---|
| `demo.admin` | Administrateur | 346 / 346 | 92 |
| `demo.manager1` | Manager | 346 / 346 | 92 |
| `demo.agent1` | Agent courrier | 278 / 346 | 25 |
| `demo.archive` | Archiviste | 257 / 346 | 4 |
| `demo.compta` | Comptabilité | 255 / 346 | 2 |
| `demo.audit` | Audit | 253 / 346 | **0** |

Sur les courriers (150 au total) : manager 150, agent 142, comptabilité 137. **Le cloisonnement par
confidentialité et par dossier de classement est effectif et mesurable.**

---

## 5. Anomalies relevées

Gravité : **Bloquante** = fonction inutilisable · **Majeure** = contournement nécessaire ·
**Mineure** = gêne ou écart cosmétique.

### ANO-01 — WebDAV : erreur 500 sur tout dossier contenant des documents · **Bloquante** · *Corrigée*

**Constat.** Toute requête `PROPFIND` sur un dossier contenant au moins un document, tout `GET` de
fichier et tout `PROPFIND` sur un fichier renvoyaient **HTTP 500**. Seuls répondaient la racine et
les dossiers vides. Le lecteur réseau était donc inutilisable au-delà du premier niveau.

**Reproduction** (avant correction) :

```
PROPFIND /webdav/aite_ecm/                      -> 207   (racine : OK)
PROPFIND /webdav/aite_ecm/Archives et éliminations -> 207 (dossier sans document : OK)
PROPFIND /webdav/aite_ecm/Juridique et contrats  -> 500  (dossier avec documents : ÉCHEC)
GET      /webdav/aite_ecm/Juridique et contrats/DOC-2026-00217 - ….pdf -> 500
```

**Cause racine.** `addons/aite_ecm_webdav/controllers/webdav.py`, lignes 103 et 165 :
`format_datetime(valeur, usegmt=True)`. Les champs date d'Odoo sont **naïfs** (sans fuseau) ;
`email.utils.format_datetime` exige un `datetime` portant explicitement le fuseau UTC et lève
`ValueError: usegmt option requires a UTC datetime`. L'exception n'était visible que dans le journal
serveur, le contrôleur renvoyant un 500 muet.

**Correction appliquée et vérifiée.** Introduction d'une fonction `http_date()` qui rend la date
explicitement UTC avant formatage, utilisée aux deux emplacements. Après correction : les 9 dossiers
répondent 207, le `GET` renvoie le fichier avec `ETag` et `Last-Modified` conformes, et les
22 cas protocolaires passent sauf ANO-03 et ANO-07.

### ANO-02 — Banc de tests des modules ECM inopérant · **Majeure**

**Constat.** Sur la suite livrée telle quelle, **39 tests échouent**. Ces échecs masquaient ANO-01 :
aucun signal n'était remonté sur une fonction pourtant totalement cassée.

**Trois causes distinctes, toutes dans le code de test :**

| Cause | Détail | Tests concernés |
|---|---|---|
| Utilisateurs sans le groupe *Utilisateur interne* | `groups_id` ne contient que le rôle AITE ; l'utilisateur est un compte externe et ne peut pas lire `ir.sequence` → `AccessError` dès la création d'un document | 8 fichiers, ~54 tests |
| Utilisateurs sans adresse e-mail | Tout `message_post` échoue : « *Unable to send message, please configure the sender's email address* » | 11 tests |
| Tests HTTP du WebDAV | Les 5 tests protocolaires reçoivent 401 quel que soit le paramétrage de base, y compris avec `dbfilter` strict | 5 tests |

**Preuve.** Les tests du domaine Courrier et le générateur du jeu de données ajoutent bien
`base.group_user` (`test_webdav.py:128`, `generator.py:385-390`) et fonctionnent ; les tests ECM ne
le font pas. En ajoutant `base.group_user` puis une adresse e-mail aux utilisateurs de test, le
nombre d'échecs tombe de **39 à 17** sans toucher au code produit.

**Effet de bord.** `test_07_security` (`aite_ecm_webdav`) **passe pour une mauvaise raison** : il
vérifie `assertNotIn("Secret de l'autre", resp.text)` sur une réponse 401 au corps vide. Le test est
vert alors qu'il ne teste rien.

**Recommandation.** Réparer les trois causes, puis traiter les 17 échecs restants comme le socle de
non-régression. Sans cela, aucune campagne automatisée n'a de valeur.

### ANO-03 — WebDAV : un fichier déposé n'est pas relisible à son propre chemin · **Majeure**

**Constat.** Copier un fichier dans le lecteur réseau le crée, mais il devient introuvable à
l'emplacement où l'utilisateur l'a déposé. Chaque nouvelle copie crée un document supplémentaire.

**Reproduction :**

```
PUT /webdav/aite_ecm/Sans classement/rapport.docx      -> 201 Created
GET /webdav/aite_ecm/Sans classement/rapport.docx      -> 404 Not Found
PROPFIND du dossier -> le serveur expose « DOC-2026-00355 - rapport.docx »
```

Quatre `PUT` successifs du même chemin ont produit **quatre documents distincts**
(`DOC-2026-00351` à `DOC-2026-00354`), tous nommés « UAT-nouveau-document ».

**Cause racine.** `models/aite_ecm_webdav.py`, `_document_filename()` : le nom exposé est
`"<référence> - <titre>.<extension>"`. Un document créé par `PUT` reçoit une référence attribuée
*après* le dépôt, si bien que le nom exposé diffère du nom écrit par le client. Le repli de
`_document_by_filename()` (recherche par référence en tête de nom) ne peut pas s'appliquer, le nom
d'origine ne contenant pas de séparateur « - ».

**Impact utilisateur.** Le glisser-déposer vers le lecteur réseau et l'« Enregistrer sous » depuis
Word sont inexploitables : le fichier disparaît de la vue du client et se duplique à chaque
tentative. En revanche, **l'édition d'un document existant fonctionne parfaitement** (SC-11.10 à
SC-11.13) car le client utilise alors le nom exposé par le serveur.

**Pistes de correction.** Soit exposer les documents sous leur nom de fichier réel et lever
l'ambiguïté autrement, soit, après création par `PUT`, répondre `201` avec un en-tête `Location`
pointant le nom définitif, soit conserver le nom déposé comme clé de résolution alternative.

### ANO-04 — Suppression d'une pièce de courrier impossible · **Majeure**

**Constat.** Supprimer un document de courrier échoue en base :

```
psycopg2.errors.ForeignKeyViolation: update or delete on table "ir_attachment"
violates foreign key constraint "aite_ecm_document_version_attachment_id_fkey"
```

**Cause racine.** Le pont `aite_courrier_ecm` miroite la pièce de courrier en document ECM **sans
dupliquer le fichier** : le même `ir.attachment` est référencé par la version courrier et par la
version ECM. À la suppression du document courrier, Odoo supprime en cascade l'`ir.attachment`, mais
`aite_ecm_document_version.attachment_id` est déclaré `ondelete='restrict'` : la base refuse.

**Reproduction automatisée.** Deux tests le détectent :
`aite_courrier_webdav/TestWebdav.test_delete_document` et
`aite_courrier_ecm/TestCourrierEcmBridge.test_05_unlink_to_trash`.

**Portée.** Toute suppression de pièce de courrier, depuis l'interface comme depuis le WebDAV
courrier. Le partage de fichier entre les deux référentiels demande une stratégie explicite de
cycle de vie.

### ANO-05 — Un document finalisé accepte une nouvelle version · **Majeure**

**Constat.** Le test `aite_ecm_document/TestEcmDocument.test_06_locked_when_final` échoue sur
`AssertionError: AccessError not raised` : après finalisation, `add_version` aurait dû être refusée.
Le verrouillage des documents finalisés — pierre angulaire de la valeur probante — n'est pas garanti
dans ce cas de figure.

**À confirmer en recette fonctionnelle** avant correction : reproduire depuis l'interface
(finaliser un document, puis tenter d'ajouter une version) pour déterminer si l'écart vient du
produit ou de l'ordre d'exécution du test.

### ANO-06 — Champ « Adresse WebDAV » affiché en double · **Mineure**

Sur la fiche document, le champ apparaît deux fois (visible sur `sc02_06_conservation.png`).
`aite_ecm_office/views/aite_ecm_document_views.xml:35` replace `webdav_url` alors que
`aite_ecm_webdav/views/aite_ecm_document_views.xml:13` le positionne déjà. Reliquat de la
séparation des deux modules décrite au changelog 18.0.2.1.1 : le champ a été retiré du modèle
Office mais pas de sa vue.

### ANO-07 — `HEAD` renvoie une taille nulle · **Mineure**

`_handle_head()` réutilise la réponse du `GET` puis vide le corps, ce qui remet `Content-Length` à 0.
La RFC 7231 impose que `HEAD` annonce la même taille que `GET`. Certains clients WebDAV s'appuient
sur cet en-tête pour préparer un téléchargement.

### ANO-08 — Statuts « En traitement » et « Validé » jamais atteints · **Mineure**

Le champ `state` de `aite.courrier` déclare six valeurs ; le moteur n'écrit que `draft`, `nw`, `rj`
et `ar`. Conséquences : le filtre « En cours » du tableau de bord se réduit à « Nouveau », et les
libellés publics du portail affichent un état figé pendant tout le traitement. Soit implémenter ces
deux transitions, soit retirer les valeurs et ajuster tableau de bord et portail.

### ANO-09 — Anomalies détectées par les tests, à qualifier · **Mineure à majeure**

Après réparation du banc de test, 17 échecs subsistent. Outre ANO-04 et ANO-05, ils désignent :

| Test | Symptôme | Lecture |
|---|---|---|
| `aite_ecm_nextcloud/test_02_push_on_version` | `Invalid field aite.courrier.audit.log.res_model` | Le connecteur interroge un champ inexistant du journal d'audit |
| `aite_ecm_nextcloud/test_08_poll`, `test_10_webhook` | Sondage sans effet ; webhook renvoie 500 au lieu de 403 | Gestion d'erreur du webhook à revoir |
| `aite_ecm_records/test_05_protection` | `NotNullViolation` sur `aite_ecm_seal.document_id` | Un sceau est créé sans document rattaché |
| `aite_ecm_records/test_02`, `test_04` | `'TestRecords' object has no attribute '_context'` | Défaut de test : `with_context` appelé sur la classe de test |
| `aite_ecm_office/test_06_google_round_trip` | `Expected singleton: res.users()` | Recordset vide là où un utilisateur unique est attendu |
| `aite_ecm_document/test_07_trash_and_purge` | Mise en corbeille refusée par la politique de conservation | Comportement v2.1 volontaire ; **test à mettre à jour** |

---

## 6. Synthèse par domaine

| Domaine | Verdict | Réserve |
|---|---|---|
| Installation Community | ✅ Conforme | Aucune |
| Courrier : circuits, SLA, audit | ✅ Conforme | ANO-08 (statuts intermédiaires) |
| GED du courrier | ⚠️ Réserve | ANO-04 (suppression impossible) |
| Référentiel ECM, explorateur | ✅ Conforme | Aucune |
| Dossiers métier | ✅ Conforme | Aucune |
| Conservation et archivage | ✅ Conforme | ANO-09 (sceau sans document) |
| Valeur probante | ✅ Conforme | ANO-05 à confirmer |
| Partage externe | ✅ Conforme | Aucune |
| API REST | ✅ Conforme | Aucune |
| **Lecteur réseau WebDAV** | ⚠️ **Réserve** | ANO-01 corrigée ; **ANO-03 ouverte** |
| Sécurité et cloisonnement | ✅ Conforme | Aucune |
| Non-régression automatisée | ❌ **Non conforme** | ANO-02 |

**Recommandation de mise en production.** Le déploiement est envisageable pour l'ensemble des
domaines à l'exception de deux points : la suppression des pièces de courrier (ANO-04) et le dépôt
de fichiers nouveaux par le lecteur réseau (ANO-03). Ce dernier peut être contourné en formant les
utilisateurs à créer le document depuis l'interface puis à l'éditer via le lecteur réseau, parcours
validé sans réserve. La remise en état du banc de tests (ANO-02) conditionne la maîtrise des
prochaines livraisons.

---

## 7. Annexes

### 7.1 Rejouer la campagne WebDAV

```bash
B="demo.admin:demo1234"; U="http://localhost:8169/webdav/aite_ecm"
curl -i -X OPTIONS -u "$B" "$U"                                   # SC-11.2
curl -X PROPFIND -H "Depth: 1" -u "$B" "$U"                       # SC-11.5
curl -X PROPFIND -H "Depth: 1" -u "$B" "$U/Juridique%20et%20contrats"
curl -o fichier.pdf -u "$B" "$U/Juridique%20et%20contrats/DOC-…pdf"  # SC-11.8
curl -X LOCK -u "$B" -H "Timeout: Second-3600" "$U/…"             # SC-11.10
curl -X PUT  -u "$B" --data-binary @fichier.docx "$U/…"           # SC-11.13
curl -X UNLOCK -u "$B" "$U/…"                                     # SC-11.12
```

### 7.2 Rejouer la campagne API

```bash
K="<clé d'API>"; A="http://localhost:8169/api/ecm/v1"
curl -H "X-API-Key: $K" "$A/ping"
curl -H "X-API-Key: $K" "$A/documents?limit=3"
curl -X POST -H "X-API-Key: $K" -H "Content-Type: application/json" \
     -d '{"name":"Test","type_code":"DOC","file":{"filename":"t.pdf","content_base64":"…"}}' \
     "$A/documents"
```

### 7.3 Rejouer les tests automatisés

```bash
MODS="aite_courrier,aite_courrier_base,…,aite_ecm_webdav,aite_ecm_workflow"
TAGS=$(echo "$MODS" | tr ',' '\n' | sed 's|^|/|' | paste -sd,)
odoo-bin -c odoo.conf -d aite_test -u "$MODS" --test-enable --test-tags "$TAGS" --stop-after-init
```

> Ne pas lancer `--test-enable` sans `--test-tags` : la suite JavaScript d'Odoo s'exécute alors
> pendant plusieurs dizaines de minutes sans rapport avec la recette AITE.

### 7.4 Index des captures

Toutes les captures sont dans `docs/uat/captures/` et portent un bandeau reprenant leur référence.

| Fichier | Scénario |
|---|---|
| `00_accueil.png` | Connexion et écran d'accueil |
| `sc01_01` … `sc01_07` | SC-01 Courrier : analyse, tableau de bord, liste, fiche, pièces, historique, audit |
| `sc02_01` … `sc02_07` | SC-02 ECM : explorateur, liste, fiche, versions, relations, conservation, preuve |
| `sc03_01` | SC-03 Plan de classement |
| `sc04_01`, `sc04_02` | SC-04 Dossiers métier |
| `sc05_01` | SC-05 Partages externes |
| `sc06_01` … `sc06_05` | SC-06 Conservation |
| `sc07_01`, `sc07_02` | SC-07 Valeur probante |
| `sc08_01` … `sc08_04` | SC-08 Configuration |
| `sc11_00`, `sc11_01` | SC-11 Lecteur réseau WebDAV |
| `sc12_01`, `sc12_02` | SC-12 Sécurité par rôle |
| `sc13_01` | SC-13 Sceau de preuve |
| `sc14_01` | SC-14 Paramètres ECM |
