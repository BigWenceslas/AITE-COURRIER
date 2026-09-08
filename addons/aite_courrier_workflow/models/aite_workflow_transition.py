# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AiteWorkflowTransition(models.Model):
    """Transition entre deux étapes d'un circuit.

    Une transition est dirigée : ``forward`` fait avancer le courrier,
    ``backward`` le renvoie en arrière (retour pour correction). Elle peut
    exiger un commentaire justificatif.
    """

    _name = 'aite.workflow.transition'
    _description = "Transition de circuit"
    _order = 'circuit_id, step_from_id, id'

    circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit',
        string="Circuit",
        required=True,
        ondelete='cascade',
        index=True,
    )
    step_from_id = fields.Many2one(
        comodel_name='aite.workflow.step',
        string="Étape de départ",
        required=True,
        # cascade : supprimer une étape supprime ses transitions sortantes.
        ondelete='cascade',
        index=True,
    )
    step_to_id = fields.Many2one(
        comodel_name='aite.workflow.step',
        string="Étape d'arrivée",
        required=True,
        # cascade : supprimer une étape supprime ses transitions entrantes.
        ondelete='cascade',
        index=True,
    )
    label = fields.Char(string="Libellé", required=True, translate=True)
    direction = fields.Selection(
        selection=[
            ('forward', "En avant"),
            ('backward', "En arrière"),
        ],
        string="Sens",
        required=True,
        default='forward',
    )
    comment_required = fields.Boolean(string="Commentaire obligatoire")

    @api.depends('label', 'step_from_id.name', 'step_to_id.name')
    def _compute_display_name(self):
        for transition in self:
            label = transition.label or _("Transition")
            if transition.step_from_id and transition.step_to_id:
                transition.display_name = "%s (%s → %s)" % (
                    label, transition.step_from_id.name, transition.step_to_id.name)
            else:
                transition.display_name = label

    @api.constrains('step_from_id', 'step_to_id', 'circuit_id')
    def _check_steps_circuit(self):
        """Les deux étapes appartiennent au circuit de la transition.

        Neutralisé pendant le chargement des données (cf. étape) : les
        références sont déjà cohérentes par construction dans ce cas.
        """
        if self.env.context.get('install_module'):
            return
        for transition in self:
            if transition.step_from_id.circuit_id != transition.circuit_id or \
                    transition.step_to_id.circuit_id != transition.circuit_id:
                raise ValidationError(_(
                    "Les étapes d'une transition doivent appartenir à son "
                    "circuit (« %s »).", transition.circuit_id.display_name,
                ))
            if transition.step_from_id == transition.step_to_id:
                raise ValidationError(_(
                    "Une transition ne peut pas relier une étape à elle-même."
                ))
