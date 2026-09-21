# -*- coding: utf-8 -*-
import base64
from datetime import timedelta
from urllib.parse import quote

from odoo import fields
from odoo.tests import HttpCase, tagged

DOCX = base64.b64encode(b"PK\x03\x04 fake docx v1")
DOCX2 = base64.b64encode(b"PK\x03\x04 fake docx v2")


@tagged('post_install', '-at_install', 'aite_ecm_webdav')
class TestEcmWebdav(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.agent = Users.create({'name': "Agent DAV", 'login': "dav_agent",
                                  'email': "dav_agent@aite.test",
                                  'password': "dav_agent_pwd",
                                  'groups_id': [(6, 0, [cls.env.ref(
                                      'aite_courrier_base.group_agent').id])]})
        cls.other = Users.create({'name': "Autre DAV", 'login': "dav_other",
                                  'email': "dav_other@aite.test",
                                  'password': "dav_other_pwd",
                                  'groups_id': [(6, 0, [cls.env.ref(
                                      'aite_courrier_base.group_agent').id])]})
        cls.folder = cls.env.ref('aite_ecm_document.folder_juridique')
        cls.doc = cls.env['aite.ecm.document'].with_user(cls.agent).create({
            'name': "Contrat DAV", 'folder_id': cls.folder.id,
            'confidentiality_id': cls.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        cls.doc.add_version("contrat.docx", DOCX)

    def _dav(self, method, path, user="dav_agent", password="dav_agent_pwd",
             data=None, headers=None):
        hdrs = {'Authorization': 'Basic ' + base64.b64encode(
            ("%s:%s" % (user, password)).encode()).decode()}
        hdrs.update(headers or {})
        url = '/webdav/aite_ecm/' + '/'.join(quote(p) for p in path.split('/')) \
            if path else '/webdav/aite_ecm/'
        return self.opener.request(method, self.base_url() + url, data=data,
                                   headers=hdrs, timeout=30)

    def test_01_propfind(self):
        resp = self._dav('PROPFIND', '', headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 207)
        self.assertIn("Sans classement", resp.text)
        self.assertIn("Juridique et contrats", resp.text)
        # Le client WebDAV de Windows refuse d'ouvrir une collection sans
        # date de modification : racine, dossiers et « Sans classement »
        # doivent tous en porter une, pas seulement les fichiers.
        self.assertEqual(resp.text.count('<D:response>'),
                         resp.text.count('<D:getlastmodified>'),
                         "une collection sans getlastmodified est inaccessible "
                         "depuis l'Explorateur Windows")
        resp = self._dav('PROPFIND', "Juridique et contrats", headers={'Depth': '1'})
        self.assertIn("%s - Contrat DAV.docx" % self.doc.reference, resp.text)

    def test_02_get(self):
        resp = self._dav('GET', "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, base64.b64decode(DOCX))
        self.assertIn(self.doc.latest_version_id.sha256, resp.headers.get('ETag', ''))

    def test_03_put(self):
        path = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        resp = self._dav('PUT', path, data=base64.b64decode(DOCX2))
        self.assertEqual(resp.status_code, 204)
        self.doc.invalidate_recordset()
        self.assertEqual(self.doc.version_count, 2)
        self.assertEqual(self.doc.latest_version_id.uploaded_by, self.agent)
        resp = self._dav('PUT', "Juridique et contrats/Nouveau depuis le lecteur.docx",
                         data=base64.b64decode(DOCX))
        self.assertEqual(resp.status_code, 201)
        new = self.env['aite.ecm.document'].search([('name', '=', "Nouveau depuis le lecteur")])
        self.assertEqual(new.folder_id, self.folder)

    def test_04_lock(self):
        path = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        resp = self._dav('LOCK', path, headers={'Timeout': 'Second-3600'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('opaquelocktoken', resp.headers.get('Lock-Token', ''))
        self.doc.invalidate_recordset()
        self.assertEqual(self.doc.checkout_user_id, self.agent)
        resp = self._dav('PUT', path, user="dav_other", password="dav_other_pwd",
                         data=base64.b64decode(DOCX2))
        self.assertEqual(resp.status_code, 423)
        resp = self._dav('UNLOCK', path)
        self.assertEqual(resp.status_code, 204)
        self.doc.invalidate_recordset()
        self.assertFalse(self.doc.is_checked_out)

    def test_05_move(self):
        path = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        dest = self.base_url() + '/webdav/aite_ecm/' + quote(
            "Direction générale/%s - Contrat renommé.docx" % self.doc.reference)
        resp = self._dav('MOVE', path, headers={'Destination': dest})
        self.assertEqual(resp.status_code, 201)
        self.doc.invalidate_recordset()
        self.assertEqual(self.doc.folder_id, self.env.ref('aite_ecm_document.folder_direction'))
        self.assertEqual(self.doc.name, "Contrat renommé")

    def test_06_office_uri(self):
        self.assertTrue(self.doc.office_uri.startswith("ms-word:ofe|u|"))
        self.assertIn("/webdav/aite_ecm/", self.doc.office_uri)
        self.assertEqual(self.doc.office_app, "Word")
        pdf = self.env['aite.ecm.document'].create({'name': "PDF"})
        pdf.add_version("x.pdf", base64.b64encode(b"%PDF-1.4"))
        self.assertFalse(pdf.office_uri)

    def test_07_format_refuse_ne_cree_rien(self):
        """Un dépôt au format interdit renvoie 409 sans rien laisser en base.

        Le contrôleur traduit l'erreur en réponse HTTP au lieu de la laisser
        remonter : la transaction est donc validée, et sans savepoint le
        document créé avant le contrôle de format survivrait au refus.
        """
        Document = self.env['aite.ecm.document']
        before = Document.search_count([])
        resp = self._dav('PUT', "Juridique et contrats/programme.exe",
                         data=b"MZ faux binaire")
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(Document.search([('name', '=', "programme")]),
                         "un document sans version est resté après le refus")
        self.assertEqual(Document.search_count([]), before)

    def test_08_security(self):
        resp = self.opener.request('PROPFIND', self.base_url() + '/webdav/aite_ecm/',
                                   headers={'Depth': '1'}, timeout=30)
        self.assertEqual(resp.status_code, 401)
        secret = self.env['aite.ecm.document'].with_user(self.other).create({
            'name': "Secret de l'autre", 'folder_id': self.folder.id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_confidential').id})
        secret.add_version("s.docx", DOCX)
        resp = self._dav('PROPFIND', "Juridique et contrats", headers={'Depth': '1'})
        self.assertNotIn("Secret de l'autre", resp.text)

    def test_09_api_key_as_password(self):
        """Une clé d'API vaut mot de passe : c'est la voie prévue pour un
        client sans session, et la seule pour un compte à double
        authentification."""
        if 'res.users.apikeys' not in self.env:
            self.skipTest("clés d'API indisponibles")
        key = self.env['res.users.apikeys'].with_user(self.agent)._generate(
            'rpc', "Lecteur réseau", fields.Datetime.now() + timedelta(days=1))
        resp = self._dav('PROPFIND', '', password=key, headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 207)
        resp = self._dav('PROPFIND', '', user="dav_other", password=key,
                         headers={'Depth': '1'})
        self.assertEqual(resp.status_code, 401,
                         "la clé d'un compte ne vaut pas pour un autre login")

    def test_10_creation_depuis_l_explorateur(self):
        """La séquence par laquelle l'Explorateur Windows crée un fichier.

        Il verrouille d'abord le nom — encore libre —, dépose le contenu,
        puis redemande le fichier **sous ce même nom**. Un 404 à l'une ou
        l'autre de ces étapes et la création échoue : « Élément introuvable ».
        """
        nom = "Nouveau Document Microsoft Word.docx"
        chemin = "Juridique et contrats/%s" % nom

        resp = self._dav('LOCK', chemin, headers={'Timeout': 'Second-3600'})
        self.assertEqual(resp.status_code, 201,
                         "verrou refusé sur un nom libre : l'Explorateur ne "
                         "peut alors rien créer")
        self.assertIn('opaquelocktoken', resp.headers.get('Lock-Token', ''))

        resp = self._dav('PUT', chemin, data=base64.b64decode(DOCX))
        self.assertEqual(resp.status_code, 201)

        resp = self._dav('PROPFIND', chemin, headers={'Depth': '0'})
        self.assertEqual(resp.status_code, 207,
                         "le fichier déposé reste introuvable sous le nom que "
                         "le client lui a donné")

        self.assertEqual(self._dav('UNLOCK', chemin).status_code, 204)

        doc = self.env['aite.ecm.document'].search(
            [('name', '=', "Nouveau Document Microsoft Word")])
        self.assertEqual(len(doc), 1)
        self.assertEqual(doc.folder_id, self.folder)
        self.assertEqual(doc.version_count, 1)

    def test_11_lock_sans_droit_ecriture(self):
        """Un verrou sur un nom libre reste soumis aux droits du dossier."""
        self.folder.write({'write_user_ids': [(6, 0, [self.other.id])]})
        resp = self._dav('LOCK', "Juridique et contrats/Essai interdit.docx")
        self.assertEqual(resp.status_code, 403)

    def test_12_bouton_office_confie_l_uri_au_navigateur(self):
        """Le bouton « Ouvrir dans Office » ne passe pas par ``act_url``.

        Le client web normalise les adresses de ce type d'action : les barres
        verticales du protocole Office deviennent ``%7C`` et le ``//`` du
        schéma imbriqué se réduit. Le navigateur résout alors l'adresse en
        chemin relatif d'Odoo et répond 404, sans lancer Word.
        """
        action = self.doc.with_user(self.agent).action_open_in_office()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'aite_ecm_open_uri')
        uri = action['params']['uri']
        self.assertTrue(uri.startswith('ms-word:ofe|u|'), uri)
        self.assertIn('http://', uri,
                      "le schéma imbriqué doit rester intact")

    def test_13_head_annonce_la_vraie_taille(self):
        """HEAD doit annoncer la taille du fichier, avec un corps vide.

        ``Response.set_data(b'')`` recalcule ``Content-Length`` : la réponse
        annonçait 0 octet. Word interroge la taille avant de charger et en
        concluait que le document était vide — il s'ouvrait alors sans rien.
        """
        chemin = "Juridique et contrats/%s - Contrat DAV.docx" % self.doc.reference
        attendu = len(base64.b64decode(DOCX))
        resp = self._dav('HEAD', chemin)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('Content-Length'), str(attendu),
                         "un client en déduirait un fichier vide")
        self.assertEqual(resp.content, b'')
        # Le GET correspondant sert bien ce nombre d'octets.
        self.assertEqual(len(self._dav('GET', chemin).content), attendu)

    def _parametre(self, cle, valeur):
        self.env['ir.config_parameter'].sudo().set_param(cle, valeur)
        self.doc.invalidate_recordset()

    def test_14_mode_url_par_defaut(self):
        """Sans réglage, le bouton sert l'URL WebDAV — inchangé."""
        self._parametre('web.base.url', 'http://srv-ecm:8069')
        self.assertEqual(self.doc.office_target, self.doc.webdav_url)
        self.assertTrue(self.doc.office_uri.startswith(
            "ms-word:ofe|u|http://srv-ecm:8069/webdav/aite_ecm/"))

    def test_15_mode_unc_pour_une_instance_en_http(self):
        """Office refuse Basic sur http ; le mode « unc » passe par le lecteur
        réseau, où c'est Windows qui s'authentifie."""
        self._parametre('web.base.url', 'http://srv-ecm:8069')
        self._parametre('aite_ecm.office_uri_mode', 'unc')
        self.assertEqual(
            self.doc.office_target,
            "\\\\srv-ecm@8069\\DavWWWRoot\\webdav\\aite_ecm"
            "\\Juridique et contrats\\%s - Contrat DAV.docx" % self.doc.reference)
        self.assertTrue(self.doc.office_uri.startswith(
            "ms-word:ofe|u|\\\\srv-ecm@8069\\"))
        # L'adresse affichée sur la fiche reste l'URL : c'est elle qu'on copie.
        self.assertTrue(self.doc.webdav_url.startswith("http://srv-ecm:8069/"))

    def test_16_mode_unc_en_https(self):
        """Derrière HTTPS, le partage Windows prend la forme « hôte@SSL »."""
        self._parametre('web.base.url', 'https://ecm.exemple.fr')
        self._parametre('aite_ecm.office_uri_mode', 'unc')
        self.assertTrue(self.doc.office_target.startswith(
            "\\\\ecm.exemple.fr@SSL\\DavWWWRoot\\webdav\\aite_ecm\\"))

    def test_17_racine_unc_imposee(self):
        """Une racine imposée l'emporte sur la déduction depuis web.base.url.

        Windows range « \\\\hôte@8069\\… » en zone « Sites sensibles » : il y
        lit un « utilisateur@hôte ». Désigner la lettre du lecteur monté
        contourne ce classement.
        """
        self._parametre('web.base.url', 'http://srv-ecm:8069')
        self._parametre('aite_ecm.office_uri_mode', 'unc')
        self._parametre('aite_ecm.office_unc_root', 'Z:')
        self.assertEqual(
            self.doc.office_target,
            "Z:\\Juridique et contrats\\%s - Contrat DAV.docx" % self.doc.reference)
        self.assertTrue(self.doc.office_uri.startswith("ms-word:ofe|u|Z:\\"))

    def test_18_racine_imposee_ignoree_en_mode_url(self):
        """La racine imposée ne s'applique qu'au mode « unc »."""
        self._parametre('web.base.url', 'http://srv-ecm:8069')
        self._parametre('aite_ecm.office_unc_root', 'Z:')
        self.assertEqual(self.doc.office_target, self.doc.webdav_url)

