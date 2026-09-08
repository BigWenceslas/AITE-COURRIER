# aite_ecm_nextcloud — Connecteur Nextcloud

Nextcloud devient l'**espace de travail fichiers** de l'ECM (synchronisation
bureau et mobile, édition en ligne, liens publics) ; Odoo reste le
**référentiel** (métadonnées, circuits, droits, audit, versions).

```
   Odoo (AITE ECM)                                  Nextcloud
   ─────────────────                                ─────────────────────
   document, versions,   ── WebDAV PUT/MOVE ──▶     AITE ECM/
   plan de classement                                ├─ Juridique et contrats/
                                                     │   └─ DOC-2026-00128 - Contrat…/
   nouvelle version     ◀── webhook / sondage ──     │        └─ contrat.pdf
   (attribuée au réservant)                          └─ Courrier/2026/COUR-… (option)
   lien public          ── OCS shares ──▶            https://cloud…/s/…
```

## 1. Côté Nextcloud

1. Créez un **compte de service** (ex. `odoo-ecm`) et, dans son profil,
   *Paramètres › Sécurité › Appareils et sessions*, générez un **mot de passe
   d'application** (obligatoire si l'authentification est déléguée à un
   annuaire ou à un SSO).
2. Le connecteur crée lui-même le dossier racine (par défaut `AITE ECM`) dans
   l'espace de ce compte.
3. **Utilisateurs** : partagez le dossier racine (ou seulement certaines
   branches) avec un groupe Nextcloud en lecture/écriture. Leurs clients de
   synchronisation et l'édition en ligne (Nextcloud Office / Collabora,
   OnlyOffice) travaillent sur ces fichiers ; chaque enregistrement redevient
   une version Odoo.
4. **Webhooks (recommandé, Nextcloud ≥ 30)** : `occ app:enable
   webhook_listeners`. Le compte de service doit être administrateur (ou
   administrateur délégué) pour enregistrer le webhook, et Nextcloud doit
   pouvoir joindre l'URL publique d'Odoo (`web.base.url`). Les webhooks sont
   émis par la tâche de fond Nextcloud (toutes les 5 min par défaut ;
   quasi instantané avec un *worker* `background-job:worker`, voir la
   documentation Nextcloud).

## 2. Côté Odoo

ECM › Configuration › **Paramètres** :

| Réglage | Rôle |
|---|---|
| URL, compte de service, mot de passe d'application, dossier racine | connexion — bouton **Tester la connexion** |
| Mode | *Désactivé* · *Miroir seul* (Odoo → Nextcloud) · *Bidirectionnel* (retour des modifications) |
| Envoi immédiat des versions | sinon, envoi par la tâche planifiée (toutes les 5 min) |
| Sondage périodique | détection des modifications par ETag, filet de sécurité sans webhook |
| Synchroniser aussi les pièces de courrier | arborescence `Courrier/<année>/<référence> - <objet>/` |
| Miroiter aussi les documents Confidentiel / Secret | **désactivé par défaut** (le partage Nextcloud est moins fin que les droits ECM) |
| Validité des liens publics | expiration par défaut des liens Nextcloud (7 jours) |
| Secret du webhook + **Enregistrer le webhook dans Nextcloud** | crée l'abonnement à `NodeWrittenEvent` vers `/ecm/nextcloud/webhook` |
| **Envoyer tout le fonds** | planifie l'envoi initial de tous les documents possédant un fichier |

## 3. Fonctionnement

* **Envoi** : à chaque nouvelle version (immédiat, sinon tâche planifiée).
  Le chemin reproduit le plan de classement : `<dossier>/<REF> - <titre>/<fichier>`.
  Renommer ou reclasser un document dans Odoo déplace le fichier (MOVE).
  Suppression définitive dans Odoo → dossier retiré de Nextcloud (la
  corbeille ne touche pas au miroir).
* **Retour** : un fichier modifié dans Nextcloud (ETag différent) est importé
  comme **nouvelle version**, attribuée à l'utilisateur qui a **réservé** le
  document, sinon au propriétaire ; audit source « Nextcloud », message dans
  le fil. Contenu identique (même SHA-256) → rien n'est créé.
  Document **finalisé ou archivé** → aucune écrasure : état *Conflit*, message
  au fil ; remettre en brouillon puis « Importer depuis Nextcloud ».
* **Sondage** : l'ETag du dossier racine ne change pas tant que rien ne bouge
  en dessous — le sondage est donc gratuit au repos ; sinon, comparaison des
  ETags dossier par dossier.
* **Lien public Nextcloud** : mot de passe aléatoire (affiché dans le fil, à
  transmettre séparément), expiration par défaut, révocable. Les partages AITE
  (`aite_ecm_share`, filigrane, quota) restent disponibles.
* **États** (onglet Nextcloud du document, filtres « Conflits Nextcloud »,
  « Nextcloud en attente ») : non synchronisé, à envoyer, à importer,
  synchronisé, conflit, erreur.

## 4. Alternative complémentaire : Odoo vu depuis Nextcloud

Nextcloud peut monter le **WebDAV servi par Odoo** (`aite_courrier_webdav`)
comme *Stockage externe* de type WebDAV : les utilisateurs voient alors la
GED courrier dans Nextcloud sans copie. Cette voie n'offre ni synchronisation
bureau, ni édition en ligne, ni webhooks, mais convient pour la consultation.

## 5. Tests

```bash
./odoo-bin -d <base> -i aite_ecm_nextcloud --test-tags /aite_ecm_nextcloud --stop-after-init
```

Les tests utilisent un faux serveur Nextcloud en mémoire ; aucune instance
Nextcloud n'est nécessaire (`tests/test_01_nextcloud.md`).

## 6. Limites connues et suite

* L'auteur d'une modification Nextcloud est déduit de la réservation Odoo (ou
  du propriétaire) : un rapprochement des comptes Nextcloud ↔ Odoo (`user.uid`
  du webhook) est prévu.
* Verrou Nextcloud (`files_lock`) ↔ réservation Odoo, suppression côté
  Nextcloud → corbeille Odoo, et quotas par dossier : prochaines itérations.
