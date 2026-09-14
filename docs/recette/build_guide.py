# -*- coding: utf-8 -*-
"""Assemble le guide de recette illustré à partir des résultats d'exécution.

Lit ``resultats.json`` (parcours navigateur) et ``resultats_interfaces.json``
(WebDAV, API, partage), puis écrit ``GUIDE_RECETTE.md`` : pour chaque
scénario, le rôle, l'objectif, les étapes avec leur contrôle et la capture
d'écran correspondante.

Usage : ``python3 docs/recette/build_guide.py``
"""
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'resultats.json')
INTERFACES = os.path.join(HERE, 'resultats_interfaces.json')
GUIDE = os.path.join(HERE, 'GUIDE_RECETTE.md')

HEADER = """# Guide de recette — AITE ECM & AITE Courrier

Ce guide est **produit par l'exécution réelle** des parcours : chaque
capture provient de la dernière campagne, chaque contrôle a été vérifié par
le moteur de recette. Il sert à deux choses :

* **rejouer la recette à la main** — les étapes sont écrites pour être
  suivies par un testeur, avec le compte à utiliser et le résultat attendu ;
* **prouver ce qui a été vérifié** — la colonne « constat » reprend ce que
  le moteur a effectivement lu à l'écran.

| | |
| --- | --- |
| Version de la suite | 18.0.2.1.x (Odoo 18 Community) |
| Campagne | {date} |
| Instance | {base_url} |
| Jeu de données | `aite_ecm_demo`, profil « léger » |
| Mot de passe des comptes de recette | `aite2026` |

## Comment rejouer cette recette

1. Installer la suite : `./odoo-bin -c odoo.conf -d <base> -i aite_ecm
   --stop-after-init`, puis les modules optionnels souhaités
   (`aite_ecm_records`, `aite_ecm_sae`, `aite_ecm_webdav`, `aite_ecm_office`,
   `aite_courrier_portal`, `aite_ecm_demo`).
2. Générer le jeu de données : **ECM › Configuration › Jeu de données de
   test › Démarrer**, ou
   `./odoo-bin shell -d <base> < addons/aite_ecm_demo/scripts/seed_demo.py`.
3. Donner un mot de passe connu aux comptes `demo.*` (Réglages ›
   Utilisateurs), puis suivre les scénarios ci-dessous.
4. Pour rejouer automatiquement :
   `python3 docs/recette/uat_runner.py` (parcours navigateur) et
   `python3 docs/recette/uat_interfaces.py --api-key … --share-url …`
   (interfaces techniques).

## Comptes de recette

| Identifiant | Personne | Rôle AITE |
| --- | --- | --- |
| `demo.agent1` · `demo.agent2` · `demo.agent3` | Aurélie Mbarga, Boris Tchoumi, Clarisse Ekani | Agent courrier |
| `demo.assist1` · `demo.assist2` | Nadège Fotso, Franck Onana | Assistant(e) |
| `demo.manager1` · `demo.manager2` | Patrick Essomba, Solange Ngo Bassong | Manager |
| `demo.compta` | Hervé Kenfack | Comptabilité |
| `demo.signer` | Gisèle Atangana | Signataire |
| `demo.archive` | Landry Nkolo | Archiviste |
| `demo.audit` | Irène Djomo | Audit |
| `demo.admin` | Serge Kamdem | Administrateur AITE |
| `portail.recette` | Clinique La Providence | Tiers externe (portail) |

"""


def summary_table(report):
    lines = ["## Synthèse", "",
             "| Scénario | Rôle | Compte | Étapes | Résultat |",
             "| --- | --- | --- | --- | --- |"]
    for sc in report['scenarios']:
        mark = "✅ conforme" if sc['status'] == 'ok' else "❌ **anomalie**"
        lines.append("| **%s** — %s | %s | `%s` | %d | %s |"
                     % (sc['code'], sc['title'], sc['role'], sc['login'],
                        len(sc['steps']), mark))
    lines.append("")
    return lines


def scenario_section(sc):
    lines = ["---", "",
             "## %s — %s" % (sc['code'], sc['title']), ""]
    if sc.get('goal'):
        lines += ["> %s" % sc['goal'], ""]
    lines += ["**Rôle** : %s  ·  **Compte** : `%s`  ·  **Durée** : %s s"
              % (sc['role'], sc['login'], sc.get('duration', '—')), ""]
    if sc['status'] != 'ok':
        lines += ["> ❌ **Anomalie** : %s" % sc.get('error', ''), ""]
    for index, step in enumerate(sc['steps'], start=1):
        mark = "✅" if step['status'] == 'ok' else "❌"
        lines.append("### %s %d. %s" % (mark, index, step['label']))
        lines.append("")
        if step.get('check'):
            lines.append("*Contrôle* : %s" % step['check'])
            lines.append("")
        if step.get('error'):
            lines.append("*Anomalie* : `%s`" % step['error'])
            lines.append("")
        if step.get('shot'):
            lines.append("![%s](captures/%s)" % (step['label'], step['shot']))
            lines.append("")
    if sc.get('console'):
        lines.append("> ⚠ %d message(s) d'erreur dans la console du "
                     "navigateur :" % len(sc['console']))
        for message in sc['console'][:5]:
            lines.append("> - `%s`" % message['text'][:200])
        lines.append("")
    return lines


def interfaces_section(data):
    if not data:
        return []
    lines = ["---", "", "## Interfaces techniques", "",
             "Contrôles joués hors navigateur, comme le ferait un client "
             "réel : l'Explorateur Windows sur le lecteur réseau, un "
             "progiciel tiers sur l'API, un correspondant externe sur un "
             "lien de partage.", "",
             "| Interface | Contrôle | Résultat | Constat |",
             "| --- | --- | --- | --- |"]
    for entry in data['controles']:
        mark = "✅" if entry['statut'] == 'ok' else "❌"
        lines.append("| %s | %s | %s | %s |"
                     % (entry['famille'], entry['libelle'], mark,
                        entry['constat'].replace('|', '/')[:120]))
    lines.append("")
    return lines


def main():
    report = json.load(open(RESULTS, encoding='utf-8'))
    interfaces = None
    if os.path.exists(INTERFACES):
        interfaces = json.load(open(INTERFACES, encoding='utf-8'))
    out = [HEADER.format(date=report.get('date', datetime.now().isoformat()),
                         base_url=report.get('base_url', ''))]
    out += summary_table(report)
    out += interfaces_section(interfaces)
    for sc in report['scenarios']:
        out += scenario_section(sc)
    out += ["---", "",
            "*Guide produit automatiquement par "
            "`docs/recette/build_guide.py` à partir de la dernière campagne.*",
            ""]
    with open(GUIDE, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    shots = sum(len(sc['shots']) for sc in report['scenarios'])
    print("Guide écrit : %s (%d scénarios, %d captures)"
          % (GUIDE, len(report['scenarios']), shots))


if __name__ == '__main__':
    main()
