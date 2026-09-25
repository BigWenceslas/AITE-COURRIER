# Tutoriel — signature électronique du courrier sur Odoo Community

> Faire signer une pièce de courrier sur **Odoo 18 Community**, et exiger
> cette signature à une étape du circuit. Installation, paramétrage, parcours
> complet, sécurité, limites et recette.
>
> Module `aite_courrier_sign_oca` 18.0.1.0.0, adossé au module communautaire
> OCA `sign_oca` 18.0.1.4.3. Pour Odoo Enterprise et son app Sign, voir
> `TUTORIEL_SIGNATURE.md`.

---

## 1. Ce que fait le module

Odoo Community n'a pas d'app de signature. L'Odoo Community Association
(OCA) en publie une, `sign_oca` : un parapheur qui envoie un PDF par e-mail,
le fait signer dans le navigateur et journalise chaque geste. Le module
`aite_courrier_sign_oca` la relie au circuit de traitement du courrier.

| Apport | Où |
| --- | --- |
| Case **Signature requise** sur une étape | Courrier › Configuration › Circuits de traitement |
| Bouton **Demander la signature** | en-tête de la fiche courrier |
| Signature depuis un lien reçu par e-mail, **sans compte Odoo** | navigateur du signataire |
| **PDF signé versé en GED**, en nouvelle version | onglet Documents du courrier |
| Blocage serveur des transitions en avant | moteur de validation |
| Bouton statistique **Signatures** | fiche courrier |
| Champs **Courrier**, **Étape du circuit**, **Pièce source**, **Signataires** | fiche de la demande de signature |
| Traces *Demande de signature*, *Action bloquée*, *Signature complétée* | Courrier › Audit › Journal d'audit |

### Ce qu'il ne fait pas

- **Un seul signataire** : le **responsable du courrier** (à défaut,
  l'utilisateur qui demande). Pas de circuit de signature à plusieurs.
- **PDF uniquement.** Un DOCX doit être converti avant.
- **Zone de signature fixe** : page 1, en bas à droite.
- **Signature électronique simple** (§8) : pas de certificat qualifié.

---

## 2. Prérequis

| # | À vérifier | Comment |
| --- | --- | --- |
| 2.1 | Le paquet contient `oca\sign_oca` | dossier livré avec la suite, à côté de `addons\` |
| 2.2 | Le serveur de messagerie sortant fonctionne | Paramètres › Technique › Serveurs de messagerie sortants › *Tester la connexion* |
| 2.3 | `web.base.url` est la bonne adresse | Paramètres › Technique › Paramètres système ; c'est elle qui construit le lien envoyé au signataire |
| 2.4 | `aite_courrier_sign` n'est pas « à installer » | Applications, filtre retiré, chercher `aite_courrier_sign` |

**2.2 n'est pas optionnel** : sans e-mail, le signataire ne reçoit jamais son
lien et la demande reste en attente sans que personne ne le sache.

**2.4** : `aite_courrier_sign` (variante Enterprise) et
`aite_courrier_sign_oca` s'excluent. Si le premier est resté bloqué « à
installer » (bouton *Annuler l'installation* visible), l'installation du
second est refusée :

```
odoo.exceptions.UserError: Les modules "AITE Courrier - Signature électronique (OCA)"
et "AITE Courrier - Signature électronique" sont incompatibles.
```

Cliquer **Annuler l'installation** sur `aite_courrier_sign`, puis reprendre
au §3. Cet échec remet d'ailleurs lui-même le module bloqué à « non
installé » : relancer la commande suffit aussi.

---

## 3. Installer

1. Copier le dossier **`oca\sign_oca`** du paquet dans le dossier des
   modules, à côté des `aite_*`. Un seul exemplaire : ne pas le copier à
   deux endroits de `addons_path`.
2. Installer, service arrêté (PowerShell administrateur) :

   ```powershell
   net stop odoo-server-18.0

   & "C:\Program Files\Odoo 18\python\python.exe" `
     "C:\Program Files\Odoo 18\server\odoo-bin" `
     -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
     -i aite_courrier_sign_oca --stop-after-init

   net start odoo-server-18.0
   ```

   La commande installe aussi `sign_oca` et deux modules standard d'Odoo,
   `base_sparse_field` et `web_editor`. Aucune bibliothèque Python à ajouter :
   `sign_oca` utilise celles qu'Odoo embarque (reportlab, PyPDF2).

✅ **Vérification** : Courrier › Configuration › Circuits de traitement,
ouvrir un circuit : la liste des étapes porte une colonne **Signature
requise**. Pour l'administrateur, une app **Signature** apparaît aussi : c'est
celle de `sign_oca`.

---

## 4. Paramétrer le circuit

Sans cette étape, **le bouton n'apparaît jamais**.

Courrier › Configuration › **Circuits de traitement** › ouvrir le circuit ›
cocher **Signature requise** sur l'étape voulue.

| Étape (courrier sortant) | Signature requise |
| --- | --- |
| Rédaction | ☐ |
| Relecture | ☐ |
| **Approbation direction** | ☑ |
| Envoi | ☐ |
| Archivage | ☐ |

Le bouton **Demander la signature** s'affiche quand le courrier est *sur*
une étape cochée, pour les personnes **habilitées à agir sur cette étape**
(ses rôles, et ses utilisateurs si l'étape en désigne), tant que la signature
n'est pas obtenue. Le **signataire** est le **responsable** du courrier :
renseignez-le, avec une adresse e-mail sur sa fiche contact.

Option : Paramètres › **Signature OCA** › *Envoyer aux signataires une copie
du document complété signé*. Désactivée par défaut ; la page de fin de
signature annonce pourtant cet e-mail (texte de `sign_oca`).

---

## 5. Le parcours

### 5.1 Préparer le courrier

1. Créer le courrier, choisir son **responsable** (le signataire), **lancer
   le circuit**.
2. Onglet **Documents** : ajouter la pièce à signer, **en PDF**.
3. Faire avancer le courrier jusqu'à l'étape *Signature requise*.

### 5.2 Demander la signature

Bouton orange **Demander la signature**. Le module :

1. retient la **dernière version PDF** parmi les pièces du courrier ;
2. crée la demande `Signature — COUR-2026-0042`, avec **sa propre copie** du
   PDF — la version GED n'est pas touchée ;
3. place une zone de signature obligatoire page 1, en bas à droite ;
4. envoie au responsable l'e-mail *Nouveau document à signer*, avec son lien ;
5. l'écrit dans le fil du courrier (« Demande de signature envoyée à … ») et
   au journal d'audit ;
6. ouvre la fiche de la demande : **Courrier**, **Étape du circuit**,
   **Pièce source**, **Signataires** (« Gisèle Atangana (en attente) »).

Sur cette fiche, le tableau des signataires reste vide pour le demandeur :
chaque ligne porte le jeton du lien de signature, réservé au signataire
(§7). Le champ **Signataires** donne l'information utile.

### 5.3 Côté signataire

Il n'a besoin d'aucun compte Odoo : le lien suffit.

1. Il ouvre le lien de l'e-mail : le PDF s'affiche, zone à signer en couleur,
   repère *Click to start* à gauche.
2. Il clique la zone : une fenêtre propose de signer en **Automatique** (son
   nom en écriture manuscrite), en **Dessinant** ou en **Chargeant** une
   image ; il confirme par **Adopter & Signer**.
3. Il clique **Valider et envoyer le document** : page *Merci d'avoir signé*.

Un signataire qui a un compte Odoo retrouve aussi ses documents à signer
sous l'icône crayon de la barre du haut.

### 5.4 Le PDF signé revient dans le courrier

Dès la signature, le PDF signé devient une **nouvelle version** de la pièce
d'origine, nommée `<pièce>_signe.pdf` (ex. `convention_signe.pdf`, v2) ; la
version d'origine reste consultable. Le fil du courrier et le journal d'audit
reçoivent « Demande « … » signée par … ».

Deux cas où la version ne peut pas être créée — le PDF signé est alors
**joint au fil du courrier** et le journal le précise :

- la pièce est **verrouillée** (finalisée, archivée, courrier archivé) ;
- le **demandeur** n'a plus accès au courrier (confidentialité) : la version
  est créée en son nom, avec ses droits, jamais avec ceux du signataire.

### 5.5 La garde

Tant que la signature **du passage en cours sur l'étape** n'est pas obtenue,
toute transition **en avant** est refusée :

> Cette étape exige une signature électronique : aucune demande n'a été
> signée depuis l'arrivée du courrier sur l'étape. Utilisez « Demander la
> signature » puis attendez la signature.

- Le contrôle est **côté serveur** : un appel RPC ou un script ne le
  contourne pas.
- Retourner et rejeter restent possibles.
- Chaque refus est tracé `err` au journal d'audit, **dans une transaction à
  part** : l'annulation qui accompagne le refus ne l'efface pas.
- **Une signature par passage** : un courrier renvoyé en arrière puis revenu
  sur l'étape, ou arrivé sur une seconde étape *Signature requise*, doit être
  signé de nouveau. Une signature antérieure ne vaut que pour son passage.

### 5.6 Redemander, quitter l'étape

- **Redemander** (changement de responsable, e-mail égaré) annule la demande
  en attente et en envoie une nouvelle ; l'ancien lien ne permet plus de
  signer.
- Quand le courrier **quitte l'étape** (retour, par exemple), la demande en
  attente est annulée et le fil l'indique.

---

## 6. Suivi et traçabilité

| Où | Ce qu'on y trouve |
| --- | --- |
| Fiche courrier, bouton **Signatures** | toutes les demandes du courrier, annulées comprises |
| Fiche courrier, fil | demande envoyée, demande remplacée ou annulée, signature avec le PDF signé |
| Journal d'audit | *Demande de signature* (info), *Action bloquée* et *Tentative non autorisée* (err), *Signature complétée* (ok) |
| App Signature (groupes Signature, dont l'administrateur) | les demandes, filtrables par **Courrier** ; le journal `sign_oca` de chaque demande : création, envoi, consultation, signature, annulation, avec date et adresse IP |

---

## 7. Sécurité

Le module corrige trois ouvertures de `sign_oca` sur les données du courrier :

| `sign_oca` seul | Avec `aite_courrier_sign_oca` |
| --- | --- |
| Tout utilisateur interne lit **toutes** les demandes, PDF compris | chacun ne lit que celles dont il est demandeur, abonné ou signataire |
| Des collègues rattachés à une **même société partenaire** lisent leurs lignes signataires, donc leurs **jetons**, et peuvent signer les uns pour les autres | une ligne signataire n'est lisible que par le signataire |
| `/my/sign/<id>/download` sert **n'importe quelle** demande à tout utilisateur connecté | réservé à qui peut lire la demande ou la signer |

Point d'attention qui demeure : les droits **Signature** de `sign_oca`
(*Utilisateur*, *Gestionnaire*, *Administrateur*) permettent de signer à la
place d'autrui. Les réserver aux administrateurs de la signature ; les
agents du courrier n'en ont pas besoin — le module travaille pour eux.

---

## 8. Valeur de la signature

C'est une **signature électronique simple** au sens du règlement eIDAS :
l'image de la signature est apposée dans le PDF ; la preuve tient au
journal (date, adresse IP, jeton du lien), à l'empreinte du PDF après chaque
signature et à une chaîne d'inaltérabilité (SHA-256) qui relie chaque
signature à la précédente. Il n'y a ni certificat qualifié, ni signature
cryptographique du PDF (PAdES).

Elle convient aux visas, validations et approbations internes. Pour un acte
qui exige une signature avancée ou qualifiée, passer par un prestataire de
confiance.

`sign_oca` est au statut **Beta** à l'OCA, sous licence **AGPL-3** ;
`aite_courrier_sign_oca`, qui en hérite le code, est sous la même licence.

---

## 9. Dépannage

| Symptôme | Cause | Remède |
| --- | --- | --- |
| *Les modules … sont incompatibles* à l'installation | `aite_courrier_sign` bloqué « à installer » | §2.4 |
| `sign_oca` introuvable à l'installation | dossier `oca\sign_oca` non copié, ou hors `addons_path` | §3.1 |
| Le bouton n'apparaît pas | étape non cochée ; ou vous n'êtes pas habilité à agir sur l'étape | §4 |
| Le bouton a disparu | la signature du passage en cours est obtenue | normal : la garde est levée |
| « Aucune version PDF n'est disponible » | les pièces sont en DOCX, image… | convertir en PDF, téléverser |
| « Le signataire … n'a pas d'adresse e-mail » | pas d'e-mail sur le contact du responsable | le renseigner |
| « Cette étape exige une signature électronique » | garde §5.5 | demander la signature, attendre |
| Signature obtenue, mais la garde bloque encore | le courrier est revenu sur l'étape depuis | nouvelle demande (§5.5) |
| Le signataire ne reçoit rien | serveur de messagerie | §2.2 |
| Le lien pointe au mauvais endroit | `web.base.url` | §2.3 |
| « Request cannot be signed » | demande annulée (remplacée, ou courrier sorti de l'étape) | utiliser le lien de la dernière demande |
| Le PDF signé est dans le fil, pas en GED | pièce verrouillée, ou demandeur sans accès | §5.4 |

---

## 10. Scénario de recette

| # | Action | Attendu | ☐ |
| --- | --- | --- | --- |
| 1 | Installer `aite_courrier_sign_oca` | colonne *Signature requise* dans les circuits | ☐ |
| 2 | Cocher *Signature requise* sur une étape | enregistré | ☐ |
| 3 | Créer un courrier avec un responsable qui a un e-mail, lancer le circuit | référence attribuée | ☐ |
| 4 | Pièce **DOCX**, aller sur l'étape, cliquer le bouton | refus « Aucune version PDF » | ☐ |
| 5 | Pièce **PDF**, recliquer | fiche de la demande : Courrier, Étape, Pièce source, Signataires « (en attente) » | ☐ |
| 6 | Boîte du responsable | e-mail *Nouveau document à signer* | ☐ |
| 7 | **Sans signer**, valider le courrier | refus explicite ; *Action bloquée* au journal d'audit | ☐ |
| 8 | Ouvrir le lien dans une fenêtre privée (sans session) | le PDF s'affiche, zone en bas à droite de la page 1 | ☐ |
| 9 | Signer, *Valider et envoyer le document* | *Merci d'avoir signé* | ☐ |
| 10 | Recharger le courrier | bouton disparu ; onglet Documents : v2 `…_signe.pdf` avec la signature | ☐ |
| 11 | Valider le courrier | autorisé | ☐ |
| 12 | Renvoyer le courrier sur l'étape, valider | refusé : nouvelle signature exigée | ☐ |
| 13 | Demander deux fois de suite | la première demande est *Annulée* ; son lien ne signe plus | ☐ |
| 14 | Utilisateur interne sans lien avec la demande : `/my/sign/<id>/download` | page introuvable | ☐ |

---

## 11. Vérifications faites avant livraison

Sur Odoo 18.0 Community, PostgreSQL 16, `sign_oca` 18.0.1.4.3 (commit
`2489814`) :

- 12 tests automatisés du module (parcours, garde par passage, remplacement,
  annulation en sortie d'étape, pièce verrouillée, droits du demandeur,
  cloisonnement des demandes et des jetons, téléchargement, signature
  anonyme par le lien) ; campagne complète de la suite avec le module :
  342 tests, 0 échec ;
- mêmes tests, plus les 19 de `sign_oca`, sous **Python 3.12 et reportlab
  4.1.0** — les versions de l'installateur Windows d'Odoo 18 : 0 échec ;
- parcours réel dans Chromium : demande par un agent, refus de la
  transition tracé au journal, signature par le lien sans session, PDF signé
  en v2 dans la GED, transition acceptée ;
- installation sur la copie d'une base en service où `aite_courrier_sign`
  était bloqué « à installer » : refus « incompatibles », puis installation
  sans erreur une fois le blocage levé ; la règle d'accès renforcée tient
  après une mise à jour de `sign_oca` seul.

Non vérifié ici : l'envoi réel de l'e-mail (pas de serveur SMTP dans cet
environnement) — le message est bien créé, avec le lien.

---

*AITE Consulting — tutoriel signature électronique, Odoo Community.*
