# -*- coding: utf-8 -*-
"""Recette des interfaces techniques : WebDAV, API REST, lien de partage.

Ces trois portes d'entrée ne passent pas par le navigateur Odoo : on les
éprouve comme le ferait un client réel — l'Explorateur Windows monte le
lecteur WebDAV, un progiciel tiers appelle l'API avec sa clé, un
correspondant externe ouvre un lien de partage. Chaque contrôle est
consigné dans ``resultats_interfaces.json``.

Usage ::

    python3 docs/recette/uat_interfaces.py
    python3 docs/recette/uat_interfaces.py --url http://localhost:8169 \\
        --db aite_uat
"""
import argparse
import base64
import json
import os
import re
import sys
import traceback
from datetime import datetime
from urllib.parse import quote

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'resultats_interfaces.json')
BASE_URL = os.environ.get('AITE_URL', 'http://localhost:8169')
LOGIN = os.environ.get('AITE_LOGIN', 'demo.archive')
PASSWORD = os.environ.get('AITE_PASSWORD', 'aite2026')
DOCX = b"PK\x03\x04 fichier de recette AITE"


class Anomaly(Exception):
    pass


class Report:
    def __init__(self):
        self.entries = []

    def check(self, family, label, func):
        entry = {'famille': family, 'libelle': label, 'statut': 'ok'}
        try:
            entry['constat'] = func() or "contrôle passé"
        except Exception as exc:  # noqa: BLE001
            entry['statut'] = 'ko'
            entry['constat'] = "%s: %s" % (type(exc).__name__, exc)
            entry['trace'] = traceback.format_exc()[-800:]
        self.entries.append(entry)
        mark = "OK  " if entry['statut'] == 'ok' else "ÉCHEC"
        print("   %s %-52s %s" % (mark, label, entry['constat'][:90]))
        return entry


def dav(method, path='', auth=None, data=None, headers=None):
    url = BASE_URL + '/webdav/aite_ecm/' + '/'.join(
        quote(p) for p in path.split('/') if p)
    return requests.request(method, url, auth=auth or (LOGIN, PASSWORD),
                            data=data, headers=headers or {}, timeout=30)


# ====================================================================== #
def run_webdav(report):
    print("\n— WebDAV (lecteur réseau) —")
    report.check('WebDAV', "Refus sans identifiants",
                 lambda: _dav_unauthorized())
    listing = {}
    report.check('WebDAV', "PROPFIND de la racine",
                 lambda: _dav_propfind(listing))
    report.check('WebDAV', "Un dossier de classement est listé",
                 lambda: _dav_folder(listing))
    report.check('WebDAV', "OPTIONS annonce la classe 2 (verrous)",
                 lambda: _dav_options())
    report.check('WebDAV', "Identifiants erronés refusés",
                 lambda: _dav_bad_password())
    report.check('WebDAV', "Enregistrement depuis le lecteur réseau (PUT)",
                 lambda: _dav_put(listing))


def _dav_unauthorized():
    resp = requests.request('PROPFIND', BASE_URL + '/webdav/aite_ecm/',
                            timeout=30)
    if resp.status_code != 401:
        raise Anomaly("attendu 401, obtenu %s" % resp.status_code)
    if 'Basic' not in resp.headers.get('WWW-Authenticate', ''):
        raise Anomaly("en-tête WWW-Authenticate absent : un client réseau ne "
                      "saura pas quoi présenter")
    return "401 + WWW-Authenticate: Basic"


def _dav_propfind(listing):
    resp = dav('PROPFIND', headers={'Depth': '1'})
    if resp.status_code != 207:
        raise Anomaly("attendu 207 Multi-Status, obtenu %s — %s"
                      % (resp.status_code, resp.text[:200]))
    names = re.findall(r'<D:displayname>([^<]*)</D:displayname>', resp.text)
    listing['names'] = names
    if not names:
        raise Anomaly("aucune ressource listée")
    return "%d entrée(s) : %s…" % (len(names), ", ".join(names[:3]))


def _dav_folder(listing):
    names = [n for n in listing.get('names', []) if n and n != '/']
    if not names:
        raise Anomaly("racine vide")
    target = names[1] if len(names) > 1 else names[0]
    resp = dav('PROPFIND', target, headers={'Depth': '1'})
    if resp.status_code != 207:
        raise Anomaly("PROPFIND « %s » : %s" % (target, resp.status_code))
    return "« %s » exploré (%d octets de réponse)" % (target,
                                                      len(resp.content))


def _dav_options():
    resp = dav('OPTIONS')
    if resp.status_code != 200:
        raise Anomaly("OPTIONS : %s" % resp.status_code)
    dav_header = resp.headers.get('DAV', '')
    if '2' not in dav_header:
        raise Anomaly("classe DAV annoncée : %r (verrous attendus)"
                      % dav_header)
    return "DAV: %s — Allow: %s" % (dav_header,
                                    resp.headers.get('Allow', '')[:60])


def _dav_bad_password():
    resp = dav('PROPFIND', auth=(LOGIN, 'mauvais-mot-de-passe'),
               headers={'Depth': '0'})
    if resp.status_code != 401:
        raise Anomaly("attendu 401, obtenu %s" % resp.status_code)
    return "401 sur mot de passe erroné"


def _dav_put(listing):
    """Écrit un fichier comme le ferait Word en enregistrant : le document
    doit gagner une version, pas être écrasé."""
    folders = [n for n in listing.get('names', [])
               if n and n not in ('aite_ecm', '/')]
    for folder in folders:
        resp = dav('PROPFIND', folder, headers={'Depth': '1'})
        files = [n for n in re.findall(
            r'<D:displayname>([^<]*)</D:displayname>', resp.text)
            if '.' in n]
        if not files:
            continue
        target = "%s/%s" % (folder, files[0])
        before = dav('GET', target)
        if before.status_code != 200:
            continue
        put = dav('PUT', target, data=DOCX + b" v2",
                  headers={'Content-Type': 'application/octet-stream'})
        if put.status_code not in (200, 201, 204):
            raise Anomaly("PUT « %s » : %s — %s"
                          % (target, put.status_code, put.text[:150]))
        after = dav('GET', target)
        if after.status_code != 200:
            raise Anomaly("relecture après PUT : %s" % after.status_code)
        if after.content == before.content:
            raise Anomaly("le contenu n'a pas changé après l'enregistrement")
        return "« %s » réenregistré (%d → %d octets)" % (
            files[0], len(before.content), len(after.content))
    raise Anomaly("aucun fichier trouvé dans l'espace WebDAV")


# ====================================================================== #
def run_api(report, api_key):
    print("\n— API REST /api/ecm/v1 —")
    prefix = BASE_URL + '/api/ecm/v1'
    head = {'X-API-Key': api_key, 'Content-Type': 'application/json'}
    state = {}

    def sans_cle():
        resp = requests.get(prefix + '/ping', timeout=30)
        if resp.status_code != 401:
            raise Anomaly("attendu 401, obtenu %s" % resp.status_code)
        return "401 sans clé d'API"

    def ping():
        resp = requests.get(prefix + '/ping', headers=head, timeout=30)
        if resp.status_code != 200:
            raise Anomaly("%s — %s" % (resp.status_code, resp.text[:200]))
        return "authentifié comme %s" % resp.json().get('user')

    def recherche():
        resp = requests.get(prefix + '/documents?limit=5', headers=head,
                            timeout=30)
        body = resp.json()
        if resp.status_code != 200 or not body.get('items'):
            raise Anomaly("recherche vide (%s)" % resp.status_code)
        state['doc'] = body['items'][0]
        return "%d document(s) au total, page de %d" % (body['total'],
                                                        len(body['items']))

    def fiche():
        doc = state['doc']
        resp = requests.get('%s/documents/%d' % (prefix, doc['id']),
                            headers=head, timeout=30)
        if resp.status_code != 200:
            raise Anomaly("%s" % resp.status_code)
        return "%s — %s" % (resp.json().get('reference'),
                            resp.json().get('name', '')[:40])

    def creation():
        payload = {'name': "Document créé par l'API — recette",
                   'type_code': 'PROC',
                   'file': {'filename': "recette.pdf",
                            'content_base64': base64.b64encode(
                                b"%PDF-1.4\n%recette\n%%EOF\n").decode()}}
        resp = requests.post(prefix + '/documents', headers=head,
                             data=json.dumps(payload), timeout=30)
        if resp.status_code != 201:
            raise Anomaly("%s — %s" % (resp.status_code, resp.text[:200]))
        body = resp.json()
        state['cree'] = body
        if not re.match(r'DOC-\d{4}-\d+', body.get('reference', '')):
            raise Anomaly("référence inattendue : %r" % body.get('reference'))
        return "créé %s" % body['reference']

    def version():
        doc = state['cree']
        payload = {'filename': "recette_v2.pdf",
                   'content_base64': base64.b64encode(
                       b"%PDF-1.4\n%recette v2\n%%EOF\n").decode(),
                   'comment': "seconde version"}
        resp = requests.post('%s/documents/%d/versions' % (prefix, doc['id']),
                             headers=head, data=json.dumps(payload),
                             timeout=30)
        if resp.status_code != 201:
            raise Anomaly("%s — %s" % (resp.status_code, resp.text[:200]))
        body = resp.json()
        if body.get('version') != 'v2' or len(body.get('sha256', '')) != 64:
            raise Anomaly("version ou empreinte inattendue : %s" % body)
        return "v2 déposée, empreinte %s…" % body['sha256'][:16]

    def telechargement():
        doc = state['cree']
        resp = requests.get('%s/documents/%d/download' % (prefix, doc['id']),
                            headers=head, timeout=30)
        if resp.status_code != 200 or not resp.content.startswith(b'%PDF'):
            raise Anomaly("téléchargement : %s" % resp.status_code)
        return "%d octets, %s" % (len(resp.content),
                                  resp.headers.get('Content-Type'))

    def format_refuse():
        doc = state['cree']
        payload = {'filename': "charge.exe", 'content_base64': base64.b64encode(
            b"MZ").decode()}
        resp = requests.post('%s/documents/%d/versions' % (prefix, doc['id']),
                             headers=head, data=json.dumps(payload),
                             timeout=30)
        if resp.status_code != 422:
            raise Anomaly("un exécutable a été accepté (%s)"
                          % resp.status_code)
        return "422 — format refusé"

    def openapi():
        resp = requests.get(prefix + '/openapi.json', headers=head,
                            timeout=30)
        spec = resp.json()
        if 'openapi' not in spec or '/documents' not in spec.get('paths', {}):
            raise Anomaly("spécification incomplète")
        return "OpenAPI %s, %d chemin(s)" % (spec['openapi'],
                                             len(spec['paths']))

    report.check('API', "Refus sans clé d'API", sans_cle)
    report.check('API', "Authentification par clé", ping)
    report.check('API', "Recherche de documents", recherche)
    report.check('API', "Fiche d'un document", fiche)
    report.check('API', "Création d'un document avec fichier", creation)
    report.check('API', "Dépôt d'une seconde version", version)
    report.check('API', "Téléchargement du fichier", telechargement)
    report.check('API', "Format exécutable refusé", format_refuse)
    report.check('API', "Spécification OpenAPI", openapi)


# ====================================================================== #
def run_share(report, share_url, token):
    print("\n— Lien de partage externe —")

    def page_publique():
        resp = requests.get(share_url, timeout=30)
        if resp.status_code != 200:
            raise Anomaly("%s" % resp.status_code)
        return "page d'accueil servie (%d octets), sans authentification" \
            % len(resp.content)

    def fichier():
        resp = requests.get(share_url.rstrip('/') + '/file', timeout=30)
        if resp.status_code != 200:
            raise Anomaly("%s" % resp.status_code)
        if resp.headers.get('X-Content-Type-Options') != 'nosniff':
            raise Anomaly("en-tête de sécurité X-Content-Type-Options absent")
        return "%d octets, %s" % (len(resp.content),
                                  resp.headers.get('Content-Type'))

    def jeton_invalide():
        resp = requests.get("%s/ecm/share/%s" % (BASE_URL, 'jeton-inexistant'),
                            timeout=30)
        if resp.status_code != 404:
            raise Anomaly("attendu 404, obtenu %s" % resp.status_code)
        return "404 sur jeton inconnu"

    report.check('Partage', "Page publique du lien", page_publique)
    report.check('Partage', "Téléchargement du fichier partagé", fichier)
    report.check('Partage', "Jeton inconnu refusé", jeton_invalide)
    print("      lien testé : %s" % share_url)
    return token


# ====================================================================== #
def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=BASE_URL)
    parser.add_argument('--api-key', default=os.environ.get('AITE_API_KEY'))
    parser.add_argument('--share-url', default=os.environ.get('AITE_SHARE_URL'))
    args = parser.parse_args()
    BASE_URL = args.url
    report = Report()
    run_webdav(report)
    if args.api_key:
        run_api(report, args.api_key)
    else:
        print("\n— API REST — ignorée (pas de clé fournie : --api-key)")
    if args.share_url:
        run_share(report, args.share_url, None)
    else:
        print("\n— Lien de partage — ignoré (pas de lien : --share-url)")
    failures = [e for e in report.entries if e['statut'] != 'ok']
    with open(RESULTS, 'w', encoding='utf-8') as fh:
        json.dump({'base_url': BASE_URL,
                   'date': datetime.now().isoformat(' ', 'seconds'),
                   'controles': report.entries}, fh,
                  ensure_ascii=False, indent=2)
    print("\n%d contrôle(s), %d en échec — rapport : %s"
          % (len(report.entries), len(failures), RESULTS))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
