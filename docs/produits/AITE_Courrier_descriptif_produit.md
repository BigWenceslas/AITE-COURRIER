# AITE Courrier — Descriptif produit

> **Offre de services AITE Consulting**
> Solution de gestion du courrier et de la correspondance administrative, nativement intégrée à Odoo 18 Enterprise.
> *Document de présentation produit — référence offre de services.*

---

## 1. Présentation

**AITE Courrier** est une application complète de **gestion du courrier** (entrant, sortant, interne) et de la **correspondance administrative**, conçue par AITE Consulting et nativement intégrée à **Odoo 18 Enterprise**.

Elle couvre l'intégralité du cycle de vie d'un courrier — de sa réception ou de sa création jusqu'à son archivage — en s'appuyant sur des **circuits de validation configurables**, une **gestion documentaire versionnée adossée à la GED native d'Odoo (Documents)**, un **accès WebDAV** type lecteur réseau, et un **tableau de bord de pilotage**.

L'application est livrée sous forme d'une **suite modulaire** : l'installation d'un seul module « chapeau » déploie l'ensemble des composants.

---

## 2. Proposition de valeur

| Enjeu client | Réponse AITE Courrier |
|---|---|
| Traçabilité du courrier | Référence unique `COUR-AAAA-NNNN`, journal d'audit, suivi des étapes |
| Délais de traitement maîtrisés | Circuits de validation par étapes, indicateurs SLA, alertes de retard |
| Sécurité de l'information | 4 niveaux de confidentialité, héritage automatique aux documents |
| Capitalisation documentaire | GED versionnée intégrée à l'app Documents native, classement automatique |
| Accès bureautique simple | Montage WebDAV : les courriers comme un lecteur réseau (Windows/macOS) |
| Pilotage | Tableau de bord avec indicateurs, graphiques et tableaux croisés |

---

## 3. Périmètre fonctionnel

### 3.1 Gestion du courrier

- **Objet métier Courrier** structuré : objet, expéditeur, type, service destinataire, priorité, confidentialité, date de réception, responsable.
- **Cycle de vie** en 6 statuts : *Brouillon → Nouveau → En traitement → Validé / Rejeté → Archivé*.
- **Référence unique** `COUR-AAAA-NNNN` attribuée automatiquement au lancement du circuit.
- **Verrouillage des champs métier** une fois le courrier archivé (intégrité des données).

### 3.2 Circuits de validation (workflow)

- **Moteur de circuits configurable** : circuits, étapes et transitions paramétrables.
- Le circuit est **instancié (copié depuis le type)** au lancement, garantissant l'historique même si le modèle évolue.
- **5 circuits prêts à l'emploi** :
  1. **Courrier entrant standard** — Réception → Qualification → Affectation → Traitement → Archivage
  2. **Courrier sortant** — Préparation → Contrôle → Validation → Signature → Émission
  3. **Courrier interne** — Création → Diffusion → Accusé de réception → Archivage
  4. **Facture fournisseur** — Réception → Contrôle administratif → Comptabilité → Validation responsable → Visa DG → Clôture → Archivage
  5. **Devis commercial** — Création → Analyse commerciale → Validation responsable → Validation direction → …

### 3.3 Gestion documentaire (GED)

- **Adossée à la GED native d'Odoo (module Documents)** : pas de GED parallèle. Chaque pièce du courrier est exposée comme `documents.document` dans un **espace « Courrier »** comportant **un dossier par courrier** (sa référence).
- **Aucune duplication du binaire** : le document natif pointe sur la même pièce jointe.
- **Versionnage automatique** (v1, v2, …) avec conservation de l'historique.
- **Classement à deux axes** : arborescence de **dossiers** (couleur, description, compteur) et **étiquettes** transversales colorées.
- **Auto-classement** : dossier par défaut déduit du type de courrier.
- **Confidentialité héritée** du courrier, **verrouillage** des versions finalisées/archivées.
- **Contrôles** : formats autorisés (PDF, DOCX, XLSX) et taille maximale (50 Mo).

### 3.4 Accès WebDAV

- **Montage de l'espace documentaire en lecteur réseau** (Explorateur Windows, Finder macOS, rclone, cadaver…).
- **Servi directement par le serveur Odoo**, sans dépendance externe.
- Arborescence `/webdav/aite_courrier/<référence>/<document>` — droits, verrous et confidentialité hérités de la GED.

### 3.5 Référentiels & sécurité

- **Confidentialité** — 4 niveaux : Public, Interne, Confidentiel, Secret.
- **Priorité** — Urgent, Haute, Normale.
- **Types de courrier** — Entrant, Sortant, Interne, Facture, Devis (catégorisés entrant/sortant/interne).
- **Groupes d'accès** dédiés et **journal d'audit** des opérations sensibles.

### 3.6 Tableau de bord & pilotage

- **Tableau de bord OWL** avec cartes d'indicateurs (KPI).
- **Graphiques** (barres) et **tableaux croisés** (pivot) sur le portefeuille de courriers.
- **Filtres** : En cours, En retard (SLA), Mes courriers, Reçus ce mois.
- **Regroupements** : par statut, catégorie, étape courante, service, responsable, mois de réception.

---

## 4. Architecture modulaire

| Module | Rôle |
|---|---|
| `aite_courrier` | Application « chapeau » : installe toute la suite + tableau de bord |
| `aite_courrier_base` | Socle : groupes, référentiels, journal d'audit |
| `aite_courrier_workflow` | Moteur de circuits + 5 circuits prêts à l'emploi |
| `aite_courrier_core` | Objet métier Courrier et cycle de vie |
| `aite_courrier_ged` | Gestion documentaire versionnée, adossée à Documents (GED native) |
| `aite_courrier_validation` | Exécution des transitions de circuit |
| `aite_courrier_webdav` | Accès WebDAV à l'espace documentaire |

> L'installation du module `aite_courrier` déploie automatiquement l'ensemble, **y compris l'app Documents native** d'Odoo (dépendance).

---

## 5. Prérequis techniques

- **Odoo 18 Enterprise** (le module Documents — GED native — fait partie de l'offre Enterprise).
- Serveur de production standard Odoo ; aucun composant externe requis pour le WebDAV.
- Navigateur récent pour le back-office ; client WebDAV natif de Windows/macOS pour le montage en lecteur réseau.

---

## 6. Bénéfices clés

- **Mise en service rapide** : circuits, référentiels et tableau de bord livrés prêts à l'emploi.
- **Conformité & traçabilité** : référence unique, audit, niveaux de confidentialité.
- **Pas de silo documentaire** : intégration native à la GED Odoo, capitalisation centralisée.
- **Adoption facilitée** : accès bureautique familier via WebDAV.
- **Évolutivité** : circuits et référentiels entièrement paramétrables, architecture modulaire.

---

## 7. Services associés (AITE Consulting)

- **Cadrage & paramétrage** des circuits et référentiels selon l'organisation du client.
- **Déploiement & intégration** dans l'environnement Odoo Enterprise existant.
- **Reprise de données** et personnalisation des modèles de courriers.
- **Formation** des utilisateurs et des administrateurs fonctionnels.
- **Support & maintenance** (correctif et évolutif).

---

*© AITE Consulting — www.aite-consulting.com. Document produit AITE Courrier.*
