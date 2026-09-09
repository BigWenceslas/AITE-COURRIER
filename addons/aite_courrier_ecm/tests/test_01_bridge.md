# Spécification de tests — aite_courrier_ecm (pont courrier ↔ ECM)

| Cas | Attendu |
|---|---|
| T01 Miroir à la création | Pièce créée avec une version → document ECM rattaché au courrier (`res_model='aite.courrier'`), type « Pièce de courrier », dossier `Courrier/<année>/<référence>`, confidentialité du courrier, **même `ir.attachment`** (aucune copie) |
| T02 Nouvelle version | v2 côté courrier → v2 côté ECM, même pièce jointe ; v2 côté ECM → v2 côté courrier |
| T03 Renommage et confidentialité | Renommer la pièce ou changer la confidentialité du courrier met à jour le jumeau |
| T04 Archivage | Courrier archivé → document ECM en statut « Archivé » (verrouillé) |
| T05 Suppression | Pièce supprimée → document ECM à la corbeille (traçabilité conservée) |
| T06 Reprise | `_ecm_mirror_all` reflète les pièces créées avant l'installation |
