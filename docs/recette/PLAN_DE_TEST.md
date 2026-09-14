# Plan de test — AITE ECM & AITE Courrier

Trois niveaux de vérification, complémentaires et tous rejouables :

| Niveau | Ce qu'il éprouve | Outil | Volume |
| --- | --- | --- | --- |
| **Tests unitaires et d'intégration** | règles métier, droits, calculs, contrôleurs HTTP | tests Odoo (`--test-enable`) | **297 tests**, 25 modules |
| **Recette applicative (UAT)** | parcours réels, dans un vrai navigateur, sous l'identité des rôles | `docs/recette/uat_runner.py` (Playwright) | **17 scénarios**, 45 captures |
| **Recette des interfaces** | WebDAV, API REST, lien de partage — vus d'un client externe | `docs/recette/uat_interfaces.py` | **18 contrôles** |

Le détail illustré des parcours est dans
[`GUIDE_RECETTE.md`](./GUIDE_RECETTE.md). Les anomalies relevées et corrigées
pendant la campagne sont listées dans [`ANOMALIES.md`](./ANOMALIES.md).

---

## 1. Environnement de recette

| Élément | Valeur retenue |
| --- | --- |
| Odoo | 18.0 **Community** |
| Python / PostgreSQL | 3.11 / 16 |
| Modules installés | les 25 modules AITE installables sur Community |
| Modules exclus | `aite_courrier_sign`, `aite_ecm_documents`, `aite_courrier_ged_documents` (Enterprise) |
| Jeu de données | `aite_ecm_demo`, profil « léger » |

> Les trois modules Enterprise ne sont pas exécutés faute d'Odoo Enterprise ;
> ils restent simplement non installés, ce que prévoit la documentation
> d'installation. Leur code est en revanche couvert par la relecture et par
> les contrôles d'intégrité du module chapeau.

### Installer et préparer

```bash
# 1. Suite complète + modules optionnels
./odoo-bin -c odoo.conf -d recette --without-demo=all \
    -i aite_ecm,aite_ecm_webdav,aite_ecm_office,aite_ecm_records,\
aite_ecm_sae,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,\
aite_courrier_portal,aite_ecm_demo --stop-after-init

# 2. Jeu de données (sinon la tâche planifiée s'en charge en arrière-plan)
./odoo-bin shell -c odoo.conf -d recette \
    < addons/aite_ecm_demo/scripts/seed_demo.py
```

---

## 2. Tests unitaires et d'intégration

```bash
./odoo-bin -c odoo.conf -d recette --without-demo=all \
    -i <liste des modules> --test-enable \
    --test-tags /aite_courrier_base,/aite_courrier_core,… --stop-after-init
```

Le script `run_tests.sh` fourni dans ce dossier enchaîne base neuve,
installation et exécution complète.

### Couverture par module

| Module | Tests | Ce qui est couvert |
| --- | ---: | --- |
| `aite_courrier_base` | 23 | 8 rôles et leurs implications, référentiels, journal d'audit immuable |
| `aite_courrier_workflow` | 22 | circuits, étapes, transitions, habilitations, éditeur de circuits |
| `aite_courrier_core` | 13 | cycle de vie, référence `COUR-AAAA-NNNN`, SLA, confidentialité |
| `aite_courrier_validation` | 16 | valider, retourner, rejeter, commenter, statut suivant le circuit |
| `aite_courrier_ged` | 16 | pièces, versions, verrouillage, contrat d'accès |
| `aite_courrier_capture` | 9 | passerelle e-mail, pièces jointes filtrées, audit |
| `aite_courrier_ocr` | 10 | file d'indexation, couche texte PDF, recherche par contenu |
| `aite_courrier_reponse` | 10 | modèles fusionnés, PDF versionné, courrier sortant, envoi |
| `aite_courrier_webdav` | 15 | service WebDAV du courrier, contrôle d'accès |
| `aite_courrier_portal` | 10 | cloisonnement des tiers, dépôt, suivi, pièces à jeton |
| `aite_courrier` | 3 | tableau de bord (clés de boucle, agrégats) |
| `aite_ecm_document` | 25 | document, versions, réservation, corbeille, droits, explorateur |
| `aite_ecm_workflow` | 6 | circuits polymorphes sur les documents |
| `aite_ecm_dossier` | 7 | dossiers métier, complétude, circuit |
| `aite_ecm_share` | 11 | validité des liens, filigrane, accès public, quotas |
| `aite_ecm_api` | 11 | clé d'API, lecture, écriture, droits du porteur, OpenAPI |
| `aite_courrier_ecm` | 7 | miroir des pièces de courrier vers l'ECM |
| `aite_ecm_records` | 10 | règles, échéances, gel juridique (marqueur périmé compris), bordereaux, boîtes |
| `aite_ecm_sae` | 9 | scellement, chaîne de preuve, horodatage, export SEDA |
| `aite_ecm_webdav` | 9 | serveur WebDAV ECM (PROPFIND, GET, PUT, LOCK, MOVE) |
| `aite_ecm_office` | 6 | jetons WOPI, aller-retour Google Docs |
| `aite_ecm_nextcloud` | 15 | envoi, import, conflits, sondage, webhook |
| `aite_ecm_nextcloud_courrier` | 8 | miroir Nextcloud des pièces de courrier |
| `aite_ecm_demo` | 10 | plan de génération, phases, purge (résidus des ponts compris), cohérence des compteurs |
| `aite_ecm` | 16 | intégrité de l'assemblage + parcours fonctionnel complet (courrier → circuit → ECM → preuve → partage → WebDAV → API) |

---

## 3. Recette applicative (UAT)

```bash
python3 docs/recette/uat_runner.py            # les 17 scénarios
python3 docs/recette/uat_runner.py SC01 SC07  # une sélection
python3 docs/recette/uat_runner.py --head     # navigateur visible
python3 docs/recette/build_guide.py           # régénère le guide illustré
```

Chaque étape effectue une action **et** contrôle son effet : une référence
attribuée, une étape franchie, un champ obligatoire honoré, une liste non
vide. Une étape sans effet fait échouer le scénario — c'est ainsi qu'ont été
trouvées les anomalies du portail et du statut de circuit.

| Code | Scénario | Rôle |
| --- | --- | --- |
| SC01 | Enregistrer un courrier entrant et lancer son circuit | Agent courrier |
| SC02 | Faire avancer un courrier d'une étape du circuit | Manager |
| SC03 | Espace documentaire : pièce et versions | Assistant(e) |
| SC04 | Explorateur ECM : parcourir le fonds | Archiviste |
| SC05 | Créer un document ECM | Archiviste |
| SC06 | Conservation : règles, documents échus, gel juridique | Archiviste |
| SC07 | Bordereau d'élimination | Manager |
| SC08 | Journal de preuve scellé | Audit |
| SC09 | Archives physiques : boîtes et prêts | Archiviste |
| SC10 | Partages externes : liens, quotas, expiration | Manager |
| SC11 | Dossiers métier : complétude et circuit | Comptabilité |
| SC12 | Tableau de bord de pilotage | Manager |
| SC13 | Journal d'audit | Audit |
| SC14 | Cloisonnement de la confidentialité | Agent courrier |
| SC15 | Portail : dépôt et suivi d'une demande | Tiers externe |
| SC16 | Vérification d'intégrité d'un document scellé | Archiviste |
| SC17 | Historique des versions d'un document | Assistant(e) |

---

## 4. Recette des interfaces techniques

```bash
python3 docs/recette/uat_interfaces.py \
    --api-key <clé> --share-url <lien de partage>
```

* **WebDAV** — refus sans identifiants (avec `WWW-Authenticate`), PROPFIND
  de la racine et d'un dossier, classe DAV 2 annoncée, enregistrement d'un
  fichier (PUT) créant une version, mot de passe erroné refusé.
* **API REST** — refus sans clé, authentification, recherche, fiche,
  création avec fichier, dépôt de version, téléchargement, refus d'un
  exécutable, spécification OpenAPI.
* **Lien de partage** — page publique, téléchargement avec en-têtes de
  sécurité, jeton inconnu refusé.

---

## 5. Points non couverts par cette campagne

| Point | Raison | Recommandation |
| --- | --- | --- |
| `aite_courrier_sign`, `aite_ecm_documents`, `aite_courrier_ged_documents` | nécessitent Odoo Enterprise | rejouer la campagne sur une instance Enterprise |
| Édition en ligne Collabora / OnlyOffice (WOPI) | nécessite un serveur Office externe | test d'intégration sur plateforme cliente ; les jetons et le protocole sont couverts unitairement |
| Google Docs | nécessite un client OAuth Google | doublure complète en test unitaire (aller-retour, export, suppression) |
| Nextcloud réel | nécessite une instance Nextcloud | doublure complète en test unitaire (envoi, import, conflit, webhook) |
| OCR d'images numérisées | nécessite Tesseract sur le serveur | l'extraction de la couche texte PDF est couverte ; l'OCR reste optionnel |
| Copie PDF/A | nécessite LibreOffice sur le serveur | vérifier après installation de `soffice` |
| Rendu PDF des états | nécessite `wkhtmltopdf` | le rendu HTML est couvert ; installer `wkhtmltopdf` en production |
| Montée en charge | hors périmètre | prévoir un test de charge sur volumétrie cible |
