# -*- coding: utf-8 -*-
import logging

from lxml import etree

from odoo import api, models

_logger = logging.getLogger(__name__)

# Le client web d'Odoo 18 recopie les textes des vues (string, help, title,
# contenu des balises) tels quels dans le gabarit JavaScript qu'il compile,
# entre accents graves et sans échapper l'antislash (toStringExpression,
# web/static/src/views/utils.js). Ces attributs-ci, des expressions ou des
# objets, passent par JSON.stringify : leur antislash est sans danger.
ATTRIBUTS_EXPRESSIONS = frozenset({
    'attrs', 'column_invisible', 'context', 'domain', 'eval', 'filter_domain',
    'invisible', 'options', 'readonly', 'required', 'states',
})
# Même dessin que l'antislash, sans effet dans une chaîne JavaScript.
ANTISLASH_AFFICHE = '⧵'


def _est_expression(attribut):
    return attribut in ATTRIBUTS_EXPRESSIONS or attribut.startswith(('decoration-', 't-'))


def neutraliser_antislashs(arch):
    """Remplace l'antislash des textes de la vue ``arch`` (XML) par
    ANTISLASH_AFFICHE. Renvoie la vue et le nombre de textes modifiés."""
    racine = etree.fromstring(arch)
    modifies = 0
    for noeud in racine.iter():
        if isinstance(noeud.tag, str):
            for attribut, valeur in noeud.attrib.items():
                if '\\' in valeur and not _est_expression(attribut):
                    noeud.set(attribut, valeur.replace('\\', ANTISLASH_AFFICHE))
                    modifies += 1
        for partie in ('text', 'tail'):
            valeur = getattr(noeud, partie)
            if valeur and '\\' in valeur:
                setattr(noeud, partie, valeur.replace('\\', ANTISLASH_AFFICHE))
                modifies += 1
    return etree.tostring(racine, encoding='unicode'), modifies


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        # La page Paramètres réunit les réglages de tous les modules installés
        # en un seul gabarit : un antislash dans un seul texte la fait planter
        # entièrement. Il en reste un quand un module a été copié sans être mis
        # à jour (aide d'aite_ecm_office antérieure à 18.0.2.0.4).
        if view_type != 'form' or '\\' not in result['arch']:
            return result
        arch, modifies = neutraliser_antislashs(result['arch'])
        if modifies:
            self._signaler_vues_avec_antislash()
            result = dict(result, arch=arch)
        return result

    @api.model
    def _signaler_vues_avec_antislash(self):
        vues = self.env['ir.ui.view'].sudo().search([
            ('model', '=', self._name), ('type', '=', 'form')])
        fautives = vues.filtered(lambda vue: '\\' in (vue.arch_db or ''))
        _logger.warning(
            "Page Paramètres : antislash remplacé à l'affichage (%s). Module "
            "copié mais pas mis à jour ? Applications › Mettre à niveau.",
            ", ".join(vue.xml_id or vue.name for vue in fautives) or "vue inconnue")
