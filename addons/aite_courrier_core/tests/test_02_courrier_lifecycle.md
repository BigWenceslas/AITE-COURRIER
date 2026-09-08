# Spécification de test — Cycle de vie du courrier (lot 2 / core)

> Ce fichier **fait foi** : `test_courrier_lifecycle.py` doit rester aligné dessus.

## Modèle couvert

- `aite.courrier`
- `aite.courrier.step.history`

## TC-01 — Référence incrémentale `COUR-AAAA-NNNN`

Au lancement du circuit, le courrier reçoit une référence
`COUR-<année>-<NNNN>` (4 chiffres) générée par `ir.sequence`. Deux courriers
lancés successivement portent des numéros consécutifs.

## TC-02 — Objet requis

Créer un courrier sans `subject` échoue avec le message « Objet requis »
(`ValidationError`).

## TC-03 — Aperçu du circuit en brouillon

En brouillon, `preview_circuit_id` et `preview_step_ids` exposent le circuit
actif du type choisi (sans l'instancier). Pour un courrier de type `ENTR`,
l'aperçu correspond au circuit entrant standard (5 étapes, dont l'initiale).

## TC-04 — Brouillon non instancié

Un courrier en `state = draft` n'a **ni** référence, **ni** `circuit_id`,
**ni** `current_step_id`. Il apparaît dans le filtre Brouillons
(`[('state', '=', 'draft')]`).

## TC-05 — Lancement du circuit

`action_launch_circuit()` sur un brouillon :
- attribue la référence,
- copie `circuit_id` depuis le circuit actif du type,
- positionne `current_step_id` sur l'étape initiale,
- passe `state` à `nw`,
- crée la première entrée d'historique d'étape.

## TC-06 — Lecture seule une fois archivé

Lorsqu'un courrier atteint une étape finale (`_enter_step`), `state` passe à
`ar`. Toute modification d'un champ métier d'un courrier archivé est refusée
(`UserError`).

## TC-07 — Audit à la création

Le lancement du circuit écrit une entrée d'audit « Création courrier »
(`action_type = info`) rattachée au courrier.

## TC-08 — Audit à la modification

Modifier un champ métier d'un courrier déjà lancé écrit une entrée d'audit
« Modification courrier ».

## TC-09 — Confidentialité (`_check_courrier_access`)

Pour un courrier `Confidentiel`/`Secret` :
- un rôle habilité (manager) y a accès ;
- un opérationnel simple, ni responsable, ni créateur, ni membre du service,
  n'y a pas accès ;
- ce même opérationnel y a accès dès qu'il en est le responsable.

## Catégorie héritée du type

`courrier.category` est héritée du type (`entrant` / `sortant` / `interne`,
champ related stocké) et permet de filtrer l'espace courrier.
