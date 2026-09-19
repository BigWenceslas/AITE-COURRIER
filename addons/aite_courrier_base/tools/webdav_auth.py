# -*- coding: utf-8 -*-
"""Authentification HTTP Basic des serveurs WebDAV de la suite.

Un client WebDAV — Explorateur Windows, Finder, Word — ne garde pas de
session : il présente ses identifiants à **chaque** requête, et en envoie des
dizaines par dossier ouvert. Or Odoo 17 et 18 hachent les mots de passe avec
600 000 itérations de PBKDF2 : vérifier un mot de passe coûte de l'ordre
d'une seconde de calcul. Sans cache, chaque listage et chaque lecture paient
ce prix — c'est ce qui rendait le lecteur réseau inutilisable.

Deux réponses, complémentaires :

* les **clés d'API** Odoo, faites pour l'accès programmatique — hachage
  léger, révocables une à une, seule voie pour un compte à double
  authentification, qu'une connexion Basic ne peut pas mener au bout ;
* un **cache** de courte durée des vérifications réussies, pour les postes
  qui continuent d'utiliser le mot de passe du compte.

Le cache ne conserve qu'une empreinte SHA-256, salée par le secret de la base ;
il vit en mémoire du processus, expire après ``TTL`` secondes, et revérifie à
chaque coup que le compte est toujours actif. Un mot de passe ou une clé
révoqués restent donc acceptés au plus ``TTL`` secondes sur ce processus.
"""
import hashlib
import logging
import re
import threading
import time

_logger = logging.getLogger(__name__)

#: Durée de validité d'une vérification réussie, en secondes.
TTL = 300
#: Taille maximale du cache ; au-delà, un dixième des entrées les plus
#: proches de l'expiration est évincé.
MAX_ENTRIES = 2000

#: Forme d'une clé d'API Odoo : 40 caractères hexadécimaux. Sert seulement à
#: choisir l'ordre des essais, jamais à en exclure un.
_API_KEY = re.compile(r'^[0-9a-f]{40}$')

_cache = {}
_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
def _fingerprint(secret, db, login, password):
    material = '\0'.join((secret, db, login, password)).encode('utf-8')
    return hashlib.sha256(material).hexdigest()


def _remember(fingerprint, uid):
    with _lock:
        if len(_cache) >= MAX_ENTRIES:
            soonest = sorted(_cache.items(), key=lambda item: item[1][1])
            for key, _entry in soonest[:max(1, MAX_ENTRIES // 10)]:
                _cache.pop(key, None)
        _cache[fingerprint] = (uid, time.monotonic() + TTL)


def _recall(fingerprint):
    with _lock:
        entry = _cache.get(fingerprint)
        if not entry:
            return None
        uid, expiry = entry
        if expiry <= time.monotonic():
            _cache.pop(fingerprint, None)
            return None
        return uid


def _forget(fingerprint):
    with _lock:
        _cache.pop(fingerprint, None)


def forget_all():
    """Vide le cache — tests, ou révocation à effet immédiat."""
    with _lock:
        _cache.clear()


# --------------------------------------------------------------------------- #
# Vérifications
# --------------------------------------------------------------------------- #
def _by_api_key(env, login, key):
    """uid si ``key`` est une clé d'API valide **du** compte ``login``."""
    try:
        uid = env['res.users.apikeys'].sudo()._check_credentials(
            scope='rpc', key=key)
    except Exception:  # noqa: BLE001 - clé mal formée, table absente…
        return None
    if not uid:
        return None
    user = env['res.users'].sudo().browse(uid)
    if not user.exists() or not user.active or user.login != login:
        return None
    return uid


def _by_password(request, db, login, password):
    """uid par la connexion Odoo ordinaire ; ``None`` si refusée, ou laissée
    incomplète (double authentification en attente)."""
    try:
        request.session.authenticate(
            db, {'login': login, 'password': password, 'type': 'password'})
    except Exception:  # noqa: BLE001
        return None
    return request.session.uid or None


def authenticate(request, db, login, password):
    """uid du compte désigné par ``login`` / ``password``, ou ``None``.

    ``password`` est le mot de passe du compte **ou** l'une de ses clés
    d'API ; les deux sont essayés, la forme du secret décidant de l'ordre.
    L'appelant reste responsable de ``request.update_env(user=uid)``.
    """
    if not (db and login and password):
        return None
    env = request.env if getattr(request, 'db', None) else None
    secret = (env['ir.config_parameter'].sudo().get_param('database.secret', '')
              if env is not None else '')
    fingerprint = _fingerprint(secret, db, login, password)

    uid = _recall(fingerprint)
    if uid:
        if env is None:
            return uid
        user = env['res.users'].sudo().browse(uid)
        if user.exists() and user.active:
            return uid
        _forget(fingerprint)

    attempts = [
        lambda: _by_api_key(env, login, password) if env is not None else None,
        lambda: _by_password(request, db, login, password),
    ]
    if not _API_KEY.match(password):
        attempts.reverse()
    for attempt in attempts:
        uid = attempt()
        if uid:
            _remember(fingerprint, uid)
            return uid
    return None
