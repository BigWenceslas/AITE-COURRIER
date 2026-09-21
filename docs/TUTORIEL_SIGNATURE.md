# Tutoriel — signature électronique du courrier

> Faire signer une pièce de courrier avec **Odoo Sign**, et exiger cette
> signature à une étape du circuit. Paramétrage, parcours complet, limites
> connues et recette.
>
> Module `aite_courrier_sign` 18.0.1.0.0.

> ⚠️ **À lire avant de commencer.** Ce module exige **Odoo Enterprise** : il
> s'appuie sur l'app `sign`, absente de Community. Il n'a jamais été exécuté
> sur une instance réelle — il est exclu de la campagne de recette pour cette
> raison (`docs/recette/PLAN_DE_TEST.md` §5) et ne porte aucun test
> automatisé. Ce document décrit fidèlement ce que fait son code ; la
> vérification sur une instance Enterprise reste à faire. Le §8 liste ce qu'il
> faut regarder en priorité.

---

## 1. Ce que fait le module

Il relie deux choses qui existaient déjà : le circuit de traitement d'AITE
Courrier, et le parapheur électronique d'Odoo.

| Apport | Où |
| --- | --- |
| Bouton **Demander la signature** | en-tête de la fiche courrier |
| Case **Signature requise** sur une étape | éditeur de circuit |
| Blocage serveur des transitions en avant | moteur de validation |
| Bouton statistique **Signatures** | fiche courrier |
| Champ `courrier_id` sur les demandes Sign | app Sign |

Le parti pris : le parapheur reste Odoo Sign. Le module ne réimplémente ni la
signature, ni son horodatage, ni sa valeur probante — il les emprunte à une
brique native, conformément au positionnement « 100 % Odoo » de la suite.

### Ce qu'il ne fait pas

Ces limites sont structurelles, pas des anomalies. Les connaître évite de
promettre ce que le module ne tient pas :

- **Un seul signataire**, et c'est le **responsable du courrier** (à défaut,
  l'utilisateur courant). Ni choix du signataire, ni circuit de signature à
  plusieurs, ni signataire externe.
- **Le document doit être un PDF.** Un contrat en DOCX doit être converti
  avant.
- **Le document signé ne revient pas dans la GED.** Le PDF signé par Sign
  reste dans Sign. Les versions du document de courrier n'en gardent pas
  trace ; seul le lien vers la demande subsiste.
- **La zone de signature est fixe** : page 1, en bas à droite. Sur un contrat
  de douze pages, elle sera page 1.

---

## 2. Prérequis

| # | À vérifier | Comment |
| --- | --- | --- |
| 2.1 | Odoo **Enterprise** | l'app **Signature** (`sign`) apparaît dans Applications |
| 2.2 | L'app Sign est **installée** | Applications → *Signature* → Installer |
| 2.3 | Le serveur de messagerie est configuré | Paramètres → Technique → Serveurs de messagerie sortants → *Tester la connexion* |
| 2.4 | `web.base.url` est correct | c'est lui qui construit le lien de signature envoyé par e-mail |

Le point 2.3 n'est pas optionnel : sans envoi d'e-mail, le signataire ne reçoit
jamais son lien, et la demande reste en attente sans que personne ne le sache.

---

## 3. Installer le module

```powershell
net stop odoo-server-18.0

& "C:\Program Files\Odoo 18\python\python.exe" `
  "C:\Program Files\Odoo 18\server\odoo-bin" `
  -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
  -i aite_courrier_sign --stop-after-init

net start odoo-server-18.0
```

Il tire `aite_courrier_core`, `aite_courrier_workflow`, `aite_courrier_ged`,
`aite_courrier_validation` et `sign`.

✅ **Vérification** — ouvrir un circuit (Courrier → Configuration → Circuits) :
la liste des étapes porte désormais une colonne **Signature requise**.

---

## 4. Paramétrer le circuit

C'est l'étape que l'on oublie, et sans elle **le bouton n'apparaît jamais**.

Courrier → Configuration → **Circuits** → ouvrir le circuit → onglet des
étapes → cocher **Signature requise** sur l'étape voulue.

Exemple, sur un circuit de courrier sortant :

| Étape | Signature requise |
| --- | --- |
| Rédaction | ☐ |
| Relecture | ☐ |
| **Approbation direction** | ☑ |
| Envoi | ☐ |
| Archivage | ☐ |

> **Le bouton « Demander la signature » ne s'affiche que lorsque le courrier
> est *sur* une étape cochée**, et disparaît dès qu'une signature est
> complétée. Sur une étape non cochée, il n'y a aucun moyen de demander une
> signature depuis la fiche. C'est voulu — l'exigence de signature est une
> propriété du circuit, pas une action libre — mais c'est déroutant la
> première fois.

---

## 5. Le parcours

### 5.1 Préparer le courrier

1. Créer le courrier, **lancer le circuit** (une référence `COUR-AAAA-NNNN`
   est attribuée).
2. Onglet **Documents** : ajouter la pièce à signer, **en PDF**, et la
   téléverser.
3. Faire avancer le courrier jusqu'à l'étape marquée *Signature requise*.

### 5.2 Demander la signature

Le bouton **Demander la signature** apparaît dans l'en-tête, en orange.

Ce qui se produit alors, dans l'ordre :

1. Le module retient la **dernière version PDF** parmi les documents du
   courrier — la plus récemment téléversée, tous documents confondus.
2. Il en fait une **copie**, qui devient le modèle Sign. L'original de la GED
   n'est pas touché.
3. Il crée un **modèle Sign** nommé `Signature — COUR-2026-0042`, avec une
   zone de signature obligatoire pré-positionnée page 1, en bas à droite.
4. Il crée la **demande** au nom du **responsable du courrier**, rattachée au
   courrier par `courrier_id`.
5. Il consigne l'opération dans le **fil de discussion** du courrier et dans
   le **journal d'audit**.
6. Il ouvre la fiche de la demande Sign.

### 5.3 Côté signataire

Le signataire reçoit le lien d'Odoo Sign par e-mail, ouvre le document, signe.
La demande passe à l'état **Signé**.

Sur la fiche du courrier, le bouton statistique **Signatures** donne accès à
toutes les demandes rattachées.

### 5.4 La garde

Tant qu'aucune demande **complétée** n'est rattachée au courrier, toute
transition **en avant** depuis l'étape marquée est refusée :

> Cette étape exige une signature électronique : aucune demande de signature
> complétée n'est rattachée au courrier. Utilisez « Demander la signature »
> puis attendez sa complétion.

Deux précisions qui comptent :

- Le contrôle est **côté serveur**, dans `do_transition`. Il ne dépend pas de
  l'interface : un appel RPC ou un script ne le contourne pas.
- Les transitions **en arrière** (retourner, rejeter) restent possibles. Une
  signature manquante ne bloque pas un renvoi au rédacteur.

Chaque refus laisse une trace `err` dans le journal d'audit — utile pour
comprendre après coup pourquoi un dossier a stagné.

---

## 6. Suivi et traçabilité

| Où | Ce qu'on y trouve |
| --- | --- |
| Fiche courrier, bouton **Signatures** | toutes les demandes rattachées, et leur état |
| Fiche courrier, fil de discussion | « ✍️ Demande de signature envoyée à … » |
| Journal d'audit | *Demande de signature* (info) et *Action bloquée* (err) |
| App Signature | les demandes, avec leur champ **Courrier** |

Depuis l'app Signature, le champ `courrier_id` permet de filtrer ou de
regrouper les demandes par courrier — pratique pour un suivi transverse.

---

## 7. Dépannage

| Message | Cause | Remède |
| --- | --- | --- |
| Le bouton n'apparaît pas | l'étape courante n'est pas cochée *Signature requise* | §4 |
| Le bouton a disparu | une signature est déjà complétée sur ce courrier | c'est normal : la garde est levée |
| « Aucune version PDF n'est disponible » | les pièces sont en DOCX, XLSX, image… | convertir en PDF et téléverser |
| « Le signataire … n'a pas d'adresse e-mail » | le responsable n'a pas d'adresse sur son contact | renseigner l'e-mail du partenaire lié |
| « Cette étape exige une signature électronique » | garde §5.4 | demander la signature, attendre la complétion |
| Le signataire ne reçoit rien | serveur de messagerie non configuré | §2.3 |
| Le lien de signature pointe au mauvais endroit | `web.base.url` erroné | §2.4 |

---

## 8. À vérifier sur une instance Enterprise

Le module n'ayant jamais tourné, voici ce que je regarderais en premier, dans
cet ordre — ce sont les points où le code fait des hypothèses sur Odoo Sign.

1. **L'envoi de la demande.** Le module crée l'enregistrement `sign.request`
   mais n'appelle aucune action d'envoi explicite. Vérifier que le signataire
   reçoit bien son e-mail ; sinon, il manque probablement un appel du type
   `request.action_sent()` après la création.
2. **Les identifiants XML de Sign.** Le code cherche
   `sign.sign_item_role_default` et `sign.sign_item_type_signature`. S'ils ont
   changé de nom dans votre version d'Odoo, la zone de signature n'est pas
   créée — la demande part quand même, mais le signataire doit placer sa
   signature lui-même.
3. **Le positionnement de la zone**, page 1 en bas à droite : vérifier qu'il
   tombe au bon endroit sur vos documents types.
4. **La garde sur une étape marquée** : tenter une transition en avant sans
   signature doit être refusée, y compris par RPC.
5. **Le comportement à plusieurs signatures** : la garde accepte **n'importe
   quelle** demande complétée rattachée au courrier. Une signature obtenue à
   une étape antérieure, sur un autre document, lève donc la garde d'une étape
   ultérieure. À valider : est-ce le comportement attendu ?

Les points 1 et 2 sont ceux qui empêcheraient purement et simplement le
parcours de fonctionner. Les points 3 et 5 relèvent de l'adéquation au besoin.

---

## 9. Scénario de recette

À jouer sur une instance Enterprise, avec un compte disposant d'une adresse
e-mail valide.

| # | Action | Attendu | ☐ |
| --- | --- | --- | --- |
| 1 | Installer `aite_courrier_sign` | colonne *Signature requise* dans l'éditeur de circuit | ☐ |
| 2 | Cocher *Signature requise* sur une étape | enregistré | ☐ |
| 3 | Créer un courrier, lancer le circuit | référence attribuée | ☐ |
| 4 | Ajouter une pièce **DOCX**, aller sur l'étape, cliquer le bouton | refus : « Aucune version PDF n'est disponible » | ☐ |
| 5 | Ajouter une pièce **PDF**, recliquer | la fiche de la demande Sign s'ouvre | ☐ |
| 6 | Ouvrir le PDF dans Sign | zone de signature présente, page 1 en bas à droite | ☐ |
| 7 | Vérifier la boîte du signataire | e-mail de demande reçu | ☐ |
| 8 | **Sans signer**, tenter une transition en avant | refus explicite ; trace `err` au journal d'audit | ☐ |
| 9 | Tenter une transition **en arrière** | autorisée | ☐ |
| 10 | Signer depuis le lien reçu | demande à l'état *Signé* | ☐ |
| 11 | Recharger la fiche du courrier | le bouton *Demander la signature* a disparu | ☐ |
| 12 | Retenter la transition en avant | autorisée | ☐ |
| 13 | Bouton statistique **Signatures** | la demande est listée | ☐ |
| 14 | App Signature, champ *Courrier* | pointe sur le bon courrier | ☐ |
| 15 | Journal d'audit | *Demande de signature* (info) et *Action bloquée* (err) présents | ☐ |
| 16 | Onglet *Documents* du courrier | ⚠️ le PDF **signé** n'y figure pas — limite connue (§1) | ☐ |

---

## 10. Pistes d'évolution

Si la recette confirme que les limites du §1 gênent l'usage réel, voici ce
qu'elles coûteraient, par ordre de valeur :

| Évolution | Effort | Pourquoi |
| --- | --- | --- |
| Rapatrier le PDF signé comme nouvelle version GED | moyen | sans cela, la preuve signée vit hors du dossier de courrier |
| Choisir le signataire, en accepter plusieurs | moyen | un contrat se signe rarement à une seule main |
| Exiger une signature **sur le document courant** plutôt que n'importe laquelle | faible | referme la porte ouverte au §8.5 |
| Positionner la zone de signature par type de courrier | faible | la page 1 ne convient pas à tous les modèles |
| Couverture de tests | moyen | le module n'en a aucun |

---

*AITE Consulting — tutoriel signature électronique.*
