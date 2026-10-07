# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests import TransactionCase, tagged
from odoo.tools.misc import file_path

from odoo.addons.aite_courrier_base.models.res_config_settings import (
    ANTISLASH_AFFICHE, _est_expression,
)

# Types de vues que le client web compile en gabarit JavaScript. Odoo 18 y
# recopie string, help, title et textes dans des chaînes entre accents graves
# sans échapper l'antislash (toStringExpression, web/static/src/views/utils.js).
COMPILED_VIEW_TYPES = ('form', 'kanban', 'list')

# Ce qu'une base garde d'aite_ecm_office 18.0.2.0.3 quand le module a été copié
# sans être mis à jour : l'aide et son chemin de registre.
STALE_SETTINGS_ARCH = r"""
<xpath expr="//form" position="inside">
    <app string="Vue périmée" name="aite_test_vue_perimee">
        <block title="Office et Google Docs"
               help="valeur basichostallowlist sous HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity">
            <setting string="Chemin" help="C:\users\public">
                <div invisible="'a\\b' == 'c'">Clé HKCU\Software</div>
            </setting>
        </block>
    </app>
</xpath>
"""


@tagged('post_install', '-at_install', 'aite_courrier_base')
class TestWebClientViews(TransactionCase):
    """Ce que le client web d'Odoo 18 fait des vues et réglages AITE, vérifié
    sans navigateur. Un antislash dans une vue compilée la casse : suivi d'un
    chiffre, d'un u ou d'un x (« Office, antislash, 16.0 », « C:, antislash,
    users »), c'est une erreur de syntaxe et toute la page plante ; sinon il
    disparaît, ou devient un saut de ligne ou une tabulation, à l'affichage."""

    def _langs(self):
        return [code for code, _name in self.env['res.lang'].get_installed()]

    def _settings_arch(self, lang=None):
        settings = self.env['res.config.settings'].with_context(lang=lang)
        return settings.get_views([(False, 'form')])['views']['form']['arch']

    def test_aite_views_have_no_backslash(self):
        data = self.env['ir.model.data'].search([('model', '=', 'ir.ui.view')])
        data = data.filtered(lambda d: d.module.startswith('aite_'))
        views = self.env['ir.ui.view'].browse(data.mapped('res_id')).exists() \
            .filtered(lambda v: v.type in COMPILED_VIEW_TYPES)
        self.assertTrue(views, "Aucune vue AITE à contrôler.")
        offenders = sorted({
            "%s (%s)" % (view.xml_id or view.name, lang)
            for lang in self._langs()
            for view in views.with_context(lang=lang)
            if '\\' in (view.arch_db or '')})
        self.assertFalse(offenders, "Antislash dans des vues compilées par le "
                                    "client web : %s" % ", ".join(offenders))

    def test_settings_page_has_no_backslash(self):
        # La page Paramètres réunit les réglages de tous les modules
        # installés en un seul gabarit : un antislash la bloque entièrement.
        for lang in self._langs():
            self.assertNotIn('\\', self._settings_arch(lang),
                             "Antislash dans la page Paramètres (%s)" % lang)

    def test_settings_page_survives_stale_view(self):
        # Une vue périmée ne doit plus bloquer la page : les antislashs de ses
        # textes sont remplacés, ceux des expressions gardés, la vue signalée.
        stale = self.env['ir.ui.view'].create({
            'name': 'aite.test.vue.perimee',
            'model': 'res.config.settings',
            'inherit_id': self.env.ref('base.res_config_settings_view_form').id,
            'arch': STALE_SETTINGS_ARCH,
        })
        with self.assertLogs('odoo.addons.aite_courrier_base', 'WARNING') as logs:
            arch = self._settings_arch()
        self.assertIn(stale.name, logs.output[0])
        texts = []
        for node in etree.fromstring(arch).iter():
            if isinstance(node.tag, str):
                texts += [value for name, value in node.attrib.items()
                          if not _est_expression(name)]
            texts += [node.text or '', node.tail or '']
        self.assertFalse([text for text in texts if '\\' in text],
                         "Antislash restant dans un texte de la page Paramètres")
        self.assertIn('HKCU%sSoftware%sPolicies' % (ANTISLASH_AFFICHE, ANTISLASH_AFFICHE), arch)
        self.assertIn('C:%susers' % ANTISLASH_AFFICHE, arch)
        self.assertIn('Clé HKCU%sSoftware' % ANTISLASH_AFFICHE, arch)
        self.assertIn("invisible=\"'a\\\\b' == 'c'\"", arch,
                      "Une expression a été modifiée")

    def test_aite_settings_apps_have_icon(self):
        # Sans attribut logo, l'onglet d'une application de réglages affiche
        # /<name>/static/description/icon.png : absente, l'icône est cassée.
        missing = []
        for app in etree.fromstring(self._settings_arch()).iter('app'):
            name = app.get('name') or ''
            if not name.startswith('aite_'):
                continue
            logo = app.get('logo') or '/%s/static/description/icon.png' % name
            try:
                file_path(logo.lstrip('/'))
            except FileNotFoundError:
                missing.append("%s (%s)" % (name, logo))
        self.assertFalse(missing, "Icône introuvable pour des applications de "
                                  "réglages : %s" % ", ".join(missing))

    def test_aite_computed_settings_shown_on_load(self):
        # La page Paramètres s'ouvre par un onchange qui met False dans les
        # champs calculés et ne recalcule que ceux dont une dépendance a une
        # valeur par défaut : sans @api.depends('company_id'), le champ reste
        # vide à l'écran alors qu'il a une valeur.
        # Comme le navigateur, l'onchange porte sur tous les champs de la vue.
        Settings = self.env['res.config.settings']
        in_view = Settings.get_views([(False, 'form')])['models'][Settings._name]['fields']
        names = [name for name in in_view
                 if (Settings._fields[name]._module or '').startswith('aite_')
                 and Settings._fields[name].compute
                 and not Settings._fields[name].store]
        loaded = Settings.onchange({}, [], {name: {} for name in in_view})['value']
        saved = Settings.create({})
        empty = [name for name in names if saved[name] and not loaded.get(name)]
        self.assertFalse(empty, "Réglages vides à l'ouverture de la page "
                                "Paramètres : %s" % ", ".join(empty))
