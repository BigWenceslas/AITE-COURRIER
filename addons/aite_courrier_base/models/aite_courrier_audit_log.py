# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError


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
        """
        return env['aite.courrier.audit.log'].sudo().create({
            'name': action,
            'action_type': action_type,
            'source': source,
            'model_name': model,
            'res_id': res_id,
            'res_ref': res_ref,
            'detail': detail,
        })
