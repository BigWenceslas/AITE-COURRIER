# Grille de recette — AITE Courrier / AITE ECM

Feuille de saisie à dupliquer à chaque campagne. Le détail des étapes et les captures de référence
sont dans `DOSSIER_UAT.md`.

**Campagne** : ………………………  **Version testée** : ………………………  **Date** : ………………
**Recetteur** : ………………………  **Environnement** : ☐ Community ☐ Enterprise · Base : ………………

Statuts : **C** conforme · **NC** non conforme · **NT** non testé · **SO** sans objet

---

## Préalables

| # | Contrôle | Attendu | Statut | Observation |
|---|---|---|---|---|
| P1 | Installation du chapeau `aite_ecm` | Aucune erreur au journal | | |
| P2 | Modules installés | 24 sur Community, 27 sur Enterprise | | |
| P3 | Base résolvable pour le WebDAV | `db_name` ou `--db-filter` renseigné | | |
| P4 | `wkhtmltopdf` disponible | Génération PDF opérationnelle | | |
| P5 | Comptes de recette créés | 8 rôles distincts, mots de passe connus | | |

## SC-01 — Courrier : pilotage et cycle de vie

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-01.1 | Courrier › Analyse | Graphique et pivot chargés | | |
| SC-01.2 | Tableau de bord | 6 indicateurs + charge par étape | | |
| SC-01.3 | Liste des courriers | Références `COUR-AAAA-NNNN` | | |
| SC-01.4 | Fiche courrier | Circuit, étape, SLA, responsable | | |
| SC-01.5 | Onglet Documents | Pièces versionnées | | |
| SC-01.6 | Onglet Historique | Étapes datées avec acteur | | |
| SC-01.7 | Journal d'audit | Horodaté, lecture seule | | |
| SC-01.8 | Traiter une transition | Étape avancée, historique complété | | |
| SC-01.9 | Rejeter avec motif | Motif obligatoire, statut Rejeté | | |
| SC-01.10 | Courrier archivé | Champs figés | | |

## SC-02 — Référentiel documentaire ECM

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-02.1 | Explorateur de fichiers | Arborescence, vignettes, facettes | | |
| SC-02.2 | Liste des documents | Références `DOC-AAAA-NNNNN` | | |
| SC-02.3 | Fiche document | Type, dossier, confidentialité, métadonnées | | |
| SC-02.4 | Onglet Versions | Empreintes SHA-256 | | |
| SC-02.5 | Onglet Relations | Relations typées | | |
| SC-02.6 | Onglet Conservation | Règle, DUA, sort final | | |
| SC-02.7 | Onglet Preuve | Sceaux du document | | |
| SC-02.8 | Réserver / libérer | Verrou exclusif, autrui bloqué | | |
| SC-02.9 | Déposer une nouvelle version | v(n+1), auteur et date corrects | | |
| SC-02.10 | Format non autorisé | Refus explicite | | |
| SC-02.11 | Corbeille et restauration | Document restauré intact | | |

## SC-03 à SC-05 — Classement, dossiers, partage

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-03.1 | Plan de classement | Arborescence et droits hérités | | |
| SC-03.2 | Dossier restreint | Agent non habilité : accès refusé | | |
| SC-04.1 | Liste des dossiers métier | Taux de complétude affiché | | |
| SC-04.2 | Fiche dossier | Pièces attendues et fournies | | |
| SC-04.3 | Clôture d'un dossier incomplet | Refusée à l'agent, permise au manager | | |
| SC-05.1 | Liste des partages | Expiration, quota, filigrane | | |
| SC-05.2 | Lien valide | Page de téléchargement affichée | | |
| SC-05.3 | Téléchargement | Filigrane présent sur le PDF | | |
| SC-05.4 | Compteur d'accès | Incrémenté à chaque accès | | |
| SC-05.5 | Lien expiré | Page « Lien indisponible » | | |
| SC-05.6 | Jeton inexistant | 404, aucune fuite d'information | | |

## SC-06 / SC-07 — Conservation et valeur probante

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-06.1 | Règles de conservation | 5 règles livrées | | |
| SC-06.2 | Documents échus | Liste alimentée par le calcul nocturne | | |
| SC-06.3 | Pose d'un gel juridique | Modification et destruction bloquées | | |
| SC-06.4 | Bordereau d'élimination | Constitution, validation, exécution tracée | | |
| SC-06.5 | Archives physiques | Boîte, emplacement, prêt | | |
| SC-06.6 | Destruction hors bordereau | Refusée | | |
| SC-07.1 | Journal de preuve | Sceaux chaînés, journal inaltérable | | |
| SC-07.2 | Export SEDA | Paquet ZIP avec bordereau | | |
| SC-07.3 | Vérification d'intégrité | Chaîne recalculée sans anomalie | | |
| SC-07.4 | Attestation d'intégrité | PDF généré | | |

## SC-09 — API REST

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-09.1 | `GET /ping` authentifié | `status: ok` | | |
| SC-09.2 | Sans clé | 401 | | |
| SC-09.3 | Clé invalide | 401 | | |
| SC-09.4 | `GET /types` | Types du référentiel | | |
| SC-09.5 | `GET /folders` | Plan de classement | | |
| SC-09.6 | `GET /documents` | Total et pagination corrects | | |
| SC-09.7 | Recherche plein texte | Résultats pertinents | | |
| SC-09.8 | `GET /openapi.json` | Spécification servie | | |
| SC-09.9 | `POST /documents` | Document et v1 créés | | |
| SC-09.10 | `POST …/versions` | v2 créée | | |
| SC-09.11 | `GET …/download` | Fichier conforme | | |
| SC-09.12 | Document inexistant | 404 | | |

## SC-11 — Lecteur réseau WebDAV

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-11.2 | `OPTIONS` | `DAV: 1, 2` | | |
| SC-11.3 | Sans identifiants | 401 | | |
| SC-11.4 | Mot de passe erroné | 401 | | |
| SC-11.5 | `PROPFIND` racine | Plan de classement listé | | |
| SC-11.6 | `PROPFIND` de chaque dossier | 207 sur tous | | |
| SC-11.7 | Dossier inexistant | 404 | | |
| SC-11.8 | `GET` d'un document | Contenu correct | | |
| SC-11.9 | En-têtes | `ETag` et `Last-Modified` présents | | |
| SC-11.10 | `LOCK` | Document réservé côté ECM | | |
| SC-11.11 | `PUT` par un tiers pendant le verrou | 423 | | |
| SC-11.12 | `UNLOCK` | Réservation libérée | | |
| SC-11.13 | `PUT` sur document existant | Nouvelle version | | |
| SC-11.14 | Fichier `~$…` | 403 | | |
| SC-11.15 | Fichier `.tmp` | 403 | | |
| SC-11.16 | `MKCOL` | Dossier créé | | |
| SC-11.17 | `MOVE` | Titre et dossier mis à jour | | |
| SC-11.18 | `DELETE` | Mise en corbeille | | |
| SC-11.21 | **`PUT` d'un fichier nouveau puis relecture** | 201 puis 200 | | *cf. ANO-03* |
| SC-11.22 | `HEAD` | Taille identique au `GET` | | *cf. ANO-07* |

### Montage poste de travail

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-11.30 | Windows : connecter un lecteur réseau | Le lecteur s'ouvre dans l'Explorateur | | HTTPS requis, sinon `BasicAuthLevel` |
| SC-11.31 | Windows : ouvrir un document dans Word | Ouverture et verrouillage | | |
| SC-11.32 | Windows : enregistrer depuis Word | Nouvelle version côté ECM | | |
| SC-11.33 | macOS : Se connecter au serveur | Le volume est monté | | |
| SC-11.34 | Copier un fichier dans le lecteur | Le fichier reste visible | | *cf. ANO-03* |

## SC-12 — Sécurité par rôle

| # | Cas | Attendu | Statut | Observation |
|---|---|---|---|---|
| SC-12.1 | Vue agent sur le fonds | Périmètre restreint | | |
| SC-12.2 | Menus de l'agent | Configuration masquée | | |
| SC-12.3 | Document confidentiel d'autrui | Invisible pour l'agent | | |
| SC-12.4 | Compte Audit | Aucun document confidentiel visible | | |
| SC-12.5 | Journal d'audit | Modification refusée à tous | | |
| SC-12.6 | Transition non habilitée | Refus côté serveur | | |

---

## Récapitulatif

| Domaine | C | NC | NT | Verdict |
|---|---|---|---|---|
| Préalables | | | | |
| SC-01 Courrier | | | | |
| SC-02 ECM | | | | |
| SC-03 à SC-05 | | | | |
| SC-06 / SC-07 Conservation et preuve | | | | |
| SC-09 API | | | | |
| SC-11 WebDAV | | | | |
| SC-12 Sécurité | | | | |
| **Total** | | | | |

**Décision** : ☐ Recette prononcée ☐ Prononcée avec réserves ☐ Refusée
**Réserves** : ……………………………………………………………………………………………………
**Signature** : ……………………………  **Date** : ……………………
