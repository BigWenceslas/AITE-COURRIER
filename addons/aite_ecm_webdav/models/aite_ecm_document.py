# -*- coding: utf-8 -*-
from urllib.parse import quote, urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import UserError

OFFICE_SCHEMES = {
    'ms-word': ('doc', 'docx', 'docm', 'dot', 'dotx', 'odt', 'rtf', 'txt'),
    'ms-excel': ('xls', 'xlsx', 'xlsm', 'xlt', 'ods', 'csv'),
    'ms-powerpoint': ('ppt', 'pptx', 'pptm', 'odp'),
}
OFFICE_LABELS = {'ms-word': "Word", 'ms-excel': "Excel", 'ms-powerpoint': "PowerPoint"}


class AiteEcmDocument(models.Model):
    _inherit = 'aite.ecm.document'

    webdav_url = fields.Char(string="Adresse WebDAV", compute='_compute_webdav_url')
    office_target = fields.Char(
        string="Adresse pour les applications de bureau",
        compute='_compute_webdav_url',
        help="Adresse confiée à Word, Excel, PowerPoint ou LibreOffice : "
             "l'URL WebDAV, ou le chemin du lecteur réseau Windows selon les "
             "paramètres système « aite_ecm.office_uri_mode » et "
             "« aite_ecm.office_unc_root ».")
    office_app = fields.Char(string="Application Office", compute='_compute_webdav_url')
    office_uri = fields.Char(string="Ouvrir dans Office", compute='_compute_webdav_url')

    @api.model
    def _webdav_base(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return "%s/webdav/aite_ecm" % base.rstrip('/')

    @api.model
    def _office_uri_mode(self):
        r"""Forme d'adresse remise aux applications de bureau.

        ``url`` (défaut) sert l'URL WebDAV ; ``unc`` sert le chemin UNC du
        lecteur réseau Windows.

        Le mode ``unc`` a été introduit pour les instances servies en
        **http**, contre le blocage d'Office — « Microsoft Office a bloqué
        l'accès… car la source utilise une méthode de connexion qui peut être
        non sécurisée ». Il ne le contourne pas. Depuis la version 2311, Word,
        Excel et PowerPoint sous Windows bloquent par défaut toute invite
        d'authentification Basic : le blocage vise la méthode, pas le
        transport, et vaut **en https comme en http**. Un fichier ouvert
        depuis le lecteur réseau n'y échappe pas : Word convertit le chemin
        (``X:\…``, ``\\hote@8069\…``) en adresse http(s) et télécharge
        lui-même le fichier. La spécification Office URI Schemes n'admet
        d'ailleurs, après ``ofe|u|``, que des URI http ou https. Ce mode n'est
        donc plus recommandé ; il reste servi tel quel sur choix explicite, et
        suppose un poste **Windows** dont le lecteur est monté : sur un poste
        macOS ou Linux, et pour LibreOffice qui n'a pas ce blocage, l'URL
        reste la bonne réponse. D'où un choix explicite plutôt qu'une
        détection automatique.

        Le serveur WebDAV d'Odoo n'offrant que Basic, le remède est sur le
        poste : autoriser l'hôte par la stratégie « Allow specified hosts to
        show Basic Authentication prompts to Office apps » (GPO ou Cloud
        Policy), ou par son équivalent registre. Celui-ci s'exécute dans la
        session du compte Windows qui utilise Word (PowerShell administrateur
        si ce compte est administrateur du poste, jamais avec un autre compte :
        ``HKCU`` serait celui de l'autre compte), toutes les applications
        Office fermées ::

            reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f

        Hôtes séparés par « ; », sans ``https://`` ; en production, le nom du
        serveur ; guillemets obligatoires en PowerShell. À la réouverture,
        Word demande des identifiants : login Odoo et mot de passe, ou clé
        d'API. Selon son libellé, la stratégie ne vaut que pour les versions
        d'Office sur abonnement ; une Cloud Policy du tenant ou le Baseline
        Security Mode peuvent primer ; Microsoft ne la recommande qu'à titre
        transitoire.

        HTTPS reste recommandé : il protège le mot de passe et dispense le
        client WebDAV de Windows de ``BasicAuthLevel``. Il ne lève pas ce
        blocage.
        """
        mode = self.env['ir.config_parameter'].sudo().get_param(
            'aite_ecm.office_uri_mode', 'url')
        return 'unc' if mode == 'unc' else 'url'

    @api.model
    def _webdav_unc_root(self):
        r"""Racine WebDAV vue comme un partage réseau Windows.

        ``http://hote:8069``  →  ``\\hote@8069\webdav\aite_ecm``
        ``https://hote``      →  ``\\hote@SSL\webdav\aite_ecm``

        Sans ``DavWWWRoot`` : avec ce mot-clé, le client WebDAV de Windows
        interroge d'abord la racine du site — chez Odoo, la page de
        connexion, pas un dossier WebDAV — et renonce (« Erreur système 5 »,
        constaté au montage sur une instance Windows) ; le même chemin sans
        lui se monte et s'ouvre.

        Le paramètre système ``aite_ecm.office_unc_root`` prend le pas sur
        cette déduction : y mettre ``Z:`` désigne le lecteur monté, ce qui
        évite la zone de sécurité que Windows attribue à ``hote@port``. Cela
        ne lève pas le blocage de l'authentification Basic par Office : depuis
        ``Z:\…``, Word repasse par l'URL WebDAV et s'authentifie lui-même
        (voir ``_office_uri_mode``, qui décrit le remède sur le poste).
        """
        settings = self.env['ir.config_parameter'].sudo()
        # Racine imposée par l'administrateur : lettre du lecteur monté
        # (« Z: »), ou partage nommé autrement que l'URL publique. Windows
        # range « \\hote@8069\… » en zone « Sites sensibles » — il y lit un
        # « utilisateur@hôte » —, ce qu'un chemin de lecteur évite.
        override = (settings.get_param('aite_ecm.office_unc_root') or '').strip()
        if override:
            return override.rstrip('\\/')
        base = settings.get_param('web.base.url', '')
        parts = urlsplit(base)
        host = parts.hostname or 'localhost'
        port = parts.port
        if parts.scheme == 'https':
            server = host + '@SSL' + ('@%d' % port if port and port != 443 else '')
        else:
            server = host + ('@%d' % port if port and port != 80 else '')
        return '\\\\%s\\webdav\\aite_ecm' % server

    @api.depends('folder_id', 'name', 'reference', 'version_ids')
    def _compute_webdav_url(self):
        service = self.env['aite.ecm.webdav']
        base = self._webdav_base()
        unc = self._office_uri_mode() == 'unc'
        unc_root = self._webdav_unc_root() if unc else ''
        for doc in self:
            if not doc.latest_version_id:
                doc.webdav_url = doc.office_uri = doc.office_app = False
                doc.office_target = False
                continue
            path = service.document_path(doc)
            url = "%s/%s" % (base, '/'.join(quote(p) for p in path.split('/')))
            doc.webdav_url = url
            # L'adresse affichée reste toujours l'URL ; seule celle remise aux
            # applications de bureau peut prendre la forme UNC. Cette forme
            # sort de la spécification Office URI Schemes (``ofe|u|`` suivi
            # d'une URI http ou https) et ne contourne pas le blocage Basic
            # d'Office : voir ``_office_uri_mode``.
            doc.office_target = ('%s\\%s' % (unc_root, path.replace('/', '\\'))
                                 if unc else url)
            ext = doc.latest_version_id.file_extension
            scheme = next((s for s, exts in OFFICE_SCHEMES.items() if ext in exts), False)
            doc.office_app = OFFICE_LABELS.get(scheme) if scheme else False
            doc.office_uri = ("%s:ofe|u|%s" % (scheme, doc.office_target)
                              if scheme else False)

    def action_open_in_office(self):
        """Ouvre le fichier dans Word / Excel / PowerPoint (édition sur le
        serveur, enregistrement → nouvelle version).

        Prérequis de poste : l'hôte autorisé par ``basichostallowlist``, sans
        quoi Office bloque l'invite d'authentification Basic, en https comme
        en http (voir ``_office_uri_mode``)."""
        self.ensure_one()
        if not self.office_uri:
            raise UserError(_("Ce format ne s'ouvre pas dans une application Office."))
        if not self._check_document_access('write'):
            uri = self.office_uri.replace(':ofe|', ':ofv|')     # lecture seule
        else:
            uri = self.office_uri
        return self._open_protocol_uri(uri)

    @api.model
    def _open_protocol_uri(self, uri):
        """Action ouvrant une URI de protocole applicatif.

        Volontairement pas un ``ir.actions.act_url`` : le client web normalise
        l'adresse, et une URI de protocole y perd ses barres verticales et son
        schéma imbriqué. Le navigateur la résout alors en chemin relatif
        d'Odoo — 404, sans jamais lancer Word. L'URI part donc telle quelle
        vers le navigateur (cf. ``static/src/open_uri.js``).
        """
        return {'type': 'ir.actions.client', 'tag': 'aite_ecm_open_uri',
                'params': {'uri': uri}}

    def _explorer_record(self):
        data = super()._explorer_record()
        data.update({'office_uri': self.office_uri or False,
                     'office_app': self.office_app or False,
                     'webdav_url': self.webdav_url or False})
        return data
