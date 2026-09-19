# Recette du flux WebDAV — environnement local

> Comment vérifier, sur une instance Odoo lancée en local, que l'accès WebDAV
> fonctionne de bout en bout : découverte, authentification, listage, dépôt,
> versionnage, renommage, verrous, suppression.

Deux racines peuvent être servies, selon les modules installés :

| Racine | Module | Contenu exposé |
| ------ | ------ | -------------- |
| `/webdav/aite_courrier` | `aite_courrier_webdav` | un dossier par courrier enregistré, ses pièces |
| `/webdav/aite_ecm` | `aite_ecm_webdav` | le plan de classement ECM, « Sans classement » |

---

## 1. Prérequis

1. **Le module est installé.** Sur la stack `docker-compose.yml` du dépôt :

   ```bash
   docker compose up -d
   docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d aite_courrier \
     --stop-after-init -i aite_courrier_webdav
   docker compose restart odoo
   ```

   Sur l'instance WSL décrite dans le README, remplacer par la commande
   `python3 …/odoo -c …/odoo18e.conf -d <base> -i aite_courrier_webdav`.

2. **La base est désignée.** Le contrôleur WebDAV s'authentifie hors session :
   si le serveur héberge **plusieurs bases**, il ne sait pas laquelle utiliser
   et répond `401` quels que soient les identifiants. Renseigner dans
   `odoo.conf` :

   ```ini
   db_name = aite_courrier
   ```

3. **Un compte interne.** Les utilisateurs *portail* n'ont pas accès. Le mot
   de passe du compte convient ; une **clé d'API** (Préférences › Sécurité du
   compte) est préférable — vérification légère, révocable, et seule voie pour
   un compte à double authentification.

4. **Des données à lister.** La racine `/webdav/aite_courrier` ne liste que les
   courriers **déjà enregistrés**, c'est-à-dire porteurs d'une référence
   `COUR-AAAA-NNNN` : créer un courrier puis **Lancer le circuit**. Côté ECM,
   le dossier **« Sans classement »** existe toujours.

---

## 2. Test express (30 secondes, `curl`)

```bash
URL=http://localhost:8069
LOGIN=admin; PASS=admin

# 1. le service répond et annonce ses capacités (sans authentification)
curl -s -i -X OPTIONS $URL/webdav/aite_courrier | head -5

# 2. l'accès est protégé
curl -s -o /dev/null -w '%{http_code}\n' -X PROPFIND $URL/webdav/aite_courrier/

# 3. le listage renvoie du XML multistatus
curl -s -u "$LOGIN:$PASS" -X PROPFIND -H 'Depth: 1' \
     $URL/webdav/aite_courrier/ | head -20
```

Attendu : `200` avec `DAV: 1, 2` puis `Allow: …` — `401` — puis un
`<D:multistatus>` listant les références de courrier.

---

## 3. Test complet (scénario automatisé)

`docs/recette/test_webdav.py` déroule le dialogue complet et imprime un rapport
PASS / FAIL / SKIP. Aucune dépendance : Python 3.8+ et la bibliothèque standard.
Il détecte seul les racines servies.

```bash
python3 docs/recette/test_webdav.py \
    --url http://localhost:8069 --login admin --password admin
```

| Option | Effet |
| ------ | ----- |
| `--root courrier` ou `--root ecm` | ne tester qu'une racine (défaut : toutes celles qui répondent) |
| `--collection COUR-2026-0001` | imposer le courrier / dossier ECM utilisé pour les écritures |
| `--keep` | laisser le fichier déposé en place, pour l'inspecter dans l'UI |
| `--strict` | ajouter les contrôles qui laissent des données résiduelles (cf. §5) |
| `-v` | tracer chaque requête HTTP |
| `--no-color` | sortie sans couleurs, pour un journal |

Ce qui est vérifié, en trois phases :

1. **Service** — `OPTIONS` anonyme, en-têtes `DAV` et `Allow`, `401` + défi
   `Basic` sans identifiants, `401` avec de mauvais identifiants.
2. **Listage** — `PROPFIND` racine en `Depth: 1` et `Depth: 0`, forme du
   `multistatus`, `404` sur une collection inconnue.
3. **Cycle de vie d'un fichier** — `PUT` (→ `201`), `GET` relu **à l'octet
   près**, `HEAD`, `PROPFIND` du fichier et `getcontentlength`, `PUT` de nouveau
   (→ `204`, nouvelle version) et relecture de la v2, présence dans le listage,
   `MOVE` (renommage) avec l'ancien nom en `404`, `LOCK` / `UNLOCK`, extension
   refusée (→ `409`), `COPY` (→ `403`), `MKCOL`, `DELETE` (→ `204`) puis `404`.

Le script **ne crée ni courrier ni dossier de classement** : il travaille dans
une collection existante et supprime ce qu'il y dépose. Code de sortie `0` si
tout passe, `1` si un contrôle échoue, `2` si le serveur est injoignable.

---

## 4. Quand ça échoue

| Symptôme | Cause probable | Remède |
| -------- | -------------- | ------ |
| `Serveur injoignable` | instance arrêtée, mauvais port | `curl -I http://localhost:8069/web/login` |
| Racine « absente (OPTIONS → 404) » | module non installé | installer `aite_courrier_webdav` / `aite_ecm_webdav`, puis **redémarrer** Odoo |
| `401` avec des identifiants corrects | serveur multi-base | renseigner `db_name` dans `odoo.conf` |
| `401` persistant | compte *portail*, ou compte 2FA avec son mot de passe | compte interne ; pour un compte 2FA, une clé d'API |
| Racine `207` mais vide | aucun courrier enregistré | créer un courrier et **Lancer le circuit** |
| `PUT` → `409` | extension hors liste ou fichier > 50 Mo (100 Mo en ECM) | formats courrier : PDF, DOCX, XLSX, JPG, PNG, TIF, EML, MSG |
| `PUT` → `423` | document finalisé, archivé, ou réservé par un autre | libérer la réservation dans l'UI |
| `PUT` → `403` | droits en écriture insuffisants sur le courrier | vérifier le rôle et la confidentialité |
| Windows : « Le nom du dossier n'est pas valide » | le client WebDAV de Windows refuse Basic sur HTTP | cf. §6 |

---

## 5. Limites connues

- **ECM, `MKCOL`.** Créer une collection crée un vrai dossier de classement,
  que WebDAV ne sait pas supprimer ensuite : ce contrôle n'est joué qu'avec
  `--strict`.
- **`LOCK` côté courrier** est consultatif (jeton non persisté) : la vraie
  protection en écriture reste `is_locked`, qui renvoie `423` au `PUT`.
- **Corrigé en 18.0.2.0.2 (ECM).** Un dépôt au format refusé laissait un
  document ECM sans version en base : création et première version sont
  désormais encadrées par un savepoint. Le harnais vérifie l'absence de
  résidu après le `409`.

---

## 6. Monter le lecteur réseau

Le test `curl`/script valide le **service**, indépendamment des restrictions
des clients. Pour le montage réel :

- **Windows** — Explorateur → *Connecter un lecteur réseau* →
  `http://localhost:8069/webdav/aite_courrier`. Le service **WebClient** doit
  tourner, et Basic sur HTTP doit être autorisé (`BasicAuthLevel` à `2`) :
  détail dans
  [`addons/aite_courrier_webdav/docs/WEBDAV.md`](../../addons/aite_courrier_webdav/docs/WEBDAV.md).
- **macOS** — Finder → ⌘K → `http://localhost:8069/webdav/aite_courrier`.
- **Linux** — `davs://` dans Fichiers, ou
  `sudo mount -t davfs http://localhost:8069/webdav/aite_courrier /mnt/courrier`.

En production, exposer Odoo en **HTTPS** : le montage Windows fonctionne alors
sans réglage de registre.

---

*AITE Consulting — recette du flux WebDAV.*
