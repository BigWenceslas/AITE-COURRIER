# -*- coding: utf-8 -*-
from unittest.mock import patch

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
            'email': "admin_courrier_test@aite.test",
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

    def test_erreur_ecrite_dans_une_transaction_a_part(self):
        """Une entrée « err » passe par un curseur dédié, validé aussitôt.

        Elle précède presque toujours une exception, dont le retour arrière
        effaçait la trace du refus. Pendant les tests, la connexion reste
        partagée (``_audit_autonomous`` est faux) ; on force ici le chemin
        d'exploitation, le registre en mode test fournissant un curseur adossé
        à celui du test.
        """
        self.assertFalse(self.AuditLog._audit_autonomous(self.env),
                         "pendant les tests, l'audit reste dans la transaction")
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        registry_class = type(self.registry)
        real_cursor = registry_class.cursor
        cursors = []

        def spy(registry, *args, **kwargs):
            cr = real_cursor(registry, *args, **kwargs)
            cursors.append(cr)
            return cr

        with patch.object(type(self.AuditLog), '_audit_autonomous',
                          return_value=True), \
                patch.object(registry_class, 'cursor', spy):
            log = self.AuditLog._log(
                self.env, "Tentative non autorisée", 'err', 'aite.courrier',
                1, "COUR-2026-0001", "Action refusée.")
            self.assertEqual(len(cursors), 1,
                             "l'erreur doit s'écrire par un curseur dédié")
            self.assertTrue(log.exists())
            self.assertEqual(log.action_type, 'err')
            self.assertEqual(log.create_uid, self.env.user)
            # les autres types restent dans la transaction courante
            self.AuditLog._log(
                self.env, "Validation", 'ok', 'aite.courrier', 1,
                "COUR-2026-0001", "")
            self.assertEqual(len(cursors), 1)
