# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteWorkflowStep(models.Model):
    """Extension d'étape : exigence de signature électronique.

    Une étape marquée « Signature requise » bloque toute transition en avant
    tant qu'aucune demande de signature complétée n'est rattachée au courrier
    (contrôle serveur dans ``aite_courrier_sign/models/aite_courrier.py``).
    """

    _inherit = 'aite.workflow.step'

    require_signature = fields.Boolean(
        string="Signature requise",
        help="Bloque les transitions en avant depuis cette étape tant "
             "qu'aucune demande Odoo Sign rattachée au courrier n'est "
             "complétée (signée).",
    )
