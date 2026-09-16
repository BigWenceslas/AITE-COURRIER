# -*- coding: utf-8 -*-
"""Le WebDAV du courrier, éprouvé **par le réseau**.

Les tests de `test_webdav.py` appellent le service en Python : ils prouvent
la logique métier, pas le protocole. Le contrôleur HTTP — aiguillage par
verbe, authentification Basic, sérialisation XML multistatus, codes de
statut, en-têtes — n'avait jamais été exécuté. C'est ce que ce fichier
couvre, sur le même modèle que `aite_ecm_webdav`.
"""
import base64
from urllib.parse import quote

from odoo.tests import HttpCase, tagged

PDF = b"%PDF-1.4 rapport v1\n%%EOF\n"
PDF2 = b"%PDF-1.4 rapport v2\n%%EOF\n"


@tagged('post_install', '-at_install', 'aite_courrier_webdav')
class TestCourrierWebdavHttp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        group_agent = cls.env.ref('aite_courrier_base.group_agent')
        cls.agent = Users.create({
            'name': "Agent DAV courrier", 'login': "dav_cour_agent",
            'email': "dav_cour_agent@aite.test", 'password': "dav_cour_pwd",
            'groups_id': [(6, 0, [group_agent.id])]})
        cls.other = Users.create({
            'name': "Autre agent DAV", 'login': "dav_cour_other",
            'email': "dav_cour_other@aite.test", 'password': "dav_cour_other_pwd",
            'groups_id': [(6, 0, [group_agent.id])]})

        cls.type_entr = cls.env.ref('aite_courrier_base.type_entr')
        cls.courrier = cls.env['aite.courrier'].with_user(cls.agent).create({
            'subject': "Courrier WebDAV HTTP", 'type_id': cls.type_entr.id})
        cls.courrier.action_launch_circuit()
        cls.reference = cls.courrier.reference
        cls.document = cls.env['aite.courrier.document'].with_user(
            cls.agent).create({'name': "Rapport",
                               'courrier_id': cls.courrier.id})
        cls.document.add_version(
            'Rapport.pdf', base64.b64encode(PDF).decode())

    # ------------------------------------------------------------------ #
    def _dav(self, method, path='', user="dav_cour_agent",
             password="dav_cour_pwd", data=None, headers=None, auth=True):
        hdrs = {}
        if auth:
            jeton = base64.b64encode(
                ("%s:%s" % (user, password)).encode()).decode()
            hdrs['Authorization'] = 'Basic ' + jeton
        hdrs.update(headers or {})
        url = '/webdav/aite_courrier/'
        if path:
            url += '/'.join(quote(p) for p in path.split('/'))
        return self.opener.request(method, self.base_url() + url, data=data,
                                   headers=hdrs, timeout=30)

    def _file(self, name='Rapport.pdf'):
        return "%s/%s" % (self.reference, name)

    # --- découverte et authentification -------------------------------- #
    def test_01_options_repond_sans_authentification(self):
        """OPTIONS doit passer sans identifiants : c'est par lui que le
        client découvre les capacités avant de demander un mot de passe."""
        resp = self._dav('OPTIONS', auth=False)
        self.assertEqual(resp.status_code, 200)
        dav = resp.headers.get('DAV', '')
        self.assertIn('1', dav)
        self.assertIn('2', dav, "la classe 2 (verrous) doit être annoncée, "
                                "sans quoi le Finder monte en lecture seule")
        allow = resp.headers.get('Allow', '')
        for verbe in ('PROPFIND', 'GET', 'PUT', 'LOCK', 'MOVE'):
            self.assertIn(verbe, allow)

    def test_02_refus_sans_identifiants(self):
        resp = self._dav('PROPFIND', headers={'Depth': '1'}, auth=False)
        self.assertEqual(resp.status_code, 401)
        self.assertIn('Basic', resp.headers.get('WWW-Authenticate', ''),
                      "sans ce défi, le client ne propose pas de mot de passe")

    def test_03_refus_sur_mot_de_passe_errone(self):
        resp = self._dav('PROPFIND', password="pas_le_bon",
                         headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 401)

    # --- lecture ------------------------------------------------------- #
    def test_04_propfind_racine_puis_courrier(self):
        resp = self._dav('PROPFIND', headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 207)
        self.assertIn('multistatus', resp.text)
        self.assertIn(self.reference, resp.text)

        resp = self._dav('PROPFIND', self.reference, headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 207)
        self.assertIn('Rapport.pdf', resp.text)

    def test_05_propfind_courrier_inconnu(self):
        resp = self._dav('PROPFIND', "COUR-1900-9999", headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 404)

    def test_06_get_renvoie_le_fichier(self):
        resp = self._dav('GET', self._file())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, PDF)

    def test_07_head_sans_corps(self):
        resp = self._dav('HEAD', self._file())
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.content)

    # --- écriture ------------------------------------------------------ #
    def test_08_put_ajoute_une_version(self):
        avant = self.document.version_count
        resp = self._dav('PUT', self._file(), data=PDF2)
        self.assertEqual(resp.status_code, 204)
        self.document.invalidate_recordset()
        self.assertEqual(self.document.version_count, avant + 1)

    def test_09_put_cree_une_piece(self):
        resp = self._dav('PUT', self._file('Annexe.pdf'), data=PDF)
        self.assertEqual(resp.status_code, 201)
        piece = self.env['aite.courrier.document'].search(
            [('courrier_id', '=', self.courrier.id), ('name', '=', "Annexe")])
        self.assertTrue(piece, "le PUT n'a pas créé la pièce")
        self.assertTrue(piece.latest_version_id)

    def test_10_put_format_refuse(self):
        resp = self._dav('PUT', self._file('outil.exe'), data=b"MZ\x90\x00")
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(self.env['aite.courrier.document'].search(
            [('courrier_id', '=', self.courrier.id), ('name', '=', "outil")]))

    def test_11_put_sur_courrier_archive_est_verrouille(self):
        courrier = self.env['aite.courrier'].with_user(self.agent).create({
            'subject': "Courrier clos WebDAV", 'type_id': self.type_entr.id})
        courrier.action_launch_circuit()
        piece = self.env['aite.courrier.document'].with_user(
            self.agent).create({'name': "Pièce", 'courrier_id': courrier.id})
        piece.add_version('Piece.pdf', base64.b64encode(PDF).decode())
        courrier.sudo().write({'state': 'ar'})
        resp = self._dav('PUT', "%s/Piece.pdf" % courrier.reference, data=PDF2)
        self.assertEqual(resp.status_code, 423)

    # --- verrous, déplacement, suppression ----------------------------- #
    def test_12_lock_et_unlock(self):
        resp = self._dav('LOCK', self._file(),
                         headers={'Timeout': 'Second-3600'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('opaquelocktoken', resp.headers.get('Lock-Token', ''))
        self.assertIn('activelock', resp.text)
        self.assertEqual(self._dav('UNLOCK', self._file()).status_code, 204)

    def test_13_proppatch_acquitte(self):
        """Certains clients posent un horodatage après le PUT : il faut
        acquitter, sinon Windows signale l'enregistrement en échec."""
        resp = self._dav('PROPPATCH', self._file())
        self.assertEqual(resp.status_code, 207)
        self.assertIn('multistatus', resp.text)

    def test_14_move_renomme(self):
        piece = self.env['aite.courrier.document'].with_user(
            self.agent).create({'name': "Avant",
                                'courrier_id': self.courrier.id})
        piece.add_version('Avant.pdf', base64.b64encode(PDF).decode())
        destination = "%s/webdav/aite_courrier/%s" % (
            self.base_url(), quote("%s/Après.pdf" % self.reference))
        resp = self._dav('MOVE', "%s/Avant.pdf" % self.reference,
                         headers={'Destination': destination})
        self.assertEqual(resp.status_code, 201)
        piece.invalidate_recordset()
        self.assertEqual(piece.name, "Après")

    def test_15_delete(self):
        piece = self.env['aite.courrier.document'].with_user(
            self.agent).create({'name': "Jetable",
                                'courrier_id': self.courrier.id})
        piece.add_version('Jetable.pdf', base64.b64encode(PDF).decode())
        resp = self._dav('DELETE', "%s/Jetable.pdf" % self.reference)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(piece.exists())

    # --- cloisonnement et robustesse ----------------------------------- #
    def test_16_verbe_non_supporte(self):
        resp = self._dav('PATCH', self._file())
        self.assertIn(resp.status_code, (405, 501))
        if resp.status_code == 405:
            self.assertIn('PROPFIND', resp.headers.get('Allow', ''))

    def test_17_confidentiel_absent_de_la_liste(self):
        """Un courrier confidentiel d'un autre agent ne doit apparaître ni
        dans le listing, ni être lisible par son chemin direct."""
        Conf = self.env['aite.courrier.confidentiality']
        confidentiel = Conf.search([('code', '=', 'CONF')], limit=1)
        if not confidentiel:
            self.skipTest("référentiel de confidentialité absent")
        secret = self.env['aite.courrier'].with_user(self.other).create({
            'subject': "Secret de l'autre agent",
            'type_id': self.type_entr.id,
            'confidentiality_id': confidentiel.id})
        secret.action_launch_circuit()
        piece = self.env['aite.courrier.document'].with_user(
            self.other).create({'name': "Secret", 'courrier_id': secret.id})
        piece.add_version('Secret.pdf', base64.b64encode(PDF).decode())

        resp = self._dav('PROPFIND', headers={'Depth': '1'})
        self.assertNotIn(secret.reference, resp.text,
                         "le courrier confidentiel d'un autre agent est listé")
        resp = self._dav('GET', "%s/Secret.pdf" % secret.reference)
        self.assertIn(resp.status_code, (403, 404),
                      "le fichier confidentiel est servi par son chemin direct")
