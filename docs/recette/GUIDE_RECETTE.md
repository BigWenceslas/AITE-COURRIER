# Guide de recette — AITE ECM & AITE Courrier

Ce guide est **produit par l'exécution réelle** des parcours : chaque
capture provient de la dernière campagne, chaque contrôle a été vérifié par
le moteur de recette. Il sert à deux choses :

* **rejouer la recette à la main** — les étapes sont écrites pour être
  suivies par un testeur, avec le compte à utiliser et le résultat attendu ;
* **prouver ce qui a été vérifié** — la colonne « constat » reprend ce que
  le moteur a effectivement lu à l'écran.

| | |
| --- | --- |
| Version de la suite | 18.0.2.1.x (Odoo 18 Community) |
| Campagne | 2026-09-16 10:28:06 |
| Instance | http://localhost:8169 |
| Jeu de données | `aite_ecm_demo`, profil « léger » |
| Mot de passe des comptes de recette | `aite2026` |

## Comment rejouer cette recette

1. Installer la suite : `./odoo-bin -c odoo.conf -d <base> -i aite_ecm
   --stop-after-init`, puis les modules optionnels souhaités
   (`aite_ecm_records`, `aite_ecm_sae`, `aite_ecm_webdav`, `aite_ecm_office`,
   `aite_courrier_portal`, `aite_ecm_demo`).
2. Générer le jeu de données : **ECM › Configuration › Jeu de données de
   test › Démarrer**, ou
   `./odoo-bin shell -d <base> < addons/aite_ecm_demo/scripts/seed_demo.py`.
3. Donner un mot de passe connu aux comptes `demo.*` (Réglages ›
   Utilisateurs), puis suivre les scénarios ci-dessous.
4. Pour rejouer automatiquement :
   `python3 docs/recette/uat_runner.py` (parcours navigateur) et
   `python3 docs/recette/uat_interfaces.py --api-key … --share-url …`
   (interfaces techniques).

## Comptes de recette

| Identifiant | Personne | Rôle AITE |
| --- | --- | --- |
| `demo.agent1` · `demo.agent2` · `demo.agent3` | Aurélie Mbarga, Boris Tchoumi, Clarisse Ekani | Agent courrier |
| `demo.assist1` · `demo.assist2` | Nadège Fotso, Franck Onana | Assistant(e) |
| `demo.manager1` · `demo.manager2` | Patrick Essomba, Solange Ngo Bassong | Manager |
| `demo.compta` | Hervé Kenfack | Comptabilité |
| `demo.signer` | Gisèle Atangana | Signataire |
| `demo.archive` | Landry Nkolo | Archiviste |
| `demo.audit` | Irène Djomo | Audit |
| `demo.admin` | Serge Kamdem | Administrateur AITE |
| `portail.recette` | Clinique La Providence | Tiers externe (portail) |


## Synthèse

| Scénario | Rôle | Compte | Étapes | Résultat |
| --- | --- | --- | --- | --- |
| **SC01** — Enregistrer un courrier entrant et lancer son circuit | Agent courrier | `demo.agent1` | 6 | ✅ conforme |
| **SC02** — Faire avancer un courrier d'une étape du circuit | Manager | `demo.manager1` | 5 | ✅ conforme |
| **SC03** — Espace documentaire : consulter une pièce et ses versions | Assistante | `demo.assist1` | 2 | ✅ conforme |
| **SC04** — Explorateur ECM : parcourir le fonds documentaire | Archiviste | `demo.archive` | 3 | ✅ conforme |
| **SC05** — Créer un document ECM et y déposer un fichier | Archiviste | `demo.archive` | 4 | ✅ conforme |
| **SC06** — Conservation : règles, documents échus, gel juridique | Archiviste | `demo.archive` | 4 | ✅ conforme |
| **SC07** — Bordereau d'élimination : de la constitution à l'exécution | Manager | `demo.manager1` | 2 | ✅ conforme |
| **SC08** — Valeur probante : journal de preuve scellé | Audit | `demo.audit` | 2 | ✅ conforme |
| **SC09** — Archives physiques : boîtes, emplacement et prêts | Archiviste | `demo.archive` | 2 | ✅ conforme |
| **SC10** — Partages externes : liens, quotas et expiration | Manager | `demo.manager2` | 2 | ✅ conforme |
| **SC11** — Dossiers métier : complétude et circuit | Comptabilité | `demo.compta` | 2 | ✅ conforme |
| **SC12** — Tableau de bord de pilotage | Manager | `demo.manager2` | 1 | ✅ conforme |
| **SC13** — Journal d'audit : qui a fait quoi | Audit | `demo.audit` | 1 | ✅ conforme |
| **SC14** — Cloisonnement : un agent ne voit pas un courrier confidentiel d'un tiers | Agent courrier | `demo.agent3` | 2 | ✅ conforme |
| **SC15** — Portail : un tiers dépose une demande et la suit | Tiers externe (portail) | `portail.recette` | 5 | ✅ conforme |
| **SC16** — Vérifier l'intégrité d'un document scellé | Archiviste | `demo.archive` | 2 | ✅ conforme |
| **SC17** — Déposer une nouvelle version d'un document | Assistante | `demo.assist2` | 1 | ✅ conforme |
| **SC18** — Cachet de traitement d'un courrier clos | Manager | `demo.manager1` | 3 | ✅ conforme |

---

## Interfaces techniques

Contrôles joués hors navigateur, comme le ferait un client réel : l'Explorateur Windows sur le lecteur réseau, un progiciel tiers sur l'API, un correspondant externe sur un lien de partage.

| Interface | Contrôle | Résultat | Constat |
| --- | --- | --- | --- |
| WebDAV | Refus sans identifiants | ✅ | 401 + WWW-Authenticate: Basic |
| WebDAV | PROPFIND de la racine | ✅ | 10 entrée(s) : aite_ecm, Achats et fournisseurs, Archives et éliminations… |
| WebDAV | Un dossier de classement est listé | ✅ | « Achats et fournisseurs » exploré (34716 octets de réponse) |
| WebDAV | OPTIONS annonce la classe 2 (verrous) | ✅ | DAV: 1, 2 — Allow: OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND, PROPPATCH, MKCOL, |
| WebDAV | Identifiants erronés refusés | ✅ | 401 sur mot de passe erroné |
| WebDAV | Enregistrement depuis le lecteur réseau (PUT) | ✅ | « DOC-2026-00257 - Attestation de non-redevance fiscale (ANR) — Bureautique Plus SARL.pdf » réenregistré (1229 → 31 octe |
| API | Refus sans clé d'API | ✅ | 401 sans clé d'API |
| API | Authentification par clé | ✅ | authentifié comme Landry Nkolo |
| API | Recherche de documents | ✅ | 254 document(s) au total, page de 5 |
| API | Fiche d'un document | ✅ | DOC-2026-00356 — Procédure de recette AITE ECM |
| API | Création d'un document avec fichier | ✅ | créé DOC-2026-00357 |
| API | Dépôt d'une seconde version | ✅ | v2 déposée, empreinte 7a7eab677175cc62… |
| API | Téléchargement du fichier | ✅ | 27 octets, application/pdf |
| API | Format exécutable refusé | ✅ | 422 — format refusé |
| API | Spécification OpenAPI | ✅ | OpenAPI 3.0.3, 7 chemin(s) |
| Partage | Page publique du lien | ✅ | page d'accueil servie (1583 octets), sans authentification |
| Partage | Téléchargement du fichier partagé | ✅ | 2146 octets, application/pdf |
| Partage | Jeton inconnu refusé | ✅ | 404 sur jeton inconnu |

---

## SC01 — Enregistrer un courrier entrant et lancer son circuit

> Un agent d'accueil enregistre le courrier du jour et le met en circulation.

**Rôle** : Agent courrier  ·  **Compte** : `demo.agent1`  ·  **Durée** : 56.6 s

### ✅ 1. Écran d'accueil de l'agent

*Contrôle* : « Courrier » affiché

![Écran d'accueil de l'agent](captures/SC01_01_ecran_d_accueil_de_l_agent.png)

### ✅ 2. Liste des courriers

*Contrôle* : 80 courrier(s) déjà enregistré(s)

![Liste des courriers](captures/SC01_02_liste_des_courriers.png)

### ✅ 3. Formulaire de saisie

*Contrôle* : « Objet » affiché

![Formulaire de saisie](captures/SC01_03_formulaire_de_saisie.png)

### ✅ 4. Courrier renseigné (objet, expéditeur, type)

*Contrôle* : objet et expéditeur saisis

![Courrier renseigné (objet, expéditeur, type)](captures/SC01_04_courrier_renseigne_objet_expediteur_type.png)

### ✅ 5. Courrier enregistré

*Contrôle* : « Brouillon » affiché

![Courrier enregistré](captures/SC01_05_courrier_enregistre.png)

### ✅ 6. Circuit lancé — la référence est attribuée

*Contrôle* : référence COUR-2026-0141, courrier sorti du brouillon

![Circuit lancé — la référence est attribuée](captures/SC01_06_circuit_lance_la_reference_est_attribuee.png)

---

## SC02 — Faire avancer un courrier d'une étape du circuit

> Un responsable de service prend un courrier en cours et le fait passer à l'étape suivante, commentaire à l'appui.

**Rôle** : Manager  ·  **Compte** : `demo.manager1`  ·  **Durée** : 40.5 s

### ✅ 1. Courriers en traitement du service

*Contrôle* : 60 courrier(s) affiché(s)

![Courriers en traitement du service](captures/SC02_01_courriers_en_traitement_du_service.png)

### ✅ 2. Fiche du courrier à traiter

*Contrôle* : COUR-2026-0014 — étape « Affectation »

![Fiche du courrier à traiter](captures/SC02_02_fiche_du_courrier_a_traiter.png)

### ✅ 3. Assistant de traitement

*Contrôle* : « Action » affiché

![Assistant de traitement](captures/SC02_03_assistant_de_traitement.png)

### ✅ 4. Transition appliquée

*Contrôle* : étape « Affectation » → « Traitement » (statut : En traitement)

![Transition appliquée](captures/SC02_04_transition_appliquee.png)

### ✅ 5. Historique du circuit

*Contrôle* : historique du circuit affiché

![Historique du circuit](captures/SC02_05_historique_du_circuit.png)

---

## SC03 — Espace documentaire : consulter une pièce et ses versions

> L'assistante retrouve une pièce d'un courrier et vérifie ses versions.

**Rôle** : Assistante  ·  **Compte** : `demo.assist1`  ·  **Durée** : 26.0 s

### ✅ 1. Espace documentaire

*Contrôle* : 4 groupe(s) de pièce affiché(s)

![Espace documentaire](captures/SC03_01_espace_documentaire.png)

### ✅ 2. Fiche d'une pièce

*Contrôle* : « Versions » affiché

![Fiche d'une pièce](captures/SC03_02_fiche_d_une_piece.png)

---

## SC04 — Explorateur ECM : parcourir le fonds documentaire

> L'archiviste navigue dans le plan de classement et ouvre un document.

**Rôle** : Archiviste  ·  **Compte** : `demo.archive`  ·  **Durée** : 28.3 s

### ✅ 1. Documents ECM

*Contrôle* : 80 document(s) affiché(s)

![Documents ECM](captures/SC04_01_documents_ecm.png)

### ✅ 2. Fiche document

*Contrôle* : « Référence » affiché

![Fiche document](captures/SC04_02_fiche_document.png)

### ✅ 3. Plan de classement

*Contrôle* : 80 dossier de classement(s) affiché(s)

![Plan de classement](captures/SC04_03_plan_de_classement.png)

---

## SC05 — Créer un document ECM et y déposer un fichier

> Création d'un document typé, dépôt d'une version, finalisation.

**Rôle** : Archiviste  ·  **Compte** : `demo.archive`  ·  **Durée** : 31.4 s

### ✅ 1. Documents ECM

![Documents ECM](captures/SC05_01_documents_ecm.png)

### ✅ 2. Formulaire de création

*Contrôle* : « Nom » affiché

![Formulaire de création](captures/SC05_02_formulaire_de_creation.png)

### ✅ 3. Document renseigné

![Document renseigné](captures/SC05_03_document_renseigne.png)

### ✅ 4. Document enregistré

*Contrôle* : référence DOC-2026-00360 attribuée

![Document enregistré](captures/SC05_04_document_enregistre.png)

---

## SC06 — Conservation : règles, documents échus, gel juridique

> Contrôle du cycle de vie archivistique et des protections.

**Rôle** : Archiviste  ·  **Compte** : `demo.archive`  ·  **Durée** : 29.9 s

### ✅ 1. Règles de conservation

*Contrôle* : 5 règle de conservation(s) affiché(s)

![Règles de conservation](captures/SC06_01_regles_de_conservation.png)

### ✅ 2. Documents échus

*Contrôle* : 1 document(s) échu(s)

![Documents échus](captures/SC06_02_documents_echus.png)

### ✅ 3. Gels juridiques

*Contrôle* : 2 gel juridique(s) affiché(s)

![Gels juridiques](captures/SC06_03_gels_juridiques.png)

### ✅ 4. Détail d'un gel

*Contrôle* : « Motif » affiché

![Détail d'un gel](captures/SC06_04_detail_d_un_gel.png)

---

## SC07 — Bordereau d'élimination : de la constitution à l'exécution

> Le bordereau préparé par l'archiviste est validé puis exécuté.

**Rôle** : Manager  ·  **Compte** : `demo.manager1`  ·  **Durée** : 26.1 s

### ✅ 1. Bordereaux d'élimination

*Contrôle* : 1 bordereau(s) affiché(s)

![Bordereaux d'élimination](captures/SC07_01_bordereaux_d_elimination.png)

### ✅ 2. Bordereau à valider

*Contrôle* : « Bordereau » affiché

![Bordereau à valider](captures/SC07_02_bordereau_a_valider.png)

---

## SC08 — Valeur probante : journal de preuve scellé

> L'auditeur consulte la chaîne de sceaux et son horodatage.

**Rôle** : Audit  ·  **Compte** : `demo.audit`  ·  **Durée** : 25.4 s

### ✅ 1. Journal de preuve

*Contrôle* : 80 sceau(s) affiché(s)

![Journal de preuve](captures/SC08_01_journal_de_preuve.png)

### ✅ 2. Détail d'un sceau

*Contrôle* : « Empreinte » affiché

![Détail d'un sceau](captures/SC08_02_detail_d_un_sceau.png)

---

## SC09 — Archives physiques : boîtes, emplacement et prêts

> Suivi des boîtes d'archives et de leurs sorties.

**Rôle** : Archiviste  ·  **Compte** : `demo.archive`  ·  **Durée** : 25.1 s

### ✅ 1. Boîtes d'archives

*Contrôle* : 4 boîte(s) affiché(s)

![Boîtes d'archives](captures/SC09_01_boites_d_archives.png)

### ✅ 2. Détail d'une boîte

*Contrôle* : « Emplacement » affiché

![Détail d'une boîte](captures/SC09_02_detail_d_une_boite.png)

---

## SC10 — Partages externes : liens, quotas et expiration

> Contrôle des liens diffusés hors de l'organisation.

**Rôle** : Manager  ·  **Compte** : `demo.manager2`  ·  **Durée** : 25.4 s

### ✅ 1. Partages externes

*Contrôle* : 28 partage(s) affiché(s)

![Partages externes](captures/SC10_01_partages_externes.png)

### ✅ 2. Détail d'un partage

*Contrôle* : lien public http://localhost:8169/ecm/share/UXM0cocIvy5YvvYULGRepP3ppf-cUU_s

![Détail d'un partage](captures/SC10_02_detail_d_un_partage.png)

---

## SC11 — Dossiers métier : complétude et circuit

> Un dossier fournisseur et ses pièces attendues.

**Rôle** : Comptabilité  ·  **Compte** : `demo.compta`  ·  **Durée** : 26.2 s

### ✅ 1. Dossiers métier

*Contrôle* : 40 dossier métier(s) affiché(s)

![Dossiers métier](captures/SC11_01_dossiers_metier.png)

### ✅ 2. Détail d'un dossier

*Contrôle* : « Complétude » affiché

![Détail d'un dossier](captures/SC11_02_detail_d_un_dossier.png)

---

## SC12 — Tableau de bord de pilotage

> Vue de direction : volumes, charge par étape, retards.

**Rôle** : Manager  ·  **Compte** : `demo.manager2`  ·  **Durée** : 104.5 s

### ✅ 1. Tableau de bord

*Contrôle* : 6 bloc(s) d'indicateurs, 718 caractères affichés

![Tableau de bord](captures/SC12_01_tableau_de_bord.png)

---

## SC13 — Journal d'audit : qui a fait quoi

> Traçabilité transverse des opérations.

**Rôle** : Audit  ·  **Compte** : `demo.audit`  ·  **Durée** : 23.8 s

### ✅ 1. Journal d'audit

*Contrôle* : 80 entrée d'audit(s) affiché(s)

![Journal d'audit](captures/SC13_01_journal_d_audit.png)

---

## SC14 — Cloisonnement : un agent ne voit pas un courrier confidentiel d'un tiers

> Contrôle de la confidentialité entre agents.

**Rôle** : Agent courrier  ·  **Compte** : `demo.agent3`  ·  **Durée** : 25.5 s

### ✅ 1. Courriers visibles par l'agent

*Contrôle* : 80 courrier(s) visibles

![Courriers visibles par l'agent](captures/SC14_01_courriers_visibles_par_l_agent.png)

### ✅ 2. Recherche des courriers « Secret »

*Contrôle* : 0 résultat(s) — les courriers confidentiels d'un tiers restent masqués

![Recherche des courriers « Secret »](captures/SC14_02_recherche_des_courriers_secret.png)

---

## SC15 — Portail : un tiers dépose une demande et la suit

> Parcours d'un correspondant externe, hors de l'application.

**Rôle** : Tiers externe (portail)  ·  **Compte** : `portail.recette`  ·  **Durée** : 8.6 s

### ✅ 1. Espace personnel du tiers

*Contrôle* : « Mes courriers » affiché

![Espace personnel du tiers](captures/SC15_01_espace_personnel_du_tiers.png)

### ✅ 2. Mes courriers

*Contrôle* : « courrier » affiché

![Mes courriers](captures/SC15_02_mes_courriers.png)

### ✅ 3. Formulaire de dépôt

*Contrôle* : « Objet » affiché

![Formulaire de dépôt](captures/SC15_03_formulaire_de_depot.png)

### ✅ 4. Demande déposée

*Contrôle* : « Réclamation sur la facture de mars » affiché

![Demande déposée](captures/SC15_04_demande_deposee.png)

### ✅ 5. Cachet de traitement vu par le tiers

*Contrôle* : 2 fonction(s) au cachet : 09/16/2026 · Réception	Agent courrier	09/15/2026

![Cachet de traitement vu par le tiers](captures/SC15_05_cachet_de_traitement_vu_par_le_tiers.png)

---

## SC16 — Vérifier l'intégrité d'un document scellé

> Contrôle à la demande de la chaîne de preuve d'un document.

**Rôle** : Archiviste  ·  **Compte** : `demo.archive`  ·  **Durée** : 28.2 s

### ✅ 1. Document scellé et son journal de preuve

*Contrôle* : document DOC-2026-00360

![Document scellé et son journal de preuve](captures/SC16_01_document_scelle_et_son_journal_de_preuve.png)

### ✅ 2. Vérification d'intégrité

*Contrôle* : intégrité confirmée (Intègre)

![Vérification d'intégrité](captures/SC16_02_verification_d_integrite.png)

---

## SC17 — Déposer une nouvelle version d'un document

> Le versionnement conserve l'historique et l'empreinte.

**Rôle** : Assistante  ·  **Compte** : `demo.assist2`  ·  **Durée** : 32.9 s

### ✅ 1. Document et son historique de versions

*Contrôle* : DOC-2026-00357 — 2 version(s), la plus récente : v2	recette_v2.pdf	seconde version	27	Landry Nkolo	09/16/2026 10:00:30	 · Ouvrir · Télécharger

![Document et son historique de versions](captures/SC17_01_document_et_son_historique_de_versions.png)

---

## SC18 — Cachet de traitement d'un courrier clos

> Un courrier arrivé au bout de son circuit porte un cachet qui nomme les intervenants et la fonction au titre de laquelle ils ont agi — là où le portail ne montre que les fonctions.

**Rôle** : Manager  ·  **Compte** : `demo.manager1`  ·  **Durée** : 31.6 s

### ✅ 1. Filtrer les courriers traités

*Contrôle* : 52 courrier traité(s) affiché(s)

![Filtrer les courriers traités](captures/SC18_01_filtrer_les_courriers_traites.png)

### ✅ 2. Courrier clos — le ruban « Traité »

*Contrôle* : COUR-2026-0009 porte le ruban « Traité »

![Courrier clos — le ruban « Traité »](captures/SC18_02_courrier_clos_le_ruban_traite.png)

### ✅ 3. Cachet : intervenants et fonctions

*Contrôle* : COUR-2026-0009 — 2 visa(s), le premier : Réception	Franck Onana	Agent courrier	09/15/2026 15:13:24	

![Cachet : intervenants et fonctions](captures/SC18_03_cachet_intervenants_et_fonctions.png)

---

*Guide produit automatiquement par `docs/recette/build_guide.py` à partir de la dernière campagne.*
