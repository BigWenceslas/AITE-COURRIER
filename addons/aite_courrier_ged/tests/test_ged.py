# -*- coding: utf-8 -*-
import base64
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestGed(TransactionCase):
    """Gestion documentaire — aligné sur tests/test_03_ged.md."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['aite.courrier.document']
        cls.AuditLog = cls.env['aite.courrier.audit.log']
        cls.type_entr = cls.env.ref('aite_courrier_base.type_entr')
        Conf = cls.env['aite.courrier.confidentiality']
        cls.conf_pub = Conf.search([('code', '=', 'PUB')], limit=1)
        cls.conf_conf = Conf.search([('code', '=', 'CONF')], limit=1)

    def _new_courrier(self, **kw):
        vals = {'subject': "Courrier GED", 'type_id': self.type_entr.id}
        vals.update(kw)
        return self.env['aite.courrier'].create(vals)

    def _new_document(self, courrier=None, **kw):
        courrier = courrier or self._new_courrier()
        vals = {'name': "Document test", 'courrier_id': courrier.id}
        vals.update(kw)
        return self.Document.create(vals)

    @staticmethod
    def _b64(content=b'hello'):
        return base64.b64encode(content).decode()

    def _audit(self, doc, name):
        return self.AuditLog.search([
            ('model_name', '=', 'aite.courrier.document'),
            ('res_id', '=', doc.id),
            ('name', '=', name),
        ])

    # --- TC-01 : confidentialité héritée ---
    def test_tc01_confidentiality_inherited(self):
        courrier = self._new_courrier(confidentiality_id=self.conf_conf.id)
        doc = self._new_document(courrier)
        self.assertEqual(doc.confidentiality_id, self.conf_conf)
        courrier.confidentiality_id = self.conf_pub
        self.assertEqual(doc.confidentiality_id, self.conf_pub,
                         "La confidentialité du document suit celle du courrier.")

    # --- TC-02 : versionnage v1/v2 ---
    def test_tc02_versioning(self):
        doc = self._new_document()
        v1 = doc.add_version('rapport.pdf', self._b64())
        v2 = doc.add_version('rapport.pdf', self._b64(b'updated'))
        self.assertEqual(v1.version, 'v1')
        self.assertEqual(v2.version, 'v2')
        self.assertEqual(doc.version_count, 2)
        self.assertEqual(doc.latest_version_id, v2)
        self.assertTrue(v1.exists(), "La version précédente est conservée.")

    # --- TC-03 : verrouillage des versions finales/archivées ---
    def test_tc03_locked_versions(self):
        doc = self._new_document()
        doc.add_version('rapport.pdf', self._b64())
        doc.action_mark_final()
        self.assertTrue(doc.is_locked)
        with self.assertRaises(AccessError):
            doc.add_version('rapport.pdf', self._b64(b'v2'))
        with self.assertRaises(UserError):
            doc.version_ids.unlink()

    def test_tc03_locked_when_courrier_archived(self):
        courrier = self._new_courrier()
        doc = self._new_document(courrier)
        doc.add_version('rapport.pdf', self._b64())
        self.assertFalse(doc.is_locked)
        courrier.write({'state': 'ar'})
        self.assertTrue(doc.is_locked,
                        "Un courrier archivé verrouille ses documents.")

    # --- TC-04 : contrôle format / taille ---
    def test_tc04_extension_rejected(self):
        doc = self._new_document()
        with self.assertRaises(ValidationError):
            doc.add_version('note.txt', self._b64())

    def test_tc04_size_rejected(self):
        doc = self._new_document()
        with patch.object(type(self.Document), 'MAX_FILE_SIZE', 5):
            with self.assertRaises(ValidationError):
                doc.add_version('gros.pdf', self._b64(b'123456'))  # 6 > 5 octets

    # --- TC-05 : audit ajout / suppression ---
    def test_tc05_audit_add_and_remove(self):
        doc = self._new_document()
        version = doc.add_version('rapport.pdf', self._b64())
        self.assertTrue(self._audit(doc, "Ajout pièce jointe"))
        version.unlink()
        self.assertTrue(self._audit(doc, "Suppression pièce jointe"),
                        "L'audit de suppression est conservé après suppression.")

    # --- TC-06 : contrat d'accès _check_document_access ---
    def test_tc06_check_document_access(self):
        courrier = self._new_courrier(confidentiality_id=self.conf_conf.id)
        doc = self._new_document(courrier)
        manager = self.env['res.users'].create({
            'name': 'M', 'login': 'ged_manager',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_manager').id])],
        })
        agent = self.env['res.users'].create({
            'name': 'A', 'login': 'ged_agent',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_agent').id])],
        })
        self.assertTrue(doc._check_document_access('read', manager))
        self.assertFalse(doc._check_document_access('read', agent))
        courrier.responsible_id = agent
        self.assertTrue(doc._check_document_access('read', agent))
        doc.add_version('rapport.pdf', self._b64())
        doc.action_mark_final()
        self.assertFalse(doc._check_document_access('write', manager),
                         "Écriture refusée sur document verrouillé.")

    # --- TC-08 : visibilité opérationnelle selon confidentialité (ir.rule) ---
    def test_tc08_operational_read_rule(self):
        agent = self.env['res.users'].create({
            'name': 'A', 'login': 'ged_rule_agent',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_agent').id])],
        })
        # Document sans confidentialité : lisible par un opérationnel.
        public_doc = self._new_document()
        public_doc.with_user(agent).read(['name'])
        # Document confidentiel d'un tiers : non lisible.
        conf_courrier = self._new_courrier(confidentiality_id=self.conf_conf.id)
        conf_doc = self._new_document(conf_courrier)
        with self.assertRaises(AccessError):
            conf_doc.with_user(agent).read(['name'])

    # --- TC-09 : auto-classement depuis le type de courrier ---
    def test_tc09_auto_classification_from_type(self):
        folder = self.env.ref('aite_courrier_ged.folder_factures')
        type_fact = self.env.ref('aite_courrier_base.type_fact')
        self.assertEqual(type_fact.default_folder_id, folder,
                         "Le type Facture est rattaché au dossier Factures.")
        courrier = self._new_courrier(type_id=type_fact.id)
        doc = self._new_document(courrier)
        self.assertEqual(doc.folder_id, folder,
                         "Le document hérite du dossier par défaut du type.")

    def test_tc09_explicit_folder_overrides_auto(self):
        type_fact = self.env.ref('aite_courrier_base.type_fact')
        other = self.env.ref('aite_courrier_ged.folder_rh')
        courrier = self._new_courrier(type_id=type_fact.id)
        doc = self._new_document(courrier, folder_id=other.id)
        self.assertEqual(doc.folder_id, other,
                         "Un dossier explicite prime sur l'auto-classement.")

    def test_tc09_no_default_folder_left_blank(self):
        # type_entr n'a pas de dossier par défaut : classement manuel.
        courrier = self._new_courrier(type_id=self.type_entr.id)
        self.assertFalse(self.type_entr.default_folder_id)
        doc = self._new_document(courrier)
        self.assertFalse(doc.folder_id)

    # --- TC-10 : compteur de documents par dossier ---
    def test_tc10_folder_document_count(self):
        folder = self.env.ref('aite_courrier_ged.folder_rh')
        before = folder.document_count
        self._new_document(folder_id=folder.id)
        self._new_document(folder_id=folder.id)
        folder.invalidate_recordset(['document_ids', 'document_count'])
        self.assertEqual(folder.document_count, before + 2)

    # --- TC-07 : suppression interdite si verrouillé (pas d'audit) ---
    def test_tc07_locked_delete_no_audit(self):
        doc = self._new_document()
        version = doc.add_version('rapport.pdf', self._b64())
        doc.action_mark_final()
        before = len(self._audit(doc, "Suppression pièce jointe"))
        with self.assertRaises(UserError):
            version.unlink()
        after = len(self._audit(doc, "Suppression pièce jointe"))
        self.assertEqual(before, after,
                         "Aucun audit de suppression si l'opération est refusée.")
