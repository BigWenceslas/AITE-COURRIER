# Spécification de test — Moteur de workflow AITE Courrier (lot 5)

> Ce fichier **fait foi** : `test_workflow_engine.py` doit rester aligné dessus.
> Toute évolution des circuits de base ou des méthodes moteur commence par une
> mise à jour de cette spec.

## Modèles couverts

- `aite.workflow.circuit` (méthode `get_initial_step`)
- `aite.workflow.step` (méthodes `outgoing_transitions`, `can_user_act`)
- Données : les 5 circuits de base chargés à l'installation.

## TC-01 — Les 5 circuits de base sont instanciés

À l'installation, les 5 circuits existent, rattachés au bon type, avec le bon
nombre d'étapes et de transitions.

| Circuit (xmlid)             | Type   | Étapes | Transitions |
| --------------------------- | ------ | ------ | ----------- |
| `circuit_entrant_standard`  | ENTR   | 5      | 7           |
| `circuit_sortant`           | SORT   | 5      | 7           |
| `circuit_interne`           | INT    | 4      | 4           |
| `circuit_facture`           | FACT   | 7      | 10          |
| `circuit_devis`             | DEVIS  | 6      | 9           |

## TC-02 — Étape initiale d'un circuit

`circuit.get_initial_step()` retourne l'unique étape `is_initial`. Pour le
circuit entrant standard, il s'agit de l'étape « Réception » (séquence 1).

## TC-03 — Topologie valide des circuits livrés

Chaque circuit de base comporte exactement une étape initiale et au moins une
étape finale.

## TC-04 — Transitions sortantes d'une étape

`step.outgoing_transitions()` retourne les transitions partant de l'étape.
Pour l'étape « Qualification » (entrant standard), il y a 2 transitions
sortantes : « Affecter » (forward) et « Retourner » (backward).

## TC-05 — Habilitation par rôle (`role_ids`)

`step.can_user_act(user)` :

- retourne `True` si l'utilisateur possède l'un des rôles de l'étape ;
- retourne `False` si l'utilisateur ne possède aucun des rôles.

Exemple : l'étape « Réception » (entrant standard) autorise `group_agent`.
Un utilisateur agent peut agir ; un utilisateur seulement archiviste, non.

## TC-06 — Restriction par utilisateurs (`user_ids`)

Lorsque `user_ids` est renseigné sur une étape :

- seuls les utilisateurs listés **et** possédant l'un des rôles peuvent agir ;
- un utilisateur listé mais sans rôle ne peut pas agir ;
- un utilisateur ayant le rôle mais non listé ne peut pas agir.

Lorsque `user_ids` est vide, tout utilisateur possédant l'un des rôles peut agir.

## TC-07 — Libellé lisible d'une transition

`transition.display_name` affiche « Libellé (étape de départ → étape d'arrivée) »,
afin que les listes déroulantes (assistant d'action) soient compréhensibles.
