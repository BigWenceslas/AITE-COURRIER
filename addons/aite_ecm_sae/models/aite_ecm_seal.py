# -*- coding: utf-8 -*-
"""Valeur probante : scellement des versions et **journal de preuve chaîné**.

Chaque événement significatif (dépôt d'une version, finalisation, archivage,
vérification, élimination) produit un **sceau** : une empreinte SHA-256 qui
couvre à la fois le contenu du fichier, les données de l'événement **et
l'empreinte du sceau précédent**. Modifier ou supprimer un maillon rompt la
chaîne, ce qui est détectable — c'est le principe des journaux inaltérables
attendus par NF Z42-013 / ISO 14641.

Horodatage : par défaut, l'heure du serveur signée avec une clé propre à la
base (HMAC) ; en option, un jeton RFC 3161 délivré par une autorité tierce.
"""
import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SECRET_PARAM = 'aite_ecm_sae.seal_secret'
TSA_PARAM = 'aite_ecm_sae.tsa_url'
EVENTS = [
    ('version', "Dépôt d'une version"),
    ('final', "Finalisation"),
    ('archive', "Archivage"),
    ('check', "Vérification d'intégrité"),
    ('dispose', "Élimination"),
    ('export', "Export d'archives"),
]


class AiteEcmSeal(models.Model):
    """Un maillon du journal de preuve. Aucune modification n'est possible
    après création (write et unlink refusés)."""

    _name = 'aite.ecm.seal'
    _description = "Sceau — journal de preuve"
    _order = 'id'

    document_id = fields.Many2one(
        comodel_name='aite.ecm.document', string="Document", required=True,
        ondelete='restrict', index=True)
    document_reference = fields.Char(string="Référence", required=True,
                                     index=True)
    version_id = fields.Many2one(
        comodel_name='aite.ecm.document.version', string="Version",
        ondelete='set null')
    version_label = fields.Char(string="Version")
    event = fields.Selection(selection=EVENTS, string="Événement",
                             required=True, index=True)
    content_sha256 = fields.Char(string="Empreinte du fichier")
    previous_hash = fields.Char(string="Empreinte du sceau précédent")
    seal_hash = fields.Char(string="Empreinte du sceau", required=True,
                            index=True)
    timestamp = fields.Datetime(string="Horodatage", required=True)
    timestamp_token = fields.Text(string="Jeton d'horodatage")
    timestamp_source = fields.Selection(
        selection=[('internal', "Interne (clé du serveur)"),
                   ('rfc3161', "Autorité tierce (RFC 3161)")],
        string="Source", default='internal', required=True)
    user_id = fields.Many2one(comodel_name='res.users', string="Par",
                              required=True)
    detail = fields.Char(string="Détail")
    payload = fields.Text(string="Données scellées", readonly=True)

    # ------------------------------------------------------------------ #
    # Immuabilité
    # ------------------------------------------------------------------ #
    def write(self, vals):
        raise UserError(_(
            "Le journal de preuve est inaltérable : un sceau ne se modifie "
            "pas."))

    def unlink(self):
        raise UserError(_(
            "Le journal de preuve est inaltérable : un sceau ne se supprime "
            "pas."))

    # ------------------------------------------------------------------ #
    # Clé et horodatage
    # ------------------------------------------------------------------ #
    @api.model
    def _secret(self):
        Param = self.env['ir.config_parameter'].sudo()
        secret = Param.get_param(SECRET_PARAM)
        if not secret:
            secret = secrets.token_hex(32)
            Param.set_param(SECRET_PARAM, secret)
        return secret.encode()

    @api.model
    def _timestamp_token(self, seal_hash, moment):
        """Jeton d'horodatage : HMAC de l'empreinte et de l'instant, avec la
        clé de la base (source « interne »)."""
        message = "%s|%s" % (seal_hash, fields.Datetime.to_string(moment))
        return hmac.new(self._secret(), message.encode(),
                        hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------ #
    # Création d'un maillon
    # ------------------------------------------------------------------ #
    @api.model
    def _last(self):
        return self.sudo().search([], order='id desc', limit=1)

    @api.model
    def seal(self, document, event, version=None, detail=''):
        """Ajoute un maillon au journal ; retourne le sceau."""
        version = version or (document.latest_version_id if event != 'dispose'
                              else document.latest_version_id)
        moment = fields.Datetime.now()
        previous = self._last()
        payload = {
            'reference': document.reference,
            'document_id': document.id,
            'event': event,
            'version': version.version if version else None,
            'content_sha256': version.sha256 if version else None,
            'timestamp': fields.Datetime.to_string(moment),
            'user': self.env.user.login,
            'detail': detail or '',
            'previous_hash': previous.seal_hash if previous else '',
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        seal_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        values = {
            'document_id': document.id,
            'document_reference': document.reference or str(document.id),
            'version_id': version.id if version else False,
            'version_label': version.version if version else False,
            'event': event,
            'content_sha256': version.sha256 if version else False,
            'previous_hash': previous.seal_hash if previous else False,
            'seal_hash': seal_hash,
            'timestamp': moment,
            'user_id': self.env.user.id,
            'detail': detail or '',
            'payload': raw,
        }
        token, source = self._external_timestamp(seal_hash, moment)
        values.update({'timestamp_token': token, 'timestamp_source': source})
        return self.sudo().create(values)

    @api.model
    def _external_timestamp(self, seal_hash, moment):
        """Jeton RFC 3161 si une autorité est configurée, sinon jeton interne."""
        url = (self.env['ir.config_parameter'].sudo().get_param(TSA_PARAM)
               or '').strip()
        if not url:
            return self._timestamp_token(seal_hash, moment), 'internal'
        try:
            import requests
            from rfc3161ng import RemoteTimestamper       # dépendance optionnelle
            timestamper = RemoteTimestamper(url, hashname='sha256')
            token = timestamper(data=seal_hash.encode())
            return base64.b64encode(token).decode(), 'rfc3161'
        except Exception as exc:  # noqa: BLE001 — repli sur l'horodatage interne
            _logger.warning("[sae] horodatage RFC 3161 indisponible : %s", exc)
            return self._timestamp_token(seal_hash, moment), 'internal'

    # ------------------------------------------------------------------ #
    # Vérification
    # ------------------------------------------------------------------ #
    @api.model
    def verify_chain(self, limit=None):
        """Recalcule toute la chaîne ; retourne la liste des ruptures."""
        seals = self.sudo().search([], order='id', limit=limit)
        problems = []
        previous_hash = ''
        for seal in seals:
            try:
                payload = json.loads(seal.payload or '{}')
            except ValueError:
                problems.append({'seal': seal.id, 'reference': seal.document_reference,
                                 'problem': _("données scellées illisibles")})
                previous_hash = seal.seal_hash
                continue
            expected = hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=False)
                .encode('utf-8')).hexdigest()
            if expected != seal.seal_hash:
                problems.append({'seal': seal.id,
                                 'reference': seal.document_reference,
                                 'problem': _("sceau altéré")})
            if (seal.previous_hash or '') != previous_hash:
                problems.append({'seal': seal.id,
                                 'reference': seal.document_reference,
                                 'problem': _("chaînage rompu")})
            if seal.timestamp_source == 'internal' and seal.timestamp_token:
                if not hmac.compare_digest(
                        seal.timestamp_token,
                        self._timestamp_token(seal.seal_hash, seal.timestamp)):
                    problems.append({'seal': seal.id,
                                     'reference': seal.document_reference,
                                     'problem': _("horodatage invalide")})
            previous_hash = seal.seal_hash
        return problems

    @api.model
    def verify_documents(self, documents=None):
        """Compare l'empreinte enregistrée et le contenu réel des fichiers."""
        Document = self.env['aite.ecm.document'].sudo()
        documents = documents if documents is not None else Document.search(
            [('version_ids', '!=', False)])
        problems = []
        for doc in documents:
            for version in doc.version_ids:
                if not version.sha256:
                    continue
                raw = base64.b64decode(version.attachment_id.sudo().datas or b'')
                if hashlib.sha256(raw).hexdigest() != version.sha256:
                    problems.append({'document': doc.id,
                                     'reference': doc.reference,
                                     'version': version.version,
                                     'problem': _("contenu modifié hors ECM")})
        return problems

    @api.model
    def _cron_verify(self):
        """Contrôle périodique : chaîne + fichiers ; alerte les managers en
        cas d'anomalie."""
        problems = self.verify_chain() + self.verify_documents()
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param('aite_ecm_sae.last_check',
                        fields.Datetime.to_string(fields.Datetime.now()))
        Param.set_param('aite_ecm_sae.last_check_problems', len(problems))
        if problems:
            _logger.error("[sae] %d anomalie(s) d'intégrité : %s",
                          len(problems), problems[:5])
            self.env['aite.courrier.audit.log']._log(
                self.env, _("Anomalie d'intégrité"), 'err', 'aite.ecm.seal',
                0, '', _("%d anomalie(s) détectée(s)") % len(problems),
                'system')
        else:
            _logger.info("[sae] intégrité vérifiée : aucune anomalie")
        return True
