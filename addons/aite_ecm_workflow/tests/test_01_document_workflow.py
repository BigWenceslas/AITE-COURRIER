# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from odoo.addons.aite_ecm_document.tests.common import EcmTransactionCase

PDF = base64.b64encode(b"%PDF-1.4\n%AITE wf\n%%EOF\n")


@tagged('post_install', '-at_install', 'aite_ecm_workflow')
class TestDocumentWorkflow(EcmTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = cls._make_user("Agent WF", "wf_agent", 'group_agent')
        cls.manager = cls._make_user("Manager WF", "wf_manager", 'group_manager')
        cls.proc_type = cls.env.ref('aite_ecm_document.type_procedure')

    def _doc(self):
        doc = self.env['aite.ecm.document'].with_user(self.agent).create({
            'name': "Procédure d'achat", 'type_id': self.proc_type.id,
            'confidentiality_id': self.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        return doc

    def test_01_launch(self):
        doc = self._doc()
        self.assertTrue(doc.wf_has_circuit)
        with self.assertRaises(UserError):
            doc.action_wf_launch()
        doc.add_version("procedure.pdf", PDF)
        doc.action_wf_launch()
        self.assertEqual(doc.wf_status, 'running')
        self.assertEqual(doc.wf_step_id,
                         self.env.ref('aite_ecm_workflow.step_ecm_proc_redaction'))
        self.assertEqual(len(doc.wf_history_ids), 1)

    def test_02_transitions_and_finalize(self):
        doc = self._doc()
        doc.add_version("procedure.pdf", PDF)
        doc.action_wf_launch()
        forward = self.env.ref('aite_ecm_workflow.trans_ecm_proc_transmettre')
        doc.wf_do_transition(forward)
        back = self.env.ref('aite_ecm_workflow.trans_ecm_proc_retour')
        with self.assertRaises(UserError):
            doc.with_user(self.manager).wf_do_transition(back)
        approve = self.env.ref('aite_ecm_workflow.trans_ecm_proc_approuver')
        doc.with_user(self.manager).wf_do_transition(approve, "Conforme")
        self.assertEqual(doc.wf_status, 'done')
        self.assertEqual(doc.state, 'final')
        self.assertTrue(doc.is_locked)

    def test_03_habilitation(self):
        doc = self._doc()
        doc.add_version("procedure.pdf", PDF)
        doc.action_wf_launch()
        doc.wf_do_transition(self.env.ref('aite_ecm_workflow.trans_ecm_proc_transmettre'))
        with self.assertRaises(AccessError):
            doc.wf_do_transition(self.env.ref('aite_ecm_workflow.trans_ecm_proc_approuver'))
        with self.assertRaises(UserError):
            doc.add_version("procedure_v2.pdf", PDF)

    def test_04_reject(self):
        doc = self._doc()
        doc.add_version("procedure.pdf", PDF)
        doc.action_wf_launch()
        doc.wf_do_transition(self.env.ref('aite_ecm_workflow.trans_ecm_proc_transmettre'))
        doc.with_user(self.manager).action_wf_reject("Hors périmètre")
        self.assertEqual(doc.wf_status, 'rejected')
        self.assertEqual(doc.state, 'draft')
