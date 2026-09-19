# -*- coding: utf-8 -*-
from datetime import timedelta
from types import SimpleNamespace

from odoo import fields
from odoo.exceptions import AccessDenied
from odoo.tests import TransactionCase, tagged

from ..tools import webdav_auth


@tagged('post_install', '-at_install', 'aite_courrier_base')
class TestWebdavAuth(TransactionCase):
    """L'aide d'authentification des serveurs WebDAV : cache et clés d'API."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].with_context(
            no_reset_password=True).create({
                'name': "Agent DAV cache", 'login': "dav_cache",
                'email': "dav_cache@aite.test", 'password': "dav_cache_pwd"})

    def setUp(self):
        super().setUp()
        webdav_auth.forget_all()
        self.calls = []

    def _request(self):
        """Faux ``request`` : environnement réel, connexion Odoo simulée —
        elle compte ses appels, c'est ce que le cache doit économiser."""
        test = self

        class Session:
            uid = None

            def authenticate(self, db, credential):
                test.calls.append(credential['login'])
                if credential['password'] == "dav_cache_pwd" and test.user.active:
                    self.uid = test.user.id
                    return {'uid': self.uid}
                self.uid = None
                raise AccessDenied()

        return SimpleNamespace(env=self.env, db=self.env.cr.dbname,
                               session=Session())

    def _auth(self, password, login="dav_cache"):
        return webdav_auth.authenticate(
            self._request(), self.env.cr.dbname, login, password)

    def test_01_password_verified_once(self):
        self.assertEqual(self._auth("dav_cache_pwd"), self.user.id)
        self.assertEqual(self._auth("dav_cache_pwd"), self.user.id)
        self.assertEqual(len(self.calls), 1,
                         "le second appel doit être servi par le cache")

    def test_02_wrong_password_never_cached(self):
        self.assertIsNone(self._auth("faux"))
        self.assertIsNone(self._auth("faux"))
        self.assertEqual(len(self.calls), 2)

    def test_03_cache_expires(self):
        self.assertEqual(self._auth("dav_cache_pwd"), self.user.id)
        ttl = webdav_auth.TTL
        webdav_auth.TTL = 0
        try:
            webdav_auth.forget_all()
            self.assertEqual(self._auth("dav_cache_pwd"), self.user.id)
            self.assertEqual(self._auth("dav_cache_pwd"), self.user.id)
        finally:
            webdav_auth.TTL = ttl
        self.assertEqual(len(self.calls), 3, "à TTL nul, chaque appel revérifie")

    def test_04_deactivated_user_evicted(self):
        self.assertEqual(self._auth("dav_cache_pwd"), self.user.id)
        self.user.active = False
        self.assertIsNone(self._auth("dav_cache_pwd"),
                          "un compte désactivé ne doit pas survivre dans le cache")

    def test_05_api_key(self):
        if 'res.users.apikeys' not in self.env:
            self.skipTest("clés d'API indisponibles")
        key = self.env['res.users.apikeys'].with_user(self.user)._generate(
            'rpc', "Lecteur réseau", fields.Datetime.now() + timedelta(days=1))
        self.assertEqual(self._auth(key), self.user.id)
        self.assertEqual(self.calls, [],
                         "une clé d'API ne passe pas par la connexion par mot de passe")
        self.assertIsNone(self._auth(key, login="admin"),
                          "la clé d'un compte ne vaut pas pour un autre login")
