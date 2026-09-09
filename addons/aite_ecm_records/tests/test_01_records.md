# Spécification de tests — aite_ecm_records

| Cas | Attendu |
|---|---|
| T01 Règle applicable | Facture dans « Finance » → règle OHADA 10 ans ; contrat → règle « Contrats » (départ = métadonnée `contrat_date_fin`) ; règle imposée l'emporte |
| T02 Échéance et cycle | Départ « finalisation » + 10 ans → échéance ; document non finalisé → état « utilité courante » en attente du déclencheur ; échéance passée → « échue » ; sort final « conserver » → « conservation définitive » |
| T03 Gel juridique | Gel actif sur un dossier → tous ses documents gelés : modification, corbeille et suppression refusées ; levée → protections retirées |
| T04 Bordereau | « Rassembler » ne prend que les documents échus, à éliminer et non gelés ; validation par un manager ; exécution → documents supprimés, lignes conservées avec empreinte, certificat déposé |
| T05 Protection | Suppression directe d'un document sous conservation refusée (passer par un bordereau) ; document gelé jamais éliminé même dans un bordereau validé |
| T06 Archives physiques | Boîte créée avec code séquentiel, prêt et retour, documents liés |
