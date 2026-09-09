# -*- coding: utf-8 -*-
"""Socle commun aux tests de la Fondation ECM.

Créer un utilisateur de test « à la main » est une source d'échecs récurrents :

* sans ``base.group_user``, le compte est un utilisateur **externe** ; il ne
  peut pas lire ``ir.sequence`` et la simple création d'un document échoue en
  ``AccessError`` ;
* sans adresse e-mail, tout ``message_post`` échoue (« Unable to send message,
  please configure the sender's email address »), donc tout lancement de
  circuit ou de dossier.

Les rôles AITE viennent **en plus** du groupe utilisateur interne : ils ne le
remplacent jamais. Passer par :meth:`EcmTestUsersMixin._make_user` garantit les
deux invariants.
"""
from odoo.tests import HttpCase, TransactionCase


class EcmTestUsersMixin:
    """Fabrique d'utilisateurs de test conformes à un compte réel."""

    @classmethod
    def _make_user(cls, name, login, roles, **extra):
        """Utilisateur interne portant les ``roles`` AITE demandés.

        :param roles: identifiants XML de groupes, avec ou sans le préfixe
            ``aite_courrier_base.`` (``'group_agent'`` ou l'identifiant complet).
        """
        if isinstance(roles, str):
            roles = [roles]
        group_ids = [cls.env.ref('base.group_user').id]
        for role in roles:
            xmlid = role if '.' in role else 'aite_courrier_base.%s' % role
            group_ids.append(cls.env.ref(xmlid).id)
        vals = {
            'name': name,
            'login': login,
            'email': extra.pop('email', '%s@example.com' % login),
            'groups_id': [(6, 0, group_ids)],
        }
        vals.update(extra)
        return cls.env['res.users'].with_context(
            no_reset_password=True, mail_create_nolog=True).create(vals)


class EcmTransactionCase(EcmTestUsersMixin, TransactionCase):
    """``TransactionCase`` doté de la fabrique d'utilisateurs ECM."""


class EcmHttpCase(EcmTestUsersMixin, HttpCase):
    """``HttpCase`` doté de la fabrique d'utilisateurs ECM."""
