# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Reprend l'espace racine « ECM » créé par les versions précédentes du
    socle (xmlid déplacé), crée l'arborescence Documents complète du plan de
    classement et rattache les cartes existantes aux documents ECM."""
    env = env(su=True)
    Data = env['ir.model.data']
    old = env.ref('aite_ecm_document.documents_folder_ecm',
                  raise_if_not_found=False)
    new = env.ref('aite_ecm_documents.documents_folder_ecm',
                  raise_if_not_found=False)
    if old and new and old != new:
        env['documents.document'].with_context(ecm_skip_adopt=True).search(
            [('folder_id', '=', new.id)]).write({'folder_id': old.id})
        Data.search([('module', '=', 'aite_ecm_documents'),
                     ('name', '=', 'documents_folder_ecm')]).write(
            {'res_id': old.id})
        Data.search([('module', '=', 'aite_ecm_document'),
                     ('name', '=', 'documents_folder_ecm')]).unlink()
        new.with_context(ecm_skip_adopt=True).unlink()
    for folder in env['aite.ecm.folder'].search([]):
        folder._get_or_create_documents_folder()
    env['aite.ecm.document']._documents_rebuild_cards()
