# -*- coding: utf-8 -*-
"""Explorateur de fichiers natif (Community et Enterprise) — côté serveur.

Le client OWL (``static/src/explorer``) n'appelle que des méthodes de modèle
(``explorer_meta``, ``explorer_search``, ``explorer_bulk``…) et le contrôleur
de dépôt ``/ecm/explorer/upload`` : les règles d'accès ECM s'appliquent
naturellement (dossiers, confidentialité, verrous).
"""
import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff', 'bmp', 'webp')
THUMB_SIZE = (360, 360)


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    thumbnail = fields.Binary(string="Vignette", attachment=True, copy=False)
    thumbnail_status = fields.Selection(
        selection=[('none', "Aucune"), ('client', "À générer"),
                   ('present', "Disponible"), ('error', "Impossible")],
        string="État de la vignette", default='none', copy=False)

    # ================================================================== #
    # Vignettes
    # ================================================================== #
    def _refresh_thumbnail(self, raw=None, extension=None):
        """Image → vignette serveur (Pillow) ; PDF → générée par le
        navigateur (pdf.js) à l'affichage ; autres formats → icône."""
        self.ensure_one()
        version = self.latest_version_id
        extension = (extension or version.file_extension or '').lower()
        if extension in IMAGE_EXTENSIONS:
            try:
                from odoo.tools.image import image_process
                if raw is None:
                    raw = base64.b64decode(version.attachment_id.datas or b'')
                thumb = image_process(raw, size=THUMB_SIZE, output_format='JPEG')
                self.sudo().write({'thumbnail': base64.b64encode(thumb),
                                   'thumbnail_status': 'present'})
                return
            except Exception as exc:  # noqa: BLE001 — image illisible
                _logger.info("[ecm] vignette impossible pour %s : %s",
                             self.reference, exc)
                self.sudo().write({'thumbnail': False,
                                   'thumbnail_status': 'error'})
                return
        status = 'client' if extension == 'pdf' else 'none'
        self.sudo().write({'thumbnail': False, 'thumbnail_status': status})

    def add_version(self, filename, datas, comment=False):
        version = super().add_version(filename, datas, comment)
        try:
            raw = base64.b64decode(datas or b'')
            self._refresh_thumbnail(raw, version.file_extension)
        except Exception:  # noqa: BLE001
            pass
        return version

    @api.model
    def explorer_set_thumbnail(self, doc_id, thumbnail_b64):
        """Vignette générée par le navigateur (pdf.js) pour un PDF."""
        doc = self.browse(int(doc_id)).exists()
        if not doc:
            return False
        doc.check_access('read')
        if doc.latest_version_id.file_extension != 'pdf':
            return False
        doc.sudo().write({'thumbnail': thumbnail_b64 or False,
                          'thumbnail_status': 'present' if thumbnail_b64
                          else 'error'})
        return True

    # ================================================================== #
    # Métadonnées de l'explorateur (facettes)
    # ================================================================== #
    @api.model
    def explorer_meta(self):
        Doc = self.env['aite.ecm.document']
        counts_folder = {f.id if f else 0: n for f, n in Doc._read_group(
            [], ['folder_id'], ['__count'])}
        folders = [{
            'id': f.id, 'name': f.name, 'parent_id': f.parent_id.id or False,
            'color': f.color, 'count': counts_folder.get(f.id, 0),
            'can_write': f.user_can(self.env.user, 'write'),
        } for f in self.env['aite.ecm.folder'].search([], order='sequence, name')]
        tag_counts = {t.id: n for t, n in Doc._read_group(
            [('tag_ids', '!=', False)], ['tag_ids'], ['__count'])}
        tags = [{'id': t.id, 'name': t.name, 'color': t.color,
                 'count': tag_counts.get(t.id, 0)}
                for t in self.env['aite.ecm.tag'].search([])]
        type_counts = {t.id if t else 0: n for t, n in Doc._read_group(
            [], ['type_id'], ['__count'])}
        types = [{'id': t.id, 'name': t.name, 'code': t.code,
                  'count': type_counts.get(t.id, 0)}
                 for t in self.env['aite.ecm.document.type'].search([])]
        IrModel = self.env['ir.model'].sudo()
        res_models = []
        for model, n in Doc._read_group([('res_model', '!=', False)],
                                        ['res_model'], ['__count']):
            label = IrModel._get(model).name if model in self.env else model
            res_models.append({'model': model, 'label': label, 'count': n})
        state_counts = {s: n for s, n in Doc._read_group([], ['state'],
                                                          ['__count'])}
        trash_count = Doc.with_context(active_test=False).search_count(
            [('active', '=', False)])
        user = self.env.user
        return {
            'folders': folders, 'tags': tags, 'types': types,
            'res_models': res_models,
            'states': [{'key': k, 'label': v,
                        'count': state_counts.get(k, 0)}
                       for k, v in Doc._fields['state']._description_selection(
                           self.env)],
            'trash_count': trash_count,
            'unfiled_count': counts_folder.get(0, 0),
            'no_folder_write': not folders,
            'is_manager': self._is_manager(),
            'can_create_folder': self.env['aite.ecm.folder'].has_access('create'),
            'share_installed': 'aite.ecm.share' in self.env,
            'workflow_installed': 'wf_status' in Doc._fields,
            'users': [{'id': u.id, 'name': u.name} for u in self.env['res.users']
                      .search([('share', '=', False), ('active', '=', True)],
                              order='name', limit=300)],
            'user_id': user.id,
        }

    # ================================================================== #
    # Recherche
    # ================================================================== #
    @api.model
    def _explorer_domain(self, params):
        domain = []
        folder_id = params.get('folder_id')
        if folder_id == 'unfiled':
            domain.append(('folder_id', '=', False))
        elif folder_id:
            op = 'child_of' if params.get('include_sub', True) else '='
            domain.append(('folder_id', op, int(folder_id)))
        if params.get('tag_ids'):
            for tag_id in params['tag_ids']:
                domain.append(('tag_ids', 'in', [int(tag_id)]))
        if params.get('type_id'):
            domain.append(('type_id', '=', int(params['type_id'])))
        if params.get('res_model'):
            domain.append(('res_model', '=', params['res_model']))
        if params.get('state'):
            domain.append(('state', '=', params['state']))
        if params.get('mine'):
            domain.append(('owner_id', '=', self.env.user.id))
        if params.get('checked_out'):
            domain.append(('checkout_user_id', '!=', False))
        search = (params.get('search') or '').strip()
        if search:
            domain += ['|', '|', '|', ('name', 'ilike', search),
                       ('reference', 'ilike', search),
                       ('version_ids.file_name', 'ilike', search),
                       ('content_fulltext', 'ilike', search)]
        return domain

    def _explorer_record(self):
        self.ensure_one()
        version = self.latest_version_id
        thumb_url = False
        if self.thumbnail_status == 'present' and self.thumbnail:
            thumb_url = "/web/image/aite.ecm.document/%d/thumbnail?unique=%s" % (
                self.id, fields.Datetime.to_string(self.write_date).replace(
                    ' ', '_'))
        return {
            'id': self.id, 'reference': self.reference, 'name': self.name,
            'type': self.type_id.name or '', 'type_id': self.type_id.id or False,
            'folder_id': self.folder_id.id or False,
            'folder': self.folder_id.complete_name or '',
            'tags': [{'id': t.id, 'name': t.name, 'color': t.color}
                     for t in self.tag_ids],
            'owner': self.owner_id.name or '',
            'owner_id': self.owner_id.id or False,
            'state': self.state,
            'state_label': dict(self._fields['state']._description_selection(
                self.env)).get(self.state, self.state),
            'confidentiality': self.confidentiality_id.name or '',
            'confidentiality_code': self.confidentiality_code or '',
            'is_locked': self.is_locked,
            'is_checked_out': self.is_checked_out,
            'checked_out_by_me': self.checked_out_by_me,
            'checkout_user': self.checkout_user_id.name or '',
            'file_name': version.file_name or '',
            'file_extension': version.file_extension or '',
            'mimetype': version.mime_type or '',
            'file_size': version.file_size or 0,
            'attachment_id': version.attachment_id.id or False,
            'version_count': self.version_count,
            'write_date': fields.Datetime.to_string(self.write_date),
            'thumbnail_url': thumb_url,
            'thumbnail_status': self.thumbnail_status,
            'res_model': self.res_model or False,
            'res_id': self.res_id or False,
            'res_display': self.res_display or '',
            'active': self.active,
            'can_write': self._check_document_access('write'),
            'access_summary': self.access_summary,
            'shared_users': self.shared_user_ids.mapped('name'),
            'editor_users': self.editor_user_ids.mapped('name'),
            'wf_status': getattr(self, 'wf_status', False) or False,
            'wf_step': getattr(self, 'wf_step_id', False) and self.wf_step_id.name or '',
            'wf_can_act': bool(getattr(self, 'wf_can_act', False)),
            'wf_has_circuit': bool(getattr(self, 'wf_has_circuit', False)),
            'wf_deadline': fields.Datetime.to_string(self.wf_deadline)
            if getattr(self, 'wf_deadline', False) else False,
            'wf_is_overdue': bool(getattr(self, 'wf_is_overdue', False)),
            'extra_actions': self._explorer_extra_actions(),
        }

    def _explorer_extra_actions(self):
        """Boutons supplémentaires de l'inspecteur, fournis par les modules
        complémentaires : liste de dicts ``{key, label, icon, kind, url|method,
        cls}`` — ``kind`` vaut ``url`` (ouvrir l'URL, y compris un schéma
        d'application comme ``ms-word:``) ou ``method`` (méthode de modèle qui
        renvoie une action)."""
        self.ensure_one()
        return []

    @api.model
    def explorer_call(self, doc_id, method):
        """Exécute une action déclarée par ``_explorer_extra_actions``."""
        doc = self.browse(int(doc_id)).exists()
        if not doc:
            return False
        allowed = {a['method'] for a in doc._explorer_extra_actions()
                   if a.get('kind') == 'method'}
        if method not in allowed:
            raise UserError(_("Action non autorisée : %s") % method)
        return getattr(doc, method)() or True

    @api.model
    def explorer_search(self, params=None):
        params = params or {}
        Doc = self.env['aite.ecm.document']
        if params.get('trash'):
            Doc = Doc.with_context(active_test=False)
            domain = [('active', '=', False)]
        else:
            domain = self._explorer_domain(params)
        order = {'name': 'name asc', 'date': 'write_date desc',
                 'reference': 'reference desc'}.get(params.get('order'),
                                                    'write_date desc')
        limit = min(int(params.get('limit') or 60), 200)
        offset = int(params.get('offset') or 0)
        docs = Doc.search(domain, limit=limit, offset=offset, order=order)
        return {'records': [d._explorer_record() for d in docs],
                'total': Doc.search_count(domain),
                'offset': offset, 'limit': limit}

    # ================================================================== #
    # Actions
    # ================================================================== #
    @api.model
    def explorer_create_folder(self, name, parent_id=None):
        folder = self.env['aite.ecm.folder'].create({
            'name': name, 'parent_id': int(parent_id) if parent_id else False})
        return {'id': folder.id, 'name': folder.name,
                'parent_id': folder.parent_id.id or False}

    @api.model
    def explorer_bulk(self, action, ids, params=None):
        """Applique une action à une sélection ; renvoie les erreurs par
        document sans interrompre les autres."""
        params = params or {}
        docs = self.env['aite.ecm.document'].with_context(
            active_test=False).browse(ids).exists()
        errors, done = [], 0
        for doc in docs:
            try:
                with self.env.cr.savepoint():
                    if action == 'trash':
                        doc.action_trash()
                    elif action == 'restore':
                        doc.action_restore()
                    elif action == 'final':
                        doc.action_mark_final()
                    elif action == 'archive':
                        doc.action_mark_archived()
                    elif action == 'draft':
                        doc.action_reset_draft()
                    elif action == 'checkout':
                        doc.action_checkout()
                    elif action == 'checkin':
                        doc.action_checkin()
                    elif action == 'move':
                        doc.write({'folder_id': int(params['folder_id'])
                                   if params.get('folder_id') else False})
                    elif action == 'tag':
                        doc.write({'tag_ids': [(4, int(t))
                                               for t in params.get('tag_ids', [])]})
                    elif action == 'untag':
                        doc.write({'tag_ids': [(3, int(t))
                                               for t in params.get('tag_ids', [])]})
                    elif action == 'rename':
                        doc.write({'name': params.get('name') or doc.name})
                    elif action == 'set_type':
                        doc.write({'type_id': int(params['type_id'])
                                   if params.get('type_id') else False})
                    elif action == 'share_read':
                        doc.write({'shared_user_ids': [(4, int(u)) for u in params.get('user_ids', [])]})
                    elif action == 'share_write':
                        doc.write({'editor_user_ids': [(4, int(u)) for u in params.get('user_ids', [])]})
                    elif action == 'unshare':
                        doc.write({'shared_user_ids': [(5, 0, 0)], 'editor_user_ids': [(5, 0, 0)]})
                    elif action == 'wf_launch':
                        doc.action_wf_launch()
                    elif action == 'wf_reset':
                        doc.action_wf_reset()
                    else:
                        raise UserError(_("Action inconnue : %s") % action)
                    done += 1
            except (UserError, AccessError) as exc:
                errors.append({'id': doc.id, 'reference': doc.reference,
                               'message': str(exc)})
        return {'done': done, 'errors': errors}

    @api.model
    def explorer_wf_wizard(self, doc_id):
        """Action de l'assistant de circuit (module workflow requis)."""
        doc = self.browse(int(doc_id)).exists()
        if not doc or not hasattr(doc, 'action_wf_open_wizard'):
            return False
        return doc.action_wf_open_wizard()

    @api.model
    def explorer_share(self, doc_id):
        """Lien de partage AITE (module aite_ecm_share) : renvoie l'action
        à ouvrir, ou False si le module est absent."""
        doc = self.browse(int(doc_id)).exists()
        if not doc or not hasattr(doc, 'action_create_share'):
            return False
        return doc.action_create_share()
