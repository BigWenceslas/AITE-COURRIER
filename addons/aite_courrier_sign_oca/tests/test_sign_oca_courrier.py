# -*- coding: utf-8 -*-
import base64
import json
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from reportlab.pdfgen import canvas

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


def _pdf_b64(pages=2):
    buf = BytesIO()
    can = canvas.Canvas(buf)
    for n in range(pages):
        can.drawString(72, 720, "Courrier de test, page %d" % (n + 1))
        can.showPage()
    can.save()
    return base64.b64encode(buf.getvalue())


def _png_b64():
    buf = BytesIO()
    Image.new('RGB', (60, 20), 'white').save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


class SignOcaCourrierCommon:

    @classmethod
    def _setup_common(cls):
        ref = cls.env.ref
        cls.step1 = ref('aite_courrier_workflow.step_entr_1')
        cls.step2 = ref('aite_courrier_workflow.step_entr_2')
        cls.step3 = ref('aite_courrier_workflow.step_entr_3')
        cls.step2.require_signature = True
        cls.t12 = ref('aite_courrier_workflow.trans_entr_1_2')
        cls.t23 = ref('aite_courrier_workflow.trans_entr_2_3')
        cls.t21 = ref('aite_courrier_workflow.trans_entr_2_1')
        cls.t32 = ref('aite_courrier_workflow.trans_entr_3_2')
        cls.signer_user = cls.env['res.users'].create({
            'name': "Signataire AITE", 'login': 'aite_signer',
            'email': 'signer@example.com', 'password': 'aite_signer_pw1',
            'groups_id': [Command.set([ref('base.group_user').id])],
        })

    def _courrier_at_signature_step(self, with_pdf=True, **vals):
        courrier = self.env['aite.courrier'].create(dict({
            'subject': "Courrier à signer",
            'type_id': self.env.ref('aite_courrier_base.type_entr').id,
            'responsible_id': self.signer_user.id,
        }, **vals))
        courrier.action_launch_circuit()
        courrier.do_transition(self.t12)
        self.assertEqual(courrier.current_step_id, self.step2)
        doc = self.env['aite.courrier.document'].create({
            'name': "Pièce", 'courrier_id': courrier.id})
        if with_pdf:
            doc.add_version('lettre.pdf', _pdf_b64())
        else:
            doc.add_version('lettre.docx', base64.b64encode(b'docx'))
        return courrier, doc

    def _request(self, courrier, user=None):
        action = courrier.with_user(user or self.env.user) \
            .action_request_signature()
        return self.env['sign.oca.request'].browse(action['res_id'])

    def _sign(self, request):
        signer = request.signer_ids
        items = {key: dict(item, value=_png_b64())
                 for key, item in request.signatory_data.items()}
        signer.sudo().action_sign(items, access_token=signer.access_token)


class TestSignOcaCourrier(SignOcaCourrierCommon, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common()

    def _audits(self, courrier, name):
        return self.env['aite.courrier.audit.log'].search([
            ('model_name', '=', 'aite.courrier'), ('res_id', '=', courrier.id),
            ('name', '=', name)])

    def _spy_audit(self):
        """Relève les appels à _log : une entrée 'err' écrite dans la
        transaction de test disparaît avec le savepoint d'assertRaises."""
        AuditLog = self.registry['aite.courrier.audit.log']
        original = AuditLog._log
        calls = []

        def spy(model, env, action, action_type, *args, **kwargs):
            calls.append((action, action_type))
            return original(model, env, action, action_type, *args, **kwargs)
        return patch.object(AuditLog, '_log', spy), calls

    def _user(self, login, *groups, **vals):
        return self.env['res.users'].create(dict({
            'name': login, 'login': login, 'email': '%s@example.com' % login,
            'groups_id': [Command.set(
                [self.env.ref('base.group_user').id]
                + [self.env.ref(g).id for g in groups])],
        }, **vals))

    def test_01_request_guard_and_completion(self):
        courrier, doc = self._courrier_at_signature_step()
        request = self._request(courrier)
        self.assertEqual(request.state, '0_sent', "action_send appelé")
        self.assertEqual(request.courrier_id, courrier)
        self.assertEqual(request.courrier_step_id, self.step2)
        self.assertEqual(request.courrier_document_id, doc)
        self.assertEqual(courrier.sign_request_count, 1)
        self.assertFalse(courrier.has_completed_signature)
        self.assertEqual(request.signer_ids.partner_id,
                         self.signer_user.partner_id)
        items = list(request.signatory_data.values())
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]['position_x'], items[0]['position_y'],
                          items[0]['page'], items[0]['required']),
                         (66, 88, 1, True))
        self.assertTrue(request.signer_ids.access_token)
        self.assertTrue(self.env['mail.mail'].search([
            ('recipient_ids', 'in', self.signer_user.partner_id.ids),
            ('subject', '=', "New document to sign")]))
        self.assertTrue(self._audits(courrier, "Demande de signature"))
        # Le signataire ouvre son lien depuis la demande (bouton « Signer »).
        action = request.with_user(self.signer_user).sign()
        self.assertEqual(action['url'], request.signer_ids.access_url)
        # Garde : en avant refusé (et tracé), en arrière permis.
        spy, calls = self._spy_audit()
        with spy, self.assertRaises(UserError):
            courrier.do_transition(self.t23)
        self.assertIn(("Action bloquée", 'err'), calls)
        self.assertEqual(courrier.current_step_id, self.step2)
        # Signature : la garde se lève et le PDF signé revient en GED.
        original = doc.latest_version_id
        self._sign(request)
        self.assertEqual(request.state, '2_signed')
        self.assertTrue(courrier.has_completed_signature)
        self.assertEqual(len(doc.version_ids), 2)
        self.assertEqual(doc.latest_version_id.file_name, 'lettre_signe.pdf')
        self.assertTrue(original.exists(), "la version d'origine est gardée")
        completed = self._audits(courrier, "Signature complétée")
        self.assertIn("Signataire AITE", completed.detail)
        courrier.do_transition(self.t23)
        self.assertEqual(courrier.current_step_id, self.step3)

    def test_02_backward_allowed_without_signature(self):
        courrier, _doc = self._courrier_at_signature_step()
        courrier.do_transition(self.t21, "à revoir")
        self.assertEqual(courrier.current_step_id, self.step1)

    def test_03_no_pdf_refused(self):
        courrier, _doc = self._courrier_at_signature_step(with_pdf=False)
        with self.assertRaises(UserError):
            courrier.action_request_signature()
        self.assertEqual(courrier.sign_request_count, 0)

    def test_04_internal_users_see_only_their_requests(self):
        courrier, _doc = self._courrier_at_signature_step()
        request = self._request(courrier)
        signer = request.signer_ids
        other = self._user('aite_other')
        # Collègues rattachés à la même société partenaire : cas où la
        # règle d'origine de sign_oca exposait le jeton de signature.
        company = self.env['res.partner'].create(
            {'name': "Société AITE", 'is_company': True})
        (other | self.signer_user).partner_id.parent_id = company
        Req = self.env['sign.oca.request']
        Signer = self.env['sign.oca.request.signer']
        self.assertFalse(Req.with_user(other).search([('id', '=', request.id)]))
        self.assertFalse(Signer.with_user(other).search(
            [('id', '=', signer.id)]), "jeton hors de portée d'un collègue")
        with self.assertRaises(AccessError):
            signer.with_user(other).read(['access_token'])
        self.assertTrue(Req.with_user(self.signer_user).search(
            [('id', '=', request.id)]), "le signataire garde l'accès")
        self.assertTrue(Signer.with_user(self.signer_user).search(
            [('id', '=', signer.id)]))
        # La garde ne dépend pas des droits Signature de l'utilisateur.
        self.assertFalse(courrier.with_user(other).has_completed_signature)
        self.assertEqual(courrier.with_user(other).sign_request_count, 1)

    def test_05_each_visit_of_the_step_needs_its_own_signature(self):
        courrier, _doc = self._courrier_at_signature_step()
        self._sign(self._request(courrier))
        courrier.do_transition(self.t23)
        courrier.do_transition(self.t32, "à reprendre")
        self.assertEqual(courrier.current_step_id, self.step2)
        self.assertFalse(courrier.has_completed_signature,
                         "la signature du passage précédent ne compte plus")
        with self.assertRaises(UserError):
            courrier.do_transition(self.t23)
        second = self._request(courrier)
        self.assertEqual(courrier.sign_request_count, 2)
        self._sign(second)
        self.assertTrue(courrier.has_completed_signature)
        courrier.do_transition(self.t23)
        self.assertEqual(courrier.current_step_id, self.step3)

    def test_06_new_request_replaces_the_pending_one(self):
        courrier, _doc = self._courrier_at_signature_step()
        first = self._request(courrier)
        second = self._request(courrier)
        self.assertEqual(first.state, '3_cancel')
        self.assertEqual(second.state, '0_sent')
        self.assertIn("Demande précédente annulée",
                      courrier.message_ids[:1].body)
        with self.assertRaises(ValidationError):
            self._sign(first)
        self._sign(second)
        self.assertTrue(courrier.has_completed_signature)
        with self.assertRaises(UserError):
            self._request(courrier)

    def test_07_leaving_the_step_cancels_the_pending_request(self):
        courrier, _doc = self._courrier_at_signature_step()
        request = self._request(courrier)
        courrier.do_transition(self.t21, "à revoir")
        self.assertEqual(request.state, '3_cancel')
        with self.assertRaises(ValidationError):
            self._sign(request)

    def test_08_locked_document_gets_signed_pdf_in_chatter(self):
        courrier, doc = self._courrier_at_signature_step()
        request = self._request(courrier)
        doc.state = 'final'
        self.assertTrue(doc.is_locked)
        self._sign(request)
        self.assertEqual(len(doc.version_ids), 1, "document verrouillé")
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'aite.courrier'), ('res_id', '=', courrier.id),
            ('name', '=', 'lettre_signe.pdf')])
        self.assertEqual(len(attachment), 1)
        self.assertTrue(attachment.raw.startswith(b'%PDF'))
        self.assertTrue(courrier.has_completed_signature)

    def test_09_only_users_able_to_act_may_request(self):
        courrier, _doc = self._courrier_at_signature_step()
        outsider = self._user('aite_archiviste',
                              'aite_courrier_base.group_archive')
        spy, calls = self._spy_audit()
        with spy, self.assertRaises(AccessError):
            courrier.with_user(outsider).action_request_signature()
        self.assertIn(("Tentative non autorisée", 'err'), calls)
        self.assertEqual(courrier.sign_request_count, 0)
        # Sans habilitation, le refus standard passe avant la garde.
        with self.assertRaises(AccessError):
            courrier.with_user(outsider).do_transition(self.t23)

    def test_10_signed_pdf_follows_the_requester_rights(self):
        department = self.env['hr.department'].create({'name': "Service A"})
        agent = self._user('aite_agent', 'aite_courrier_base.group_agent')
        employee = self.env['hr.employee'].create({
            'name': "Agent A", 'user_id': agent.id,
            'department_id': department.id})
        courrier, doc = self._courrier_at_signature_step(
            department_id=department.id,
            confidentiality_id=self.env.ref(
                'aite_courrier_base.confidentiality_confidential').id)
        request = self._request(courrier, agent)
        self.assertEqual(request.user_id, agent)
        own = self.env['sign.oca.request'].with_user(agent).search(
            [('id', '=', request.id)])
        self.assertTrue(own, "le demandeur suit sa demande")
        self.assertFalse(self.env['sign.oca.request.signer'].with_user(agent)
                         .search([('request_id', '=', request.id)]),
                         "sans lire les lignes qui portent le jeton")
        # Lecture du formulaire, comme l'envoie le client web : les lignes
        # signataires, lues avec les droits du demandeur, arrivent vides dans
        # le cache, partagé avec le calcul en sudo du résumé.
        self.env.invalidate_all()
        form = own.web_read({
            'to_sign': {}, 'state': {}, 'name': {},
            'courrier_signers_summary': {},
            'signer_ids': {'fields': {'partner_id': {'fields': {
                'display_name': {}}}, 'signed_on': {}},
                'limit': 40, 'order': ''},
            'display_name': {},
        })
        self.assertEqual(form[0]['courrier_signers_summary'],
                         "Signataire AITE (en attente)")
        self.assertEqual(form[0]['signer_ids'], [])
        self.env.invalidate_all()  # fin de la requête du client web
        # L'agent quitte le service avant la signature : il n'a plus accès
        # au courrier confidentiel, le PDF signé ne peut pas être versé en
        # son nom et rejoint l'historique.
        employee.department_id = False
        self._sign(request)
        self.assertEqual(len(doc.version_ids), 1)
        self.assertIn("PDF signé joint à l'historique",
                      self._audits(courrier, "Signature complétée").detail)


@tagged('post_install', '-at_install')
class TestSignOcaDownload(SignOcaCourrierCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common()
        cls.portal = cls.env['res.users'].create({
            'name': "Intrus portail", 'login': 'aite_intrus',
            'password': 'aite_intrus_pw1', 'email': 'intrus@example.com',
            'groups_id': [Command.set([cls.env.ref('base.group_portal').id])],
        })

    def test_download_requires_link_to_request(self):
        courrier, _doc = self._courrier_at_signature_step()
        request = self._request(courrier)
        self.authenticate('aite_intrus', 'aite_intrus_pw1')
        res = self.url_open('/my/sign/%d/download' % request.id,
                            allow_redirects=False)
        self.assertEqual(res.status_code, 404)
        self.authenticate('aite_signer', 'aite_signer_pw1')
        res = self.url_open('/my/sign/%d/download' % request.id,
                            allow_redirects=False)
        self.assertEqual(res.status_code, 303)

    def test_anonymous_portal_signature_lifts_guard(self):
        courrier, doc = self._courrier_at_signature_step()
        request = self._request(courrier)
        signer = request.signer_ids
        items = {k: dict(v, value=_png_b64())
                 for k, v in request.signatory_data.items()}
        res = self.url_open(
            '/sign_oca/sign/%d/%s' % (signer.id, signer.access_token),
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                             'params': {'items': items}}),
            headers={'Content-Type': 'application/json'})
        self.assertNotIn('error', res.json(), res.text[:300])
        self.env.invalidate_all()
        self.assertEqual(request.state, '2_signed')
        self.assertTrue(courrier.has_completed_signature)
        self.assertEqual(doc.latest_version_id.file_name, 'lettre_signe.pdf')
        self.assertEqual(doc.latest_version_id.uploaded_by, request.user_id)
        log = self.env['sign.oca.request.log'].search(
            [('request_id', '=', request.id), ('action', '=', 'sign')])
        # sign_oca journalise la signature portail sous __system__/OdooBot :
        # seul signer_id (+ jeton, IP) identifie le signataire.
        self.assertEqual(log.signer_id, signer)
        self.assertEqual(log.uid.id, 1)
        courrier.do_transition(self.t23)
