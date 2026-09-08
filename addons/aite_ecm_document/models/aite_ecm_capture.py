# -*- coding: utf-8 -*-
"""Numérisation vers l'ECM : trois voies praticables depuis un navigateur.

* **Appareil photo du mobile** (explorateur, bouton « Numériser ») : les photos
  sont assemblées côté serveur en un PDF multipage.
* **Dossier de dépôt surveillé** : le scanner réseau écrit (SMB/FTP) dans un
  répertoire du serveur ; une tâche planifiée y crée les documents ECM.
* **Scan vers e-mail** : les pièces reçues sur l'alias ``ecm-scan`` deviennent
  des documents.
"""
import base64
import io
import logging
import os
import re
import time

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)
PARAM = 'aite_ecm.'
SCAN_IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'tif', 'tiff', 'bmp', 'webp', 'gif')


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    # ================================================================== #
    # Photos → PDF
    # ================================================================== #
    @api.model
    def _images_to_pdf(self, images):
        """Assemble des images (octets) en un PDF multipage (Pillow)."""
        from PIL import Image
        pages = []
        for raw in images:
            img = Image.open(io.BytesIO(raw))
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            max_side = 2000                     # limite le poids des photos
            if max(img.size) > max_side:
                ratio = max_side / float(max(img.size))
                img = img.resize((int(img.width * ratio), int(img.height * ratio)))
            pages.append(img)
        if not pages:
            return b''
        buf = io.BytesIO()
        pages[0].save(buf, format='PDF', save_all=True, append_images=pages[1:],
                      resolution=150.0)
        return buf.getvalue()

    @api.model
    def _scan_document_name(self):
        return _("Numérisation du %s") % fields.Datetime.context_timestamp(
            self, fields.Datetime.now()).strftime('%d/%m/%Y %H:%M')

    # ================================================================== #
    # Dossier de dépôt surveillé
    # ================================================================== #
    @api.model
    def _hotfolder_params(self):
        get = self.env['ir.config_parameter'].sudo().get_param
        return {
            'path': (get(PARAM + 'hotfolder_path') or '').strip(),
            'folder_id': int(get(PARAM + 'hotfolder_folder_id') or 0),
            'type_id': int(get(PARAM + 'hotfolder_type_id') or 0),
            'user_id': int(get(PARAM + 'hotfolder_user_id') or 0),
            'min_age': int(get(PARAM + 'hotfolder_min_age', 30) or 30),
        }

    @api.model
    def _cron_hotfolder_import(self):
        """Importe les fichiers déposés par le scanner réseau."""
        p = self._hotfolder_params()
        path = p['path']
        if not path or not os.path.isabs(path) or not os.path.isdir(path):
            return False
        done_dir = os.path.join(path, 'traites')
        error_dir = os.path.join(path, 'erreurs')
        for d in (done_dir, error_dir):
            os.makedirs(d, exist_ok=True)
        Doc = self.env['aite.ecm.document']
        if p['user_id']:
            user = self.env['res.users'].browse(p['user_id']).exists()
            if user:
                Doc = Doc.with_user(user).sudo()
        allowed = set(self.ALLOWED_EXTENSIONS)
        imported = 0
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if not os.path.isfile(full) or name.startswith('.'):
                continue
            ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
            if ext not in allowed:
                continue
            if time.time() - os.path.getmtime(full) < p['min_age']:
                continue                        # encore en cours d'écriture
            try:
                with open(full, 'rb') as fh:
                    raw = fh.read()
                with self.env.cr.savepoint():
                    title = re.sub(r'[_\-]+', ' ', name.rsplit('.', 1)[0]).strip() \
                        or self._scan_document_name()
                    doc = Doc.create({
                        'name': title,
                        'folder_id': p['folder_id'] or False,
                        'type_id': p['type_id'] or False,
                    })
                    doc.with_context(audit_source='system').add_version(
                        name, base64.b64encode(raw), _("Dossier de dépôt"))
                target = os.path.join(done_dir, "%s_%s" % (
                    time.strftime('%Y%m%d%H%M%S'), name))
                os.replace(full, target)
                imported += 1
            except Exception as exc:  # noqa: BLE001 — fichier suivant
                _logger.warning("[ecm] dépôt %s en erreur : %s", name, exc)
                try:
                    os.replace(full, os.path.join(error_dir, name))
                except OSError:
                    pass
        if imported:
            _logger.info("[ecm] dossier de dépôt : %d fichier(s) importé(s)", imported)
        return imported

    # ================================================================== #
    # Scan vers e-mail (alias)
    # ================================================================== #
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Un e-mail reçu sur l'alias ECM crée un document par pièce jointe
        (la première devient la version du document créé ici)."""
        custom_values = dict(custom_values or {})
        subject = (msg_dict.get('subject') or '').strip()
        custom_values.setdefault('name', subject or self._scan_document_name())
        attachments = list(msg_dict.get('attachments') or [])
        usable = []
        for att in attachments:
            fname = att[0] if isinstance(att, (tuple, list)) else getattr(att, 'fname', '')
            content = att[1] if isinstance(att, (tuple, list)) else getattr(att, 'content', b'')
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext in self.ALLOWED_EXTENSIONS and content:
                usable.append((fname, content))
        doc = super().message_new(msg_dict, custom_values)
        for i, (fname, content) in enumerate(usable):
            if isinstance(content, str):
                content = content.encode('utf-8')
            datas = base64.b64encode(content)
            target = doc
            if i > 0:
                target = self.create({
                    'name': "%s — %s" % (custom_values['name'], fname),
                    'folder_id': doc.folder_id.id, 'type_id': doc.type_id.id,
                    'owner_id': doc.owner_id.id})
            target.with_context(audit_source='system').add_version(
                fname, datas, _("Reçu par e-mail"))
        return doc
