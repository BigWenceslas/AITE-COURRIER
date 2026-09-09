# -*- coding: utf-8 -*-
import functools
import json
import logging

from odoo import http, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)
PREFIX = '/api/ecm/v1'


def json_response(data, status=200):
    return request.make_json_response(data, status=status)


def error(message, status=400, code=None):
    return json_response({'error': {'code': code or status,
                                    'message': message}}, status)


def api_route(*urls, methods=('GET',)):
    """Route REST : auth par X-API-Key, exécution avec les droits de
    l'utilisateur, erreurs métier converties en JSON."""
    def decorator(func):
        # ``readonly=False`` : l'authentification par clé d'API et l'audit
        # écrivent, et les points d'entrée POST créent documents et versions.
        # Un curseur en lecture seule ferait échouer toute la requête.
        @http.route([PREFIX + u for u in urls], type='http', auth='none',
                    methods=list(methods) + ['OPTIONS'], csrf=False,
                    save_session=False, readonly=False)
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if request.httprequest.method == 'OPTIONS':
                return request.make_response('', headers=[
                    ('Access-Control-Allow-Methods',
                     'GET, POST, OPTIONS'),
                    ('Access-Control-Allow-Headers',
                     'Content-Type, X-API-Key')])
            key = request.httprequest.headers.get('X-API-Key') \
                or request.httprequest.args.get('api_key')
            if not key:
                return error("Clé d'API manquante (en-tête X-API-Key).", 401)
            uid = request.env['res.users.apikeys'].sudo()._check_credentials(
                scope='rpc', key=key)
            if not uid:
                return error("Clé d'API invalide.", 401)
            request.update_env(user=uid)
            try:
                with request.env.cr.savepoint():
                    return func(self, *args, **kwargs)
            except AccessError as exc:
                return error(str(exc), 403)
            except (UserError, ValidationError) as exc:
                return error(str(exc), 422)
            except ValueError as exc:
                return error(str(exc), 400)
            except Exception as exc:  # noqa: BLE001
                _logger.exception("API ECM : erreur interne")
                return error("Erreur interne : %s" % exc, 500)
        return wrapper
    return decorator


def _body():
    try:
        return json.loads(request.httprequest.get_data(as_text=True) or '{}')
    except ValueError:
        raise ValueError("Corps JSON invalide.")


def _version_data(version):
    if not version:
        return None
    return {'id': version.id, 'version': version.version,
            'file_name': version.file_name, 'size': version.file_size,
            'mimetype': version.mime_type, 'sha256': version.sha256,
            'uploaded_by': version.uploaded_by.name,
            'upload_date': fields.Datetime.to_string(version.upload_date)}


def _document_data(doc, full=False):
    data = {
        'id': doc.id, 'reference': doc.reference, 'name': doc.name,
        'type': {'id': doc.type_id.id, 'code': doc.type_id.code,
                 'name': doc.type_id.name} if doc.type_id else None,
        'folder': {'id': doc.folder_id.id,
                   'path': doc.folder_id.complete_name}
        if doc.folder_id else None,
        'state': doc.state, 'confidentiality': doc.confidentiality_code,
        'owner': doc.owner_id.name, 'tags': doc.tag_ids.mapped('name'),
        'res_model': doc.res_model or None, 'res_id': doc.res_id or None,
        'checked_out_by': doc.checkout_user_id.name or None,
        'latest_version': _version_data(doc.latest_version_id),
        'create_date': fields.Datetime.to_string(doc.create_date),
        'write_date': fields.Datetime.to_string(doc.write_date),
    }
    if full:
        data.update({
            'description': doc.description or '',
            'properties': doc.properties or [],
            'versions': [_version_data(v) for v in doc.version_ids],
            'links': [{'type': l.link_type_id.code, 'target_id': l.target_id.id,
                       'target_reference': l.target_id.reference}
                      for l in doc.link_ids],
        })
    return data


class EcmApiController(http.Controller):

    @api_route('/ping')
    def ping(self, **kw):
        return json_response({'status': 'ok', 'user': request.env.user.name,
                              'version': '18.0.2.0.0'})

    @api_route('/types')
    def types(self, **kw):
        types = request.env['aite.ecm.document.type'].search([])
        return json_response({'items': [
            {'id': t.id, 'code': t.code, 'name': t.name,
             'default_folder_id': t.default_folder_id.id or None,
             'metadata': t.metadata_definition or []} for t in types]})

    @api_route('/folders')
    def folders(self, **kw):
        folders = request.env['aite.ecm.folder'].search([])
        return json_response({'items': [
            {'id': f.id, 'name': f.name, 'path': f.complete_name,
             'parent_id': f.parent_id.id or None} for f in folders]})

    @api_route('/documents')
    def list_documents(self, **kw):
        args = request.httprequest.args
        domain = []
        if args.get('q'):
            domain += ['|', '|', ('reference', 'ilike', args['q']),
                       ('name', 'ilike', args['q']),
                       ('content_fulltext', 'ilike', args['q'])]
        if args.get('type'):
            domain.append(('type_id.code', '=', args['type']))
        if args.get('folder'):
            domain.append(('folder_id', 'child_of', int(args['folder'])))
        if args.get('state'):
            domain.append(('state', '=', args['state']))
        if args.get('res_model'):
            domain.append(('res_model', '=', args['res_model']))
            if args.get('res_id'):
                domain.append(('res_id', '=', int(args['res_id'])))
        limit = min(int(args.get('limit', 50)), 500)
        offset = int(args.get('offset', 0))
        Document = request.env['aite.ecm.document']
        docs = Document.search(domain, limit=limit, offset=offset,
                               order='id desc')
        return json_response({
            'total': Document.search_count(domain), 'limit': limit,
            'offset': offset, 'items': [_document_data(d) for d in docs]})

    @api_route('/documents/<int:doc_id>')
    def get_document(self, doc_id, **kw):
        doc = request.env['aite.ecm.document'].browse(doc_id).exists()
        if not doc:
            return error("Document introuvable.", 404)
        doc.check_access('read')
        return json_response(_document_data(doc, full=True))

    @api_route('/documents', methods=('POST',))
    def create_document(self, **kw):
        body = _body()
        if not body.get('name'):
            raise ValueError("Le champ 'name' est requis.")
        Type = request.env['aite.ecm.document.type']
        doc_type = Type
        if body.get('type_id'):
            doc_type = Type.browse(int(body['type_id']))
        elif body.get('type_code'):
            doc_type = Type.search([('code', '=', body['type_code'])], limit=1)
            if not doc_type:
                raise ValueError("Type inconnu : %s" % body['type_code'])
        vals = {'name': body['name'], 'type_id': doc_type.id or False,
                'folder_id': int(body['folder_id'])
                if body.get('folder_id') else False,
                'description': body.get('description'),
                'res_model': body.get('res_model'),
                'res_id': int(body['res_id']) if body.get('res_id') else False}
        if body.get('properties'):
            vals['properties'] = body['properties']
        if body.get('tags'):
            Tag = request.env['aite.ecm.tag']
            tags = Tag
            for name in body['tags']:
                tags |= Tag.search([('name', '=', name)], limit=1) \
                    or Tag.create({'name': name})
            vals['tag_ids'] = [(6, 0, tags.ids)]
        doc = request.env['aite.ecm.document'].with_context(
            audit_source='api').create(vals)
        file_ = body.get('file') or {}
        if file_.get('content_base64'):
            doc.with_context(audit_source='api').add_version(
                file_.get('filename') or body['name'],
                file_['content_base64'], file_.get('comment'))
        return json_response(_document_data(doc, full=True), 201)

    @api_route('/documents/<int:doc_id>/versions', methods=('POST',))
    def add_version(self, doc_id, **kw):
        doc = request.env['aite.ecm.document'].browse(doc_id).exists()
        if not doc:
            return error("Document introuvable.", 404)
        body = _body()
        if not body.get('content_base64'):
            raise ValueError("Le champ 'content_base64' est requis.")
        version = doc.with_context(audit_source='api').add_version(
            body.get('filename') or doc.file_name or doc.name,
            body['content_base64'], body.get('comment'))
        return json_response(_version_data(version), 201)

    @api_route('/documents/<int:doc_id>/download')
    def download(self, doc_id, **kw):
        doc = request.env['aite.ecm.document'].browse(doc_id).exists()
        if not doc:
            return error("Document introuvable.", 404)
        doc.check_access('read')
        version = doc.latest_version_id
        if not version:
            return error("Aucun fichier.", 404)
        import base64
        raw = base64.b64decode(version.attachment_id.datas or b'')
        return request.make_response(raw, headers=[
            ('Content-Type', version.mime_type or 'application/octet-stream'),
            ('Content-Disposition', http.content_disposition(version.file_name)),
            ('Content-Length', str(len(raw)))])

    @api_route('/openapi.json')
    def openapi(self, **kw):
        return json_response(OPENAPI_SPEC)


DOC_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'}, 'reference': {'type': 'string'},
        'name': {'type': 'string'}, 'state': {'type': 'string'},
        'type': {'type': 'object', 'nullable': True},
        'folder': {'type': 'object', 'nullable': True},
        'confidentiality': {'type': 'string'},
        'latest_version': {'type': 'object', 'nullable': True},
    },
}
OPENAPI_SPEC = {
    'openapi': '3.0.3',
    'info': {'title': 'AITE ECM API', 'version': '1.0.0',
             'description': "API REST de la plateforme AITE ECM (Odoo 18). "
                            "Authentification : en-tête X-API-Key."},
    'servers': [{'url': PREFIX}],
    'components': {
        'securitySchemes': {'ApiKeyAuth': {'type': 'apiKey', 'in': 'header',
                                           'name': 'X-API-Key'}},
        'schemas': {'Document': DOC_SCHEMA}},
    'security': [{'ApiKeyAuth': []}],
    'paths': {
        '/ping': {'get': {'summary': "Test d'authentification",
                          'responses': {'200': {'description': 'OK'}}}},
        '/types': {'get': {'summary': "Types de documents et métadonnées",
                           'responses': {'200': {'description': 'OK'}}}},
        '/folders': {'get': {'summary': "Plan de classement",
                             'responses': {'200': {'description': 'OK'}}}},
        '/documents': {
            'get': {'summary': "Rechercher des documents",
                    'parameters': [
                        {'name': n, 'in': 'query',
                         'schema': {'type': 'string'}}
                        for n in ('q', 'type', 'folder', 'state',
                                  'res_model', 'res_id', 'limit', 'offset')],
                    'responses': {'200': {'description': 'Liste paginée'}}},
            'post': {'summary': "Créer un document (fichier base64 optionnel)",
                     'requestBody': {'required': True, 'content': {
                         'application/json': {'schema': {
                             'type': 'object',
                             'required': ['name'],
                             'properties': {
                                 'name': {'type': 'string'},
                                 'type_code': {'type': 'string'},
                                 'folder_id': {'type': 'integer'},
                                 'description': {'type': 'string'},
                                 'tags': {'type': 'array',
                                          'items': {'type': 'string'}},
                                 'properties': {'type': 'array'},
                                 'res_model': {'type': 'string'},
                                 'res_id': {'type': 'integer'},
                                 'file': {'type': 'object', 'properties': {
                                     'filename': {'type': 'string'},
                                     'content_base64': {'type': 'string'},
                                     'comment': {'type': 'string'}}},
                             }}}}},
                     'responses': {'201': {'description': 'Créé'},
                                   '422': {'description': 'Refus métier'}}}},
        '/documents/{id}': {'get': {
            'summary': "Détail d'un document",
            'parameters': [{'name': 'id', 'in': 'path', 'required': True,
                            'schema': {'type': 'integer'}}],
            'responses': {'200': {'description': 'OK'},
                          '404': {'description': 'Introuvable'}}}},
        '/documents/{id}/versions': {'post': {
            'summary': "Ajouter une version",
            'parameters': [{'name': 'id', 'in': 'path', 'required': True,
                            'schema': {'type': 'integer'}}],
            'requestBody': {'required': True, 'content': {
                'application/json': {'schema': {
                    'type': 'object', 'required': ['content_base64'],
                    'properties': {'filename': {'type': 'string'},
                                   'content_base64': {'type': 'string'},
                                   'comment': {'type': 'string'}}}}}},
            'responses': {'201': {'description': 'Version créée'}}}},
        '/documents/{id}/download': {'get': {
            'summary': "Télécharger la dernière version",
            'parameters': [{'name': 'id', 'in': 'path', 'required': True,
                            'schema': {'type': 'integer'}}],
            'responses': {'200': {'description': 'Fichier'}}}},
    },
}
