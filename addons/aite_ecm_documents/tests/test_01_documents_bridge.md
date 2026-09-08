# Spécification de tests — aite_ecm_documents

| Cas | Attendu |
|---|---|
| T01 Miroir du plan | Création d'un dossier ECM → dossier Documents créé sous « ECM » ; changement de parent → carte dossier déplacée |
| T02 Une carte par document | v1 puis v2 → une seule carte active, `attachment_id` = pièce de la v2 |
| T03 Adoption | Carte créée dans l'espace ECM avec une pièce jointe → document ECM créé (dossier correspondant, v1 = la pièce, aucune duplication) ; carte rattachée (« Attaché à ») |
| T04 Remplacement | Nouvelle pièce jointe écrite sur la carte → version v2 du document ECM |
| T05 Verrou | Document finalisé : remplacement dans Documents refusé (UserError) |
| T06 Suppression | Suppression de la carte depuis Documents refusée (UserError) |
| T07 Étiquettes et corbeille | Étiquettes ECM reflétées sur la carte ; mise à la corbeille → carte archivée |
