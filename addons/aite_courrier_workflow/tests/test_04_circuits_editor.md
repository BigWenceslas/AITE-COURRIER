# Spécification de test — Éditeur de circuits AITE Courrier (lot 4)

> Ce fichier **fait foi** : `test_circuits_editor.py` doit rester aligné dessus.
> Toute évolution du paramétrage des circuits commence par une mise à jour de
> cette spec.

## Modèles couverts

- `aite.workflow.circuit`
- `aite.workflow.step`
- `aite.workflow.transition`

## TC-01 — Un seul circuit actif par type

Pour un type de courrier donné, un seul circuit peut être `active`. Créer
(ou activer) un second circuit actif sur le même type doit échouer
(`ValidationError`). Plusieurs circuits inactifs sont autorisés.

## TC-02 — Exactement une étape initiale

Un circuit doit comporter **exactement une** étape `is_initial`. Enregistrer
un circuit sans étape initiale (0) doit échouer (`ValidationError`).

## TC-03 — Au moins une étape finale

Un circuit doit comporter **au moins une** étape `is_final`. Enregistrer un
circuit sans étape finale doit échouer (`ValidationError`).

## TC-04 — Cocher l'étape initiale décoche les autres

Lorsqu'on positionne `is_initial = True` sur une étape, les autres étapes du
même circuit sont automatiquement remises à `is_initial = False`. Il reste
donc toujours au plus une étape initiale.

## TC-05 — Suppression d'un circuit (cascade)

Supprimer un circuit supprime en cascade toutes ses étapes **et** toutes ses
transitions.

## TC-06 — Suppression d'une étape (cascade des transitions)

Supprimer une étape supprime en cascade ses transitions **entrantes** et
**sortantes**. Les transitions ne référençant pas l'étape supprimée sont
conservées.

## TC-07 — Type non supprimable s'il est rattaché à un circuit

`type_id` est en `ondelete='restrict'` : tenter de supprimer un type de
courrier encore référencé par un circuit doit échouer (intégrité référentielle).

## TC-08 — Champs obligatoires

- Une étape sans `name` doit échouer.
- Une transition sans `label`, `step_from_id` ou `step_to_id` doit échouer.
- Une transition reliant une étape à elle-même doit échouer (`ValidationError`).

## TC-09 — Sécurité (CRUD)

- `group_admin` : lecture, écriture, création, suppression sur les trois modèles.
- Les groupes opérationnels (agent, assistant, manager, compta, signer,
  archive, audit) : lecture seule.

## TC-10 — Ergonomie de l'étape initiale (onchange)

Dans le formulaire du circuit (saisie en ligne des étapes) : cocher
« étape initiale » sur une nouvelle ligne **ne la décoche pas elle-même** ;
cocher l'initiale sur une autre étape décoche la précédente. À l'enregistrement,
il reste exactement une étape initiale.
