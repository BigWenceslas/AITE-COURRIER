# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteWorkflowStep(models.Model):
    _inherit = 'aite.workflow.step'

    # Même nom que dans aite_courrier_sign (Enterprise) : paramétrage identique.
    require_signature = fields.Boolean(
        string="Signature requise",
        help="Bloque les transitions en avant depuis cette étape tant "
             "qu'aucune demande de signature rattachée au courrier n'est "
             "signée.",
    )
