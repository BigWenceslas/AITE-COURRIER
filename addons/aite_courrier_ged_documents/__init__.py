# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Reprend l'espace racine « Courrier » créé par les versions
    précédentes de la GED (xmlid déplacé)."""
    env = env(su=True)
    Data = env['ir.model.data']
    old = env.ref('aite_courrier_ged.documents_folder_courrier',
                  raise_if_not_found=False)
    new = env.ref('aite_courrier_ged_documents.documents_folder_courrier',
                  raise_if_not_found=False)
    if old and new and old != new:
        env['documents.document'].search(
            [('folder_id', '=', new.id)]).write({'folder_id': old.id})
        Data.search([('module', '=', 'aite_courrier_ged_documents'),
                     ('name', '=', 'documents_folder_courrier')]).write(
            {'res_id': old.id})
        Data.search([('module', '=', 'aite_courrier_ged'),
                     ('name', '=', 'documents_folder_courrier')]).unlink()
        new.unlink()
