# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteCourrierReponseTemplate(models.Model):
    """Modèle de réponse : objet et corps avec champs de fusion.

    Le rendu utilise le moteur ``inline_template`` d'Odoo
    (``mail.render.mixin``) : les espaces réservés s'écrivent
    ``{{ object.champ }}`` et sont fusionnés sur le courrier d'origine
    (``object`` = le courrier auquel on répond).

    Espaces réservés usuels :
    ``{{ object.reference }}``, ``{{ object.subject }}``,
    ``{{ object.sender }}``, ``{{ object.sender_email }}``,
    ``{{ object.date_received }}``, ``{{ object.department_id.name }}``,
    ``{{ object.responsible_id.name }}``, ``{{ user.name }}``.
    """

    _name = 'aite.courrier.reponse.template'
    _description = "Modèle de réponse courrier"
    _order = 'sequence, name'

    sequence = fields.Integer(string="Séquence", default=10)
    name = fields.Char(string="Nom", required=True, translate=True)
    active = fields.Boolean(string="Actif", default=True)
    type_ids = fields.Many2many(
        comodel_name='aite.courrier.type',
        relation='aite_reponse_template_type_rel',
        column1='template_id', column2='type_id',
        string="Types de courrier",
        help="Types de courrier auxquels ce modèle s'applique. "
             "Vide = tous les types.",
    )
    subject = fields.Char(
        string="Objet", required=True, translate=True,
        help="Objet de la réponse. Champs de fusion autorisés, "
             "ex. : Votre courrier {{ object.reference }}.",
    )
    body_html = fields.Html(
        string="Corps", required=True, translate=True, sanitize=True,
        help="Corps de la réponse. Champs de fusion au format "
             "{{ object.champ }} (cf. légende sous le champ).",
    )

    # ------------------------------------------------------------------ #
    # Rendu (fusion des champs)
    # ------------------------------------------------------------------ #
    def _render_on(self, courrier):
        """Fusionne le modèle sur ``courrier`` → dict(subject, body_html).

        S'appuie sur le moteur de rendu standard d'Odoo (le même que les
        modèles d'e-mails) : robuste, sécurisé et déjà connu des
        administrateurs fonctionnels.
        """
        self.ensure_one()
        courrier.ensure_one()
        Renderer = self.env['mail.render.mixin']
        subject = Renderer._render_template(
            self.subject or '', 'aite.courrier', courrier.ids,
            engine='inline_template')[courrier.id]
        body = Renderer._render_template(
            self.body_html or '', 'aite.courrier', courrier.ids,
            engine='inline_template')[courrier.id]
        return {'subject': subject, 'body_html': body}

    @api.model
    def _applicable_domain(self, courrier_type):
        """Domaine des modèles applicables à un type de courrier donné."""
        domain = ['|', ('type_ids', '=', False)]
        if courrier_type:
            domain.append(('type_ids', 'in', courrier_type.ids))
        else:
            domain.append(('type_ids', '=', False))
        return domain
