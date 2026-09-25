#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie qu'un refus de transition reste tracé au journal d'audit.

    python3 docs/recette/verif_audit_refus.py --url http://localhost:8069 \\
        --db <base> --login admin --password <mot de passe>

Le moteur de validation écrit « Tentative non autorisée » au journal, puis
lève une ``AccessError``. Sur un vrai serveur, l'exception annule la
transaction de la requête : si l'entrée d'audit y était écrite, elle
disparaissait avec elle. Les tests unitaires ne le voient pas — ils partagent
une seule transaction —, d'où ce contrôle de bout en bout, joué par XML-RPC
comme le ferait l'interface.

Déroulé : un compte « recette.refus » (rôle Audit : il lit les courriers et le
journal, mais n'est habilité à aucune étape) est créé ou réutilisé ; il tente
de faire avancer un courrier en cours ; on compte ses entrées « Tentative non
autorisée » avant et après.

Bibliothèque standard uniquement. Code de sortie : 0 si le refus est tracé,
1 sinon, 2 si le contrôle n'a pas pu être joué.
"""
import argparse
import sys
import xmlrpc.client

LOGIN_REFUS = 'recette.refus'
ACTION = "Tentative non autorisée"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--url', default='http://localhost:8069')
    parser.add_argument('--db', required=True)
    parser.add_argument('--login', default='admin',
                        help="compte administrateur (création du compte de test)")
    parser.add_argument('--password', required=True)
    parser.add_argument('--refus-password', default='Recette-Refus-2026',
                        help="mot de passe du compte %s" % LOGIN_REFUS)
    args = parser.parse_args(argv)

    common = xmlrpc.client.ServerProxy(args.url + '/xmlrpc/2/common')
    models = xmlrpc.client.ServerProxy(args.url + '/xmlrpc/2/object',
                                       allow_none=True)
    admin = common.authenticate(args.db, args.login, args.password, {})
    if not admin:
        print("Connexion administrateur refusée.")
        return 2

    def call(uid, password, model, method, *params, **kw):
        return models.execute_kw(args.db, uid, password, model, method,
                                 list(params), kw)

    def xmlid(ref):
        # Lecture directe de ir.model.data : check_object_reference contrôle
        # aussi l'accès à l'enregistrement visé, que l'administrateur
        # technique n'a pas forcément (il n'a aucun rôle AITE).
        module, name = ref.split('.')
        rows = call(admin, args.password, 'ir.model.data', 'search_read',
                    [('module', '=', module), ('name', '=', name)],
                    fields=['res_id'])
        return rows[0]['res_id']

    # 1. Le compte sans habilitation
    groups = [xmlid('base.group_user'), xmlid('aite_courrier_base.group_audit')]
    found = call(admin, args.password, 'res.users', 'search',
                 [('login', '=', LOGIN_REFUS)])
    if found:
        call(admin, args.password, 'res.users', 'write', found,
             {'password': args.refus_password, 'groups_id': [(6, 0, groups)]})
        uid_refus = found[0]
    else:
        uid_refus = call(admin, args.password, 'res.users', 'create', {
            'name': "Recette — refus de transition", 'login': LOGIN_REFUS,
            'email': 'recette.refus@example.com',
            'password': args.refus_password, 'groups_id': [(6, 0, groups)]})
    if not common.authenticate(args.db, LOGIN_REFUS, args.refus_password, {}):
        print("Le compte %s ne peut pas se connecter." % LOGIN_REFUS)
        return 2

    # 2. Un courrier en cours, lisible par ce compte, avec une transition.
    # Tout se lit avec le compte de test (rôle Audit) : l'administrateur
    # technique n'a pas de rôle AITE, donc pas accès aux courriers.
    public = [xmlid('aite_courrier_base.confidentiality_public'),
              xmlid('aite_courrier_base.confidentiality_internal')]
    pwd = args.refus_password
    courriers = call(uid_refus, pwd, 'aite.courrier', 'search_read',
                     [('state', 'in', ('nw', 'pr')),
                      ('current_step_id', '!=', False),
                      ('confidentiality_id', 'in', public)],
                     fields=['reference', 'current_step_id'], limit=50)
    cible = None
    for courrier in courriers:
        step = call(uid_refus, pwd, 'aite.workflow.step', 'read',
                    [courrier['current_step_id'][0]],
                    fields=['outgoing_transition_ids'])[0]
        if step['outgoing_transition_ids']:
            cible = (courrier, step['outgoing_transition_ids'][0])
            break
    if not cible:
        print("Aucun courrier en cours avec une transition sortante : "
              "enregistrer un courrier et lancer son circuit, puis rejouer.")
        return 2
    courrier, transition = cible

    def compte():
        return call(uid_refus, pwd, 'aite.courrier.audit.log',
                    'search_count', [('name', '=', ACTION),
                                     ('res_id', '=', courrier['id']),
                                     ('create_uid', '=', uid_refus)])

    avant = compte()
    # 3. La tentative, avec l'identité du compte sans habilitation
    try:
        call(uid_refus, args.refus_password, 'aite.courrier', 'do_transition',
             [courrier['id']], transition)
    except xmlrpc.client.Fault as fault:
        refus = fault.faultString.strip().splitlines()[-1]
    else:
        print("ÉCHEC du contrôle : la transition a été acceptée pour %s ; "
              "le compte est habilité à l'étape." % LOGIN_REFUS)
        return 2
    apres = compte()

    print("Courrier   : %s" % courrier['reference'])
    print("Refus reçu : %s" % refus[:160])
    print("Entrées « %s » : %d avant, %d après" % (ACTION, avant, apres))
    if apres == avant + 1:
        print("OK — le refus est tracé au journal d'audit.")
        return 0
    print("ÉCHEC — le refus n'a laissé aucune trace au journal d'audit.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
