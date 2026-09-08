# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierType(models.Model):
    """Extension du type de courrier : dossier GED de classement par défaut.

    Permet l'**auto-classement** : à la création d'un document, si aucun dossier
    n'est précisé, il hérite du ``default_folder_id`` du type de son courrier.
    Le classement reste surchargeable manuellement document par document.
    """

    _inherit = 'aite.courrier.type'

    default_folder_id = fields.Many2one(
        comodel_name='aite.courrier.folder',
        string="Dossier GED par défaut",
        ondelete='set null',
        help="Dossier de classement appliqué automatiquement aux documents des "
             "courriers de ce type (auto-classement). Modifiable par document.",
    )
