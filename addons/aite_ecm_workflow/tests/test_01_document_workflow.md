# Spécification de tests — circuits sur documents ECM (aite_ecm_workflow)

| Cas | Attendu |
|---|---|
| T01 Lancement | Procédure avec fichier : `wf_has_circuit` vrai, `action_wf_launch` → étape Rédaction, historique créé ; sans fichier → UserError |
| T02 Transitions | Agent transmet (Rédaction → Vérification) ; retour sans commentaire → UserError ; manager approuve → étape finale, `wf_status = done`, document **finalisé** |
| T03 Habilitation | Agent tente d'approuver → AccessError ; agent tente d'ajouter une version pendant l'étape Vérification → UserError |
| T04 Rejet | Rejet motivé par le manager → `wf_status = rejected`, document reste en brouillon |
