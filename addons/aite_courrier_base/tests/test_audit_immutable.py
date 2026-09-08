# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestAuditImmutable(TransactionCase):
    """Vérifie l'immuabilité du journal d'audit, même pour group_admin."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AuditLog = cls.env['aite.courrier.audit.log']
        # Entrée créée via la méthode réutilisable _log (écrit en sudo).
        cls.log = cls.AuditLog._log(
            cls.env,
            action="Création courrier",
            action_type='ok',
            model='aite.courrier',
            res_id=1,
            res_ref="COUR-2026-0234",
            detail="Entrée de test.",
        )
        # Utilisateur membre du groupe administrateur AITE Courrier.
        cls.admin_user = cls.env['res.users'].create({
            'name': "Admin Courrier Test",
            'login': "admin_courrier_test",
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('aite_courrier_base.group_admin').id,
            ])],
        })

    def test_log_created(self):
        self.assertEqual(self.log.name, "Création courrier")
        self.assertEqual(self.log.res_ref, "COUR-2026-0234")
        self.assertEqual(self.log.source, 'ui')

    @mute_logger('odoo.models')
    def test_write_raises_for_admin(self):
        log_admin = self.log.with_user(self.admin_user)
        with self.assertRaises(AccessError):
            log_admin.write({'detail': "tentative de modification"})

    @mute_logger('odoo.models')
    def test_unlink_raises_for_admin(self):
        log_admin = self.log.with_user(self.admin_user)
        with self.assertRaises(AccessError):
            log_admin.unlink()

    def test_superuser_can_write(self):
        # Échappatoire migrations : le superuser (su) peut écrire.
        self.log.sudo().write({'detail': "correctif migration"})
        self.assertEqual(self.log.detail, "correctif migration")
