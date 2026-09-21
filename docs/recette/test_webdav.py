#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recette du flux WebDAV AITE contre une instance Odoo lancée.

Déroule sur un serveur réel le dialogue WebDAV complet — découverte,
authentification, listage, dépôt, relecture, versionnage, renommage, verrous,
suppression — puis imprime un rapport PASS / FAIL / SKIP.

    python3 docs/recette/test_webdav.py --url http://localhost:8069 \
        --login admin --password admin

Racines testées (détectées automatiquement, cf. ``--root``) :

    /webdav/aite_courrier   module aite_courrier_webdav (pièces des courriers)
    /webdav/aite_ecm        module aite_ecm_webdav (plan de classement ECM)

Le script ne crée ni courrier ni dossier de classement : il travaille dans une
collection existante et supprime ce qu'il y dépose (sauf ``--keep``).
Bibliothèque standard uniquement, Python 3.8+.

Code de sortie : 0 si tout passe, 1 si au moins un contrôle échoue, 2 si le
serveur est injoignable ou si aucune racine WebDAV ne répond.
"""
import argparse
import base64
import hashlib
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import quote
from xml.etree import ElementTree

DAV = '{DAV:}'

#: Racines exposées par les modules WebDAV de la suite.
ROOTS = {
    'courrier': '/webdav/aite_courrier',
    'ecm': '/webdav/aite_ecm',
}

#: Statuts attendus qui diffèrent d'une racine à l'autre.
#: L'ECM autorise la création de dossiers de classement (MKCOL), pas le
#: courrier dont l'arborescence est pilotée par l'application.
EXPECTED_MKCOL = {'courrier': 403, 'ecm': 201}

#: Plus petit PDF valide : le contrôle de format porte sur l'extension, mais
#: un contenu cohérent évite les faux positifs si un antivirus s'interpose.
PDF_V1 = (b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n'
          b'%%EOF\n')
PDF_V2 = (b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n'
          b'% version 2 deposee par la recette WebDAV\ntrailer<</Root 1 0 R>>\n'
          b'%%EOF\n')

BASENAME = 'recette-webdav'


class Unreachable(Exception):
    """Le serveur ne répond pas (réseau, port fermé, TLS)."""


# --------------------------------------------------------------------------- #
# Client WebDAV minimal
# --------------------------------------------------------------------------- #
class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Une redirection est un échec en WebDAV : on veut le statut brut.

    Sans cela, un 302 vers /web/login (route absente = module non installé)
    se présenterait comme un 200 sur une page HTML.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Reply:
    """Réponse HTTP : statut, corps, en-têtes."""

    def __init__(self, status, body, headers):
        self.status = status
        self.body = body or b''
        self.headers = headers

    def header(self, name, default=''):
        return self.headers.get(name, default) if self.headers else default

    @property
    def text(self):
        return self.body.decode('utf-8', 'replace')

    def summary(self, limit=160):
        """Extrait de corps utilisable dans un message d'échec."""
        text = ' '.join(self.text.split())
        return text[:limit] + ('…' if len(text) > limit else '')


class Dav:
    """Dialogue WebDAV sur une instance Odoo, en HTTP Basic."""

    def __init__(self, url, login, password, root, timeout=30, verbose=False,
                 verify=True):
        self.base = url.rstrip('/')
        self.root = root
        self.timeout = timeout
        self.verbose = verbose
        token = base64.b64encode(
            ('%s:%s' % (login, password)).encode('utf-8')).decode('ascii')
        self.authorization = 'Basic ' + token
        handlers = [NoRedirect()]
        if not verify:
            # Une autorité interne (Caddy, certificat auto-signé) n'a ni CRL
            # ni OCSP : la vérification de révocation échoue alors même que la
            # chaîne est approuvée. Sur une instance locale, on la désactive.
            handlers.append(urllib.request.HTTPSHandler(
                context=ssl._create_unverified_context()))
        self.opener = urllib.request.build_opener(*handlers)

    # -- construction d'URL ------------------------------------------------ #
    def url_for(self, path='', collection=False):
        """URL absolue d'une ressource, chaque segment étant échappé.

        Les noms de dossiers et de fichiers contiennent des espaces (« Sans
        classement », « DOC-2026-00001 - Contrat.pdf ») : sans échappement, le
        serveur reçoit une requête invalide.
        """
        segments = [quote(s) for s in path.split('/') if s]
        url = self.base + self.root
        if segments:
            url += '/' + '/'.join(segments)
        elif collection:
            url += '/'
        if collection and segments:
            url += '/'
        return url

    # -- appel ------------------------------------------------------------- #
    def call(self, method, path='', body=None, headers=None, auth=True,
             collection=False, credentials=None):
        url = self.url_for(path, collection=collection)
        sent = dict(headers or {})
        if credentials is not None:
            token = base64.b64encode(
                ('%s:%s' % credentials).encode('utf-8')).decode('ascii')
            sent['Authorization'] = 'Basic ' + token
        elif auth:
            sent['Authorization'] = self.authorization
        request = urllib.request.Request(url, data=body, headers=sent,
                                         method=method)
        try:
            response = self.opener.open(request, timeout=self.timeout)
            reply = Reply(response.status, response.read(), response.headers)
        except urllib.error.HTTPError as error:
            # 4xx, 5xx et redirections non suivies : ce sont des réponses.
            reply = Reply(error.code, error.read(), error.headers)
        except urllib.error.URLError as error:
            raise Unreachable('%s : %s' % (url, error.reason))
        except OSError as error:                     # timeout, reset, TLS
            raise Unreachable('%s : %s' % (url, error))
        if self.verbose:
            print('    → %-8s %-60s %s' % (method, url[len(self.base):],
                                           reply.status))
        return reply

    # -- raccourcis -------------------------------------------------------- #
    def propfind(self, path='', depth='1', **kwargs):
        return self.call('PROPFIND', path, headers={'Depth': depth},
                         collection=depth != '0' or not path, **kwargs)

    def listing(self, path='', depth='1'):
        """PROPFIND + analyse : liste de descripteurs de ressources."""
        reply = self.propfind(path, depth=depth)
        if reply.status != 207:
            return reply, []
        return reply, parse_multistatus(reply.body)


def parse_multistatus(raw):
    """Analyse un ``D:multistatus`` → liste de dictionnaires.

    Chaque entrée porte ``href``, ``name`` (displayname), ``is_collection`` et
    ``size``. La première entrée décrit la ressource demandée, les suivantes
    ses enfants.
    """
    resources = []
    root = ElementTree.fromstring(raw)
    for response in root.findall(DAV + 'response'):
        href = (response.findtext(DAV + 'href') or '').strip()
        prop = response.find('.//' + DAV + 'prop')
        name = size = None
        is_collection = False
        if prop is not None:
            name = prop.findtext(DAV + 'displayname')
            resourcetype = prop.find(DAV + 'resourcetype')
            is_collection = (resourcetype is not None
                             and resourcetype.find(DAV + 'collection') is not None)
            raw_size = prop.findtext(DAV + 'getcontentlength')
            size = int(raw_size) if (raw_size or '').isdigit() else None
        resources.append({
            'href': href, 'name': name, 'size': size,
            'is_collection': is_collection,
            'content_type': prop.findtext(DAV + 'getcontenttype') if prop is not None
                            else None,
        })
    return resources


# --------------------------------------------------------------------------- #
# Rapport
# --------------------------------------------------------------------------- #
class Report:
    """Collecte des contrôles et rapport final PASS / FAIL / SKIP."""

    def __init__(self, color=True):
        self.color = color
        self.rows = []

    def _paint(self, text, code):
        return '\033[%sm%s\033[0m' % (code, text) if self.color else text

    def section(self, title):
        print('\n' + self._paint(title, '1'))
        print('-' * len(title))

    def check(self, label, ok, detail='', info=''):
        """``detail`` explique l'échec, ``info`` contextualise le succès."""
        self.rows.append((label, bool(ok)))
        mark = self._paint('PASS', '32') if ok else self._paint('FAIL', '31')
        line = '  [%s] %s' % (mark, label)
        if not ok:
            if detail or info:
                line += '\n         ↳ %s' % (detail or info)
        elif info:
            line += '  (%s)' % info
        print(line)
        return ok

    def skip(self, label, reason):
        self.rows.append((label, None))
        print('  [%s] %s\n         ↳ %s'
              % (self._paint('SKIP', '33'), label, reason))

    def note(self, text):
        print('  %s %s' % (self._paint('note :', '36'), text))

    def summary(self):
        passed = sum(1 for _, ok in self.rows if ok is True)
        failed = [label for label, ok in self.rows if ok is False]
        skipped = sum(1 for _, ok in self.rows if ok is None)
        print('\n' + '=' * 62)
        print('Résultat : %s réussis, %s échoués, %s ignorés'
              % (passed, len(failed), skipped))
        for label in failed:
            print('  %s %s' % (self._paint('✗', '31'), label))
        print('=' * 62)
        return 1 if failed else 0


def expect(report, label, reply, status, detail=''):
    """Contrôle du statut HTTP d'une réponse."""
    wanted = status if isinstance(status, (list, tuple)) else [status]
    ok = reply.status in wanted
    if not ok:
        detail = ('statut %s, attendu %s — %s'
                  % (reply.status, '/'.join(str(s) for s in wanted),
                     reply.summary()))
    return report.check(label, ok, detail)


# --------------------------------------------------------------------------- #
# Phase 1 — le service répond et protège l'accès
# --------------------------------------------------------------------------- #
def phase_service(dav, report):
    report.section('1. Service et authentification')

    reply = dav.call('OPTIONS', auth=False, collection=True)
    expect(report, 'OPTIONS sans authentification → 200', reply, 200)
    dav_header = reply.header('DAV')
    report.check("en-tête DAV annonce le niveau 1", '1' in dav_header,
                 info='DAV: %s' % (dav_header or '(absent)'))
    allow = reply.header('Allow')
    missing = [verb for verb in ('PROPFIND', 'GET', 'PUT', 'DELETE', 'MOVE')
               if verb not in allow]
    report.check('en-tête Allow annonce les verbes WebDAV', not missing,
                 detail='verbes manquants : %s (Allow: %s)'
                        % (', '.join(missing), allow or '(absent)'))

    reply = dav.propfind(auth=False)
    expect(report, 'PROPFIND anonyme → 401', reply, 401)
    challenge = reply.header('WWW-Authenticate')
    report.check('le 401 porte un défi Basic', challenge.startswith('Basic'),
                 detail='WWW-Authenticate: %s' % (challenge or '(absent)'))

    reply = dav.propfind(credentials=('recette-inexistant', 'mauvais-mot-de-passe'))
    expect(report, 'PROPFIND avec identifiants erronés → 401', reply, 401)


# --------------------------------------------------------------------------- #
# Phase 2 — listage de l'arborescence
# --------------------------------------------------------------------------- #
def phase_listing(dav, report):
    """Contrôle le listage et retourne les collections disponibles."""
    report.section('2. Listage de l\'arborescence')

    reply, resources = dav.listing(depth='1')
    if not expect(report, 'PROPFIND racine (Depth: 1) → 207 multistatus',
                  reply, 207):
        # 401 = identifiants refusés : le distinguer d'une arborescence vide,
        # sinon le message de prérequis envoie chercher au mauvais endroit.
        return None if reply.status == 401 else []
    report.check('la racine est décrite comme une collection',
                 bool(resources) and resources[0]['is_collection'],
                 detail='première entrée : %s'
                        % (resources[0] if resources else '(multistatus vide)'))

    children = resources[1:]
    collections = [child['name'] for child in children
                   if child['is_collection'] and child['name']]
    report.note('%d collection(s), %d fichier(s) à la racine%s'
                % (len(collections), len(children) - len(collections),
                   ' : ' + ', '.join(collections[:8]) if collections else ''))

    reply, shallow = dav.listing(depth='0')
    expect(report, 'PROPFIND racine (Depth: 0) → 207', reply, 207)
    report.check('Depth: 0 ne retourne que la ressource demandée',
                 len(shallow) == 1, '%d entrées retournées' % len(shallow))

    reply = dav.propfind('collection-qui-nexiste-pas-recette')
    expect(report, 'PROPFIND d\'une collection inconnue → 404', reply, 404)

    return collections


# --------------------------------------------------------------------------- #
# Phase 3 — cycle de vie d'un fichier
# --------------------------------------------------------------------------- #
def resolve_name(dav, collection, put_name):
    """Nom réellement exposé pour un fichier déposé sous ``put_name``.

    Le courrier conserve le nom déposé ; l'ECM republie le document sous
    « RÉFÉRENCE - Titre.ext ». On relit donc le listage après chaque écriture
    qui crée ou renomme.
    """
    _reply, resources = dav.listing(collection, depth='1')
    base = put_name.rsplit('.', 1)[0]
    for resource in resources[1:]:
        name = resource['name'] or ''
        if name == put_name or name.endswith(' - ' + put_name) or base in name:
            return name
    return None


def phase_file(dav, report, kind, collection, keep=False, strict=False):
    """Dépôt, relecture, versionnage, renommage, verrous et suppression."""
    report.section('3. Cycle de vie d\'un fichier dans « %s »' % collection)
    put_name = BASENAME + '.pdf'
    path = '%s/%s' % (collection, put_name)
    created = []

    try:
        reply = dav.call('PUT', path, body=PDF_V1,
                         headers={'Content-Type': 'application/pdf'})
        if not expect(report, 'PUT d\'un fichier absent → 201 Created', reply, 201):
            return
        name = resolve_name(dav, collection, put_name) or put_name
        path = '%s/%s' % (collection, name)
        created.append(path)
        if name != put_name:
            report.note('publié sous « %s » (référence + titre)' % name)

        reply = dav.call('GET', path)
        expect(report, 'GET → 200', reply, 200)
        report.check('le contenu relu est identique à l\'octet près',
                     hashlib.sha256(reply.body).hexdigest()
                     == hashlib.sha256(PDF_V1).hexdigest(),
                     '%d octets reçus, %d déposés' % (len(reply.body), len(PDF_V1)))
        content_type = reply.header('Content-Type')
        report.check('le type MIME déduit de l\'extension est servi',
                     'pdf' in content_type, 'Content-Type: %r' % content_type)

        reply = dav.call('HEAD', path)
        expect(report, 'HEAD → 200', reply, 200)
        report.check('HEAD annonce la taille sans renvoyer le corps',
                     reply.header('Content-Length') == str(len(PDF_V1))
                     and not reply.body,
                     'Content-Length: %r, %d octets de corps'
                     % (reply.header('Content-Length'), len(reply.body)))

        reply, resources = dav.listing(path, depth='0')
        expect(report, 'PROPFIND du fichier (Depth: 0) → 207', reply, 207)
        size = resources[0]['size'] if resources else None
        report.check('getcontentlength correspond à la version déposée',
                     size == len(PDF_V1), 'annoncé %r, attendu %d'
                     % (size, len(PDF_V1)))

        reply = dav.call('PUT', path, body=PDF_V2,
                         headers={'Content-Type': 'application/pdf'})
        expect(report, 'PUT sur un fichier existant → 204 (nouvelle version)',
               reply, 204)
        reply = dav.call('GET', path)
        report.check('GET renvoie bien la dernière version',
                     reply.status == 200
                     and hashlib.sha256(reply.body).hexdigest()
                     == hashlib.sha256(PDF_V2).hexdigest(),
                     'statut %s, %d octets (v2 = %d octets)'
                     % (reply.status, len(reply.body), len(PDF_V2)))

        _reply, resources = dav.listing(collection, depth='1')
        report.check('le fichier apparaît dans le listage de sa collection',
                     any(r['name'] == name for r in resources[1:]),
                     detail='noms listés : %s'
                            % (', '.join(r['name'] or '?' for r in resources[1:])
                               or '(aucun)'))

        renamed = BASENAME + '-renomme.pdf'
        reply = dav.call('MOVE', path, headers={
            'Destination': dav.url_for('%s/%s' % (collection, renamed)),
            'Overwrite': 'T'})
        if expect(report, 'MOVE (renommage) → 201', reply, [201, 204]):
            new_name = resolve_name(dav, collection, renamed) or renamed
            old_path, path = path, '%s/%s' % (collection, new_name)
            created.append(path)
            expect(report, 'l\'ancien nom ne répond plus → 404',
                   dav.call('GET', old_path), 404)
            expect(report, 'le nouveau nom répond → 200',
                   dav.call('GET', path), 200)

        reply = dav.call('LOCK', path, body=(
            b'<?xml version="1.0" encoding="utf-8"?>'
            b'<D:lockinfo xmlns:D="DAV:"><D:lockscope><D:exclusive/></D:lockscope>'
            b'<D:locktype><D:write/></D:locktype></D:lockinfo>'))
        token = reply.header('Lock-Token')
        expect(report, 'LOCK → 200', reply, 200)
        report.check('LOCK renvoie un jeton de verrou', bool(token),
                     'Lock-Token: %r' % token)
        expect(report, 'UNLOCK → 204',
               dav.call('UNLOCK', path,
                        headers={'Lock-Token': token} if token else None), 204)

        reply = dav.call('PUT', '%s/%s.exe' % (collection, BASENAME),
                         body=b'MZ-recette')
        expect(report, 'PUT d\'une extension interdite → 409', reply, 409)
        _reply, after = dav.listing(collection, depth='1')
        report.check('le format refusé n\'a rien laissé dans la collection',
                     not any((r['name'] or '').startswith(BASENAME + '.exe')
                             for r in after[1:]),
                     detail='noms listés : %s'
                            % ', '.join(r['name'] or '?' for r in after[1:]))

        expect(report, 'COPY → 403 (non pris en charge)',
               dav.call('COPY', path, headers={
                   'Destination': dav.url_for('%s/copie-%s' % (collection, BASENAME))}),
               403)

        mkcol_path = '%s/%s-dossier' % (collection, BASENAME)
        if kind == 'courrier':
            expect(report, 'MKCOL → 403 (arborescence pilotée par l\'application)',
                   dav.call('MKCOL', mkcol_path), 403)
        elif strict:
            wanted = 403 if collection == 'Sans classement' else 201
            expect(report, 'MKCOL → %d' % wanted,
                   dav.call('MKCOL', mkcol_path), wanted)
            if wanted == 201:
                report.note('dossier de classement « %s-dossier » créé : '
                            'à supprimer depuis l\'ECM' % BASENAME)
        else:
            report.skip('MKCOL', 'créerait un dossier de classement '
                                 'non supprimable en WebDAV (cf. --strict)')
    finally:
        if keep:
            report.note('--keep : %s laissé(s) en place'
                        % (created[-1] if created else 'rien'))
        elif created:
            reply = dav.call('DELETE', created[-1])
            expect(report, 'DELETE → 204', reply, 204)
            expect(report, 'après suppression, GET → 404',
                   dav.call('GET', created[-1]), 404)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def pick_collection(kind, collections, wanted, report):
    """Collection de travail pour la phase 3."""
    if wanted:
        if wanted not in collections:
            report.note('« %s » absent du listage : essai quand même' % wanted)
        return wanted
    if kind == 'ecm' and 'Sans classement' in collections:
        return 'Sans classement'
    return collections[0] if collections else None


PREREQUIS = {
    'courrier': "aucun courrier visible par ce compte. Créer un courrier puis "
                "« Lancer le circuit » pour qu'une référence COUR-AAAA-NNNN "
                "soit attribuée : la racine WebDAV ne liste que les courriers "
                "enregistrés.",
    'ecm': "aucune collection listée — inattendu, « Sans classement » devrait "
           "toujours être présent. Vérifier les droits ECM du compte utilisé.",
}


def run_root(kind, args, report):
    """Déroule les trois phases sur une racine. Retourne False si injoignable."""
    dav = Dav(args.url, args.login, args.password, ROOTS[kind],
              timeout=args.timeout, verbose=args.verbose,
              verify=not args.no_verify)
    report.section('Racine %s (module aite_%s_webdav)'
                   % (ROOTS[kind], 'courrier' if kind == 'courrier' else 'ecm'))
    phase_service(dav, report)
    collections = phase_listing(dav, report)
    if collections is None:
        report.skip('3. Cycle de vie d\'un fichier',
                    "identifiants refusés par le serveur. Vérifier le login et "
                    "le mot de passe Odoo (une clé d'API fait aussi office de "
                    "mot de passe, et c'est la seule voie pour un compte à "
                    "double authentification), que le compte n'est pas un "
                    "utilisateur « portail », et — si le serveur héberge "
                    "plusieurs bases — que db_name est renseigné dans "
                    "odoo.conf : le contrôleur WebDAV ne sait pas deviner la "
                    "base.")
        return True
    collection = pick_collection(kind, collections, args.collection, report)
    if not collection:
        report.skip('3. Cycle de vie d\'un fichier', PREREQUIS[kind])
        return True
    phase_file(dav, report, kind, collection, keep=args.keep, strict=args.strict)
    return True


def detect_roots(args):
    """Racines qui répondent au OPTIONS (module installé et route servie)."""
    available, absent = [], []
    for kind, root in ROOTS.items():
        dav = Dav(args.url, args.login, args.password, root,
                  timeout=args.timeout, verbose=args.verbose,
                  verify=not args.no_verify)
        reply = dav.call('OPTIONS', auth=False, collection=True)
        if reply.status != 200 or not reply.header('DAV'):
            absent.append((kind, root, reply.status))
            continue
        # Un OPTIONS complaisant (proxy, route voisine) ne suffit pas : une
        # racine réellement servie exige une authentification.
        challenge = dav.propfind(auth=False)
        if challenge.status in (401, 207):
            available.append(kind)
        else:
            absent.append((kind, root, challenge.status))
    return available, absent


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Recette du flux WebDAV AITE sur une instance Odoo lancée.",
        epilog="Exemple : %(prog)s --url http://localhost:8069 "
               "--login admin --password admin")
    parser.add_argument('--url', default='http://localhost:8069',
                        help="URL de l'instance Odoo (défaut : %(default)s)")
    parser.add_argument('--login', required=True,
                        help="login Odoo (mot de passe ou clé d'API en --password)")
    parser.add_argument('--password', required=True, help="mot de passe Odoo")
    parser.add_argument('--root', choices=['auto', 'courrier', 'ecm'],
                        default='auto',
                        help="racine à tester (défaut : toutes celles qui répondent)")
    parser.add_argument('--collection',
                        help="référence de courrier (COUR-2026-0001) ou dossier "
                             "ECM à utiliser pour les écritures")
    parser.add_argument('--keep', action='store_true',
                        help="ne pas supprimer le fichier déposé (inspection manuelle)")
    parser.add_argument('--strict', action='store_true',
                        help="inclure MKCOL côté ECM, qui crée un dossier de "
                             "classement que WebDAV ne sait pas supprimer")
    parser.add_argument('--no-verify', action='store_true',
                        help="ne pas vérifier le certificat TLS — instance "
                             "locale servie par une autorité interne")
    parser.add_argument('--timeout', type=int, default=30,
                        help="délai d'attente réseau en secondes (défaut : %(default)s)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="tracer chaque requête HTTP")
    parser.add_argument('--no-color', action='store_true',
                        help="sortie sans couleurs (journal, CI)")
    args = parser.parse_args(argv)

    report = Report(color=not args.no_color and sys.stdout.isatty())
    print('Instance   : %s' % args.url)
    print('Compte     : %s' % args.login)

    try:
        available, absent = detect_roots(args)
    except Unreachable as error:
        print('\nServeur injoignable — %s' % error)
        print("Vérifier que l'instance tourne et que l'URL/le port sont les bons\n"
              "(depuis la machine qui exécute ce script : "
              "curl -I %s/web/login)." % args.url.rstrip('/'))
        return 2

    for kind, root, status in absent:
        print('Racine     : %s absente (OPTIONS → %s) — module aite_%s_webdav '
              'non installé ?' % (root, status,
                                  'courrier' if kind == 'courrier' else 'ecm'))
    if args.root != 'auto':
        available = [args.root]
    if not available:
        print('\nAucune racine WebDAV ne répond sur %s.' % args.url)
        print("Installer le module (-i aite_courrier_webdav ou -i aite_ecm_webdav)\n"
              "puis relancer. Forcer un test malgré tout : --root courrier.")
        return 2

    try:
        for kind in available:
            run_root(kind, args, report)
    except Unreachable as error:
        print('\nServeur devenu injoignable en cours de test — %s' % error)
        return 2
    except ElementTree.ParseError as error:
        print('\nRéponse XML illisible (%s) : relancer avec -v pour voir le corps.'
              % error)
        return 1
    return report.summary()


if __name__ == '__main__':
    sys.exit(main())
