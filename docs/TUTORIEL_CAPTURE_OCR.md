# Tutoriel — capture e-mail et recherche plein texte

> Du message reçu au courrier retrouvé par le contenu de ses pièces.
> Deux modules qui se complètent : `aite_courrier_capture` 18.0.1.0.0 fait
> entrer le courrier, `aite_courrier_ocr` 18.0.1.0.0 le rend cherchable.
>
> Tous deux s'installent sur Odoo 18 **Community** et portent des tests
> (8 cas chacun).

---

## La chaîne complète

```
   courrier@votredomaine.fr
            │
            ▼
   ┌────────────────────┐   pièces jointes    ┌──────────────────────┐
   │  CAPTURE           │ ──────────────────▶ │  GED                 │
   │  courrier brouillon│   filtrées          │  documents v1        │
   │  expéditeur, objet │                     └──────────┬───────────┘
   └────────────────────┘                                │
                                                mise en file
                                                         ▼
                                              ┌──────────────────────┐
                                              │  OCR (cron, 10 min)  │
                                              │  texte PDF natif,    │
                                              │  Tesseract en repli  │
                                              └──────────┬───────────┘
                                                         ▼
                                            recherche « Contenu des pièces »
```

L'agent n'a plus qu'à qualifier le brouillon et lancer le circuit. Les deux
modules sont indépendants : la capture fonctionne sans l'OCR, l'OCR indexe
aussi les pièces déposées à la main ou par WebDAV.

---

# Partie A — Capture e-mail

## A.1 Ce que fait le module

Tout message envoyé à une adresse dédiée crée un **courrier en brouillon**,
pré-rempli :

| Champ du courrier | Source |
| --- | --- |
| Objet | sujet de l'e-mail (ou « Courrier sans objet ») |
| Expéditeur | nom extrait de l'en-tête `From` |
| E-mail expéditeur | adresse extraite du `From` |
| Contact | `res.partner` reconnu, s'il existe |
| Type | type marqué *capture e-mail*, sinon premier type *Entrant* |
| Date de réception | le jour même |

Le corps du message reste dans le fil de discussion. Les pièces jointes
deviennent des **documents GED versionnés** (v1). Chaque capture est tracée
au journal d'audit, source *Système*.

Les réponses ultérieures au même fil alimentent le fil du courrier existant :
elles ne créent pas de doublon.

## A.2 Installer

```powershell
net stop odoo-server-18.0

& "C:\Program Files\Odoo 18\python\python.exe" `
  "C:\Program Files\Odoo 18\server\odoo-bin" `
  -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
  -i aite_courrier_capture --stop-after-init

net start odoo-server-18.0
```

Le module crée l'alias `courrier`, pointant sur le modèle `aite.courrier`.

## A.3 Configurer

Trois réglages, dans cet ordre.

### Le domaine d'alias

**Paramètres → Général → Discussion → Domaine d'alias**. Sans lui, l'alias
`courrier` n'a pas d'adresse complète et rien n'arrive.

### Le serveur entrant

**Paramètres → Technique → E-mail → Serveurs de messagerie entrants**.
Créer un serveur IMAP ou POP sur la boîte dédiée, puis *Tester et confirmer*.

C'est la pièce que l'hébergement conditionne : Odoo.sh et Odoo Online
acheminent les alias sans serveur entrant, une instance auto-hébergée a besoin
de ce relevé de boîte. Sur une instance locale de test, un compte Gmail ou
Outlook dédié suffit.

> **Sécurité.** L'alias livré est en `alias_contact = everyone` : **n'importe
> qui** peut créer un courrier en écrivant à cette adresse. C'est le
> comportement voulu d'une boîte de courrier entrant, mais cela veut dire
> qu'elle est exposée au spam comme toute adresse publique. Prévoir un
> filtrage côté serveur de messagerie plutôt que côté Odoo.

### Le type par défaut

**Courrier → Configuration → Types de courrier** : ouvrir le type qui doit
recevoir les captures et cocher **Type par défaut (capture e-mail)**.

Sans ce marquage, le module prend le premier type de catégorie *Entrant* —
ce qui fonctionne, mais laisse le choix au hasard de l'ordre.

✅ **Vérification** — **Paramètres → Technique → E-mail → Alias** : l'alias
`courrier` existe, son modèle est *Courrier*, et son adresse complète
s'affiche.

## A.4 Le parcours

1. Envoyer un e-mail à `courrier@votredomaine.fr`, avec un objet, un corps et
   une pièce jointe PDF.
2. Attendre le relevé de la boîte (bouton *Récupérer maintenant* sur le
   serveur entrant pour ne pas attendre le cron).
3. **Courrier → Courriers** : un brouillon est apparu.

Sur sa fiche : l'objet est le sujet du mail, l'expéditeur est renseigné, le
corps est dans le fil, et l'onglet **Documents** contient la pièce jointe en
v1.

Il ne reste qu'à qualifier — service destinataire, priorité, confidentialité —
puis **Lancer le circuit**.

## A.5 Ce qui est filtré, et pourquoi

Toutes les pièces jointes ne deviennent pas des documents :

| Filtre | Raison |
| --- | --- |
| Extensions hors liste GED | PDF, DOCX, XLSX, JPG, JPEG, PNG, TIF, TIFF, EML, MSG uniquement |
| Images de moins de **8 Ko** | écarte les signatures et logos des e-mails |
| Pièces déjà versionnées | évite de réarchiver un document renvoyé par e-mail |
| Pièce en échec (ex. > 50 Mo) | tracée au journal d'audit, sans bloquer le reste du message |

Le seuil de 8 Ko mérite attention : un petit scan de bonne qualité peut passer
en dessous et être ignoré. Si cela se produit, la valeur est dans le code
(`MIN_IMAGE_CAPTURE_SIZE`) et n'est pas paramétrable — à faire évoluer si
l'usage le demande.

## A.6 Dépannage

| Symptôme | Cause probable | Remède |
| --- | --- | --- |
| Aucun courrier créé | serveur entrant absent ou en erreur | *Tester et confirmer* sur le serveur |
| Aucun courrier créé, serveur OK | domaine d'alias non renseigné | §A.3 |
| Courrier créé, pièces absentes | extensions non autorisées, ou images trop petites | §A.5 |
| Type inattendu | aucun type marqué *capture e-mail* | §A.3 |
| Réponses créant des doublons | le message ne cite pas la référence du fil | vérifier que le `Message-Id` d'origine est conservé par le client |

Le journal d'audit (*Courrier créé par e-mail*, *Échec capture pièce jointe*)
donne l'historique exact de ce que la passerelle a fait.

---

# Partie B — OCR et recherche plein texte

## B.1 Ce que fait le module

Retrouver un courrier par le **contenu** de ses pièces, pas seulement par ses
métadonnées.

À chaque téléversement d'une version PDF ou image — par la capture, à la main
ou par WebDAV — l'extraction est mise **en file d'attente**. Un cron la traite
par lots de 20, toutes les 10 minutes. L'utilisateur n'attend jamais.

Deux techniques, dans cet ordre :

1. **Couche texte du PDF** (pypdf, livré avec Odoo). Couvre tous les PDF
   bureautiques — une facture exportée depuis un logiciel, un courrier
   rédigé dans Word. **Aucune dépendance à installer.**
2. **OCR Tesseract**, en repli, si la couche texte fait moins de 40
   caractères : c'est le signe d'un scan. Également utilisé pour les images.
   **Dépendances externes requises** (§B.3).

Le texte extrait est stocké sur la version et recopié dans `index_content` de
la pièce jointe, ce qui le rend visible à la recherche native d'Odoo.

## B.2 Installer

```powershell
... odoo-bin -c odoo.conf -d <votre_base> -i aite_courrier_ocr --stop-after-init
```

✅ **Vérification** — **Paramètres → Technique → Automatisation → Actions
planifiées** : « AITE Courrier : indexation plein texte (OCR) », toutes les
10 minutes, actif.

## B.3 Installer l'OCR — optionnel

**À ne faire que si vous traitez des scans ou des images.** Sans ces
dépendances, le module fonctionne : il indexe les PDF avec couche texte, et
laisse les scans sans contenu.

### Debian / Ubuntu

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils
sudo -H pip3 install pytesseract pdf2image Pillow
sudo systemctl restart odoo
```

### Windows

1. **Tesseract** — installeur UB Mannheim
   (<https://github.com/UB-Mannheim/tesseract/wiki>), en cochant le pack de
   langue **français**.
2. **Poppler** — archive depuis
   <https://github.com/oschwartz10612/poppler-windows/releases>, décompressée
   par exemple dans `C:\poppler`.
3. **Ajouter les deux au `PATH` système** : le dossier d'installation de
   Tesseract et `C:\poppler\Library\bin`. C'est indispensable — les
   bibliothèques Python cherchent `tesseract.exe` et `pdftoppm.exe` dans le
   `PATH`, le module ne configure aucun chemin explicite.
4. Les paquets Python, avec le Python d'Odoo :

```powershell
& "C:\Program Files\Odoo 18\python\python.exe" -m pip install pytesseract pdf2image Pillow
```

5. Redémarrer le service Odoo.

✅ **Vérification** — dans une invite de commande : `tesseract --version` et
`pdftoppm -v` répondent tous deux.

### Le paramètre de volume

**Paramètres → Technique → Paramètres système** :

| Clé | Défaut | Effet |
| --- | --- | --- |
| `aite_courrier.ocr_max_pages` | `10` | pages OCRisées par PDF scanné |

L'OCR est coûteux : environ une seconde par page. Sur un scan de 40 pages,
seules les 10 premières sont lues avec la valeur par défaut. Augmenter si les
documents longs doivent être cherchables en entier — et surveiller la charge.

## B.4 Suivre l'indexation

Sur la fiche d'un document, la liste des versions porte une colonne
**Indexation** :

| État | Sens |
| --- | --- |
| *Non concerné* | ni PDF ni image — rien à extraire |
| *En attente* | en file ; le cron la prendra au prochain passage |
| *Indexé* | extraction terminée |
| *Erreur* | fichier illisible, chiffré ou corrompu — voir le journal d'audit |

Un bouton **Réindexer** remet une version en file : utile après avoir installé
Tesseract, pour rattraper les scans déjà arrivés.

> **Attention à un faux positif.** Un scan traité **sans** Tesseract passe à
> *Indexé* avec un texte **vide** : l'extraction a bien eu lieu, elle n'a
> simplement rien trouvé. L'état ne distingue pas « indexé avec du contenu »
> de « indexé à vide ». Si vos recherches ne remontent rien alors que tout est
> *Indexé*, c'est la première chose à vérifier.

## B.5 Chercher par le contenu

Dans la liste des courriers, le filtre **Contenu des pièces (plein texte)**
interroge le texte extrait de toutes les versions de toutes les pièces.

Taper `résiliation` y remonte les courriers dont une pièce contient ce mot,
même si ni l'objet ni l'expéditeur ne le mentionnent.

La recherche s'exécute en `sudo` sur le texte, puis renvoie des identifiants
de courriers : **les règles de confidentialité s'appliquent ensuite
normalement**. Un agent ne verra jamais, dans ses résultats, un courrier
confidentiel auquel il n'a pas accès.

## B.6 Dépannage

| Symptôme | Cause probable | Remède |
| --- | --- | --- |
| Tout reste *En attente* | cron désactivé | §B.2 |
| Scans *Indexés* mais recherche vide | Tesseract absent | §B.3, puis *Réindexer* |
| PDF bureautiques non trouvés | texte réellement absent (PDF image) | c'est un scan : OCR nécessaire |
| *Erreur* sur une version | PDF chiffré ou corrompu | journal d'audit, *Échec indexation OCR* |
| Seules les premières pages ressortent | `ocr_max_pages` | §B.3 |
| OCR lent, serveur chargé | volume de scans | réduire `ocr_max_pages`, ou espacer le cron |

---

## Scénario de recette — les deux modules ensemble

| # | Action | Attendu | ☐ |
| --- | --- | --- | --- |
| 1 | Installer les deux modules | cron OCR actif, alias `courrier` créé | ☐ |
| 2 | Renseigner domaine d'alias et serveur entrant | *Tester et confirmer* réussit | ☐ |
| 3 | Marquer un type *capture e-mail* | enregistré | ☐ |
| 4 | Envoyer un e-mail avec un **PDF bureautique** | courrier brouillon créé, bon type | ☐ |
| 5 | Fiche du courrier | objet, expéditeur, corps dans le fil | ☐ |
| 6 | Onglet Documents | le PDF en v1 | ☐ |
| 7 | Colonne Indexation | *En attente* | ☐ |
| 8 | Déclencher le cron à la main | passe à *Indexé* | ☐ |
| 9 | Chercher un mot du PDF dans *Contenu des pièces* | le courrier remonte | ☐ |
| 10 | Envoyer un e-mail avec une **signature d'image < 8 Ko** | la signature n'est pas archivée | ☐ |
| 11 | Envoyer un e-mail avec un **.exe** | pièce ignorée, courrier créé quand même | ☐ |
| 12 | Répondre au fil du courrier | message ajouté, **pas** de nouveau courrier | ☐ |
| 13 | Déposer un **scan** (PDF sans couche texte) | *Indexé*, texte vide si Tesseract absent | ☐ |
| 14 | Installer Tesseract, cliquer **Réindexer** | texte extrait, recherche concluante | ☐ |
| 15 | Chercher avec un compte non habilité | le courrier confidentiel ne remonte pas | ☐ |
| 16 | Journal d'audit | *Courrier créé par e-mail* présent | ☐ |

---

## Limites connues

- **Seuil d'image à 8 Ko** non paramétrable : un petit scan peut être écarté
  avec les signatures.
- **Un scan sans Tesseract passe à *Indexé*** avec un texte vide — l'état ne
  dit pas que rien n'a été trouvé.
- **`ocr_max_pages` à 10** : au-delà, un document long n'est cherchable que
  partiellement.
- **Le document capturé garde son extension dans son nom** (`facture.pdf`
  plutôt que `facture`), là où un dépôt WebDAV la retire. Cosmétique, mais
  visible dans les listes.
- **L'alias accepte tout le monde** : filtrage anti-spam à prévoir en amont.
- **L'OCR d'images n'a jamais été éprouvé en conditions réelles** : la
  campagne de recette n'avait pas Tesseract sur son serveur
  (`docs/recette/PLAN_DE_TEST.md` §5). L'extraction de la couche texte PDF,
  elle, est couverte.

## Tests

```powershell
... odoo-bin -c odoo.conf -d <base_de_test> --stop-after-init `
    -u aite_courrier_capture,aite_courrier_ocr --test-enable `
    --test-tags /aite_courrier_capture,/aite_courrier_ocr
```

16 cas : type par défaut, analyse de l'expéditeur, création par e-mail,
message sans objet, pièces devenant documents, pièce déjà versionnée ignorée,
parcours complet de la passerelle — puis mise en file, texte PDF natif, scan
sans couche texte, cron, réindexation, fichier corrompu signalé sans
interruption, recherche par contenu, OCR d'image optionnel.

---

*AITE Consulting — tutoriel capture e-mail et recherche plein texte.*
