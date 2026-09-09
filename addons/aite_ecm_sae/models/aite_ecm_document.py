# -*- coding: utf-8 -*-
"""Le document ECM sous l'angle de la valeur probante : scellement
automatique, copie de préservation PDF/A, attestation d'intégrité."""
import base64
import logging
import subprocess
import tempfile
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
PDFA_SOURCES = ('doc', 'docx', 'odt', 'rtf', 'txt', 'xls', 'xlsx', 'ods',
                'ppt', 'pptx', 'odp', 'pdf', 'jpg', 'jpeg', 'png', 'tif',
                'tiff')


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    seal_ids = fields.One2many(
        comodel_name='aite.ecm.seal', inverse_name='document_id',
        string="Journal de preuve", readonly=True)
    seal_count = fields.Integer(compute='_compute_seal_count')
    last_seal_hash = fields.Char(string="Dernier sceau",
                                 compute='_compute_seal_count')
    integrity_state = fields.Selection(
        selection=[('unknown', "Non vérifiée"), ('ok', "Intègre"),
                   ('broken', "Anomalie")],
        string="Intégrité", default='unknown', readonly=True, copy=False)
    integrity_date = fields.Datetime(string="Vérifiée le", readonly=True,
                                     copy=False)
    pdfa_version_id = fields.Many2one(
        comodel_name='aite.ecm.document.version',
        string="Copie de préservation (PDF/A)", readonly=True, copy=False)

    @api.depends('seal_ids')
    def _compute_seal_count(self):
        for doc in self:
            seals = doc.seal_ids.sorted('id')
            doc.seal_count = len(seals)
            doc.last_seal_hash = seals[-1].seal_hash if seals else False

    # ------------------------------------------------------------------ #
    # Scellement automatique
    # ------------------------------------------------------------------ #
    def add_version(self, filename, datas, comment=False):
        version = super().add_version(filename, datas, comment)
        self.env['aite.ecm.seal'].seal(self, 'version', version,
                                       detail=filename)
        return version

    def action_mark_final(self):
        res = super().action_mark_final()
        for doc in self:
            self.env['aite.ecm.seal'].seal(doc, 'final',
                                           detail=_("Finalisé"))
        return res

    def action_mark_archived(self):
        res = super().action_mark_archived()
        for doc in self:
            self.env['aite.ecm.seal'].seal(doc, 'archive',
                                           detail=_("Archivé"))
        return res

    def unlink(self):
        """Un dernier sceau est posé avant la destruction (le journal
        conserve la preuve de ce qui a existé)."""
        for doc in self:
            if doc.seal_ids:
                self.env['aite.ecm.seal'].seal(
                    doc, 'dispose', detail=_("Document éliminé (%s)")
                    % (doc.latest_version_id.sha256 or ''))
        # les sceaux ne sont pas supprimables : on détache le lien
        self.env.cr.execute(
            "UPDATE aite_ecm_seal SET document_id = NULL WHERE document_id IN %s",
            (tuple(self.ids),)) if self.ids else None
        return super().unlink()

    # ------------------------------------------------------------------ #
    # Vérification
    # ------------------------------------------------------------------ #
    def action_verify_integrity(self):
        """Vérifie les fichiers et la portion de chaîne du document."""
        Seal = self.env['aite.ecm.seal']
        for doc in self:
            problems = Seal.verify_documents(doc)
            chain = [p for p in Seal.verify_chain()
                     if p.get('reference') == doc.reference]
            state = 'ok' if not (problems or chain) else 'broken'
            doc.sudo().write({'integrity_state': state,
                              'integrity_date': fields.Datetime.now()})
            Seal.seal(doc, 'check', detail=_("Vérification : %s")
                      % (_("intègre") if state == 'ok'
                         else _("anomalie détectée")))
            doc.message_post(body=_("Vérification d'intégrité : %s") % (
                _("document intègre, chaîne de preuve cohérente.")
                if state == 'ok' else
                _("<b>anomalie détectée</b> — %s") % (problems or chain)))
        return True

    def action_proof_report(self):
        """Attestation d'intégrité (PDF) du document."""
        self.ensure_one()
        return self.env.ref('aite_ecm_sae.report_proof').report_action(self)

    def action_view_seals(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'name': _("Journal de preuve — %s") % self.reference,
                'res_model': 'aite.ecm.seal', 'view_mode': 'list,form',
                'domain': [('document_id', '=', self.id)]}

    # ------------------------------------------------------------------ #
    # Copie de préservation PDF/A
    # ------------------------------------------------------------------ #
    @api.model
    def _pdfa_convert(self, raw, extension):
        """Convertit en PDF/A-2b via LibreOffice ; retourne None si l'outil
        n'est pas disponible."""
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.%s" % extension)
            with open(source, 'wb') as fh:
                fh.write(raw)
            try:
                subprocess.run(
                    ['soffice', '--headless', '--norestore', '--convert-to',
                     'pdf:writer_pdf_Export:{"SelectPdfVersion":{"type":"long",'
                     '"value":"2"}}', '--outdir', tmp, source],
                    check=True, capture_output=True, timeout=180)
            except (OSError, subprocess.SubprocessError) as exc:
                _logger.warning("[sae] conversion PDF/A impossible : %s", exc)
                return None
            target = os.path.join(tmp, "source.pdf")
            if not os.path.exists(target):
                return None
            with open(target, 'rb') as fh:
                return fh.read()

    def action_create_pdfa(self):
        """Ajoute la copie de préservation au document (nouvelle version)."""
        for doc in self:
            version = doc.latest_version_id
            if not version:
                raise UserError(_("Aucun fichier à convertir."))
            ext = (version.file_extension or '').lower()
            if ext not in PDFA_SOURCES:
                raise UserError(_(
                    "Format non convertible en PDF/A : %s", ext or '?'))
            raw = base64.b64decode(version.attachment_id.sudo().datas or b'')
            pdfa = doc._pdfa_convert(raw, ext)
            if not pdfa:
                raise UserError(_(
                    "La conversion PDF/A a échoué : LibreOffice (soffice) "
                    "doit être installé sur le serveur."))
            base = (version.file_name or doc.name).rsplit('.', 1)[0]
            new_version = doc.sudo().with_context(
                audit_source='system').add_version(
                "%s_PDFA.pdf" % base, base64.b64encode(pdfa),
                _("Copie de préservation PDF/A"))
            doc.sudo().write({'pdfa_version_id': new_version.id})
            doc._audit(doc, _("Copie PDF/A créée"), 'ok', new_version.version)
        return True

    @api.model
    def _cron_pdfa(self, limit=20):
        """Génère les copies de préservation manquantes des documents
        archivés dont la conservation est définitive ou longue."""
        domain = [('pdfa_version_id', '=', False), ('state', '=', 'archived'),
                  ('version_ids', '!=', False)]
        if 'retention_state' in self._fields:
            domain.append(('retention_state', 'in',
                           ('permanent', 'intermediate')))
        for doc in self.sudo().search(domain, limit=limit):
            try:
                with self.env.cr.savepoint():
                    doc.action_create_pdfa()
            except Exception as exc:  # noqa: BLE001
                _logger.info("[sae] PDF/A différé pour %s : %s",
                             doc.reference, exc)
        return True
