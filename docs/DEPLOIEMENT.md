# Déploiement — AITE ECM & AITE Courrier

Instance Odoo 18 **Community** installée sous `/opt/odoo18c`.

| Élément | Chemin |
| --- | --- |
| Python | `/opt/odoo18c/venv/bin/python3` |
| Binaire Odoo | `/opt/odoo18c/odoo/odoo-bin` |
| Configuration | `/opt/odoo18c/conf/odoo18c.conf` |
| Modules | `/opt/odoo18c/custom_addons/` |
| Service | `odoo18c` |

Toutes les commandes portent `--no-http` : l'instance en service peut rester
démarrée, il n'y a pas de conflit de port.

---

## 1. Déposer les modules

```bash
cp -r ~/AITE-COURRIER-main/addons/* /opt/odoo18c/custom_addons/
```

À refaire après chaque mise à jour du dépôt — la copie n'est pas un lien.

```bash
ls /opt/odoo18c/custom_addons/ | grep -c aite_        # 28
grep addons_path /opt/odoo18c/conf/odoo18c.conf       # doit contenir custom_addons
```

---

## 2. Installer sans données

Base de production ou de formation : la suite complète, aucune donnée fictive.

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier -i aite_ecm,aite_ecm_webdav,aite_ecm_office,aite_ecm_records,aite_ecm_sae,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_courrier_portal --without-demo=all --no-http --stop-after-init
```

Odoo crée la base si elle n'existe pas. Premier accès : **admin / admin**.

Pour une base strictement vide, sans la suite :

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier -i base --without-demo=all --no-http --stop-after-init
```

---

## 3. Installer avec les données de test

Même chose, plus `aite_ecm_demo` en fin de liste.

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier_data_test -i aite_ecm,aite_ecm_webdav,aite_ecm_office,aite_ecm_records,aite_ecm_sae,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_courrier_portal,aite_ecm_demo --without-demo=all --no-http --stop-after-init
```

La génération se poursuit en tâche de fond. Pour la terminer tout de suite :

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin shell -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier_data_test < /opt/odoo18c/custom_addons/aite_ecm_demo/scripts/seed_demo.py
```

Trois volumes, en modifiant `PROFILE` en tête de `seed_demo.py` :

| Profil | Tiers | Courriers | Réponses |
| --- | ---: | ---: | ---: |
| `leger` *(défaut)* | 60 | 150 | 15 |
| `standard` | 100 | 300 | 30 |
| `complet` | 130 | 500 | 60 |

Repartir de zéro, même forme avec `scripts/purge_demo.py`.

---

## 4. Mettre à jour

Après avoir recopié les modules (§1).

Un seul module :

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier -u aite_ecm_document --no-http --stop-after-init
```

Toute la suite AITE :

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier -u aite_ecm,aite_ecm_webdav,aite_ecm_office,aite_ecm_records,aite_ecm_sae,aite_ecm_nextcloud,aite_ecm_nextcloud_courrier,aite_courrier_portal --no-http --stop-after-init
```

Tout, Odoo compris — après une montée de version :

```bash
/opt/odoo18c/venv/bin/python3 /opt/odoo18c/odoo/odoo-bin -c /opt/odoo18c/conf/odoo18c.conf -d odoo18c_aite_courrier -u all --no-http --stop-after-init
```

Sauvegardez avant : `sudo -u postgres pg_dump -Fc odoo18c_aite_courrier > /tmp/avant_maj.dump`

---

## 5. Contrôler

```bash
sudo -u postgres psql -l | grep odoo18c_aite
sudo systemctl restart odoo18c
tail -n 50 /opt/odoo18c/logs/*.log
```

Une installation réussie se termine par `Modules loaded.` sans ligne `ERROR`.

---

## Modules non installés sur Community

`aite_courrier_sign`, `aite_ecm_documents` et `aite_courrier_ged_documents`
dépendent d'Odoo Enterprise. Ils restent présents dans `custom_addons` mais
hors des listes ci-dessus. Les 25 autres composent la suite.
