# Spécification de tests — aite_ecm_sae (valeur probante)

| Cas | Attendu |
|---|---|
| T01 Scellement | Dépôt de version → sceau `version` avec empreinte du fichier et de l'événement ; finalisation → sceau `final` ; chaînage : chaque sceau porte l'empreinte du précédent |
| T02 Immuabilité | `write` et `unlink` sur un sceau → UserError |
| T03 Vérification saine | `verify_chain` et `verify_documents` ne signalent rien ; `action_verify_integrity` met l'état à « Intègre » et pose un sceau `check` |
| T04 Altération détectée | Contenu de la pièce jointe modifié hors ECM → `verify_documents` signale « contenu modifié » ; charge utile d'un sceau modifiée → `verify_chain` signale « sceau altéré » et « chaînage rompu » |
| T05 Horodatage | Jeton interne reproductible (HMAC) ; jeton falsifié → « horodatage invalide » |
| T06 Export SEDA | Paquet ZIP contenant `manifest.xml` (bien formé, empreintes = fichiers), `content/`, `journal_de_preuve.json`, `LISEZMOI.txt` ; un sceau `export` est posé |
