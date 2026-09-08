# Spécification de test — Référentiels AITE Courrier (lot 2)

> Ce fichier **fait foi** : `test_referentiels.py` doit rester aligné dessus.
> Toute évolution des référentiels commence par une mise à jour de cette spec.

## Modèles couverts

- `aite.courrier.type`
- `aite.courrier.priority`
- `aite.courrier.confidentiality`

## TC-01 — Données par défaut chargées

À l'installation du module, les référentiels par défaut existent.

| Modèle | Enregistrements attendus (code) |
| ------ | ------------------------------- |
| `aite.courrier.type` | `ENTR`, `SORT`, `INT`, `FACT`, `DEVIS` |
| `aite.courrier.priority` | `u`, `h`, `n` |
| `aite.courrier.confidentiality` | `PUB`, `INT`, `CONF`, `SEC` |

## TC-02 — Catégorie des types

| Code | Catégorie |
| ---- | --------- |
| `ENTR` | `entrant` |
| `SORT` | `sortant` |
| `INT` | `interne` |
| `FACT` | `entrant` |
| `DEVIS` | `sortant` |

La catégorie ne peut prendre que les valeurs `entrant` / `sortant` / `interne`.

## TC-03 — Unicité du code

Créer un second type avec un `code` déjà existant doit échouer
(contrainte SQL d'unicité). Idem pour priorité et confidentialité.

## TC-04 — Champ obligatoire

Créer un type sans `code` ou sans `name` doit échouer.
Créer un type sans `category` doit échouer.

## TC-05 — Soft delete (active)

`active` vaut `True` par défaut. Désactiver un enregistrement
(`active = False`) le retire des recherches standards mais ne le supprime pas
(récupérable via le contexte `active_test=False`).

## TC-06 — Ordonnancement

- Les priorités sont triées par `sequence` croissante : `u` (1), `h` (2), `n` (3).
- Les confidentialités sont triées par `sequence` : `PUB` < `INT` < `CONF` < `SEC`.

## TC-07 — Découplage workflow

`aite.courrier.type` ne définit **pas** le champ `circuit_id` dans le module
`aite_courrier_base` (ajouté par héritage dans `aite_courrier_workflow`).
Le module socle s'installe donc sans dépendance vers le workflow.
