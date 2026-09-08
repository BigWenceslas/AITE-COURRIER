# -*- coding: utf-8 -*-
from odoo import fields, models


class AiteCourrierType(models.Model):
    """Extension du type de courrier : accusé de réception automatique.

    Le champ est ajouté par héritage (même logique que ``circuit_id`` ajouté
    par le module workflow) afin de garder ``aite_courrier_base`` installable
    seul, sans dépendance vers la mécanique d'envoi d'e-mails du core.
    """

    _inherit = 'aite.courrier.type'

    send_acknowledgement = fields.Boolean(
        string="Accusé de réception automatique",
        help="Au lancement du circuit, envoie automatiquement un accusé de "
             "réception à l'e-mail de l'expéditeur (si renseigné sur le "
             "courrier). Recommandé pour les types de catégorie « Entrant ».",
    )
