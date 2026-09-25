# -*- coding: utf-8 -*-
import logging

import odoo
from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class AiteCourrierAuditLog(models.Model):
    """Journal d'audit transverse de la solution AITE Courrier.

    Append-only : une entrée ne peut être ni modifiée ni supprimée par les
    utilisateurs (write/unlink lèvent une AccessError). Seul le superuser
    (ex. scripts de migration) peut y déroger. La création passe par la
    méthode :meth:`_log`, qui écrit en ``sudo`` afin que n'importe quel module
    puisse tracer une action sans dépendre des droits de l'utilisateur courant.
    """

    _name = 'aite.courrier.audit.log'
    _description = "Journal d'audit AITE Courrier"
    _order = 'create_date desc'

    # create_date / create_uid sont des champs techniques fournis par l'ORM ;
    # ils portent ici l'horodatage et l'auteur de l'action tracée.
    name = fields.Char(string="Action", required=True)
    action_type = fields.Selection(
        selection=[
            ('info', "Information"),
            ('ok', "Succès"),
            ('warn', "Avertissement"),
            ('err', "Erreur"),
        ],
        string="Type",
        default='info',
        required=True,
    )
    # Anticipe les futures sources d'événements (WebDAV hors périmètre V1).
    source = fields.Selection(
        selection=[
            ('ui', "Interface"),
            ('webdav', "WebDAV"),
            ('system', "Système"),
        ],
        string="Source",
        default='ui',
        required=True,
    )
    model_name = fields.Char(string="Modèle")
    res_id = fields.Integer(string="ID enregistrement")
    res_ref = fields.Char(string="Référence")
    detail = fields.Text(string="Détails")

    def write(self, vals):
        # Immuable : seule l'exécution en superuser (migrations) est tolérée.
        if not self.env.su:
            raise AccessError(
                "Les entrées du journal d'audit AITE Courrier sont immuables "
                "et ne peuvent pas être modifiées."
            )
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError(
                "Les entrées du journal d'audit AITE Courrier sont immuables "
                "et ne peuvent pas être supprimées."
            )
        return super().unlink()

    @api.model
    def _log(self, env, action, action_type, model, res_id, res_ref,
             detail, source='ui'):
        """Crée une entrée d'audit, réutilisable depuis tous les modules.

        L'écriture se fait en ``sudo`` pour autoriser la traçabilité quels que
        soient les droits de l'utilisateur, tout en conservant son identité
        dans ``create_uid``.

        Une entrée d'erreur (``err``) s'écrit dans une **transaction à part**,
        validée aussitôt. Elle précède presque toujours une exception — une
        tentative non autorisée, une action bloquée — et l'annulation de la
        transaction courante, qui suit toute exception, effaçait jusqu'à la
        trace du refus : le journal promettait ce qu'il ne gardait pas.
        """
        vals = {
            'name': action,
            'action_type': action_type,
            'source': source,
            'model_name': model,
            'res_id': res_id,
            'res_ref': res_ref,
            'detail': detail,
        }
        if action_type == 'err' and self._audit_autonomous(env):
            return self._log_autonomous(env, vals)
        return env['aite.courrier.audit.log'].sudo().create(vals)

    @api.model
    def _audit_autonomous(self, env):
        """Écrire les erreurs hors de la transaction courante ?

        Oui en exploitation. Non pendant les tests : une connexion séparée n'y
        verrait ni les utilisateurs ni les enregistrements créés par le test,
        encore non validés, et y laisserait des lignes que le retour arrière
        du test n'effacerait pas.
        """
        return not odoo.modules.module.current_test \
            and not env.registry.in_test_mode()

    @api.model
    def _log_autonomous(self, env, vals):
        """Écrit ``vals`` par un curseur dédié, validé à la sortie du bloc.

        L'enregistrement renvoyé appartient à l'environnement appelant : la
        transaction courante, ouverte avant cette écriture, ne le voit pas
        forcément. Si l'écriture à part échoue, on se replie sur la
        transaction courante plutôt que de faire échouer l'action tracée.
        """
        try:
            with env.registry.cursor() as cr:
                autonomous = api.Environment(cr, env.uid, dict(env.context))
                record_id = autonomous['aite.courrier.audit.log'].sudo().create(
                    vals).id
        except Exception:  # noqa: BLE001 - le repli est la raison d'être
            _logger.exception(
                "Journal d'audit : écriture autonome impossible, repli sur "
                "la transaction courante (%s).", vals.get('name'))
            return env['aite.courrier.audit.log'].sudo().create(vals)
        return env['aite.courrier.audit.log'].browse(record_id)
