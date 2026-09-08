# Spécification de test — Gestion documentaire (lot 3 / ged)

> Ce fichier **fait foi** : `test_ged.py` doit rester aligné dessus.

## Modèles couverts

- `aite.courrier.document`
- `aite.courrier.document.version`
- `aite.courrier.folder`

## TC-01 — Confidentialité héritée

`document.confidentiality_id` est héritée du courrier rattaché. Si la
confidentialité du courrier change, celle du document suit automatiquement.

## TC-02 — Versionnage v1/v2

Deux téléversements successifs créent `v1` puis `v2`. `version_count` vaut 2,
`latest_version_id` pointe sur `v2`, et `v1` est conservée.

## TC-03 — Verrouillage des versions finales/archivées

Un document `final` ou `archived`, ou rattaché à un courrier archivé, est
`is_locked = True` : ajouter une version est refusé (`AccessError`) et
supprimer une version est refusé (`UserError`).

## TC-04 — Contrôle de format et de taille

- Un fichier dont l'extension n'est pas PDF/DOCX/XLSX est refusé
  (`ValidationError`, message clair).
- Un fichier dépassant la taille maximale est refusé (`ValidationError`).

## TC-05 — Audit ajout / suppression

- Un téléversement écrit un audit « Ajout pièce jointe » (version, nom, taille).
- La suppression d'une version écrit un audit « Suppression pièce jointe »,
  conservé même après suppression du fichier.

## TC-06 — Contrat d'accès `_check_document_access`

- `read` : respecte la confidentialité héritée (manager autorisé, opérationnel
  tiers refusé sur un document confidentiel, responsable autorisé).
- `write` : refusé dès que le document est verrouillé.

## TC-07 — Suppression interdite si verrouillé

La suppression d'une version d'un document verrouillé est refusée, et l'audit
de suppression n'est alors pas créé.

## TC-08 — Visibilité opérationnelle (règle d'enregistrement)

Un document **sans** niveau de confidentialité est lisible par un opérationnel.
Un document `Confidentiel`/`Secret` d'un tiers ne l'est pas (sauf responsable,
créateur ou membre du service).
