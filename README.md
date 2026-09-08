# AITE Courrier

Solution de **gestion du courrier** pour **Odoo 18 Enterprise**
(PostgreSQL, Python 3.12).

L'application est découpée en modules séparés par responsabilité, afin de
garder un socle stable et des briques métier extensibles. Principe directeur :
**paramétrage > code spécifique**, circuits linéaires simples au MVP.

---

## Les 7 modules

| Module | Rôle |
| ------ | ---- |
| **aite_courrier** | Application « chapeau » : installer ce seul module déploie toute la suite, et ajoute le **tableau de bord** (KPI, graphiques, pivot). |
| **aite_courrier_base** | Socle transverse : groupes de sécurité, catégorie de module, référentiels communs et audit transverse. Aucune dépendance interne. |
| **aite_courrier_workflow** | Moteur de circuits de traitement (étapes, transitions, affectations) + 5 circuits de base. |
| **aite_courrier_core** | Objets métier du courrier (entrant/sortant/interne, enregistrement, cycle de vie, référence `COUR-AAAA-NNNN`). |
| **aite_courrier_ged** | Gestion documentaire **adossée à la GED native Odoo (`documents`)** : un dossier par courrier dans l'app Documents, pièces versionnées, classement par dossiers/étiquettes, auto-classement, confidentialité héritée. |
| **aite_courrier_validation** | Exécution des transitions (valider, rejeter, retourner, commenter). |
| **aite_courrier_webdav** | Accès WebDAV à l'espace documentaire (monter les courriers comme lecteur réseau). |

---

## Ordre d'installation

Le plus simple : installer le module **chapeau** `aite_courrier`, qui tire
automatiquement toutes ses dépendances — **y compris la GED native `documents`**
(Odoo Enterprise).

Pour information, l'ordre des dépendances internes est :

1. **aite_courrier_base** — socle, installé en premier.
2. **aite_courrier_workflow** — dépend de `base`.
3. **aite_courrier_core** — dépend de `base` (+ `workflow`).
4. **aite_courrier_ged** — dépend de `core` (+ `documents`).
5. **aite_courrier_validation** — dépend de `core` (+ `workflow`).
6. **aite_courrier_webdav** — dépend de `ged`.
7. **aite_courrier** — module chapeau, dépend de tous les précédents.

---

## Installation / test (environnement local WSL + venv)

> Workflow réel : le dépôt est géré **sous Windows** ; on **copie** les addons
> dans `custom_addons` côté **WSL**, puis on lance Odoo (port **8169**).
> Référence d'architecture et scénarios de recette détaillés :
> [`docs/produits/AITE_Courrier_scenarios_test.md`](./docs/produits/AITE_Courrier_scenarios_test.md).

| Élément | Chemin / valeur |
| ------- | --------------- |
| Binaire Odoo | `/opt/odoo18e/extracted/usr/bin/odoo` |
| Environnement Python | `/opt/odoo18e/venv` |
| PYTHONPATH (libs Odoo) | `/opt/odoo18e/extracted/usr/lib/python3/dist-packages` |
| Configuration | `/opt/odoo18e/conf/odoo18e.conf` |
| Addons custom (`addons_path`) | `/opt/odoo18e/custom_addons` |
| Démarrage | `/opt/odoo18e/start.sh` |
| Port HTTP | **8169** |

### 1. Copier les modules dans l'instance (WSL)

```bash
cp -r /mnt/d/Dev/Projects/Aite-Product-Courrier/aite-courrier/addons/* \
      /opt/odoo18e/custom_addons/
```

> À refaire après chaque `git pull` / modification (la copie n'est pas un lien).

### 2. Installer toute la suite sur une base

Instance 8169 **arrêtée**, puis :

```bash
source /opt/odoo18e/venv/bin/activate
export PYTHONPATH=/opt/odoo18e/extracted/usr/lib/python3/dist-packages:$PYTHONPATH

# Crée la base si besoin, installe le chapeau + toutes les dépendances + documents
python3 /opt/odoo18e/extracted/usr/bin/odoo \
  -c /opt/odoo18e/conf/odoo18e.conf -d aite_courrier \
  -i aite_courrier --without-demo=all --stop-after-init
deactivate
```

### 3. Lancer les tests (optionnel)

Tester un module précis via ses *test-tags* (instance arrêtée) :

```bash
source /opt/odoo18e/venv/bin/activate
export PYTHONPATH=/opt/odoo18e/extracted/usr/lib/python3/dist-packages:$PYTHONPATH

python3 /opt/odoo18e/extracted/usr/bin/odoo \
  -c /opt/odoo18e/conf/odoo18e.conf -d aite_courrier --stop-after-init \
  -u aite_courrier_ged --test-enable --test-tags /aite_courrier_ged
deactivate
```

Modules et tags disponibles : `/aite_courrier_base`, `/aite_courrier_workflow`,
`/aite_courrier_core`, `/aite_courrier_ged`, `/aite_courrier_validation`,
`/aite_courrier_webdav`. (Le module workflow charge 5 circuits, 27 étapes,
37 transitions prêts à l'emploi.)

### 4. Démarrer et accéder à Odoo

```bash
/opt/odoo18e/start.sh
```

Ouvrir <http://localhost:8169> puis se connecter à la base `aite_courrier`.

### 5. Espace documentaire (GED native + WebDAV)

- Les pièces des courriers apparaissent dans l'app **Documents**, espace
  **« Courrier »**, un dossier par courrier (sa référence).
- WebDAV : `http://localhost:8169/webdav/aite_courrier` (HTTP Basic). Cf.
  [`addons/aite_courrier_webdav/docs/WEBDAV.md`](./addons/aite_courrier_webdav/docs/WEBDAV.md).

---

## Structure du dépôt

```
.
├── addons/
│   ├── aite_courrier/            # module chapeau (suite complète + tableau de bord)
│   ├── aite_courrier_base/       # socle (groupes, référentiels, audit)
│   ├── aite_courrier_workflow/   # moteur de circuits + 5 circuits de base
│   ├── aite_courrier_core/       # objet métier Courrier et cycle de vie
│   ├── aite_courrier_ged/        # GED versionnée, adossée à Documents (GED native)
│   ├── aite_courrier_validation/ # exécution des transitions (actions)
│   └── aite_courrier_webdav/     # accès WebDAV à l'espace documentaire
├── docs/produits/              # descriptif produit, fiches, scénarios de test
├── docker-compose.yml          # stack Docker de dev (optionnelle, non requise)
├── odoo.conf                   # configuration de la stack Docker (optionnelle)
├── CONVENTIONS.md              # conventions de nommage / commits / modules
└── README.md
```

Voir [CONVENTIONS.md](./CONVENTIONS.md) pour les règles de développement.
# AITE-COURRIER
