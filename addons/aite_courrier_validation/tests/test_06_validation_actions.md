# Spécification de test — Actions de validation (lot 6)

> Ce fichier **fait foi** : `test_validation.py` doit rester aligné dessus.
> Complète `test_05_workflow_engine.md` (moteur) côté exécution.

## Modèle couvert

- `aite.courrier` (actions `do_transition`, `action_reject`, `action_post_comment`)

## TC-01 — Validation nominale (forward)
Valider une transition avant déplace `current_step_id` vers l'étape cible, clôt
l'entrée d'historique courante et en ouvre une nouvelle, poste une notification
et trace un audit `ok`.

## TC-02 — Rejet avec commentaire
`action_reject(comment)` passe `state` à `rj`, **sans archiver**, en conservant
l'étape courante ; audit `warn`.

## TC-03 — Rejet sans commentaire
`action_reject('')` est bloqué : « Commentaire obligatoire pour cette action »
(`UserError`), l'état reste inchangé.

## TC-04 — Retour (backward)
Une transition arrière (avec commentaire si exigé) repositionne le courrier sur
l'étape précédente ; audit `warn`.

## TC-05 — Commentaire simple
`action_post_comment(body)` ajoute un message sans changer ni l'étape ni l'état ;
audit `info`.

## TC-06 — Horodatage et signature
Le message d'action porte l'auteur (nom complet) et la date au format
`JJ/MM HHhMM`, avec le libellé de l'action.

## TC-07/08/09 — Ciblage par utilisateur (`user_ids`)
Quand l'étape restreint `user_ids` :
- un utilisateur listé **et** habilité peut agir (TC-07) ;
- un utilisateur ayant le rôle mais **non listé** reçoit une `AccessError`
  (403) (TC-08) ;
- un utilisateur sans le rôle reçoit une `AccessError` (TC-09).

## TC-10 — Workflow complet « Facture » archivé (≥ 7 audits)
Dérouler le circuit facture jusqu'à l'étape finale archive le courrier
(`state = ar`) et produit au moins 7 entrées d'audit (création + transitions).

## TC-11 — Devis rejeté non archivé
Rejeter un devis le met en `rj` mais **pas** en `ar`.

## TC-12 — Entrant avec retour puis re-validation
Valider, retourner, puis revalider ramène le courrier à l'étape attendue.

## TC-13 — Actions bloquées sur courrier archivé
Sur un courrier archivé : aucune transition disponible, et `do_transition`
lève une `UserError`.

## TC-14 — Actions bloquées sur courrier rejeté
Sur un courrier rejeté : aucune transition disponible, et `do_transition`
lève une `UserError`.

## TC-15 — Commentaire obligatoire d'une transition
Une transition `comment_required` sans commentaire est refusée **côté serveur**
(`UserError` « Commentaire obligatoire pour cette action ») ; avec commentaire,
l'action passe. (L'assistant rend aussi le champ obligatoire côté UI.)
