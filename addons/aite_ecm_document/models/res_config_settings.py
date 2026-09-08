# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ecm_hotfolder_path = fields.Char(
        string="Répertoire de dépôt du scanner",
        config_parameter='aite_ecm.hotfolder_path',
        help="Chemin absolu sur le serveur Odoo (partage réseau monté) où le "
             "scanner dépose ses fichiers. Sous-dossiers « traites » et "
             "« erreurs » créés automatiquement.")
    ecm_hotfolder_folder_id = fields.Many2one(
        comodel_name='aite.ecm.folder', string="Dossier ECM de destination")
    ecm_hotfolder_type_id = fields.Many2one(
        comodel_name='aite.ecm.document.type', string="Type des documents scannés")
    ecm_hotfolder_user_id = fields.Many2one(
        comodel_name='res.users', string="Propriétaire des documents importés",
        domain=[('share', '=', False)])
    ecm_hotfolder_min_age = fields.Integer(
        string="Délai avant import (s)", default=30,
        config_parameter='aite_ecm.hotfolder_min_age',
        help="Un fichier n'est importé que s'il n'a pas été modifié depuis ce délai.")
    ecm_checkout_hours = fields.Integer(
        string="Durée d'une réservation (h)", default=48,
        config_parameter='aite_ecm.checkout_hours')
    ecm_trash_retention_days = fields.Integer(
        string="Rétention de la corbeille (jours)", default=30,
        config_parameter='aite_ecm.trash_retention_days')
    ecm_scan_alias = fields.Char(
        string="Adresse de scan vers e-mail", compute='_compute_ecm_scan_alias')

    def _compute_ecm_scan_alias(self):
        alias = self.env.ref('aite_ecm_document.mail_alias_ecm_scan',
                             raise_if_not_found=False)
        for rec in self:
            rec.ecm_scan_alias = (alias.sudo().display_name if alias
                                  else False) or "ecm-scan@<domaine d'alias>"

    def get_values(self):
        res = super().get_values()
        get = self.env['ir.config_parameter'].sudo().get_param
        res.update({
            'ecm_hotfolder_folder_id': int(get('aite_ecm.hotfolder_folder_id') or 0) or False,
            'ecm_hotfolder_type_id': int(get('aite_ecm.hotfolder_type_id') or 0) or False,
            'ecm_hotfolder_user_id': int(get('aite_ecm.hotfolder_user_id') or 0) or False,
        })
        return res

    def set_values(self):
        super().set_values()
        setp = self.env['ir.config_parameter'].sudo().set_param
        setp('aite_ecm.hotfolder_folder_id', self.ecm_hotfolder_folder_id.id or '')
        setp('aite_ecm.hotfolder_type_id', self.ecm_hotfolder_type_id.id or '')
        setp('aite_ecm.hotfolder_user_id', self.ecm_hotfolder_user_id.id or '')
