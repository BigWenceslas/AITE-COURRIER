# Spécification de tests — aite_ecm_dossier

| Cas | Attendu |
|---|---|
| T01 Création | Référence DOS-AAAA-NNNN ; pièces instanciées depuis le type (5 pour l'agrément fournisseur) ; complétude 0 % |
| T02 Rattachement automatique | Document ECM créé avec `res_model='aite.ecm.dossier'` et le type attendu → première pièce manquante fournie ; complétude recalculée |
| T03 Clôture refusée | Dossier incomplet : `action_close` par un agent → UserError ; manager → OK |
| T04 Circuit | `action_open` lance le circuit du type : étape Instruction, historique créé ; transition par un agent habilité ; retour avec commentaire obligatoire → UserError sans commentaire ; étape finale → `wf_status='done'` |
| T05 Habilitation | Transition « Accorder l'agrément » par un agent (non manager) → AccessError |
