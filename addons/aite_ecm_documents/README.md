# aite_ecm_documents — Explorateur Documents

L'app **Documents** d'Odoo Enterprise (espaces de travail, cartes avec
vignettes, étiquettes, glisser-déposer, demandes, partage) devient
l'**explorateur de fichiers** de l'ECM. La fiche ECM reste la vue « métier »
(métadonnées, versions, réservation, relations, circuits) — les deux sont
liées dans les deux sens.

| Dans Documents | Dans l'ECM |
|---|---|
| Espaces de travail sous « ECM » | Plan de classement (créé et déplacé automatiquement) |
| Une carte par document (dernière version, vignette, étiquettes) | Document ECM et son historique de versions |
| « Attaché à » sur la carte | Ouvre la fiche ECM |
| Fichier déposé (*Charger*, glisser-déposer, réponse à une *Demande*) dans un espace ECM | **Document ECM créé automatiquement**, classé dans le dossier correspondant, v1 = le fichier déposé (aucune duplication) |
| Fichier remplacé sur une carte | Nouvelle version ECM (refusé si le document est finalisé / archivé) |
| Carte renommée ou déplacée | Titre / dossier ECM mis à jour |
| Suppression d'une carte gérée par l'ECM | Refusée : passer par la corbeille ECM (la carte est archivée, restaurée avec le document) |

Accès : **ECM › Documents › Explorateur de fichiers** (ouvre Documents sur
l'espace « ECM »), bouton **Explorateur** sur la fiche ECM, vignette
Documents dans le kanban ECM. Installation automatique avec la Fondation ECM ;
à l'installation, l'arborescence Documents complète est créée et les cartes
existantes (une par version auparavant) sont fusionnées en une carte par
document.

Les vignettes sont générées par l'app Documents lorsqu'elle affiche le fichier
(mécanisme natif) ; elles apparaissent ensuite aussi dans le kanban ECM.

Tests : `--test-tags /aite_ecm_documents` (7 cas, `tests/test_01_documents_bridge.md`).
