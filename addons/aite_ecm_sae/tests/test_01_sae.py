# -*- coding: utf-8 -*-
import base64
import hashlib
import io
import json
import zipfile
import xml.etree.ElementTree as ET

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

PDF1 = base64.b64encode(b"%PDF-1.4\n%preuve v1\n%%EOF\n")
PDF2 = base64.b64encode(b"%PDF-1.4\n%preuve v2\n%%EOF\n")
SEDA_NS = "fr:gouv:culture:archivesdefrance:seda:v2.1"


@tagged('post_install', '-at_install', 'aite_ecm_sae')
class TestSae(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Seal = cls.env['aite.ecm.seal']
        cls.doc = cls.env['aite.ecm.document'].create({
            'name': "Contrat probant",
            'type_id': cls.env.ref('aite_ecm_document.type_contrat').id,
            'folder_id': cls.env.ref('aite_ecm_document.folder_juridique').id,
            'confidentiality_id': cls.env.ref(
                'aite_courrier_base.confidentiality_internal').id})
        cls.doc.add_version("contrat.pdf", PDF1)

    def test_01_sealing(self):
        seals = self.doc.seal_ids.sorted('id')
        self.assertEqual(len(seals), 1)
        self.assertEqual(seals[0].event, 'version')
        self.assertEqual(seals[0].content_sha256,
                         self.doc.latest_version_id.sha256)
        self.doc.add_version("contrat_v2.pdf", PDF2)
        self.doc.action_mark_final()
        seals = self.doc.seal_ids.sorted('id')
        self.assertEqual([s.event for s in seals], ['version', 'version', 'final'])
        for previous, current in zip(seals, seals[1:]):
            self.assertEqual(current.previous_hash, previous.seal_hash)
        self.assertTrue(self.doc.last_seal_hash)

    def test_02_immutable(self):
        seal = self.doc.seal_ids[0]
        with self.assertRaises(UserError):
            seal.write({'detail': "modifié"})
        with self.assertRaises(UserError):
            seal.unlink()

    def test_03_verify_ok(self):
        self.assertFalse(self.Seal.verify_chain())
        self.assertFalse(self.Seal.verify_documents(self.doc))
        self.doc.action_verify_integrity()
        self.assertEqual(self.doc.integrity_state, 'ok')
        self.assertTrue(self.doc.integrity_date)
        self.assertIn('check', self.doc.seal_ids.mapped('event'))

    def test_04_tampering(self):
        # contenu modifié hors ECM
        self.doc.latest_version_id.attachment_id.sudo().write({'datas': PDF2})
        problems = self.Seal.verify_documents(self.doc)
        self.assertTrue(problems)
        self.assertIn("modifié", problems[0]['problem'])
        # charge utile d'un sceau modifiée
        seal = self.doc.seal_ids[0]
        payload = json.loads(seal.payload)
        payload['detail'] = "falsifié"
        self.env.cr.execute("UPDATE aite_ecm_seal SET payload = %s WHERE id = %s",
                            (json.dumps(payload, sort_keys=True,
                                        ensure_ascii=False), seal.id))
        seal.invalidate_recordset()
        chain = self.Seal.verify_chain()
        self.assertTrue(any("altéré" in p['problem'] for p in chain))

    def test_05_timestamp(self):
        seal = self.doc.seal_ids[0]
        self.assertEqual(seal.timestamp_source, 'internal')
        expected = self.Seal._timestamp_token(seal.seal_hash, seal.timestamp)
        self.assertEqual(seal.timestamp_token, expected)
        self.env.cr.execute(
            "UPDATE aite_ecm_seal SET timestamp_token = %s WHERE id = %s",
            ('0' * 64, seal.id))
        seal.invalidate_recordset()
        self.assertTrue(any("horodatage" in p['problem']
                            for p in self.Seal.verify_chain()))

    def test_06_seda_export(self):
        wizard = self.env['aite.ecm.seda.export'].create({
            'name': "Transfert test", 'scope': 'selection',
            'document_ids': [(6, 0, self.doc.ids)],
            'transferring_agency': "AITE Consulting",
            'archival_agency': "Archives"})
        wizard.action_export()
        self.assertTrue(wizard.file_data)
        raw = base64.b64decode(wizard.file_data)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            self.assertIn('manifest.xml', names)
            self.assertIn('journal_de_preuve.json', names)
            self.assertIn('LISEZMOI.txt', names)
            manifest = ET.fromstring(archive.read('manifest.xml'))
            digests = manifest.findall('.//{%s}MessageDigest' % SEDA_NS)
            self.assertEqual(len(digests), 1)
            content = [n for n in names if n.startswith('content/')]
            self.assertEqual(len(content), 1)
            self.assertEqual(hashlib.sha256(archive.read(content[0])).hexdigest(),
                             digests[0].text)
            seals = json.loads(archive.read('journal_de_preuve.json'))
            self.assertTrue(seals and seals[0]['seal_hash'])
        self.assertIn('export', self.doc.seal_ids.mapped('event'))
