# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Reprise : crée le miroir ECM des pièces de courrier existantes."""
    env = env(su=True)
    count = env['aite.courrier.document']._ecm_mirror_all()
    env['ir.logging'].sudo().create({
        'name': 'aite_courrier_ecm', 'type': 'server', 'level': 'INFO',
        'dbname': env.cr.dbname, 'message': "Pont courrier ↔ ECM : %d pièce(s) "
        "reflétée(s)." % count, 'path': 'post_init_hook', 'func': '', 'line': '0',
    })
