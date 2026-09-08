# -*- coding: utf-8 -*-
"""Mixin de synchronisation Nextcloud pour un modèle de document versionné.

Le modèle concret fournit :

* ``latest_version_id`` (avec ``attachment_id``), ``add_version(filename,
  datas)`` et ``is_locked`` — c'est le cas des documents ECM et des pièces de
  courrier ;
* :meth:`_nc_target_dir` : dossier Nextcloud de destination (relatif à la
  racine du connecteur) ;
* :meth:`_nc_pull_user` : utilisateur auquel attribuer une version importée.
"""
import base64
import hashlib
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .nextcloud_client import NextcloudClient, NextcloudError, sanitize

_logger = logging.getLogger(__name__)
PARAM = 'aite_ecm_nextcloud.'


class AiteEcmNextcloudMixin(models.AbstractModel):
    _name = 'aite.ecm.nextcloud.mixin'
    _description = "Synchronisation Nextcloud"

    nc_path = fields.Char(string="Chemin Nextcloud", readonly=True, copy=False,
                          help="Chemin du fichier, relatif au dossier racine "
                               "du connecteur.")
    nc_file_id = fields.Char(string="ID fichier Nextcloud", readonly=True,
                             copy=False, index=True)
    nc_etag = fields.Char(string="ETag Nextcloud", readonly=True, copy=False)
    nc_sync_state = fields.Selection(
        selection=[('none', "Non synchronisé"), ('todo', "À envoyer"),
                   ('pull', "À importer"), ('synced', "Synchronisé"),
                   ('conflict', "Conflit"), ('error', "Erreur")],
        string="Nextcloud", default='none', copy=False, readonly=True,
        index=True)
    nc_sync_date = fields.Datetime(string="Dernière synchronisation",
                                   readonly=True, copy=False)
    nc_error = fields.Text(string="Détail Nextcloud", readonly=True, copy=False)
    nc_share_url = fields.Char(string="Lien public Nextcloud", readonly=True,
                               copy=False)
    nc_share_id = fields.Char(readonly=True, copy=False)
    nc_url = fields.Char(string="Ouvrir dans Nextcloud", compute='_compute_nc_url')

    # ================================================================== #
    # Configuration
    # ================================================================== #
    @api.model
    def _nc_params(self):
        get = self.env['ir.config_parameter'].sudo().get_param
        return {
            'url': (get(PARAM + 'url') or '').strip(),
            'user': (get(PARAM + 'user') or '').strip(),
            'password': get(PARAM + 'password') or '',
            'root': (get(PARAM + 'root') or 'AITE ECM').strip('/ '),
            'mode': get(PARAM + 'mode') or 'off',
            'poll': get(PARAM + 'poll', 'True') not in ('False', '0', ''),
            'secret': get(PARAM + 'webhook_secret') or '',
            'sync_courrier': get(PARAM + 'sync_courrier') in ('True', '1'),
            'immediate': get(PARAM + 'immediate', 'True') not in ('False', '0'),
            'share_days': int(get(PARAM + 'share_days', 7) or 7),
            'sync_confidential': get(PARAM + 'sync_confidential') in ('True', '1'),
        }

    @api.model
    def _nc_active(self):
        p = self._nc_params()
        return p['mode'] != 'off' and bool(p['url'] and p['user'])

    @api.model
    def _nc_client(self):
        p = self._nc_params()
        if not (p['url'] and p['user'] and p['password']):
            raise UserError(_(
                "Nextcloud n'est pas configuré : renseignez l'URL, le compte "
                "de service et son mot de passe d'application dans "
                "ECM › Configuration › Paramètres."))
        return NextcloudClient(p['url'], p['user'], p['password'], p['root'])

    def _nc_model_enabled(self):
        """Le modèle est-il concerné par le miroir ? (surcharge courrier)"""
        return True

    @api.depends('nc_file_id')
    def _compute_nc_url(self):
        base = self._nc_params()['url']
        for rec in self:
            rec.nc_url = "%s/f/%s" % (base, rec.nc_file_id) \
                if base and rec.nc_file_id else False

    # ================================================================== #
    # Points d'accroche du modèle concret
    # ================================================================== #
    def _nc_target_dir(self):
        raise NotImplementedError

    def _nc_pull_user(self):
        self.ensure_one()
        return self.create_uid

    def _nc_reference(self):
        self.ensure_one()
        return getattr(self, 'reference', False) or self.display_name

    def _nc_can_pull(self):
        """(autorisé, motif) — un document verrouillé n'est jamais écrasé."""
        self.ensure_one()
        if getattr(self, 'is_locked', False):
            return False, _("document finalisé ou archivé dans Odoo")
        return True, ''

    # ================================================================== #
    # Utilitaires
    # ================================================================== #
    def _nc_latest(self):
        """(nom de fichier, contenu brut) de la dernière version."""
        self.ensure_one()
        version = self.latest_version_id
        if not version or not version.attachment_id:
            return None, None
        raw = base64.b64decode(version.attachment_id.sudo().datas or b'')
        return version.attachment_id.name, raw

    def _nc_target_path(self):
        self.ensure_one()
        name, _raw = self._nc_latest()
        if not name:
            return False
        return "%s/%s" % (self._nc_target_dir().strip('/'), sanitize(name))

    def _nc_mark(self, state, error=None):
        self.sudo().write({'nc_sync_state': state, 'nc_error': error or False,
                           'nc_sync_date': fields.Datetime.now()})

    def _nc_audit(self, action, action_type, detail):
        self.env['aite.courrier.audit.log']._log(
            self.env, action, action_type, self._name, self.id,
            self._nc_reference(), detail, 'nextcloud')

    def _nc_schedule(self, state='todo'):
        """Planifie un envoi (ou un import) si le connecteur est actif."""
        if not self._nc_active():
            return False
        recs = self.filtered(lambda r: r._nc_model_enabled())
        recs.sudo().write({'nc_sync_state': state})
        return bool(recs)

    # ================================================================== #
    # Envoi (Odoo → Nextcloud)
    # ================================================================== #
    def _nc_push(self, client=None):
        self.ensure_one()
        client = client or self._nc_client()
        name, raw = self._nc_latest()
        if not name:
            self._nc_mark('none')
            return False
        target = self._nc_target_path()
        directory = target.rsplit('/', 1)[0]
        client.ensure_dir(directory)
        if self.nc_path and self.nc_path != target:
            try:                       # renommage / reclassement dans Odoo
                client.move(self.nc_path, target)
            except NextcloudError as exc:
                _logger.info("[nextcloud] déplacement impossible (%s), "
                             "nouvel envoi.", exc)
        fileid, etag = client.upload(target, raw)
        self.sudo().write({'nc_path': target, 'nc_file_id': fileid or False,
                           'nc_etag': etag or False, 'nc_sync_state': 'synced',
                           'nc_error': False,
                           'nc_sync_date': fields.Datetime.now()})
        self._nc_audit(_("Envoi vers Nextcloud"), 'ok', target)
        return True

    def _nc_try_push(self, client=None):
        """Envoi tolérant : toute erreur laisse le document « à envoyer »."""
        for rec in self:
            try:
                with self.env.cr.savepoint():
                    rec._nc_push(client)
            except Exception as exc:  # noqa: BLE001 — journalisé, non bloquant
                rec._nc_mark('todo', str(exc))
                _logger.warning("[nextcloud] envoi différé pour %s : %s",
                                rec._nc_reference(), exc)

    def action_nc_push(self):
        if not self._nc_active():
            raise UserError(_("Le connecteur Nextcloud est désactivé."))
        client = self._nc_client()
        for rec in self:
            if rec._nc_model_enabled():
                rec._nc_push(client)
        return True

    # ================================================================== #
    # Import (Nextcloud → Odoo)
    # ================================================================== #
    def _nc_pull(self, client=None, force=False):
        """Importe le fichier Nextcloud comme nouvelle version si son ETag a
        changé. Retourne True si une version a été créée."""
        self.ensure_one()
        if not self.nc_path:
            return False
        client = client or self._nc_client()
        info = client.stat(self.nc_path)
        if info is None:
            self._nc_mark('error', _("Fichier absent de Nextcloud : %s")
                          % self.nc_path)
            return False
        if not force and info['etag'] == self.nc_etag:
            self._nc_mark('synced')
            return False
        allowed, reason = self._nc_can_pull()
        if not allowed:
            self._nc_mark('conflict', _(
                "Fichier modifié dans Nextcloud mais %s : version non "
                "importée.") % reason)
            self._nc_notify_conflict(reason)
            return False
        raw = client.download(self.nc_path)
        latest = self.latest_version_id
        same = latest and getattr(latest, 'sha256', None) \
            and latest.sha256 == hashlib.sha256(raw).hexdigest()
        if same:                      # contenu identique : seul l'ETag a bougé
            self.sudo().write({'nc_etag': info['etag'],
                               'nc_file_id': info['fileid'] or self.nc_file_id,
                               'nc_sync_state': 'synced', 'nc_error': False,
                               'nc_sync_date': fields.Datetime.now()})
            return False
        user = self._nc_pull_user() or self.env.user
        self.with_user(user).sudo().with_context(
            nc_skip_push=True, audit_source='nextcloud').add_version(
            self.nc_path.rsplit('/', 1)[-1], base64.b64encode(raw))
        self.sudo().write({'nc_etag': info['etag'],
                           'nc_file_id': info['fileid'] or self.nc_file_id,
                           'nc_sync_state': 'synced', 'nc_error': False,
                           'nc_sync_date': fields.Datetime.now()})
        self._nc_audit(_("Version importée depuis Nextcloud"), 'ok',
                       _("%s — par %s") % (self.nc_path, user.name))
        if hasattr(self, 'message_post'):
            self.sudo().message_post(body=_(
                "Nouvelle version importée depuis Nextcloud (%s).") % user.name)
        return True

    def _nc_notify_conflict(self, reason):
        self.ensure_one()
        if hasattr(self, 'message_post'):
            self.sudo().message_post(body=_(
                "⚠ Le fichier a été modifié dans Nextcloud mais %s. La "
                "version Odoo reste la référence ; remettez le document en "
                "brouillon puis cliquez « Importer depuis Nextcloud » pour "
                "récupérer la modification.") % reason)

    def _nc_try_pull(self, client=None, force=False):
        for rec in self:
            try:
                with self.env.cr.savepoint():
                    rec._nc_pull(client, force=force)
            except Exception as exc:  # noqa: BLE001
                rec._nc_mark('error', str(exc))
                _logger.warning("[nextcloud] import impossible pour %s : %s",
                                rec._nc_reference(), exc)

    def action_nc_pull(self):
        client = self._nc_client()
        for rec in self:
            rec._nc_pull(client, force=True)
        return True

    # ================================================================== #
    # Navigation et partage
    # ================================================================== #
    def action_nc_open(self):
        self.ensure_one()
        if not self.nc_url:
            raise UserError(_("Ce document n'est pas encore dans Nextcloud : "
                              "cliquez d'abord « Envoyer vers Nextcloud »."))
        return {'type': 'ir.actions.act_url', 'url': self.nc_url,
                'target': 'new'}

    def action_nc_share(self):
        """Lien public Nextcloud (mot de passe aléatoire, expiration par
        défaut) — complémentaire des partages AITE."""
        self.ensure_one()
        client = self._nc_client()
        if not self.nc_path:
            self._nc_push(client)
        params = self._nc_params()
        password = secrets.token_urlsafe(9)
        expire = (fields.Date.context_today(self)
                  + timedelta(days=params['share_days'])).strftime('%Y-%m-%d')
        share = client.create_public_link(
            self.nc_path, password=password, expire_date=expire,
            label=_("AITE ECM — %s") % self._nc_reference())
        self.sudo().write({'nc_share_url': share['url'],
                           'nc_share_id': share['id']})
        self._nc_audit(_("Lien public Nextcloud"), 'info',
                       _("expire le %s") % expire)
        if hasattr(self, 'message_post'):
            self.sudo().message_post(body=_(
                "Lien public Nextcloud créé (expire le %s) : %s<br/>"
                "Mot de passe à transmettre séparément : <b>%s</b>")
                % (expire, share['url'], password))
        return {'type': 'ir.actions.act_url', 'url': share['url'],
                'target': 'new'}

    def action_nc_unshare(self):
        client = self._nc_client()
        for rec in self.filtered('nc_share_id'):
            client.delete_share(rec.nc_share_id)
            rec.sudo().write({'nc_share_url': False, 'nc_share_id': False})
            rec._nc_audit(_("Lien public Nextcloud révoqué"), 'warn', '')
        return True

    # ================================================================== #
    # Tâche planifiée : envois, imports, sondage
    # ================================================================== #
    @api.model
    def _nc_models(self):
        return [m for m in ('aite.ecm.document', 'aite.courrier.document')
                if m in self.env and 'nc_sync_state' in self.env[m]._fields]

    @api.model
    def _nc_cron_sync(self, limit=100):
        if not self._nc_active():
            return False
        params = self._nc_params()
        client = self._nc_client()
        for model in self._nc_models():
            Model = self.env[model].sudo()
            todo = Model.search([('nc_sync_state', '=', 'todo')], limit=limit)
            todo.filtered(lambda r: r._nc_model_enabled())._nc_try_push(client)
            if params['mode'] == 'bidir':
                pull = Model.search([('nc_sync_state', '=', 'pull')],
                                    limit=limit)
                pull._nc_try_pull(client)
        if params['mode'] == 'bidir' and params['poll']:
            self._nc_poll(client)
        return True

    @api.model
    def _nc_poll(self, client):
        """Détecte les fichiers modifiés dans Nextcloud par comparaison des
        ETags dossier par dossier. Court-circuit : l'ETag de la racine ne
        change pas tant que rien ne bouge en dessous."""
        Param = self.env['ir.config_parameter'].sudo()
        root = client.stat('')
        if root is None:
            return False
        if root['etag'] and root['etag'] == Param.get_param(PARAM + 'root_etag'):
            return False
        changed = 0
        for model in self._nc_models():
            Model = self.env[model].sudo()
            docs = Model.search([('nc_sync_state', 'in', ('synced', 'conflict')),
                                 ('nc_path', '!=', False)])
            by_dir = {}
            for doc in docs:
                by_dir.setdefault(doc.nc_path.rsplit('/', 1)[0], []).append(doc)
            for directory, records in by_dir.items():
                try:
                    listing = {i['name']: i for i in client.listdir(directory)}
                except NextcloudError as exc:
                    _logger.warning("[nextcloud] sondage %s : %s", directory, exc)
                    continue
                for doc in records:
                    info = listing.get(doc.nc_path.rsplit('/', 1)[-1])
                    if info and info['etag'] != doc.nc_etag:
                        doc._nc_try_pull(client)
                        changed += 1
        Param.set_param(PARAM + 'root_etag', root['etag'] or '')
        return changed
