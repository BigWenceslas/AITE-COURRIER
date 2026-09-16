# Cachet de traitement en fin de circuit — étude et proposition

**Demande de la revue.** Marquer un courrier arrivé au bout de son circuit
par un cachet, à la manière du ruban « Archivé » d'Odoo, reprenant les
intervenants qui l'ont validé.

Ce document rend compte du benchmark, de ce que la suite sait déjà faire, et
propose une mise en œuvre en trois niveaux dont seul le premier est
indispensable.

---

## 1. Ce que font les autres

| Produit | Mécanisme | Ce qu'on en retient |
| --- | --- | --- |
| **Odoo natif** | Ruban `web_ribbon` (Archivé, Brouillon, Payé) piloté par un champ ; suivi des modifications dans le fil de discussion | Le ruban est purement visuel et ne porte aucune histoire. Le « qui a fait quoi » vit ailleurs, dans le chatter — et s'y noie. |
| **Odoo Sign** | Certificat de signature : liste des signataires, horodatage, adresse IP, joint au PDF | Le modèle à suivre pour la **valeur probante** : un document annexe, pas une image sur la page. |
| **Maarch Courrier** | Circuit de visa puis signature ; les intervenants **visent**, le dernier **signe** ; apposition d'une griffe ou d'une signature électronique | Distingue nettement le **visa** (avis hiérarchique) de la **signature** (engagement). Notre circuit fait la même chose sans le nommer. |
| **Parapheurs publics** (i-Parapheur et assimilés) | Chaque étape appose une annotation datée et nominative ; export d'un dossier de preuve | Le cachet est **cumulatif** : il grandit à chaque étape plutôt que d'être écrit une fois à la fin. |
| **GED du marché** (DocuWare, Therefore, M-Files) | Fonction « tampon » : un cachet paramétrable — texte, date, utilisateur — apposé sur la page | Le cachet **sur le fichier** est attendu par les utilisateurs métier, parce qu'il survit à l'impression et à l'envoi par courriel. |
| **Cachet électronique visible (CEV / 2D-Doc)** | Code à deux dimensions apposé sur le document, scellant les données clés par une signature électronique ; vérifiable au smartphone | Cadre français, hors services de confiance qualifiés eIDAS, mais admis comme preuve. La bonne cible **si** un tiers doit pouvoir vérifier sans accéder à l'application. |

Deux enseignements structurent la proposition :

1. **Le cachet à l'écran et le cachet sur le fichier ne servent pas le même
   besoin.** Le premier renseigne l'agent devant sa liste ; le second suit le
   document dehors. Les produits sérieux font les deux, séparément.
2. **La valeur probante ne vient jamais de l'image du cachet**, mais du
   journal qui l'adosse. Odoo Sign et les parapheurs publics émettent tous un
   document de preuve distinct du visuel.

---

## 2. Ce que la suite sait déjà faire

L'essentiel de la matière existe : **il n'y a presque rien à collecter, tout
est déjà enregistré.**

| Brique en place | Ce qu'elle apporte au cachet |
| --- | --- |
| `aite.courrier.step.history` | Une ligne par étape franchie : étape, **intervenant**, entrée, sortie, libellé de transition, commentaire. C'est exactement la liste des valideurs demandée. |
| `aite.courrier.audit.log` | Journal immuable, déjà éprouvé, pour adosser le cachet. |
| Ruban « Archivé » (`web_ribbon`) dans la fiche courrier | Le point d'accroche visuel existe déjà, à la ligne 50 de la vue formulaire. |
| `aite_ecm_sae` | Scellement SHA-256 en chaîne, horodatage RFC 3161, attestation d'intégrité, rapport de preuve. La couche probante est faite. |
| `aite_courrier_reponse` | Fusion de modèles et génération de PDF versionnés — le moteur d'apposition sur fichier est déjà là. |

Autrement dit : le niveau 1 ci-dessous est de l'assemblage, pas du
développement neuf.

---

## 3. Proposition

### Niveau 1 — Le cachet à l'écran ✅ *livré*

> **Arbitré en revue le 16/09/2026** : le tiers voit les **fonctions** seules,
> l'interne voit **nom et fonction**. Implémenté et couvert par deux tests —
> `test_tc10b_processing_stamp` (ordre des visas, fonction présente sur
> chacun, séparation des deux lectures) et
> `test_12_stamp_shows_functions_never_names`, qui échoue si le nom d'un
> agent apparaît dans la page servie au tiers.

Un **ruban « Traité »** sur la fiche du courrier dès que le circuit atteint
son étape finale, et sous le ruban un **cartouche de visa** : une ligne par
intervenant, dans l'ordre du circuit.

```
┌────────────────────────────────────────────────┐
│  TRAITÉ — COUR-2026-0123        le 14/09/2026  │
├────────────────────────────────────────────────┤
│  Réception    Aurélie Mbarga      02/09  09:14 │
│  Qualification Nadège Fotso       02/09  11:40 │
│  Validation   Patrick Essomba     05/09  16:02 │
│  Signature    Gisèle Atangana     12/09  08:30 │
└────────────────────────────────────────────────┘
```

Le cartouche se **calcule** depuis `step.history` : aucun champ à saisir,
aucune donnée dupliquée, et il reste juste même si l'historique est corrigé.

Un onglet « Cachet » dans la fiche, et le même bloc repris sur le portail
côté tiers, qui voit ainsi que sa demande a été traitée et par combien de
mains — sans les noms si le cloisonnement l'exige (à trancher, § 5).

**Charge estimée : 1,5 à 2 jours**, tests compris.

### Niveau 2 — Le cachet apposé sur le PDF *(recommandé en second temps)*

À la clôture, génération d'une **page de cachet** annexée au PDF de la pièce
maîtresse — ou d'un bandeau en pied de première page, au choix du client.
Le moteur de rendu QWeb → PDF est déjà utilisé par `aite_courrier_reponse` ;
la nouvelle version du document est enregistrée normalement, donc versionnée
et, si `aite_ecm_sae` est installé, scellée au passage.

C'est ce que demandent les utilisateurs quand ils disent « cachet » : quelque
chose qui survit à l'impression.

**Charge estimée : 3 à 4 jours.** Dépendance : `wkhtmltopdf` sur le serveur
(déjà signalé comme prérequis non installé dans le plan de test).

### Niveau 3 — Le cachet vérifiable par un tiers *(à arbitrer)*

Un **code à deux dimensions** dans le cachet, renvoyant à une page publique
de vérification qui rejoue la chaîne de preuve `aite_ecm_sae` : référence,
empreinte, horodatage, liste des visas. Un destinataire externe vérifie
l'authenticité sans compte ni accès à l'application.

Le vrai 2D-Doc réglementaire suppose un certificat auprès d'une autorité
référencée : **hors périmètre à ce stade**. Ce qui est proposé ici est un
cachet vérifiable *maison*, adossé au scellement déjà en place — honnête sur
ce qu'il prouve, sans prétendre au cadre français du CEV.

**Charge estimée : 4 à 5 jours**, plus l'arbitrage juridique.

---

## 4. Modèle de données

**Aucune nouvelle table pour le niveau 1.** Quatre champs calculés sur
`aite.courrier` :

| Champ | Type | Rôle |
| --- | --- | --- |
| `is_processed` | booléen stocké | Pilote le ruban ; vrai quand le circuit atteint son étape finale |
| `processed_date` | date-heure stockée | Date du cachet |
| `visa_ids` | relation calculée vers `step.history` | Les lignes du cartouche, ordonnées |
| `visa_summary` | texte calculé | Version imprimable, pour le PDF et le portail |

Les niveaux 2 et 3 ajoutent un modèle de rendu (`ir.actions.report`) et, pour
le niveau 3, un jeton de vérification publique — même mécanique que les liens
de partage de `aite_ecm_share`, déjà éprouvée.

---

## 5. Ce qu'il faut trancher avant de coder

1. ✅ **Qu'est-ce qu'un « valideur » ?** — *tranché : toutes les étapes
   franchies, les retours compris. Un cachet qui cache les allers-retours
   n'est plus un historique.*
2. ✅ **Le tiers voit-il les noms ?** — *tranché en revue : fonctions et
   dates côté portail, nom et fonction en interne.* La « fonction » est le
   rôle AITE au titre duquel la personne a agi : parmi les rôles habilités
   de l'étape, celui qu'elle porte réellement ; à défaut les rôles de
   l'étape, puis le nom de l'étape.
3. **Le cachet est-il rejouable ?** Si l'historique est corrigé après coup,
   le cachet du PDF déjà généré ne bouge plus. Il faut décider si l'on
   régénère (et l'on conserve les deux versions) ou si le cachet est figé
   à la clôture.
4. **Niveau 3 : qui porte la responsabilité de la vérification ?** Une page
   publique qui dit « ce document est authentique » engage l'entreprise.

---

## 6. Où l'on en est

Le **niveau 1 est livré et vérifié** : ruban « Traité » qui prime sur
« Archivé », onglet *Cachet* en interne, tampon sur le portail. Rien n'est
stocké en double — seuls `is_processed` et `processed_date` le sont, pour
que le ruban et les filtres soient interrogeables ; le reste se lit dans
l'historique des étapes, qui demeure la source.

Le **niveau 2** attend deux choses : `wkhtmltopdf` sur le serveur, et la
question 3 du § 5 (cachet figé à la clôture, ou régénéré). C'est là que les
utilisateurs métier verront la différence, puisque le cachet survivra alors
à l'impression et à l'envoi par courriel.

Le **niveau 3** reste une décision produit à part : il touche au juridique
bien plus qu'à la technique.

Garder le **niveau 3** pour une décision produit à part : il touche au
juridique bien plus qu'à la technique.
