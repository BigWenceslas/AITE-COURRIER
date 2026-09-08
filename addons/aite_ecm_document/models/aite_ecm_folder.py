# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AiteEcmFolder(models.Model):
    """Plan de classement d'entreprise (arborescence) avec droits hérités.

    Chaque dossier peut restreindre la lecture et/ou l'écriture à des
    groupes ; un dossier sans restriction hérite de celles de son parent
    (champs ``effective_*`` calculés récursivement et stockés, utilisés par
    les règles d'enregistrement des documents). Sans aucune restriction dans
    la branche, le dossier est ouvert à tous les utilisateurs ECM.

    """

    _name = 'aite.ecm.folder'
    _description = "Dossier de classement ECM"
    _parent_store = True
    _parent_name = 'parent_id'
    _order = 'complete_name'
    _rec_name = 'complete_name'

    name = fields.Char(string="Nom", required=True, translate=True)
    complete_name = fields.Char(
        string="Chemin", compute='_compute_complete_name', store=True,
        recursive=True)
    parent_id = fields.Many2one(
        comodel_name='aite.ecm.folder', string="Dossier parent",
        index=True, ondelete='cascade')
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        comodel_name='aite.ecm.folder', inverse_name='parent_id',
        string="Sous-dossiers")
    sequence = fields.Integer(string="Séquence", default=10)
    color = fields.Integer(string="Couleur")
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string="Société",
        help="Vide = commun à toutes les sociétés.")
    read_group_ids = fields.Many2many(
        comodel_name='res.groups', relation='aite_ecm_folder_read_group_rel',
        column1='folder_id', column2='group_id', string="Lecture réservée à",
        help="Vide = hérite du dossier parent (ou ouvert à tous).")
    write_group_ids = fields.Many2many(
        comodel_name='res.groups', relation='aite_ecm_folder_write_group_rel',
        column1='folder_id', column2='group_id', string="Écriture réservée à",
        help="Vide = hérite du dossier parent (ou ouvert à tous).")
    read_user_ids = fields.Many2many(
        comodel_name='res.users', relation='aite_ecm_folder_read_user_rel',
        column1='folder_id', column2='user_id', string="Lecteurs nommés",
        domain=[('share', '=', False)],
        help="Personnes autorisées en lecture, en plus des groupes.")
    write_user_ids = fields.Many2many(
        comodel_name='res.users', relation='aite_ecm_folder_write_user_rel',
        column1='folder_id', column2='user_id', string="Rédacteurs nommés",
        domain=[('share', '=', False)],
        help="Personnes autorisées en écriture, en plus des groupes.")
    effective_read_user_ids = fields.Many2many(
        comodel_name='res.users', relation='aite_ecm_folder_eff_read_user_rel',
        column1='folder_id', column2='user_id', string="Lecteurs effectifs",
        compute='_compute_effective_groups', store=True, recursive=True)
    effective_write_user_ids = fields.Many2many(
        comodel_name='res.users', relation='aite_ecm_folder_eff_write_user_rel',
        column1='folder_id', column2='user_id', string="Rédacteurs effectifs",
        compute='_compute_effective_groups', store=True, recursive=True)
    access_summary = fields.Text(
        string="Qui peut accéder", compute='_compute_access_summary')
    effective_read_group_ids = fields.Many2many(
        comodel_name='res.groups',
        relation='aite_ecm_folder_eff_read_group_rel',
        column1='folder_id', column2='group_id',
        string="Lecture effective", compute='_compute_effective_groups',
        store=True, recursive=True)
    effective_write_group_ids = fields.Many2many(
        comodel_name='res.groups',
        relation='aite_ecm_folder_eff_write_group_rel',
        column1='folder_id', column2='group_id',
        string="Écriture effective", compute='_compute_effective_groups',
        store=True, recursive=True)
    document_count = fields.Integer(
        string="Documents", compute='_compute_document_count')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = "%s / %s" % (
                    folder.parent_id.complete_name, folder.name)
            else:
                folder.complete_name = folder.name

    @api.depends('read_group_ids', 'write_group_ids', 'read_user_ids',
                 'write_user_ids', 'parent_id.effective_read_group_ids',
                 'parent_id.effective_write_group_ids',
                 'parent_id.effective_read_user_ids',
                 'parent_id.effective_write_user_ids')
    def _compute_effective_groups(self):
        """Un dossier sans aucune restriction propre (ni groupe ni personne)
        hérite des restrictions effectives de son parent."""
        for folder in self:
            if folder.read_group_ids or folder.read_user_ids:
                folder.effective_read_group_ids = folder.read_group_ids
                folder.effective_read_user_ids = folder.read_user_ids
            else:
                folder.effective_read_group_ids = \
                    folder.parent_id.effective_read_group_ids
                folder.effective_read_user_ids = \
                    folder.parent_id.effective_read_user_ids
            if folder.write_group_ids or folder.write_user_ids:
                folder.effective_write_group_ids = folder.write_group_ids
                folder.effective_write_user_ids = folder.write_user_ids
            else:
                folder.effective_write_group_ids = \
                    folder.parent_id.effective_write_group_ids
                folder.effective_write_user_ids = \
                    folder.parent_id.effective_write_user_ids

    @api.depends('effective_read_group_ids', 'effective_write_group_ids',
                 'effective_read_user_ids', 'effective_write_user_ids')
    def _compute_access_summary(self):
        for folder in self:
            folder.access_summary = "%s\n%s" % (
                _("Lecture : %s") % folder._describe(
                    folder.effective_read_group_ids,
                    folder.effective_read_user_ids),
                _("Écriture : %s") % folder._describe(
                    folder.effective_write_group_ids,
                    folder.effective_write_user_ids))

    @api.model
    def _describe(self, groups, users):
        if not groups and not users:
            return _("tous les rôles ECM (managers et administrateurs inclus)")
        parts = [g.name for g in groups] + [u.name for u in users]
        return ", ".join(parts) + _(" — plus les managers et administrateurs")

    def _compute_document_count(self):
        Document = self.env['aite.ecm.document']
        for folder in self:
            folder.document_count = Document.search_count(
                [('folder_id', 'child_of', folder.id)])

    @api.constrains('parent_id')
    def _check_no_cycle(self):
        for folder in self:
            seen, current = set(), folder.parent_id
            while current:
                if current.id in seen or current == folder:
                    raise ValidationError(_(
                        "Un dossier ne peut pas être son propre ancêtre."))
                seen.add(current.id)
                current = current.parent_id

    # ------------------------------------------------------------------ #
    # Droits
    # ------------------------------------------------------------------ #
    def user_can(self, user, operation='read'):
        """Droit de ``user`` sur le dossier (hérité de la branche) : aucune
        restriction, ou membre d'un groupe autorisé, ou personne nommée."""
        self.ensure_one()
        if operation == 'read':
            groups, users = self.effective_read_group_ids, self.effective_read_user_ids
        else:
            groups, users = self.effective_write_group_ids, self.effective_write_user_ids
        if not groups and not users:
            return True
        return user in users or bool(user.groups_id & groups)

    def action_open_explorer(self):
        self.ensure_one()
        return {'type': 'ir.actions.client', 'tag': 'aite_ecm_explorer',
                'name': self.name, 'context': {'ecm_folder_id': self.id}}

    def action_view_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'aite_ecm_document.action_aite_ecm_document')
        action['domain'] = [('folder_id', 'child_of', self.id)]
        action['context'] = {'default_folder_id': self.id}
        return action
