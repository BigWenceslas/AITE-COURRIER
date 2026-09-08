# -*- coding: utf-8 -*-
import base64

from odoo import Command
from odoo.tests.common import TransactionCase

from odoo.addons.aite_courrier_webdav.models.aite_courrier_webdav import (
    WebdavError, WebdavLocked, WebdavNotFound,
)


class TestWebdav(TransactionCase):
    """Service WebDAV : logique de résolution, lecture/écriture, accès."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['aite.courrier.webdav']
        cls.AuditLog = cls.env['aite.courrier.audit.log']
        cls.type_entr = cls.env.ref('aite_courrier_base.type_entr')
        Conf = cls.env['aite.courrier.confidentiality']
        cls.conf_conf = Conf.search([('code', '=', 'CONF')], limit=1)
        # Courrier enregistré (référence générée via le circuit) + un document.
        cls.courrier = cls.env['aite.courrier'].create({
            'subject': "Courrier WebDAV", 'type_id': cls.type_entr.id})
        cls.courrier.action_launch_circuit()
        cls.reference = cls.courrier.reference
        cls.document = cls.env['aite.courrier.document'].create({
            'name': "Rapport", 'courrier_id': cls.courrier.id})
        cls.document.add_version('Rapport.pdf', cls._b64(b'%PDF-1.4 contenu'))

    @staticmethod
    def _b64(content=b'%PDF-1.4'):
        return base64.b64encode(content).decode()

    # --- Résolution / PROPFIND ---
    def test_propfind_root_lists_courrier(self):
        resources = self.Service.propfind('', depth=1)
        names = [r['name'] for r in resources]
        self.assertEqual(resources[0]['path'], '', "Le premier élément est la racine.")
        self.assertIn(self.reference, names)

    def test_propfind_courrier_lists_documents(self):
        resources = self.Service.propfind(self.reference, depth=1)
        files = [r for r in resources if not r['is_collection']]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'Rapport.pdf')
        self.assertFalse(files[0]['locked'])

    def test_propfind_unknown_courrier_not_found(self):
        with self.assertRaises(WebdavNotFound):
            self.Service.propfind('CR-INEXISTANT', depth=1)

    # --- GET ---
    def test_read_file_returns_latest_version(self):
        data = self.Service.read_file('%s/Rapport.pdf' % self.reference)
        self.assertEqual(data['content'], b'%PDF-1.4 contenu')
        self.assertEqual(data['content_type'], 'application/pdf')

    # --- PUT ---
    def test_put_new_file_creates_document(self):
        path = '%s/Contrat.pdf' % self.reference
        result = self.Service.put_file(path, b'%PDF-1.4 nouveau')
        self.assertTrue(result['created'])
        doc = self.Service._document_by_filename(self.courrier, 'Contrat.pdf')
        self.assertTrue(doc)
        self.assertEqual(doc.version_count, 1)

    def test_put_existing_file_adds_version(self):
        path = '%s/Rapport.pdf' % self.reference
        result = self.Service.put_file(path, b'%PDF-1.4 maj')
        self.assertFalse(result['created'])
        self.assertEqual(self.document.version_count, 2)

    def test_put_traces_webdav_audit_source(self):
        self.Service.put_file('%s/Rapport.pdf' % self.reference, b'%PDF-1.4 maj')
        audit = self.AuditLog.search([
            ('model_name', '=', 'aite.courrier.document'),
            ('res_id', '=', self.document.id),
            ('name', '=', "Ajout pièce jointe"),
            ('source', '=', 'webdav'),
        ])
        self.assertTrue(audit, "L'opération WebDAV est tracée avec source='webdav'.")

    def test_put_on_archived_courrier_is_locked(self):
        self.courrier.write({'state': 'ar'})
        self.assertTrue(self.document.is_locked)
        with self.assertRaises(WebdavLocked):
            self.Service.put_file('%s/Rapport.pdf' % self.reference, b'%PDF-1.4 x')

    def test_put_bad_extension_conflict(self):
        from odoo.addons.aite_courrier_webdav.models.aite_courrier_webdav import (
            WebdavConflict,
        )
        with self.assertRaises(WebdavConflict):
            self.Service.put_file('%s/note.txt' % self.reference, b'texte')
        # Le document créé à la volée est nettoyé en cas d'échec.
        self.assertFalse(self.Service._document_by_filename(self.courrier, 'note.txt'))

    # --- DELETE ---
    def test_delete_document(self):
        path = '%s/Rapport.pdf' % self.reference
        self.Service.delete_resource(path)
        self.assertFalse(self.document.exists())

    def test_delete_locked_document_raises(self):
        self.document.action_mark_final()
        self.assertTrue(self.document.is_locked)
        with self.assertRaises(WebdavLocked):
            self.Service.delete_resource('%s/Rapport.pdf' % self.reference)

    # --- MOVE (renommage) ---
    def test_move_renames_document(self):
        self.Service.move_resource(
            '%s/Rapport.pdf' % self.reference,
            '%s/Bilan.pdf' % self.reference)
        self.assertEqual(self.document.name, 'Bilan')

    # --- Contrôle d'accès (confidentialité héritée) ---
    def test_access_control_filters_confidential(self):
        conf_courrier = self.env['aite.courrier'].create({
            'subject': "Secret", 'type_id': self.type_entr.id,
            'confidentiality_id': self.conf_conf.id})
        conf_courrier.action_launch_circuit()
        agent = self.env['res.users'].create({
            'name': 'Agent', 'login': 'webdav_agent',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('aite_courrier_base.group_agent').id])],
        })
        service_agent = self.Service.with_user(agent)
        names = [r['name'] for r in service_agent.propfind('', depth=1)]
        self.assertNotIn(conf_courrier.reference, names,
                         "Un courrier confidentiel d'un tiers est masqué.")
        # Refus d'accès : masqué par l'ir.rule (NotFound) ou par le contrôle
        # explicite (Forbidden) — les deux constituent un refus.
        with self.assertRaises(WebdavError):
            service_agent._courrier_by_reference(conf_courrier.reference)
