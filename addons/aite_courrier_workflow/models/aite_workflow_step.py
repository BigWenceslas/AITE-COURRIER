# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AiteWorkflowStep(models.Model):
    """Étape d'un circuit de traitement.

    Une étape porte les rôles (groupes) autorisés à agir et, optionnellement,
    une liste restreinte d'utilisateurs. La règle d'habilitation est
    centralisée dans :meth:`can_user_act`.
    """

    _name = 'aite.workflow.step'
    _description = "Étape de circuit"
    _order = 'circuit_id, sequence, id'

    circuit_id = fields.Many2one(
        comodel_name='aite.workflow.circuit',
        string="Circuit",
        required=True,
        # cascade : supprimer un circuit supprime ses étapes.
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string="Séquence", default=10)
    name = fields.Char(string="Nom", required=True, translate=True)
    description = fields.Char(string="Description", translate=True)
    role_ids = fields.Many2many(
        comodel_name='res.groups',
        relation='aite_wf_step_role_rel',
        column1='step_id',
        column2='group_id',
        string="Rôles autorisés",
        help="Groupes habilités à agir sur cette étape.",
    )
    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='aite_wf_step_user_rel',
        column1='step_id',
        column2='user_id',
        string="Utilisateurs autorisés",
        help="Si renseigné, seuls ces utilisateurs (parmi ceux ayant l'un des "
             "rôles) peuvent agir. Si vide, tout utilisateur ayant l'un des "
             "rôles est habilité.",
    )
    sla_hours = fields.Integer(string="SLA (heures)")
    is_initial = fields.Boolean(string="Étape initiale")
    is_final = fields.Boolean(string="Étape finale")

    outgoing_transition_ids = fields.One2many(
        comodel_name='aite.workflow.transition',
        inverse_name='step_from_id',
        string="Transitions sortantes",
    )
    incoming_transition_ids = fields.One2many(
        comodel_name='aite.workflow.transition',
        inverse_name='step_to_id',
        string="Transitions entrantes",
    )

    @api.constrains('is_initial', 'is_final')
    def _check_circuit_topology(self):
        """Chaque circuit a exactement une étape initiale et au moins une finale.

        Neutralisé :
        - pendant le chargement des données (``install_module``) : les étapes y
          sont créées une à une, le circuit n'est complet qu'en fin de chargement ;
        - pendant la bascule interne de l'étape initiale (``_skip_topology``) :
          l'état transitoire (0 ou 2 initiales) est ignoré, seul l'état final
          est validé.
        Reste active pour toute édition ultérieure (UI, RPC, tests).
        """
        if self.env.context.get('install_module') or \
                self.env.context.get('_skip_topology'):
            return
        for circuit in self.mapped('circuit_id'):
            steps = circuit.step_ids
            if len(steps.filtered('is_initial')) != 1:
                raise ValidationError(_(
                    "Le circuit « %s » doit comporter exactement une étape "
                    "initiale.", circuit.display_name,
                ))
            if not steps.filtered('is_final'):
                raise ValidationError(_(
                    "Le circuit « %s » doit comporter au moins une étape "
                    "finale.", circuit.display_name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        # Garantit une seule étape initiale par circuit, sans exposer d'état
        # transitoire invalide à la validation :
        #   - dans le lot enregistré, seule la dernière étape cochée « initiale »
        #     d'un même circuit est conservée (les précédentes sont décochées) ;
        #   - l'étape initiale déjà enregistrée des circuits concernés est décochée.
        # (L'enchaînement de décochage des autres se fait donc à l'enregistrement,
        # ce qui est fiable y compris à la création d'un circuit complet.)
        last_initial = {}
        for index, vals in enumerate(vals_list):
            circuit_id = vals.get('circuit_id')
            if vals.get('is_initial') and circuit_id:
                if circuit_id in last_initial:
                    vals_list[last_initial[circuit_id]]['is_initial'] = False
                last_initial[circuit_id] = index
        for circuit_id in last_initial:
            self.search([
                ('circuit_id', '=', circuit_id),
                ('is_initial', '=', True),
            ]).with_context(_skip_topology=True).write({'is_initial': False})
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('is_initial'):
            # Décocher les autres initiales AVANT d'enregistrer celle-ci, en
            # ignorant l'état transitoire ; super() valide ensuite l'état final.
            for step in self:
                step.circuit_id.step_ids.filtered(
                    lambda s: s.is_initial and s.id != step.id
                ).with_context(_skip_topology=True).write({'is_initial': False})
        return super().write(vals)

    def outgoing_transitions(self):
        """Transitions partant de l'étape."""
        self.ensure_one()
        return self.outgoing_transition_ids

    def can_user_act(self, user):
        """Indique si ``user`` est habilité à agir sur l'étape.

        Règle : l'utilisateur doit posséder l'un des rôles (``role_ids``).
        Si ``user_ids`` est renseigné, il doit en plus figurer dans cette liste.
        """
        self.ensure_one()
        if not (user.groups_id & self.role_ids):
            return False
        if self.user_ids:
            return user in self.user_ids
        return True
