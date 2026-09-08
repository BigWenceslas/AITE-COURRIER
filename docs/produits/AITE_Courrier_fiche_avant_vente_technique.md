# AITE Courrier — Fiche avant-vente technique (DSI)

> Synthèse technique à destination des équipes DSI / architectes.
> Solution native Odoo 18 Enterprise — par AITE Consulting.

---

### Positionnement technique
Suite d'**addons Odoo 18 Enterprise** couvrant la gestion du courrier et la GED associée. **Aucune dépendance externe** : circuits, GED et WebDAV s'exécutent dans le serveur Odoo.

### Architecture modulaire

| Module | Rôle technique |
|---|---|
| `aite_courrier` | Module « chapeau » (install toute la suite) + tableau de bord OWL |
| `aite_courrier_base` | Groupes de sécurité, référentiels, `aite.courrier.audit.log` |
| `aite_courrier_workflow` | Moteur de circuits (circuit / étape / transition) |
| `aite_courrier_core` | Modèle `aite.courrier`, cycle de vie, séquence `COUR-AAAA-NNNN` |
| `aite_courrier_ged` | GED versionnée **adossée à `documents`** (mixin natif) |
| `aite_courrier_validation` | Exécution des transitions de circuit |
| `aite_courrier_webdav` | Contrôleur WebDAV intégré au serveur Odoo |

### Intégration GED native
- `aite.courrier.document` hérite de **`documents.mixin`** : chaque `ir.attachment` de version génère automatiquement un `documents.document`.
- **Un dossier `documents.document` par courrier** sous un espace racine « Courrier ». **Binaire non dupliqué** (référence partagée vers la même pièce jointe).
- Confidentialité **héritée** du courrier (champ `related` stocké) ; accès centralisé via `_check_document_access(operation)`.

### WebDAV
- Routes `type='http', auth='none'` avec **HTTP Basic → `res.users`** ; dispatch par méthode (OPTIONS/PROPFIND/GET/PUT/DELETE/MOVE/COPY/LOCK…).
- Mapping des verbes vers les hooks GED : `GET/PROPFIND → read`, `PUT/DELETE/MOVE → write`, verrou → `423 Locked`.
- Audit `source='webdav'` pour distinguer les accès réseau.

### Sécurité & gouvernance
- 4 niveaux de confidentialité, groupes d'accès dédiés, journal d'audit horodaté.
- Contrôles documentaires : formats **PDF/DOCX/XLSX**, taille **≤ 50 Mo**, **verrouillage** des versions finalisées/archivées.

### Pré-requis & déploiement
- **Odoo 18 Enterprise** (module `documents` inclus dans l'offre Enterprise).
- Installation : `-i aite_courrier` (tire `documents` par dépendance).
- Couverture de tests automatisés par module (specs `tests/test_0X_*.md`).

### Points d'extension
Circuits/étapes/transitions paramétrables · référentiels ouverts · hooks GED documentés (`WEBDAV_READINESS.md`) · architecture modulaire pour ajouts métier.

---

*AITE Consulting — www.aite-consulting.com*
