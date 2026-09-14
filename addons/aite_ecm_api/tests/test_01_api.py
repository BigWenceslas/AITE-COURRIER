# -*- coding: utf-8 -*-
"""API REST ``/api/ecm/v1`` : authentification par clé, lecture, création,
versions, téléchargement, et respect des droits de l'utilisateur porteur de
la clé."""
import base64
import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

PDF = base64.b64encode(b"%PDF-1.4\n%AITE api v1\n%%EOF\n").decode()
PDF2 = base64.b64encode(b"%PDF-1.4\n%AITE api v2\n%%EOF\n").decode()
PREFIX = '/api/ecm/v1'


@tagged('post_install', '-at_install', 'aite_ecm_api')
class TestEcmApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.agent = Users.create({
            'name': "Agent API", 'login': "api_agent",
            'email': "api_agent@aite.test",
            'groups_id': [(6, 0, [cls.env.ref(
                'aite_courrier_base.group_agent').id])]})
        cls.manager = Users.create({
            'name': "Manager API", 'login': "api_manager",
            'email': "api_manager@aite.test",
            'groups_id': [(6, 0, [cls.env.ref(
                'aite_courrier_base.group_manager').id])]})
        cls.key = cls._api_key(cls.agent)
        cls.folder = cls.env.ref('aite_ecm_document.folder_juridique')
        cls.internal = cls.env.ref(
            'aite_courrier_base.confidentiality_internal')
        cls.doc = cls.env['aite.ecm.document'].with_user(cls.agent).create({
            'name': "Contrat API", 'folder_id': cls.folder.id,
            'confidentiality_id': cls.internal.id})
        cls.doc.add_version("contrat.pdf", PDF)

    @classmethod
    def _api_key(cls, user):
        """Clé d'API en clair pour ``user`` (comme « Développeur › Clé d'API »).

        ``_generate`` rattache la clé à ``env.user`` et exige une date
        d'expiration pour un utilisateur non administrateur : on fournit donc
        les deux.
        """
        expiry = fields.Datetime.now() + timedelta(days=1)
        return cls.env['res.users.apikeys'].with_user(user)._generate(
            'rpc', "Recette API", expiry)

    def _call(self, path, method='GET', key=None, payload=None,
              headers=None):
        hdrs = {'Content-Type': 'application/json'}
        if key is not False:
            hdrs['X-API-Key'] = key or self.key
        hdrs.update(headers or {})
        data = json.dumps(payload) if payload is not None else None
        return self.opener.request(method, self.base_url() + PREFIX + path,
                                   data=data, headers=hdrs, timeout=30)

    # ------------------------------------------------------------------ #
    def test_01_authentication(self):
        resp = self._call('/ping', key=False)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("X-API-Key", resp.json()['error']['message'])
        resp = self._call('/ping', key='clef-bidon')
        self.assertEqual(resp.status_code, 401)
        resp = self._call('/ping')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['user'], "Agent API")

    def test_02_referentials(self):
        resp = self._call('/types')
        self.assertEqual(resp.status_code, 200)
        codes = [t['code'] for t in resp.json()['items']]
        self.assertIn('CONTRAT', [c.upper() for c in codes if c])
        resp = self._call('/folders')
        paths = [f['path'] for f in resp.json()['items']]
        self.assertTrue(any("Juridique" in p for p in paths))

    def test_03_list_and_get(self):
        resp = self._call('/documents?q=Contrat API')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertGreaterEqual(body['total'], 1)
        self.assertIn(self.doc.id, [d['id'] for d in body['items']])
        resp = self._call('/documents/%d' % self.doc.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['reference'], self.doc.reference)
        resp = self._call('/documents/999999')
        self.assertEqual(resp.status_code, 404)

    def test_04_create_and_version(self):
        tag = self.env['aite.ecm.tag'].create({'name': "Recette API"})
        resp = self._call('/documents', 'POST', payload={
            'name': "Note de service API", 'folder_id': self.folder.id,
            'tags': [tag.name],
            'file': {'filename': "note.pdf", 'content_base64': PDF}})
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        doc = self.env['aite.ecm.document'].browse(body['id'])
        self.assertTrue(doc.reference.startswith("DOC-"))
        self.assertEqual(doc.version_count, 1)
        self.assertEqual(doc.tag_ids, tag)
        resp = self._call('/documents/%d/versions' % doc.id, 'POST',
                          payload={'filename': "note.pdf",
                                   'content_base64': PDF2,
                                   'comment': "correction"})
        self.assertEqual(resp.status_code, 201)
        doc.invalidate_recordset()
        self.assertEqual(doc.version_count, 2)
        self.assertEqual(resp.json()['version'], 'v2')
        # L'appel est tracé au journal d'audit avec la source « api ».
        self.assertTrue(self.env['aite.courrier.audit.log'].sudo().search(
            [('model_name', '=', 'aite.ecm.document'), ('res_id', '=', doc.id),
             ('source', '=', 'api')]))

    def test_04b_unknown_tag_is_refused_for_an_agent(self):
        """Un agent ne crée pas d'étiquette : l'API renvoie un refus net
        (403) plutôt qu'une erreur interne."""
        resp = self._call('/documents', 'POST', payload={
            'name': "Note à étiquette inédite", 'folder_id': self.folder.id,
            'tags': ["Étiquette jamais vue"]})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(self.env['aite.ecm.tag'].search(
            [('name', '=', "Étiquette jamais vue")]))

    def test_05_validation_errors(self):
        resp = self._call('/documents', 'POST', payload={})
        self.assertEqual(resp.status_code, 400)
        resp = self._call('/documents', 'POST',
                          payload={'name': "X", 'type_code': "INCONNU"})
        self.assertEqual(resp.status_code, 400)
        resp = self._call('/documents/%d/versions' % self.doc.id, 'POST',
                          payload={'filename': "virus.exe",
                                   'content_base64': PDF})
        self.assertEqual(resp.status_code, 422)

    def test_06_download(self):
        resp = self._call('/documents/%d/download' % self.doc.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, base64.b64decode(PDF))
        self.assertIn("contrat.pdf",
                      resp.headers.get('Content-Disposition', ''))

    def test_07_rights_follow_the_key(self):
        """La clé emprunte les droits de son porteur : un document
        confidentiel d'un tiers reste invisible."""
        secret = self.env['aite.ecm.document'].with_user(self.manager).create({
            'name': "Confidentiel direction",
            'folder_id': self.env.ref('aite_ecm_document.folder_direction').id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_confidential').id})
        secret.add_version("secret.pdf", PDF)
        resp = self._call('/documents/%d' % secret.id)
        self.assertIn(resp.status_code, (403, 404))
        resp = self._call('/documents?q=Confidentiel direction')
        self.assertNotIn(secret.id, [d['id'] for d in resp.json()['items']])
        # Avec la clé du manager, le même document est accessible.
        resp = self._call('/documents/%d' % secret.id,
                          key=self._api_key(self.manager))
        self.assertEqual(resp.status_code, 200)

    def test_08_openapi(self):
        resp = self._call('/openapi.json')
        self.assertEqual(resp.status_code, 200)
        spec = resp.json()
        self.assertIn('openapi', spec)
        # Les chemins sont relatifs au serveur déclaré (``servers``).
        self.assertEqual(spec['servers'][0]['url'], PREFIX)
        self.assertIn('/documents', spec['paths'])
        self.assertIn('X-API-Key', json.dumps(spec['components']))
