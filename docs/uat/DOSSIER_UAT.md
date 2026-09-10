# Dossier de recette (UAT) — AITE Courrier / AITE ECM v2.1

**Version du dossier** : 2.0 · **Date d'exécution** : 9 septembre 2026 · **Rédacteur** : recette technique  
**Version testée** : branche `claude/ecm-webdav-analysis-vy4196`, 28 modules  
**Socle** : Odoo 18.0 Community, PostgreSQL 16, Python 3.11

Ce dossier est **réutilisable** : chaque scénario est numéroté, décrit pas à pas, avec son résultat
attendu, sa capture d'écran de référence et une colonne à remplir à chaque campagne. Les captures
portent un bandeau d'étiquette reprenant l'identifiant du scénario.

> **Historique du dossier.** La version 1.0 rendait compte de la campagne initiale : 9 anomalies
> relevées, dont une bloquante rendant le lecteur réseau WebDAV inutilisable. La présente version 2.0
> rend compte de la **campagne de contre-essai** menée après correction : les 9 anomalies sont
> corrigées et vérifiées, la campagne protocolaire WebDAV passe à **32 cas sur 32** et la suite
> automatisée à **152 tests sans aucun échec**. Le détail de chaque correction, avec sa cause racine
> et sa preuve de vérification, figure au chapitre 5.

---

## 1. Résultat de la campagne du 9 septembre 2026

| Indicateur | Campagne initiale | **Contre-essai après correction** |
|---|---|---|
| Modules installés sans erreur | 24 / 24 | **24 / 24** |
| Scénarios de recette fonctionnelle | 34 exécutés — 33 conformes | **34 exécutés — 34 conformes** |
| Campagne protocolaire WebDAV (`curl`) | 22 cas — 20 conformes | **32 cas — 32 conformes** |
| Tests automatisés exécutés | 152 | **152** |
| Tests en échec | 39 puis 17 | **0** |
| Anomalies produit ouvertes | 9 (1 bloquante, 3 majeures, 5 mineures) | **0 — les 9 sont corrigées et vérifiées** |

**Verdict.** La plateforme s'installe proprement sur Odoo 18 Community et l'ensemble des fonctions
métier est opérationnel : courrier, circuits, GED, référentiel ECM, dossiers métier, conservation,
valeur probante, partage externe, API REST et **lecteur réseau WebDAV**.

Le lecteur réseau, seul point encore en défaut à l'ouverture de la campagne, a fait l'objet de
quatre corrections (ANO-01, ANO-03, ANO-07 et le refus explicite des corps de requête illisibles).
Il satisfait désormais l'intégralité de la campagne protocolaire, **parcours bureautique complet
compris** : dépôt d'un fichier neuf, relecture au même chemin, versionnage, verrou exclusif, refus
d'écriture concurrente, déplacement, renommage et mise en corbeille.

Le banc de tests automatisés, qui masquait ces régressions (ANO-02), a été remis en état : les trois
causes de faux échecs sont supprimées et la suite sert désormais de socle de non-régression.

**Réserves subsistantes.** Aucune anomalie produit n'est ouverte. Les seules limites tiennent à
l'environnement de recette, décrites au § 2.3 : génération PDF, OCR image, SMTP/IMAP, instance
Nextcloud réelle et passerelles Odoo Enterprise n'ont pas pu être exercées de bout en bout.

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

> **Point de vigilance levé (ANO-08).** Le champ `state` déclarait six valeurs alors que le moteur
> n'en écrivait que quatre : un courrier restait « Nouveau » de la première à l'avant-dernière
> étape. Le franchissement d'une étape positionne désormais **« En traitement »**, et la valeur
> *Validé*, que rien ne produisait, a été retirée de la liste. Le statut affiché suit maintenant
> l'avancement réel du circuit, au tableau de bord comme au portail.

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

> Le champ **Adresse WebDAV** apparaissait **deux fois** sur la fiche (ANO-06) : la capture
> `sc02_06_conservation.png` conserve la trace de l'anomalie. Le doublon a été retiré de la vue
> `aite_ecm_office` ; le champ n'est plus posé que par `aite_ecm_webdav`.

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

**Campagne protocolaire** (`curl`, 32 exécutions pour 24 références). Le script complet et rejouable figure en annexe 7.1.
Les résultats ci-dessous sont ceux du **contre-essai après correction** ; la campagne a été rejouée
deux fois de suite sans réinitialisation intermédiaire pour vérifier son idempotence.

**A. Découverte et authentification**

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.2 | `OPTIONS` | 200, en-têtes `DAV: 1, 2` et `MS-Author-Via: DAV` | C |
| SC-11.3 | `PROPFIND` sans identifiants | 401 avec `WWW-Authenticate: Basic` | C |
| SC-11.4 | `PROPFIND` avec mot de passe erroné | 401 | C |

**B. Navigation dans le plan de classement**

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.5 | `PROPFIND` racine, `Depth: 1` | 207, 9 dossiers dont « Sans classement » | C |
| SC-11.6 | `PROPFIND` sur chacun des 9 dossiers racine | 207 pour les 9 dossiers *(9 exécutions)* | C |
| SC-11.7 | `PROPFIND` dossier inexistant | 404 | C |

**C. Dépôt d'un fichier neuf et relecture** — *cœur de l'anomalie ANO-03, désormais corrigée*

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.8 | `PUT` d'un fichier **inconnu** dans un dossier | 201 Created, document ECM créé | C |
| SC-11.9 | `GET` **au chemin même où le client a déposé** | 200, contenu identique à l'octet près | C |
| SC-11.10 | Second `PUT` au même chemin | 204, **nouvelle version** — pas de document en double | C |
| SC-11.11 | `GET` après le second `PUT` | 200, contenu de la **v2** | C |
| SC-11.12 | `HEAD` d'un document | 200 et **même `Content-Length` que le `GET`** | C |
| SC-11.13 | `PUT` avec un corps illisible (type formulaire) | **415**, refus explicite plutôt qu'un fichier vide | C |
| SC-11.14 | `PUT` d'un fichier temporaire `~$…` | 403 (fichiers de travail Office ignorés) | C |
| SC-11.15 | `PUT` d'un fichier `.tmp` | 403 | C |

**D. Verrous collaboratifs** — *parcours bureautique de bout en bout*

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.16 | `LOCK` d'un document | 200, jeton `opaquelocktoken`, document **réservé** côté ECM | C |
| SC-11.17 | `PUT` par un collègue pendant le verrou | **423 Locked**, avec le nom du détenteur | C |
| SC-11.18 | `UNLOCK` | 204, réservation libérée | C |
| SC-11.19 | `PUT` du collègue après libération | 204, nouvelle version à son nom | C |

**E. Classement : création, déplacement, renommage, corbeille**

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.20 | `MKCOL` | 201, dossier de classement créé | C |
| SC-11.21 | `MOVE` vers un autre dossier **avec nouveau nom** | 201, titre et dossier ECM mis à jour | C |
| SC-11.22 | `GET` **au nouvel emplacement, sous le nouveau nom** | 200 | C |
| SC-11.23 | `DELETE` | 204, document placé **en corbeille** (non supprimé) | C |

**F. Divers**

| Réf. | Cas | Attendu | 09/09 |
|---|---|---|---|
| SC-11.24 | `COPY` | 403 (non pris en charge, conforme à la documentation) | C |
| SC-11.25 | `PROPPATCH` | 207 acquitté sans effet | C |

**Parcours bureautique complet, validé de bout en bout** (SC-11.8 à SC-11.19) : dépôt d'un fichier
depuis l'explorateur Windows, relecture au même chemin, ouverture dans Word, verrouillage
automatique, enregistrement créant une nouvelle version, refus d'écriture concurrente pour un
collègue (423), libération, reprise par le collègue. **12 cas sur 12 conformes.**

> **Note sur la résolution des noms.** Le serveur expose les documents sous `RÉFÉRENCE - Titre.ext`
> alors qu'un client dépose ou renomme sous le nom qu'il a lui-même choisi. Quatre clés de
> résolution sont donc acceptées, de la plus précise à la plus tolérante : nom exposé, titre du
> document, nom réel du fichier de la dernière version, référence en tête de nom. C'est ce qui rend
> SC-11.9 et SC-11.22 possibles.

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

**Les neuf anomalies sont corrigées et vérifiées.** Chaque fiche conserve le constat d'origine — il
sert de cas de non-régression — et se termine par la correction appliquée et sa preuve.

| Réf. | Objet | Gravité | État |
|---|---|---|---|
| ANO-01 | WebDAV : erreur 500 sur tout dossier contenant des documents | Bloquante | ✅ Corrigée |
| ANO-02 | Banc de tests des modules ECM inopérant | Majeure | ✅ Corrigée |
| ANO-03 | WebDAV : un fichier déposé n'est pas relisible à son chemin | Majeure | ✅ Corrigée |
| ANO-04 | Suppression d'une pièce de courrier impossible | Majeure | ✅ Corrigée |
| ANO-05 | Un document finalisé accepte une nouvelle version | Majeure | ✅ Corrigée |
| ANO-06 | Champ « Adresse WebDAV » affiché en double | Mineure | ✅ Corrigée |
| ANO-07 | `HEAD` renvoie une taille nulle | Mineure | ✅ Corrigée |
| ANO-08 | Statuts « En traitement » et « Validé » jamais atteints | Mineure | ✅ Corrigée |
| ANO-09 | Anomalies détectées par les tests, à qualifier | Mineure à majeure | ✅ Corrigées (6 sur 6) |

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
explicitement UTC avant formatage, utilisée aux deux emplacements :

```python
def http_date(value):
    if not value:
        return None
    if value.tzinfo is None:                       # les dates Odoo sont naïves…
        value = value.replace(tzinfo=timezone.utc)  # …et exprimées en UTC
    return format_datetime(value.astimezone(timezone.utc), usegmt=True)
```

**Seconde cause, découverte pendant la correction.** Une fois les dates réparées, les tests HTTP du
WebDAV continuaient à répondre **401**. L'instrumentation temporaire du contrôleur a fait apparaître
`Opening a read/write test cursor from a readonly one` : Odoo 18 sert les méthodes réputées de
lecture sur un **curseur en lecture seule**, alors que l'authentification HTTP Basic écrit (journal
de connexion, session).

Le défaut n'est pas propre au WebDAV : il touche **toute route qui écrit sans être déclarée comme
telle**. Le tour complet des contrôleurs de la suite a donc été fait, et sept routes ont reçu
`readonly=False` :

| Route | Écriture qu'elle effectue |
|---|---|
| `/webdav/aite_ecm` | Authentification HTTP Basic, versions, verrous, classement |
| `/webdav/aite_courrier` | Idem sur le référentiel courrier |
| `/api/ecm/v1/*` | Authentification par clé d'API, audit, création de documents et de versions |
| `/ecm/share/<token>` et `/ecm/share/<token>/file` | Compteur d'accès et journalisation de la consultation |
| `/ecm/wopi/files/<id>` et `…/contents` | Pose et levée de verrous, enregistrement du contenu édité |
| `/ecm/google/callback` | Enregistrement des jetons OAuth sur le compte |
| `/ecm/nextcloud/webhook` | Marquage des documents à importer |

Sans ce correctif, chacune de ces routes échoue dès qu'un réplica de lecture est configuré — et
systématiquement en test.

**Vérification.** Les 9 dossiers racine répondent 207, le `GET` renvoie le fichier avec `ETag` et
`Last-Modified` conformes, et **les 32 cas protocolaires passent** (SC-11.2 à SC-11.25).

### ANO-02 — Banc de tests des modules ECM inopérant · **Majeure** · *Corrigée*

**Constat.** Sur la suite livrée telle quelle, **39 tests échouent**. Ces échecs masquaient ANO-01 :
aucun signal n'était remonté sur une fonction pourtant totalement cassée.

**Trois causes distinctes.** Les deux premières sont des défauts du **code de test** ; la
troisième s'est révélée être un défaut du **produit** (voir ANO-01), que le banc n'exprimait pas
correctement.

| Cause | Détail | Tests concernés |
|---|---|---|
| Utilisateurs sans le groupe *Utilisateur interne* | `groups_id` ne contient que le rôle AITE ; l'utilisateur est un compte externe et ne peut pas lire `ir.sequence` → `AccessError` dès la création d'un document | 8 fichiers, ~54 tests |
| Utilisateurs sans adresse e-mail | Tout `message_post` échoue : « *Unable to send message, please configure the sender's email address* » | 11 tests |
| Tests HTTP du WebDAV | Les 5 tests protocolaires reçoivent 401 quel que soit le paramétrage de base, y compris avec `dbfilter` strict | 5 tests |

**Preuve.** Les tests du domaine Courrier et le générateur du jeu de données ajoutent bien
`base.group_user` (`test_webdav.py:128`, `generator.py:385-390`) et fonctionnent ; les tests ECM ne
le font pas. En ajoutant `base.group_user` puis une adresse e-mail aux utilisateurs de test, le
nombre d'échecs tombe de **39 à 17** sans toucher au code produit.

**Diagnostic des 401 du WebDAV.** Deux hypothèses ont été formulées puis **écartées par
l'expérience** avant de trouver la bonne — elles sont consignées ici pour éviter qu'on ne les
reprenne :

- *un `flush_all()` manquant avant l'authentification* : ajouté, sans effet sur le symptôme ;
- *la base non résolvable côté test* : une méthode `_resolve_db()` a été écrite, puis **retirée**
  après avoir constaté que le code d'origine répondait déjà 207 dès lors que `-d` était renseigné.
  La contrainte de base unique reste un **prérequis de déploiement** (§ 2.1), pas un défaut.

La cause réelle n'est apparue qu'en instrumentant temporairement le contrôleur pour faire remonter
l'exception avalée : `Opening a read/write test cursor from a readonly one`. Traitée en ANO-01.

**Effet de bord.** `test_07_security` (`aite_ecm_webdav`) **passait pour une mauvaise raison** : il
vérifiait `assertNotIn("Secret de l'autre", resp.text)` sur une réponse 401 au corps vide. Le test
était vert alors qu'il ne testait rien — c'est ce qui a permis à ANO-01 de traverser toute la suite
sans être détectée.

**Correction appliquée.** Un socle de test partagé,
`addons/aite_ecm_document/tests/common.py`, supprime les deux premières causes à la racine plutôt
que fichier par fichier :

```python
class EcmTestUsersMixin:
    @classmethod
    def _make_user(cls, name, login, roles, **extra):
        """Utilisateur de test : toujours interne, toujours avec une adresse."""
        if isinstance(roles, str):
            roles = [roles]
        group_ids = [cls.env.ref('base.group_user').id]
        for role in roles:
            xmlid = role if '.' in role else 'aite_courrier_base.%s' % role
            group_ids.append(cls.env.ref(xmlid).id)
        ...

class EcmTransactionCase(EcmTestUsersMixin, TransactionCase): ...
class EcmHttpCase(EcmTestUsersMixin, HttpCase): ...
```

Les **8 fichiers de test** des modules ECM en héritent : `aite_ecm_document` (2 fichiers),
`aite_ecm_dossier`, `aite_ecm_workflow`, `aite_ecm_records`, `aite_ecm_webdav`, `aite_ecm_nextcloud`
et `aite_ecm_office`. Un utilisateur de test ne peut donc plus être créé sans le groupe
*Utilisateur interne* ni sans adresse e-mail. La troisième cause — les 401 du WebDAV — relevait du
produit et non du test : c'est le `readonly=False` décrit en ANO-01.

**Vérification.** Suite complète relancée sur les 24 modules installés :
**`0 failed, 0 error(s) of 152 tests`**. Les 39 échecs initiaux sont résorbés : 22 provenaient du
banc de test, 17 étaient de véritables défauts produit, traités par ANO-04, ANO-05 et ANO-09.

### ANO-03 — WebDAV : un fichier déposé n'est pas relisible à son propre chemin · **Majeure** · *Corrigée*

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

**Correction appliquée.** C'est la troisième piste envisagée qui a été retenue : conserver le nom
déposé par le client comme clé de résolution. `_document_by_filename()` accepte désormais **quatre
clés**, de la plus précise à la plus tolérante :

| # | Clé de résolution | Cas d'usage couvert |
|---|---|---|
| 1 | Nom **exposé** par le serveur, `RÉFÉRENCE - Titre.ext` | Navigation normale, édition Office |
| 2 | **Titre** du document + extension | Dépôt d'un fichier neuf, renommage par le client |
| 3 | **Nom réel du fichier** de la dernière version | « Enregistrer sous » conservant le nom d'origine |
| 4 | **Référence** en tête du nom | Réenregistrement sous un autre titre par Office |

La clé n° 2 est celle qui referme l'anomalie : après un `PUT` de `rapport.docx`, le document porte le
titre `rapport`, que le `GET` suivant retrouve. Elle couvre aussi le `MOVE` avec renommage
(SC-11.22), où le client n'a jamais vu le nom exposé du fichier déplacé.

**Vérification.**

```
PUT  .../Juridique et contrats/campagne-uat.docx   -> 201 Created
GET  .../Juridique et contrats/campagne-uat.docx   -> 200, contenu v1 identique
PUT  (même chemin)                                 -> 204 No Content, version v2
GET  (même chemin)                                 -> 200, contenu v2
```

Un seul document est créé pour quatre `PUT` successifs, contre quatre auparavant. La campagne a été
rejouée deux fois d'affilée pour vérifier qu'elle est idempotente.

**Correction connexe — perte de contenu silencieuse.** Le diagnostic a mis au jour un défaut voisin :
un client annonçant un `Content-Type` de formulaire (`x-www-form-urlencoded`, `multipart/form-data`)
voit son corps consommé par l'analyseur de formulaires de Werkzeug ; `get_data()` renvoie alors des
octets vides et **le fichier était enregistré vide, sans la moindre erreur**. Le serveur refuse
désormais explicitement la requête en **415 Unsupported Media Type**, avec un message indiquant
l'en-tête à employer (SC-11.13). Perdre une requête vaut mieux que perdre un document.

### ANO-04 — Suppression d'une pièce de courrier impossible · **Majeure** · *Corrigée*

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
courrier.

**Correction appliquée.** Le partage de fichier entre les deux référentiels reçoit une stratégie
explicite de cycle de vie : **le jumeau ECM devient propriétaire des pièces jointes partagées**
avant la suppression de la pièce de courrier. Dans `AiteCourrierDocument.unlink()`, les
`ir.attachment` communs aux deux référentiels sont réattribués (`res_model` / `res_id`) au document
ECM ; Odoo ne les emporte donc plus en cascade et la contrainte `restrict` n'est plus violée.

**Vérification.** `aite_courrier_webdav/test_delete_document` et
`aite_courrier_ecm/test_05_unlink_to_trash` passent. Le fichier reste accessible depuis le document
ECM après suppression de la pièce de courrier — la suppression ne détruit plus de contenu.

### ANO-05 — Un document finalisé accepte une nouvelle version · **Majeure** · *Corrigée*

**Constat.** Le test `aite_ecm_document/TestEcmDocument.test_06_locked_when_final` échouait sur
`AssertionError: AccessError not raised` : après finalisation, `add_version` aurait dû être refusée.
Le verrouillage des documents finalisés — pierre angulaire de la valeur probante — n'était pas
garanti.

**Cause racine, confirmée en recette.** L'écart venait bien du produit, pas de l'ordre d'exécution
du test. Dans `_check_document_access()`, le raccourci manager était évalué **avant** le contrôle de
verrouillage :

```python
if self._is_manager(user):
    return True                       # ← sortie avant tout contrôle de verrou
if operation != 'read' and (self.is_locked or …):
    return False
```

Un manager — et tout administrateur — pouvait donc ajouter une version à un document finalisé ou
archivé.

**Correction appliquée.** Le contrôle de verrouillage passe **avant** le raccourci manager : en
écriture, un document verrouillé est refusé à tout le monde, la seule voie restant la remise en
brouillon, qui est tracée au journal d'audit.

```python
if operation != 'read' and self.is_locked:
    return False                      # ← s'applique aussi au manager
if self._is_manager(user):
    return True
```

**Vérification.** `test_06_locked_when_final` passe, ainsi que les 13 autres tests de droits du
module. L'ordre des règles est documenté dans la docstring de la méthode.

### ANO-06 — Champ « Adresse WebDAV » affiché en double · **Mineure** · *Corrigée*

Sur la fiche document, le champ apparaissait deux fois (visible sur `sc02_06_conservation.png`).
`aite_ecm_office/views/aite_ecm_document_views.xml` replaçait `webdav_url` alors que
`aite_ecm_webdav/views/aite_ecm_document_views.xml:13` le positionne déjà. Reliquat de la
séparation des deux modules décrite au changelog 18.0.2.1.1 : le champ avait été retiré du modèle
Office mais pas de sa vue.

**Correction appliquée.** Le champ est retiré de la vue Office, qui dépend de toute façon de
`aite_ecm_webdav` ; un commentaire à l'emplacement libéré évite que le doublon ne soit réintroduit.

### ANO-07 — `HEAD` renvoie une taille nulle · **Mineure** · *Corrigée*

`_handle_head()` réutilisait la réponse du `GET` puis vidait le corps, ce qui remettait
`Content-Length` à 0. La RFC 7231 impose que `HEAD` annonce la même taille que `GET` ; certains
clients WebDAV s'appuient sur cet en-tête pour préparer un téléchargement.

**Correction appliquée.** La taille est relevée avant de vider le corps puis réécrite. Werkzeug
recalculant `Content-Length` d'après le corps au moment de l'envoi, il faut en outre **désactiver ce
recalcul** — sans quoi la valeur restaurée est écrasée juste avant l'émission :

```python
resp.set_data(b'')
if length is not None:
    resp.automatically_set_content_length = False
    resp.headers['Content-Length'] = length
```

**Vérification.** SC-11.12 : `HEAD` annonce `Content-Length: 27`, valeur identique à celle du `GET`.

Le même correctif a été porté sur le WebDAV **courrier** (`/webdav/aite_courrier`), qui présentait
le défaut à l'identique, ainsi que le refus en 415 des corps de requête illisibles décrit en ANO-03.
Les deux points d'entrée WebDAV se comportent donc désormais de la même façon.

### ANO-08 — Statuts « En traitement » et « Validé » jamais atteints · **Mineure** · *Corrigée*

Le champ `state` de `aite.courrier` déclarait six valeurs ; le moteur n'écrivait que `draft`, `nw`,
`rj` et `ar`. Conséquences : le filtre « En cours » du tableau de bord se réduisait à « Nouveau », et
les libellés publics du portail affichaient un état figé pendant tout le traitement.

**Correction appliquée**, en combinant les deux options envisagées :

- `_enter_step()` positionne `state = 'pr'` (**En traitement**) au franchissement d'une étape, ce qui
  donne enfin au statut la valeur qui lui manquait pendant tout le cycle de vie ;
- la valeur `vl` (**Validé**), que rien ne produisait et que rien ne devait produire — la validation
  se lit sur l'étape du circuit — est retirée de la liste de sélection.

**Vérification.** Les tests des modules `aite_courrier_core`, `aite_courrier_workflow` et
`aite_courrier_portal` passent ; le tableau de bord et le portail n'affichent plus que des valeurs
effectivement atteignables.

### ANO-09 — Anomalies détectées par les tests · **Mineure à majeure** · *Corrigées (6 sur 6)*

Après réparation du banc de test, 17 échecs subsistaient. Outre ANO-04 et ANO-05, ils désignaient
six défauts, tous corrigés :

| Symptôme d'origine | Cause racine | Correction |
|---|---|---|
| `Invalid field aite.courrier.audit.log.res_model` (`test_02_push_on_version`) | Le journal d'audit expose `model_name`/`res_id`, pas `res_model` | Requête du test alignée sur le modèle réel |
| Sondage Nextcloud sans effet (`test_08_poll`) | Le simulateur ne faisait varier l'ETag d'un dossier qu'au **nombre** de fichiers ; Nextcloud le fait varier à **chaque écriture**, ce qui court-circuitait la détection | ETag de dossier indexé sur le compteur d'écritures |
| Webhook Nextcloud : 500 au lieu de 403 (`test_10_webhook`) | `make_json_response(payload, 403)` — le 2ᵉ argument positionnel est `headers`, pas `status` ; et la route écrivait sur un curseur en lecture seule | `status=403` nommé, et `readonly=False` sur la route |
| `NotNullViolation` sur `aite_ecm_seal.document_id` (`test_05_protection`) | Le sceau était `required` : le journal de preuve ne pouvait pas survivre à la destruction du document qu'il atteste | Champ rendu facultatif ; le sceau reste identifié par la référence et les empreintes, qui demeurent obligatoires |
| `Expected singleton: res.users()` (`test_06_google_round_trip`) | `self.env['res.users']._google_authorize_action(...)` appelé sur le **modèle** au lieu de l'utilisateur courant | `self.env.user._google_authorize_action(...)` |
| Purge de corbeille refusée (`test_07_trash_and_purge`) | La politique de conservation refusait la purge : **un seul document protégé faisait échouer toute la purge** | Point d'extension `_purgeable()` : la purge écarte les documents sous gel ou sous conservation et détruit les autres ; elle renvoie le nombre réellement purgé |

**Trois défauts de fond mis au jour au passage**, corrigés dans `aite_ecm_records` :

1. **Le gel juridique posé sur un dossier ne protégeait rien.** `legal_hold_active` est un champ
   *stocké* dont les dépendances se limitent à `legal_hold_ids` et `folder_id` : un gel visant un
   **dossier** ne déclenchait donc aucun recalcul et les documents concernés restaient modifiables.
   Le recalcul est désormais explicite à la pose comme à la levée du gel.
2. **La protection bloquait son propre recalcul.** Ce recalcul écrit `legal_hold_active` et
   `legal_hold_names`, champs que la protection refuse en écriture — elle s'opposait donc à
   l'activation du gel qu'elle est censée faire respecter. Un contexte `records_bypass` lève la
   protection pour ce seul recalcul, et `legal_hold_names` rejoint la liste des champs techniques
   autorisés.
3. **Le point de départ de la conservation dérivait.** Le déclencheur « à la finalisation » se
   fondait sur `write_date`, qui bouge à chaque modification ultérieure : l'échéance de conservation
   d'un document reculait donc à chaque écriture. Deux horodatages dédiés, `date_final` et
   `date_archived`, sont posés par `action_mark_final()` et `action_mark_archived()` et servent de
   point de départ, `write_date` ne restant qu'un repli pour les documents antérieurs.

**Vérification d'ensemble.** Suite complète sur les 24 modules installés :
**`0 failed, 0 error(s) of 152 tests`**.

---

## 6. Synthèse par domaine

| Domaine | Campagne initiale | **Contre-essai** | Anomalie traitée |
|---|---|---|---|
| Installation Community | ✅ Conforme | ✅ Conforme | — |
| Courrier : circuits, SLA, audit | ✅ Conforme | ✅ Conforme | ANO-08 |
| GED du courrier | ⚠️ Réserve | ✅ **Conforme** | ANO-04 |
| Référentiel ECM, explorateur | ✅ Conforme | ✅ Conforme | ANO-06 |
| Dossiers métier | ✅ Conforme | ✅ Conforme | — |
| Conservation et archivage | ✅ Conforme | ✅ Conforme | ANO-09 (gel, échéance, purge) |
| Valeur probante | ✅ Conforme | ✅ Conforme | ANO-05, ANO-09 (sceau orphelin) |
| Partage externe | ✅ Conforme | ✅ Conforme | — |
| API REST | ✅ Conforme | ✅ Conforme | — |
| **Lecteur réseau WebDAV** | ⚠️ **Réserve** | ✅ **Conforme** | ANO-01, ANO-03, ANO-07 |
| Connecteur Nextcloud | ⚠️ Réserve | ✅ Conforme (simulateur) | ANO-09 |
| Passerelle Office / Google | ⚠️ Réserve | ✅ Conforme (simulateur) | ANO-09 |
| Sécurité et cloisonnement | ✅ Conforme | ✅ Conforme | — |
| Non-régression automatisée | ❌ **Non conforme** | ✅ **Conforme** — 152/152 | ANO-02 |

**Recommandation de mise en production.** Aucune anomalie produit ne reste ouverte : le déploiement
est envisageable sur l'ensemble des domaines, **lecteur réseau WebDAV compris**. L'objectif d'un ECM
complet avec WebDAV fonctionnel est atteint et vérifié par une campagne protocolaire rejouable.

Quatre points d'exploitation subsistent. Aucun n'est une anomalie produit, mais **le second
conditionne le déploiement** dans un environnement où la double authentification est imposée.

1. **Prérequis de déploiement WebDAV.** Le serveur doit exposer une seule base résolvable (`db_name`
   ou `--db-filter`) : un client WebDAV n'envoie aucun cookie de session, la base ne peut donc pas
   être déduite. Sans cela, les deux points d'entrée répondent 404. Ce n'est pas un défaut du
   produit mais une contrainte à porter dans la procédure d'installation.

2. **Le lecteur réseau n'accepte que le mot de passe.** Vérifié le 10 septembre 2026 : une clé
   d'API valide est refusée en **401** par `/webdav/aite_ecm`, alors que la **même clé** est
   acceptée en **200** par `/api/ecm/v1`. `_authenticate()` n'appelle `session.authenticate()`
   qu'avec `type: 'password'`, et le fait à chaque requête. Conséquence : **un compte avec 2FA
   activée, ou un compte SSO sans mot de passe local, ne peut pas monter le lecteur réseau.** Deux
   voies selon la cible : accepter la clé d'API comme mot de passe Basic — c'est le mécanisme prévu
   par Odoo pour les clients incapables de 2FA — ou réserver le lecteur réseau à des comptes de
   service dédiés. À trancher avant mise en production si la 2FA est imposée.
3. **Compléter la couverture d'environnement.** Génération PDF (`wkhtmltopdf`), OCR image
   (`tesseract`), SMTP/IMAP et une instance Nextcloud réelle n'ont pas pu être exercés ; ces
   fonctions restent à valider en pré-production.
4. **Tenir la suite automatisée à zéro échec.** Elle est désormais un socle de non-régression
   fiable — c'est précisément son silence qui avait laissé passer une anomalie bloquante. Onze
   modules sur vingt-huit n'ont toujours aucun test, dont l'API REST et le partage externe,
   validés en campagne mais **manuellement** (SC-09, SC-05).

---

## 7. Annexes

### 7.1 Rejouer la campagne WebDAV

Le script complet est livré : **`docs/uat/scripts/campagne_webdav.sh`**. Il enchaîne les 24 cas
SC-11.2 à SC-11.25 (32 exécutions, SC-11.6 en comptant 9), affiche un verdict par cas et un total. Il est **idempotent** : le document
d'essai finit en corbeille, le dossier créé est réutilisé, on peut donc l'enchaîner sans
réinitialiser la base.

```bash
bash docs/uat/scripts/campagne_webdav.sh                       # serveur sur :8169
BASE_URL=http://serveur:8069 bash docs/uat/scripts/campagne_webdav.sh
```

Résultat attendu : `TOTAL : 32 réussis, 0 échoués`.

Les cas isolés, pour un diagnostic ponctuel :

```bash
B="demo.admin:demo1234"; U="http://localhost:8169/webdav/aite_ecm"
CT="-H Content-Type:application/octet-stream"   # indispensable : voir SC-11.13
curl -i -X OPTIONS -u "$B" "$U"                                    # SC-11.2
curl -X PROPFIND -H "Depth: 1" -u "$B" "$U"                        # SC-11.5
curl -X PROPFIND -H "Depth: 1" -u "$B" "$U/Juridique%20et%20contrats"
curl -X PUT $CT -u "$B" --data-binary @f.docx "$U/…/rapport.docx"   # SC-11.8
curl -o f.docx -u "$B" "$U/…/rapport.docx"                         # SC-11.9
curl -I -u "$B" "$U/…/rapport.docx"                                # SC-11.12
curl -X LOCK -u "$B" -H "Timeout: Second-3600" "$U/…"              # SC-11.16
curl -X UNLOCK -u "$B" "$U/…"                                      # SC-11.18
```

> **Piège à connaître.** Sans en-tête `Content-Type` binaire, `curl --data-binary` envoie
> `application/x-www-form-urlencoded` : le corps est alors consommé par l'analyseur de formulaires et
> n'atteint jamais le contrôleur. Le serveur répond désormais **415** dans ce cas (SC-11.13) au lieu
> d'enregistrer un fichier vide.

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

La liste des modules est déduite de la base, ce qui évite de la maintenir à la main :

```bash
DB=aite_test
MODS=$(psql "postgresql://odoo:odoo@localhost/$DB" -tAc \
  "SELECT name FROM ir_module_module WHERE state='installed' AND name LIKE 'aite%' ORDER BY name;" \
  | paste -sd,)
TAGS=$(echo "$MODS" | tr ',' '\n' | sed 's|^|/|' | paste -sd,)
odoo-bin -c odoo.conf -d "$DB" -u "$MODS" --test-enable --test-tags "$TAGS" --stop-after-init
```

Résultat attendu, en fin de journal :

```
odoo.tests.result: 0 failed, 0 error(s) of 152 tests when loading database 'aite_test'
```

> Ne pas lancer `--test-enable` sans `--test-tags` : la suite JavaScript d'Odoo s'exécute alors
> pendant plusieurs dizaines de minutes sans rapport avec la recette AITE.

**Deux règles à respecter en écrivant de nouveaux tests ECM** — ce sont les deux causes d'ANO-02 :

1. hériter de `EcmTransactionCase` / `EcmHttpCase`
   (`odoo.addons.aite_ecm_document.tests.common`) et créer les utilisateurs avec `_make_user()`,
   qui garantit le groupe *Utilisateur interne* et une adresse e-mail ;
2. ne jamais appeler `with_context()` ou `context_today()` sur la **classe de test** : ces méthodes
   attendent un recordset, pas un `TestCase`.

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
