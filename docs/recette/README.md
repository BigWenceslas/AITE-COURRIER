# Recette — AITE ECM & AITE Courrier

Tout ce qui sert à éprouver la suite et à en rendre compte.

| Fichier | Rôle |
| --- | --- |
| [`PLAN_DE_TEST.md`](./PLAN_DE_TEST.md) | Les trois niveaux de vérification, la couverture par module, ce qui n'est pas couvert et pourquoi |
| [`GUIDE_RECETTE.md`](./GUIDE_RECETTE.md) | Guide illustré des 17 parcours : rôle, étapes, contrôles, captures |
| [`ANOMALIES.md`](./ANOMALIES.md) | Les anomalies trouvées pendant la campagne, leur correction et le test qui les verrouille |
| `uat_runner.py` | Moteur de recette navigateur (Playwright) : joue les parcours, contrôle les effets, capture les écrans |
| `uat_interfaces.py` | Recette des interfaces techniques : WebDAV, API REST, lien de partage |
| [`GUIDE_TEST_WEBDAV.md`](./GUIDE_TEST_WEBDAV.md) | Éprouver le flux WebDAV seul sur une instance locale : prérequis, `curl` express, dépannage |
| `test_webdav.py` | Scénario WebDAV complet et autonome (aucune dépendance) sur les deux racines, `courrier` et `ecm` |
| `build_guide.py` | Assemble `GUIDE_RECETTE.md` à partir des résultats d'exécution |
| `run_tests.sh` | Base neuve + installation + tests unitaires de tous les modules |
| `captures/` | Captures d'écran de la dernière campagne |
| `resultats.json`, `resultats_interfaces.json` | Résultats bruts (étape par étape, contrôle par contrôle) |

## Enchaînement d'une campagne complète

```bash
# 1. Tests unitaires et d'intégration (base dédiée, jetable)
./docs/recette/run_tests.sh recette_units /tmp/tests.log

# 2. Base de recette applicative + jeu de données
./odoo-bin -c odoo.conf -d recette --without-demo=all \
    -i aite_ecm,aite_ecm_webdav,aite_ecm_office,aite_ecm_records,\
aite_ecm_sae,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,\
aite_courrier_portal,aite_ecm_demo --load-language=fr_FR --stop-after-init
./odoo-bin shell -c odoo.conf -d recette \
    < addons/aite_ecm_demo/scripts/seed_demo.py
./odoo-bin -c odoo.conf -d recette          # laisser tourner

# 3. Parcours utilisateur + guide illustré
python3 docs/recette/uat_runner.py
python3 docs/recette/build_guide.py
python3 docs/recette/build_pdf.py       # guide illustré au format PDF

# 4. Interfaces techniques
python3 docs/recette/uat_interfaces.py --api-key <clé> --share-url <lien>
```

Le flux WebDAV s'éprouve aussi **hors campagne**, sur n'importe quelle instance
et sans jeu de données de démonstration — utile pour valider une installation
locale :

```bash
python3 docs/recette/test_webdav.py \
    --url http://localhost:8069 --login admin --password admin
```

## Pré-requis du moteur de recette

```bash
pip install playwright requests
playwright install chromium        # ou définir AITE_CHROMIUM
```

Variables d'environnement reconnues : `AITE_URL` (instance),
`AITE_PASSWORD` (mot de passe des comptes `demo.*`), `AITE_CHROMIUM`
(chemin du navigateur), `AITE_API_KEY`, `AITE_SHARE_URL`.
