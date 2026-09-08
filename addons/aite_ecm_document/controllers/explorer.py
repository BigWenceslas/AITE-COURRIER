# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class EcmExplorerController(http.Controller):
    """Dépôt de fichiers depuis l'explorateur (multipart, un ou plusieurs
    fichiers) : nouveaux documents dans un dossier, ou nouvelle version d'un
    document existant."""

    @http.route('/ecm/explorer/upload', type='http', auth='user',
                methods=['POST'], csrf=True)
    def upload(self, ufile=None, folder_id=None, type_id=None,
               document_id=None, scan=None, **kw):
        files = request.httprequest.files.getlist('ufile')
        Doc = request.env['aite.ecm.document']
        results = []
        if scan and scan not in ('0', 'false') and files:
            # Numérisation : les photos deviennent un PDF multipage
            images = [f.read() for f in files]
            try:
                with request.env.cr.savepoint():
                    pdf = Doc._images_to_pdf(images)
                    vals = {'name': Doc._scan_document_name()}
                    if folder_id and folder_id not in ('false', '0'):
                        vals['folder_id'] = int(folder_id)
                    if type_id and type_id not in ('false', '0'):
                        vals['type_id'] = int(type_id)
                    doc = Doc.create(vals)
                    version = doc.add_version(
                        "scan_%s.pdf" % fields.Datetime.now().strftime('%Y%m%d_%H%M%S'),
                        base64.b64encode(pdf), "Numérisation (%d page(s))" % len(images))
                    results.append({'ok': True, 'id': doc.id, 'reference': doc.reference,
                                    'version': version.version, 'name': version.file_name})
            except Exception as exc:  # noqa: BLE001
                _logger.exception("[ecm] numérisation impossible")
                results.append({'ok': False, 'name': "numérisation",
                                'error': "Numérisation impossible : %s" % exc})
            return request.make_response(
                json.dumps(results), headers=[('Content-Type', 'application/json')])
        for upload in files:
            filename = upload.filename or 'document'
            content = upload.read()
            datas = base64.b64encode(content)
            try:
                with request.env.cr.savepoint():
                    if document_id:
                        doc = Doc.browse(int(document_id)).exists()
                        if not doc:
                            raise UserError("Document introuvable.")
                    else:
                        title = filename.rsplit('.', 1)[0] if '.' in filename \
                            else filename
                        vals = {'name': title}
                        if folder_id and folder_id not in ('false', '0'):
                            vals['folder_id'] = int(folder_id)
                        if type_id and type_id not in ('false', '0'):
                            vals['type_id'] = int(type_id)
                        doc = Doc.create(vals)
                    version = doc.add_version(filename, datas)
                    results.append({'ok': True, 'id': doc.id,
                                    'reference': doc.reference,
                                    'version': version.version,
                                    'name': filename})
            except (UserError, ValidationError, AccessError) as exc:
                results.append({'ok': False, 'name': filename,
                                'error': str(exc)})
            except Exception as exc:  # noqa: BLE001
                _logger.exception("[ecm] dépôt impossible : %s", filename)
                results.append({'ok': False, 'name': filename,
                                'error': "Erreur interne : %s" % exc})
        return request.make_response(
            json.dumps(results), headers=[('Content-Type', 'application/json')])
