# Scénario de recette — WebDAV

> Parcours manuel de bout en bout sur une instance Odoo 18 lancée, du service
> HTTP jusqu'à l'aller-retour Word. Chaque étape porte son résultat attendu et
> sa case à cocher. Durée : environ 45 minutes avec le montage Windows.

Pour la vérification **automatisée** (34 contrôles en une commande), voir
[`GUIDE_TEST_WEBDAV.md`](./GUIDE_TEST_WEBDAV.md) : le scénario ci-dessous la
complète sur ce qu'une machine ne voit pas — l'Explorateur, Word, les écrans.

Conventions : `$URL` = `http://localhost:8069`, `alice` / `bob` = deux comptes
internes, `$REF` = la référence du courrier créé en 1.2.

---

## 0. Préparation

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 0.1 | Modules `aite_courrier_webdav` et `aite_ecm_webdav` installés, Odoo redémarré | les deux apparaissent « Installé » dans Applications | ☐ |
| 0.2 | `db_name` renseigné dans `odoo.conf` | sinon 401 systématique sur un serveur multi-base | ☐ |
| 0.3 | Deux comptes internes `alice` et `bob`, rôle *Agent* | connexion possible aux deux | ☐ |
| 0.4 | Un fichier PDF, un DOCX et un fichier `.exe` quelconque sous la main | — | ☐ |

---

## 1. Le service répond et protège l'accès

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 1.1 | `curl.exe -s -i -X OPTIONS $URL/webdav/aite_courrier` | `200`, `DAV: 1, 2`, en-tête `Allow` listant `PROPFIND`, `PUT`, `MOVE`… | ☐ |
| 1.2 | Créer un courrier entrant, puis **Lancer le circuit** | une référence `COUR-AAAA-NNNN` est attribuée → c'est `$REF` | ☐ |
| 1.3 | `curl.exe -s -o NUL -w "%{http_code}" -X PROPFIND $URL/webdav/aite_courrier/` | `401` — sans identifiants, rien ne sort | ☐ |
| 1.4 | Même requête avec `-u alice:MAUVAIS` | `401` — un mot de passe faux ne passe pas | ☐ |
| 1.5 | Même requête avec `-u alice:<bon mot de passe>` et `-H "Depth: 1"` | `207` et un XML `multistatus` listant `$REF` | ☐ |

> Un courrier **sans référence** (encore en brouillon) n'apparaît jamais dans la
> racine : c'est voulu, l'espace documentaire suit l'enregistrement.

---

## 2. Monter le lecteur réseau (Windows)

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 2.1 | Service **WebClient** démarré, `BasicAuthLevel = 2` (cf. doc de déploiement §3) | `Get-Service WebClient` → *Running* | ☐ |
| 2.2 | Connecter `W:` sur `$URL/webdav/aite_courrier` avec les identifiants d'alice | le lecteur s'ouvre et montre un dossier par courrier enregistré | ☐ |
| 2.3 | Connecter `X:` sur `$URL/webdav/aite_ecm` | dossiers du plan de classement + **« Sans classement »** | ☐ |
| 2.4 | Ouvrir `W:\$REF\` | vide si aucune pièce, sinon les pièces du courrier | ☐ |

---

## 3. Cycle de vie d'une pièce de courrier

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 3.1 | Copier un PDF dans `W:\$REF\` | le fichier apparaît ; dans Odoo, le courrier a une **pièce de plus** | ☐ |
| 3.2 | Ouvrir la fiche de cette pièce dans Odoo | titre = nom du fichier **sans extension**, version **v1**, déposée par alice | ☐ |
| 3.3 | Onglet audit / journal | une entrée « Ajout pièce jointe » avec la source **webdav** | ☐ |
| 3.4 | Remplacer le fichier dans `W:` par une version modifiée | dans Odoo : **v2**, v1 toujours consultable dans l'historique | ☐ |
| 3.5 | Renommer le fichier dans l'Explorateur | le **titre** du document change ; la référence du courrier, non | ☐ |
| 3.6 | Supprimer le fichier | la pièce disparaît du courrier | ☐ |
| 3.7 | Créer un dossier dans `W:\$REF\` | **refusé** (`403`) : l'arborescence est pilotée par l'application | ☐ |

---

## 4. Aller-retour Word (ECM)

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 4.1 | Déposer un DOCX dans `X:\Sans classement\` | un document ECM est créé, avec une **référence `DOC-AAAA-NNNNN`** | ☐ |
| 4.2 | Rafraîchir le dossier | le fichier est republié sous `DOC-AAAA-NNNNN - <titre>.docx` | ☐ |
| 4.3 | Ouvrir ce fichier depuis `X:` dans Word | Word demande les identifiants Odoo à la première ouverture, puis ouvre en écriture | ☐ |
| 4.4 | Pendant l'édition, consulter la fiche dans Odoo | le document est **réservé** au nom d'alice | ☐ |
| 4.5 | Connecté en **bob**, tenter d'enregistrer le même fichier | refus `423` — Word propose d'enregistrer une copie | ☐ |
| 4.6 | Modifier et **Enregistrer** dans Word (alice) | une **nouvelle version** apparaît dans l'ECM, au nom d'alice | ☐ |
| 4.7 | Fermer Word | la **réservation est libérée** | ☐ |
| 4.8 | Depuis la fiche ECM, bouton **Ouvrir dans Office** | Word s'ouvre sur le même document, sans passer par le lecteur | ☐ |
| 4.9 | Avec un compte **Manager**, dans `X:\Juridique et contrats\` : *Nouveau dossier*, le nommer `Essai` | le dossier s'appelle `Essai` dans l'Explorateur **et** dans le plan de classement d'Odoo | ☐ |
| 4.10 | Supprimer ce dossier vide dans l'Explorateur | il disparaît du lecteur ; dans Odoo, il est **archivé** (filtre *Archivés*) | ☐ |
| 4.11 | Tenter de supprimer `X:\Juridique et contrats\` | refus : le dossier contient des documents | ☐ |

> Les fichiers temporaires de Word (`~$…`, `.~lock…`, `.tmp`) sont ignorés :
> ils ne doivent **jamais** produire de document fantôme dans l'ECM.

---

## 5. Droits et confidentialité

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 5.1 | Passer `$REF` en confidentialité restreinte, sans y habiliter bob | — | ☐ |
| 5.2 | `curl.exe -u bob:<mdp> -X PROPFIND -H "Depth: 1" $URL/webdav/aite_courrier/` | `$REF` **n'apparaît pas** dans la liste | ☐ |
| 5.3 | `curl.exe -u bob:<mdp> -X PROPFIND $URL/webdav/aite_courrier/$REF/` | `403` ou `404` — jamais le contenu | ☐ |
| 5.4 | Créer un document ECM confidentiel avec bob, puis lister `X:` avec alice | le document de bob **n'apparaît pas** | ☐ |
| 5.5 | Tenter la connexion du lecteur avec un compte **portail** | refusé | ☐ |

---

## 6. Verrouillage

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 6.1 | Passer une pièce de `$REF` à l'état **Finalisé** | le fichier reste visible dans `W:` | ☐ |
| 6.2 | Tenter de l'écraser depuis l'Explorateur | refus `423` : les versions d'un document finalisé sont figées | ☐ |
| 6.3 | Archiver le courrier `$REF` | toutes ses pièces deviennent en lecture seule | ☐ |
| 6.4 | Repasser la pièce en **Brouillon**, réessayer | l'enregistrement repasse | ☐ |

---

## 7. Formats, tailles et résidus

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 7.1 | Copier un `.exe` dans `W:\$REF\` | refus `409` — formats acceptés : PDF, DOCX, XLSX, JPG, PNG, TIF, EML, MSG | ☐ |
| 7.2 | Dans Odoo, rouvrir le courrier | **aucune pièce fantôme** n'a été créée | ☐ |
| 7.3 | Copier un `.exe` dans `X:\Sans classement\` | refus `409` | ☐ |
| 7.4 | **Documents ECM → filtre « sans version »**, ou recherche du nom du fichier | **aucun document vide** n'a été créé *(régression corrigée en 18.0.2.0.2)* | ☐ |
| 7.5 | Copier un fichier de plus de 50 Mo dans `W:` | refus `409` (100 Mo côté ECM) | ☐ |

---

## 8. Robustesse

| # | Action | Attendu | ☐ |
|---|--------|---------|---|
| 8.1 | Déposer un fichier dont le nom contient des accents et des espaces | déposé et relu correctement | ☐ |
| 8.2 | Déconnecter puis reconnecter le lecteur | reprise sans nouvelle saisie du mot de passe (Windows mémorise) | ☐ |
| 8.3 | Redémarrer le service Odoo, rafraîchir `W:` | le lecteur se resynchronise | ☐ |
| 8.4 | Lancer `test_webdav.py` une fois le parcours terminé | tout vert, et la collection est propre | ☐ |

---

## Matrice de synthèse

| Fonction éprouvée | Étapes | Statut |
|---|---|---|
| Découverte du service et en-têtes DAV | 1.1 | ☐ |
| Authentification et refus anonyme | 1.3 – 1.5 | ☐ |
| Montage du lecteur réseau Windows | 2.1 – 2.4 | ☐ |
| Dépôt → création de document | 3.1, 4.1 | ☐ |
| Versionnage par simple enregistrement | 3.4, 4.6 | ☐ |
| Renommage, suppression, création de dossier | 3.5 – 3.7, 4.9 – 4.11 | ☐ |
| Réservation Office ↔ verrou ECM | 4.4 – 4.7 | ☐ |
| Confidentialité héritée | 5.1 – 5.5 | ☐ |
| Verrouillage des documents finalisés | 6.1 – 6.4 | ☐ |
| Contrôles de format et de taille | 7.1 – 7.5 | ☐ |
| Absence de résidu après refus | 7.2, 7.4 | ☐ |
| Traçabilité source « webdav » | 3.3 | ☐ |

---

*AITE Consulting — scénario de recette WebDAV.*
