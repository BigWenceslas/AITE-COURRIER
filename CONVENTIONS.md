# Conventions de développement — AITE Courrier

Ce document fixe les conventions communes à tous les modules de la suite
**AITE Courrier** (Odoo 18 Enterprise, Python 3.12, PostgreSQL).

Principe directeur : **paramétrage > code spécifique**. On privilégie toujours la
configuration via l'interface et les données de paramétrage avant d'écrire du
code métier.

---

## 1. Nommage

### Modèles Python / Odoo
- Nom technique de modèle : `snake_case` préfixé par `aite.`
  Exemples : `aite.courrier`, `aite.courrier.type`, `aite.workflow.step`.
- Classe Python en `PascalCase`, sans préfixe « Aite » obligatoire mais cohérente
  avec le modèle. Exemple : `class AiteCourrier(models.Model)` pour `aite.courrier`.
- Champs : `snake_case`. Les champs relationnels se terminent par `_id` (Many2one)
  ou `_ids` (One2many / Many2many).
- Méthodes : `snake_case`. Préfixes usuels Odoo :
  - `compute_` / `_compute_` pour les champs calculés,
  - `_inverse_`, `_search_`,
  - `action_` pour les actions déclenchées depuis l'UI,
  - `_check_` pour les contraintes,
  - `_onchange_` pour les onchange.

### Modules
- Nom de module : `snake_case` préfixé par `aite_courrier_`.
  Exemples : `aite_courrier_base`, `aite_courrier_workflow`.

### Identifiants XML (XML IDs)
- `snake_case`, descriptifs et stables.
- Groupes de sécurité : `group_<role>` (ex. `group_agent`, `group_admin`).
- Vues : `view_<model>_<type>` (ex. `view_aite_courrier_form`).
- Actions : `action_<model>` ; menus : `menu_<chemin>`.

### Fichiers
- Un fichier Python par modèle dans `models/` (ex. `models/aite_courrier.py`).
- Fichiers de vues regroupés par modèle dans `views/`.

---

## 2. Format des commits — Conventional Commits

Format : `<type>(<scope>): <description courte à l'impératif>`

Types autorisés :
- `feat`     : nouvelle fonctionnalité
- `fix`      : correction de bug
- `refactor` : refonte sans changement fonctionnel
- `docs`     : documentation
- `test`     : ajout/modification de tests
- `chore`    : tâches techniques (build, config, dépendances)
- `style`    : formatage, sans impact fonctionnel
- `perf`     : amélioration de performance
- `ci`       : intégration continue

Le `scope` est de préférence le module concerné (sans le préfixe `aite_courrier_`).

Exemples :
```
feat(base): ajoute les 8 groupes de sécurité du socle
fix(workflow): corrige la transition vers l'étape de validation
docs: documente l'ordre d'installation des modules
chore(base): initialise l'ossature du dépôt
```

Règles :
- Description en minuscule, à l'impératif présent, sans point final.
- Corps de commit optionnel pour le « pourquoi » (séparé par une ligne vide).
- Une modification = un commit cohérent.

---

## 3. Structure d'un module

```
aite_courrier_<nom>/
├── __init__.py            # importe le package models
├── __manifest__.py        # métadonnées, dépendances, data, demo (commenté)
├── models/                # un fichier par modèle métier
│   └── __init__.py
├── views/                 # vues, actions, menus (XML)
├── security/              # groups.xml, ir.model.access.csv, record rules
├── data/                  # données de paramétrage chargées à l'installation
├── demo/                  # données de démonstration
├── tests/                 # tests unitaires/intégration
│   └── __init__.py
└── static/                # ressources web (si nécessaire)
```

Conventions transverses :
- Le manifest est **commenté** et déclare explicitement l'ordre de chargement
  des fichiers `data` (sécurité en premier).
- La sécurité accompagne toujours un modèle : `ir.model.access.csv` + record rules
  si nécessaire.
- Tout code doit rester **installable** et **testable** isolément.
