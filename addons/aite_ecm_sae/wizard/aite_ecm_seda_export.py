# -*- coding: utf-8 -*-
"""Export de paquets d'archives (esprit SEDA / OAIS).

Le paquet est un ZIP contenant :

* ``manifest.xml`` — bordereau de transfert : identité du service versant,
  arborescence des unités d'archives, métadonnées, empreintes SHA-256 ;
* ``content/`` — les fichiers (dernière version, ou toutes les versions) ;
* ``journal_de_preuve.json`` — les sceaux des documents exportés ;
* ``LISEZMOI.txt`` — description du paquet et mode d'emploi.

Objectif : **réversibilité** — pouvoir confier le fonds à un SAE tiers ou aux
Archives nationales, ou simplement prouver ce qui a été conservé.
"""
import base64
import hashlib
import io
import json
import zipfile
from xml.sax.saxutils import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

SEDA_NS = "fr:gouv:culture:archivesdefrance:seda:v2.1"


class AiteEcmSedaExport(models.TransientModel):
    _name = 'aite.ecm.seda.export'
    _description = "Export de paquet d'archives"

    name = fields.Char(string="Nom du transfert", required=True,
                       default=lambda self: _("Transfert du %s")
                       % fields.Date.context_today(self))
    scope = fields.Selection(
        selection=[('selection', "Documents sélectionnés"),
                   ('folder', "Un dossier de classement"),
                   ('permanent', "Documents à conservation définitive"),
                   ('expired', "Documents échus")],
        string="Périmètre", default='selection', required=True)
    folder_id = fields.Many2one(comodel_name='aite.ecm.folder',
                                string="Dossier")
    include_all_versions = fields.Boolean(
        string="Inclure toutes les versions", default=False,
        help="Sinon, seule la dernière version de chaque document est incluse.")
    archival_agency = fields.Char(string="Service d'archives destinataire",
                                  default="Service d'archives")
    transferring_agency = fields.Char(string="Service versant")
    document_ids = fields.Many2many(comodel_name='aite.ecm.document',
                                    string="Documents")
    document_count = fields.Integer(compute='_compute_document_count')
    file_name = fields.Char(readonly=True)
    file_data = fields.Binary(string="Paquet", readonly=True, attachment=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'aite.ecm.document':
            ids = self.env.context.get('active_ids') or []
            res.update({'document_ids': [(6, 0, ids)], 'scope': 'selection'})
        company = self.env.company
        res.setdefault('transferring_agency', company.name)
        return res

    @api.depends('scope', 'folder_id', 'document_ids')
    def _compute_document_count(self):
        for wizard in self:
            wizard.document_count = len(wizard._documents())

    def _documents(self):
        self.ensure_one()
        Document = self.env['aite.ecm.document'].sudo()
        if self.scope == 'selection':
            return self.document_ids
        if self.scope == 'folder':
            return Document.search([('folder_id', 'child_of', self.folder_id.id)]) \
                if self.folder_id else Document.browse()
        if self.scope == 'permanent':
            return Document.search([('retention_state', '=', 'permanent')]) \
                if 'retention_state' in Document._fields else Document.browse()
        return Document.search([('retention_state', '=', 'expired')]) \
            if 'retention_state' in Document._fields else Document.browse()

    # ------------------------------------------------------------------ #
    # Manifeste
    # ------------------------------------------------------------------ #
    def _manifest(self, entries):
        """Bordereau de transfert (structure inspirée du SEDA 2.1)."""
        self.ensure_one()
        now = fields.Datetime.to_string(fields.Datetime.now())
        parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<ArchiveTransfer xmlns="%s">' % SEDA_NS,
                 '<Date>%s</Date>' % escape(now),
                 '<MessageIdentifier>%s</MessageIdentifier>' % escape(self.name),
                 '<ArchivalAgency><Identifier>%s</Identifier></ArchivalAgency>'
                 % escape(self.archival_agency or ''),
                 '<TransferringAgency><Identifier>%s</Identifier>'
                 '</TransferringAgency>' % escape(self.transferring_agency or ''),
                 '<DataObjectPackage>']
        for entry in entries:
            parts.append(
                '<BinaryDataObject id="%s">'
                '<Uri>%s</Uri>'
                '<MessageDigest algorithm="SHA-256">%s</MessageDigest>'
                '<Size>%d</Size>'
                '<FormatIdentification><FormatLitteral>%s</FormatLitteral>'
                '</FormatIdentification>'
                '<FileInfo><Filename>%s</Filename>'
                '<LastModified>%s</LastModified></FileInfo>'
                '</BinaryDataObject>' % (
                    escape(entry['id']), escape(entry['uri']),
                    escape(entry['sha256'] or ''), entry['size'],
                    escape(entry['mimetype'] or ''), escape(entry['filename']),
                    escape(entry['modified'] or '')))
        parts.append('<DescriptiveMetadata>')
        for entry in entries:
            parts.append(
                '<ArchiveUnit id="AU_%s"><Content>'
                '<DescriptionLevel>Item</DescriptionLevel>'
                '<Title>%s</Title>'
                '<OriginatingSystemId>%s</OriginatingSystemId>'
                '<CustodialHistory><CustodialHistoryItem>%s'
                '</CustodialHistoryItem></CustodialHistory>'
                '<Keyword><KeywordContent>%s</KeywordContent></Keyword>'
                '<CreatedDate>%s</CreatedDate>'
                '</Content><DataObjectReference><DataObjectReferenceId>%s'
                '</DataObjectReferenceId></DataObjectReference></ArchiveUnit>'
                % (escape(entry['id']), escape(entry['title']),
                   escape(entry['reference']), escape(entry['history']),
                   escape(entry['folder'] or ''), escape(entry['created'] or ''),
                   escape(entry['id'])))
        parts.append('</DescriptiveMetadata>')
        parts.append('<ManagementMetadata><AppraisalRule><Rule>%s</Rule>'
                     '</AppraisalRule></ManagementMetadata>'
                     % escape(_("Voir la colonne « conservation » de chaque unité")))
        parts.append('</DataObjectPackage></ArchiveTransfer>')
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    # Construction du paquet
    # ------------------------------------------------------------------ #
    def action_export(self):
        self.ensure_one()
        documents = self._documents()
        if not documents:
            raise UserError(_("Aucun document dans le périmètre choisi."))
        buffer = io.BytesIO()
        entries, seals = [], []
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for doc in documents:
                versions = doc.version_ids if self.include_all_versions \
                    else doc.latest_version_id
                for version in versions:
                    raw = base64.b64decode(
                        version.attachment_id.sudo().datas or b'')
                    filename = "%s_%s_%s" % (doc.reference, version.version,
                                             version.file_name or 'document')
                    path = "content/%s" % filename
                    archive.writestr(path, raw)
                    entries.append({
                        'id': "%s_%s" % (doc.reference, version.version),
                        'uri': path,
                        'sha256': version.sha256
                        or hashlib.sha256(raw).hexdigest(),
                        'size': len(raw),
                        'mimetype': version.mime_type or '',
                        'filename': version.file_name or filename,
                        'modified': fields.Datetime.to_string(version.upload_date),
                        'title': doc.name,
                        'reference': doc.reference,
                        'folder': doc.folder_id.complete_name or '',
                        'created': fields.Datetime.to_string(doc.create_date),
                        'history': _("Versé depuis AITE ECM ; règle : %s")
                        % (getattr(doc, 'retention_rule_id', False)
                           and doc.retention_rule_id.name or _("non définie")),
                    })
                if 'seal_ids' in doc._fields:
                    for seal in doc.seal_ids:
                        seals.append({
                            'reference': seal.document_reference,
                            'event': seal.event,
                            'version': seal.version_label,
                            'content_sha256': seal.content_sha256,
                            'previous_hash': seal.previous_hash,
                            'seal_hash': seal.seal_hash,
                            'timestamp': fields.Datetime.to_string(seal.timestamp),
                            'timestamp_token': seal.timestamp_token,
                            'timestamp_source': seal.timestamp_source,
                            'user': seal.user_id.login,
                            'detail': seal.detail,
                        })
            manifest = self._manifest(entries)
            archive.writestr('manifest.xml', manifest)
            archive.writestr('journal_de_preuve.json',
                             json.dumps(seals, indent=2, ensure_ascii=False))
            archive.writestr('LISEZMOI.txt', self._readme(entries, seals))
        data = buffer.getvalue()
        self.write({
            'file_data': base64.b64encode(data),
            'file_name': "%s.zip" % (self.name or 'transfert').replace(' ', '_'),
        })
        for doc in documents:
            if 'seal_ids' in doc._fields:
                self.env['aite.ecm.seal'].seal(
                    doc, 'export', detail=_("Paquet d'archives « %s »") % self.name)
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def _readme(self, entries, seals):
        self.ensure_one()
        return "\n".join([
            "Paquet d'archives — %s" % self.name,
            "Produit par AITE ECM le %s" % fields.Datetime.now(),
            "Service versant : %s" % (self.transferring_agency or ''),
            "Service d'archives : %s" % (self.archival_agency or ''),
            "",
            "Contenu :",
            "  manifest.xml            bordereau de transfert (structure SEDA 2.1),",
            "                          métadonnées et empreintes SHA-256 ;",
            "  content/                %d fichier(s) ;" % len(entries),
            "  journal_de_preuve.json  %d sceau(x) : chaîne d'empreintes et"
            % len(seals),
            "                          horodatages attestant l'intégrité.",
            "",
            "Vérification : pour chaque fichier de content/, recalculer",
            "l'empreinte SHA-256 et la comparer à celle du manifeste. Le",
            "journal de preuve chaîne chaque événement à l'empreinte du",
            "précédent : toute rupture signale une altération.",
        ])
