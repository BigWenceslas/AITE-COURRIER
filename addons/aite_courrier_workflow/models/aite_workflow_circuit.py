# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AiteWorkflowCircuit(models.Model):
    """Circuit de traitement : enchaînement paramétrable d'étapes et de
    transitions appliqué à un type de courrier.

    Le circuit est purement déclaratif (paramétrage > code) : il décrit le
    parcours possible d'un courrier. L'exécution effective sur un courrier
    relève des modules core/validation.
    """

    _name = 'aite.workflow.circuit'
    _description = "Circuit de traitement du courrier"
    _order = 'type_id, name'

    name = fields.Char(string="Nom", required=True, translate=True)
    type_id = fields.Many2one(
        comodel_name='aite.courrier.type',
        string="Type de courrier",
        required=True,
        # restrict : on n'autorise pas la suppression d'un type encore rattaché
        # à un circuit (l'intégrité du paramétrage prime).
        ondelete='restrict',
        index=True,
    )
    step_ids = fields.One2many(
        comodel_name='aite.workflow.step',
        inverse_name='circuit_id',
        string="Étapes",
    )
    transition_ids = fields.One2many(
        comodel_name='aite.workflow.transition',
        inverse_name='circuit_id',
        string="Transitions",
    )
    active = fields.Boolean(string="Actif", default=True)

    @api.constrains('active', 'type_id')
    def _check_unique_active_per_type(self):
        """Un seul circuit actif par type de courrier.

        Plusieurs circuits peuvent coexister pour un même type (versions,
        archives), mais un seul peut être actif à un instant donné.
        """
        for circuit in self:
            if not circuit.active:
                continue
            duplicate = self.search_count([
                ('type_id', '=', circuit.type_id.id),
                ('active', '=', True),
                ('id', '!=', circuit.id),
            ])
            if duplicate:
                raise ValidationError(_(
                    "Un seul circuit actif est autorisé par type de courrier : "
                    "le type « %s » possède déjà un circuit actif.",
                    circuit.type_id.display_name,
                ))

    def get_initial_step(self):
        """Retourne l'unique étape initiale du circuit (recordset vide si aucune)."""
        self.ensure_one()
        return self.step_ids.filtered('is_initial')[:1]
