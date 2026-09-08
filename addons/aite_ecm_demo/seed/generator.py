# -*- coding: utf-8 -*-
"""Générateur du jeu de données de test AITE Courrier / AITE ECM.

* **Volumes par profil** (``leger`` par défaut, ``standard``, ``complet``).
* **Génération par lots reprenables** : l'état d'avancement (phase, index)
  est conservé dans un paramètre système ; chaque lot dure au plus
  ``aite_ecm_demo.batch_seconds`` secondes (40 s) puis rend la main. Une
  tâche planifiée enchaîne les lots jusqu'à la fin ; le script ``shell``
  peut aussi tout dérouler d'un coup (avec un commit par lot).
* **Aléa déterministe** : chaque unité de travail (un courrier, un document,
  un dossier…) tire son propre générateur pseudo-aléatoire à partir de la
  graine, de la phase et de l'index — le résultat ne dépend pas du
  découpage en lots.
* Les enregistrements sont créés **par les méthodes métier** sous l'identité
  d'utilisateurs de démonstration (ACL contournées, contrôles métier actifs),
  puis leurs dates sont réparties sur les six derniers mois.
"""
import base64
import json
import logging
import random
import time
import traceback
import unicodedata
from datetime import datetime, timedelta

from odoo import fields

from . import data_fr as D
from .pdf import make_pdf

_logger = logging.getLogger(__name__)

MODULE = 'aite_ecm_demo'
SEED = 2026
DEFAULT_PROFILE = 'leger'
PROFILES = {
    'leger': dict(partners=60, courriers_per_type=30, replies=15,
                  ecm_documents=60, dossiers_fournisseur=20, dossiers_salarie=20,
                  links=40, shares=30, checkouts=12, trashed=8),
    'standard': dict(partners=100, courriers_per_type=60, replies=30,
                     ecm_documents=120, dossiers_fournisseur=50,
                     dossiers_salarie=50, links=80, shares=60, checkouts=25,
                     trashed=12),
    'complet': dict(partners=130, courriers_per_type=100, replies=60,
                    ecm_documents=200, dossiers_fournisseur=100,
                    dossiers_salarie=100, links=120, shares=100, checkouts=40,
                    trashed=20),
}
COURRIER_CODES = ('ENTR', 'FACT', 'SORT', 'DEVIS', 'INT')
PHASES = ['users', 'departments', 'partners', 'structure', 'courriers',
          'replies', 'documents', 'dossiers', 'links', 'shares', 'checkouts',
          'trash', 'done']
ROLE_USERS = [  # (login, prénom, nom, groupes)
    ("demo.agent1", "Aurélie", "Mbarga", ['group_agent']),
    ("demo.agent2", "Boris", "Tchoumi", ['group_agent']),
    ("demo.agent3", "Clarisse", "Ekani", ['group_agent']),
    ("demo.assist1", "Nadège", "Fotso", ['group_assistant']),
    ("demo.assist2", "Franck", "Onana", ['group_assistant']),
    ("demo.manager1", "Patrick", "Essomba", ['group_manager']),
    ("demo.manager2", "Solange", "Ngo Bassong", ['group_manager']),
    ("demo.compta", "Hervé", "Kenfack", ['group_compta']),
    ("demo.signer", "Gisèle", "Atangana", ['group_signer']),
    ("demo.archive", "Landry", "Nkolo", ['group_archive']),
    ("demo.audit", "Irène", "Djomo", ['group_audit']),
    ("demo.admin", "Serge", "Kamdem", ['group_admin']),
]
STATE_PARAM = 'aite_ecm_demo.state'


class DemoSeeder:

    def __init__(self, env, log=None):
        # ``env`` est un Environment (hook, cron ou shell) : on recompose un
        # environnement superutilisateur avec un contexte anti-notifications.
        self.env = env(su=True, context=dict(
            env.context, mail_notrack=True, tracking_disable=True,
            mail_create_nosubscribe=True, mail_auto_subscribe_no_notify=True,
            mail_notify_force_send=False))
        self.log = log or (lambda m: _logger.info("[aite_ecm_demo] %s", m))
        self.now = fields.Datetime.now()
        self.state = self._load_state()
        self.counts = PROFILES.get(self.state.get('profile') or DEFAULT_PROFILE,
                                   PROFILES[DEFAULT_PROFILE])
        self.stats = self.state.setdefault('stats', {})
        self.rnd = random.Random(SEED)
        self.xmlids = []          # (model, res_id, name) du lot courant
        self.users = {}
        self.by_group = {}
        self.managers = []
        self._loaded = False

    # ================================================================== #
    # État persistant
    # ================================================================== #
    def _load_state(self):
        raw = self.env['ir.config_parameter'].get_param(STATE_PARAM)
        try:
            state = json.loads(raw) if raw else {}
        except ValueError:
            state = {}
        return state

    def _save_state(self):
        self.state['stats'] = self.stats
        self.env['ir.config_parameter'].set_param(
            STATE_PARAM, json.dumps(self.state))

    @property
    def phase(self):
        return self.state.get('phase', 'done')

    @property
    def is_done(self):
        return self.phase == 'done'

    def setup(self, profile=None):
        """Prépare un nouveau plan de génération (sans rien créer)."""
        profile = profile if profile in PROFILES else DEFAULT_PROFILE
        self.state = {'profile': profile, 'phase': PHASES[0], 'index': 0,
                      'stats': {}, 'started': fields.Datetime.to_string(self.now)}
        self.stats = self.state['stats']
        self.counts = PROFILES[profile]
        self._save_state()
        self.log("Plan de génération enregistré (profil « %s »)." % profile)

    # ================================================================== #
    # Utilitaires
    # ================================================================== #
    def _count(self, key, n=1):
        self.stats[key] = self.stats.get(key, 0) + n

    def _xmlid(self, record, prefix):
        for rec in record:
            self.xmlids.append((rec._name, rec.id, "%s_%d" % (prefix, rec.id)))

    def _ref(self, xmlid):
        return self.env.ref(xmlid)

    def _choice(self, seq):
        return self.rnd.choice(list(seq))

    def _past(self, max_days=180, min_days=0):
        return self.now - timedelta(days=self.rnd.uniform(min_days, max_days),
                                    hours=self.rnd.uniform(0, 9))

    @staticmethod
    def _ascii(text):
        return ''.join(c for c in unicodedata.normalize('NFKD', text)
                       if ord(c) < 128)

    def _pdf(self, title, lines, key=None):
        """PDF base64 ; ``key`` force un contenu canonique (doublons)."""
        if key:
            title = "Document en double — %s" % key
            lines = ["Contenu strictement identique (test de doublon).", D.LOREM]
        return base64.b64encode(make_pdf(title, lines))

    def _seed_unit(self, phase, index):
        self.rnd = random.Random("%d:%s:%d" % (SEED, phase, index))

    def _user_for_step(self, step):
        candidates = []
        for group in step.role_ids:
            candidates += self.by_group.get(group.id, [])
        if step.user_ids:
            candidates = [u for u in candidates if u in step.user_ids] \
                or candidates
        if not candidates:
            candidates = self.managers
        return self._choice(candidates)

    def _user_in(self, *groups):
        cands = []
        for g in groups:
            cands += self.by_group.get(self._ref('aite_courrier_base.' + g).id, [])
        return self._choice(cands or self.managers)

    def _as(self, record, user):
        """Action sous l'identité de ``user`` (audit, historique) sans blocage
        par les règles d'accès ; les contrôles métier restent actifs."""
        return record.with_user(user).sudo()

    def _safe(self, label, func):
        """Exécute ``func`` dans un savepoint ; toute erreur est comptée et
        journalisée (trace la première fois) sans interrompre la génération."""
        try:
            with self.env.cr.savepoint():
                return func()
        except Exception as exc:  # noqa: BLE001 — jeu de données : on continue
            key = 'ignorés (' + label + ')'
            first = key not in self.stats
            self._count(key)
            self._record_error(label, exc, first)
            return None

    def _record_error(self, label, exc, with_trace=True):
        detail = "%s : %s" % (label, exc)
        if with_trace:
            detail += "\n" + traceback.format_exc()[-1500:]
        self.state['last_error'] = label
        self.state['last_error_detail'] = detail[:4000]
        _logger.warning("[aite_ecm_demo] %s ignoré : %s", label, exc,
                        exc_info=with_trace)

    def summary(self):
        """Résumé lisible de l'état (tableau de bord, journal)."""
        st = self.state
        if not st.get('profile'):
            return "Aucun plan de génération."
        phase = st.get('phase', 'done')
        if phase == 'done':
            head = "Génération terminée (profil %s)." % st['profile']
        else:
            head = "Profil %s — phase « %s » : %d / %d." % (
                st['profile'], phase, st.get('index', 0),
                self._phase_total(phase))
        stats = ", ".join("%s = %d" % kv for kv in sorted(self.stats.items()))
        return head + ("\n" + stats if stats else "")

    def _person_name(self):
        first = self._choice(D.FIRST_NAMES_M + D.FIRST_NAMES_F)
        return "%s %s" % (first, self._choice(D.LAST_NAMES))

    def _address(self):
        city, quarters = self._choice(D.CITIES)
        return {
            'street': "%s %s" % (self._choice(D.STREETS),
                                 self._choice(D.STREET_NAMES)),
            'street2': self._choice(quarters),
            'city': city,
            'country_id': self.env.ref('base.cm').id,
            'phone': "+237 6%s" % ''.join(self._choice("0123456789")
                                         for _ in range(8)),
        }

    def _ext_ref(self):
        return "%s-%d-%04d" % (self._choice(["REF", "BC", "F", "N", "DOS"]),
                               self._choice([2025, 2026]),
                               self.rnd.randint(1, 9999))

    def _subject(self, code, partner):
        tpl = self._choice(D.SUBJECTS[code])
        return tpl.format(p=partner.name if partner else "—", ref=self._ext_ref())

    # ================================================================== #
    # Chargement du contexte (à chaque lot)
    # ================================================================== #
    def _demo_records(self, model):
        entries = self.env['ir.model.data'].search_read(
            [('module', '=', MODULE), ('model', '=', model)], ['res_id'])
        return self.env[model].with_context(active_test=False).browse(
            [e['res_id'] for e in entries]).exists()

    def _load_context(self):
        if self._loaded:
            return
        Users = self.env['res.users']
        self.users, self.by_group = {}, {}
        for login, _first, _last, groups in ROLE_USERS:
            user = Users.search([('login', '=', login)], limit=1)
            if not user:
                continue
            self.users[login] = user
            for g in groups:
                self.by_group.setdefault(
                    self._ref('aite_courrier_base.' + g).id, []).append(user)
        self.managers = self.by_group.get(
            self._ref('aite_courrier_base.group_manager').id, []) \
            or [self.env.ref('base.user_admin')]
        self.agents = (self.by_group.get(
            self._ref('aite_courrier_base.group_agent').id, []) +
            self.by_group.get(self._ref('aite_courrier_base.group_assistant').id, []
                              )) or self.managers
        self.actors = list(self.users.values())[:10] or self.managers
        self.departments = self.env['hr.department'].search(
            [('name', 'in', D.DEPARTMENTS)]) \
            if 'hr.department' in self.env else []
        self.partners = self._demo_records('res.partner')
        self.companies = self.partners.filtered('is_company')
        self.persons = self.partners - self.companies
        self.courriers = self._demo_records('aite.courrier')
        self.documents = self._demo_records('aite.ecm.document')
        self.dossiers = self._demo_records('aite.ecm.dossier')
        self.folders = {}
        for xmlid in ('folder_direction', 'folder_rh', 'folder_rh_dossiers',
                      'folder_juridique', 'folder_finance', 'folder_achats',
                      'folder_qualite'):
            self.folders[xmlid] = self._ref('aite_ecm_document.' + xmlid)
        for _parent, name, _restrict in D.SUBFOLDERS:
            folder = self.env['aite.ecm.folder'].search(
                [('name', '=', name)], limit=1)
            if folder:
                self.folders[name] = folder
        self.tags = self.env['aite.ecm.tag'].search([('name', 'in', D.TAGS)])
        self._loaded = True

    # ================================================================== #
    # Orchestration
    # ================================================================== #
    def _phase_total(self, phase):
        c = self.counts
        has_courrier = 'aite.courrier' in self.env
        return {
            'courriers': c['courriers_per_type'] * len(COURRIER_CODES)
            if has_courrier else 0,
            'replies': 1 if has_courrier else 0,
            'departments': 1 if 'hr.department' in self.env else 0,
            'documents': c['ecm_documents'],
            'dossiers': c['dossiers_fournisseur'] + c['dossiers_salarie'],
        }.get(phase, 1)

    def _next_phase(self):
        self.state['phase'] = PHASES[PHASES.index(self.phase) + 1]
        self.state['index'] = 0

    def run_batch(self, budget=None):
        """Exécute des unités de travail pendant ``budget`` secondes.
        Retourne True quand la génération est terminée."""
        if self.is_done or not self.state.get('profile'):
            return True
        if budget is None:
            budget = float(self.env['ir.config_parameter'].get_param(
                'aite_ecm_demo.batch_seconds', 40))
        started = time.monotonic()
        units = 0
        while not self.is_done and time.monotonic() - started < budget:
            if not self._loaded:
                # les enregistrements créés jusqu'ici doivent être visibles
                # des phases suivantes (tiers → courriers → documents…)
                self._register_xmlids()
                try:
                    self._load_context()
                except Exception as exc:  # noqa: BLE001
                    self._record_error('chargement du contexte', exc)
                    self._save_state()
                    return False
            phase, index = self.phase, self.state.get('index', 0)
            if self._phase_total(phase) == 0:      # phase sans objet (Community)
                self._next_phase()
                continue
            self._seed_unit(phase, index)
            unit = getattr(self, '_unit_' + phase)
            if self._safe('unité %s' % phase, lambda: unit(index)) is None:
                self.state['last_error'] = "%s #%d" % (phase, index)
            units += 1
            if index + 1 >= self._phase_total(phase):
                self._next_phase()
                self._loaded = False
            else:
                self.state['index'] = index + 1
        self._register_xmlids()
        self._save_state()
        if self.is_done:
            self.env['ir.config_parameter'].set_param(
                'aite_ecm_demo.seeded', fields.Datetime.to_string(self.now))
            self.log("Génération terminée : " + ", ".join(
                "%s = %d" % kv for kv in sorted(self.stats.items())))
        else:
            self.log("Lot : %d unité(s) — phase « %s » (%d/%d)" % (
                units, self.phase, self.state.get('index', 0),
                self._phase_total(self.phase)))
        return self.is_done

    def run_all(self, profile=None, commit=False, budget=None):
        """Déroule toute la génération (shell) ; commit après chaque lot."""
        if profile or not self.state.get('profile') or self.is_done:
            self.setup(profile or self.state.get('profile') or DEFAULT_PROFILE)
            if commit:
                self.env.cr.commit()
        while not self.run_batch(budget):
            if commit:
                self.env.cr.commit()
            self._loaded = False
        if commit:
            self.env.cr.commit()
        return self.stats

    # ================================================================== #
    # Phases unitaires simples
    # ================================================================== #
    def _unit_users(self, _index):
        Users = self.env['res.users'].with_context(no_reset_password=True,
                                                   mail_create_nolog=True)
        base_user = self.env.ref('base.group_user')
        for login, first, last, groups in ROLE_USERS:
            if Users.search([('login', '=', login)], limit=1):
                continue
            gids = [base_user.id] + [
                self._ref('aite_courrier_base.' + g).id for g in groups]
            vals = {'name': "%s %s" % (first, last), 'login': login,
                    'email': "%s@demo.aite-consulting.com" % login,
                    'groups_id': [(6, 0, gids)]}
            user = self._safe('utilisateur', lambda: Users.create(vals))
            if user is not None:
                self._xmlid(user, 'user')
                self._count('utilisateurs')
        self._loaded = False
        return True

    def _unit_departments(self, _index):
        Dept = self.env['hr.department']
        for name in D.DEPARTMENTS:
            if Dept.search([('name', '=', name)], limit=1):
                continue
            dept = self._safe('service', lambda: Dept.create({'name': name}))
            if dept is not None:
                self._xmlid(dept, 'dept')
                self._count('services')
        self._loaded = False
        return True

    def _unit_partners(self, _index):
        Partner = self.env['res.partner']
        Category = self.env['res.partner.category']
        cats = {}
        for key, label in [('fournisseur', "Fournisseur"), ('client', "Client"),
                           ('partenaire', "Partenaire"),
                           ('administration', "Administration")]:
            cats[key] = Category.search([('name', '=', label)], limit=1) or \
                Category.create({'name': label})
        n_companies = min(len(D.COMPANIES), max(20, self.counts['partners'] // 2))
        companies = []
        for name, kind in D.COMPANIES[:n_companies]:
            companies.append(dict(
                self._address(), name=name, is_company=True,
                email="contact@%s.cm" % ''.join(
                    c for c in self._ascii(name.lower()) if c.isalnum())[:14],
                category_id=[(6, 0, [cats[kind].id])],
                comment="Jeu de données de test AITE ECM"))
        companies = Partner.create(companies)
        persons = []
        for _ in range(self.counts['partners'] - len(companies)):
            name = self._person_name()
            vals = dict(self._address(), name=name, is_company=False,
                        email="%s@gmail.com" % self._ascii(name.lower())
                        .replace(' ', '.').replace("'", ''),
                        comment="Jeu de données de test AITE ECM")
            if self.rnd.random() < 0.35:
                vals['parent_id'] = self._choice(companies).id
                vals['function'] = self._choice(
                    ["Directeur général", "Comptable", "Responsable achats",
                     "Assistante de direction", "Juriste", "Commercial"])
            persons.append(vals)
        persons = Partner.create(persons)
        self._xmlid(companies | persons, 'partner')
        self._count('tiers', len(companies) + len(persons))
        self._loaded = False
        return True

    def _unit_structure(self, _index):
        Folder = self.env['aite.ecm.folder']
        for parent_xmlid, name, restrict in D.SUBFOLDERS:
            parent = self._ref('aite_ecm_document.' + parent_xmlid)
            if Folder.search([('name', '=', name), ('parent_id', '=', parent.id)],
                             limit=1):
                continue
            vals = {'name': name, 'parent_id': parent.id}
            if restrict:
                group = self._ref('aite_courrier_base.group_' + restrict)
                vals['read_group_ids'] = [(6, 0, [group.id])]
                vals['write_group_ids'] = [(6, 0, [group.id])]
            folder = self._safe('sous-dossier', lambda: Folder.create(vals))
            if folder is not None:
                self._xmlid(folder, 'folder')
                self._count('sous-dossiers')
        Tag = self.env['aite.ecm.tag']
        for i, name in enumerate(D.TAGS):
            if Tag.search([('name', '=', name)], limit=1):
                continue
            vals = {'name': name, 'color': (i % 11) + 1}
            tag = self._safe('étiquette', lambda: Tag.create(vals))
            if tag is not None:
                self._xmlid(tag, 'tag')
                self._count('étiquettes')
        self._loaded = False
        return True

    # ================================================================== #
    # Courriers (une unité = un courrier)
    # ================================================================== #
    def _courrier_pieces(self, courrier, agent, n):
        Doc = self._as(self.env['aite.courrier.document'], agent)
        for i in range(n):
            title = courrier.subject if i == 0 else "Annexe %d" % i
            key = 'courrier' if self.rnd.random() < 0.03 else None
            vals = {'name': title, 'courrier_id': courrier.id}
            doc = self._safe('pièce courrier', lambda: Doc.create(vals))
            if doc is None:
                continue
            fname = "%s.pdf" % self._ascii(title).replace(' ', '_') \
                .replace('/', '-')[:40]
            content = self._pdf(title, ["Courrier %s — %s" % (
                courrier.reference or 'brouillon', courrier.subject),
                "Expéditeur : %s" % (courrier.sender or '—'), D.LOREM], key=key)
            self._safe('version pièce', lambda: doc.add_version(fname, content))
            if self.rnd.random() < 0.2:
                fname2 = fname[:-4] + "_v2.pdf"
                content2 = self._pdf(title + " (v2)",
                                     ["Version corrigée.", D.LOREM])
                self._safe('version pièce',
                           lambda: doc.add_version(fname2, content2))
            self._count('pièces courrier')

    def _scenario(self, path_len):
        r = self.rnd.random()
        if r < 0.15:
            return {'forward': 0, 'backward': False, 'reject': False}
        if r < 0.55:
            return {'forward': self.rnd.randint(1, max(1, path_len - 2)),
                    'backward': self.rnd.random() < 0.25, 'reject': False}
        if r < 0.63:
            return {'forward': self.rnd.randint(0, max(1, path_len - 2)),
                    'backward': False, 'reject': True}
        return {'forward': path_len + 1, 'backward': self.rnd.random() < 0.15,
                'reject': False}

    def _advance_courrier(self, courrier, scenario):
        n_forward = scenario['forward']
        for i in range(n_forward):
            step = courrier.current_step_id
            if not step or courrier.state in ('ar', 'rj'):
                break
            forwards = step.outgoing_transition_ids.filtered(
                lambda t: t.direction == 'forward')
            if not forwards:
                break
            if scenario['backward'] and i == n_forward // 2:
                backs = step.outgoing_transition_ids.filtered(
                    lambda t: t.direction != 'forward')
                if backs:
                    user = self._user_for_step(step)
                    back = self._choice(backs)
                    comment = self._choice(D.COMMENTS_BACKWARD)
                    if self._safe('retour', lambda: self._as(courrier, user)
                                  .do_transition(back, comment)) is not None:
                        self._count('transitions arrière')
                        step = courrier.current_step_id
                        forwards = step.outgoing_transition_ids.filtered(
                            lambda t: t.direction == 'forward')
                        user = self._user_for_step(step)
                        fwd = self._choice(forwards)
                        if self._safe('reprise', lambda: self._as(courrier, user)
                                      .do_transition(fwd, "Complété.")) is None:
                            break
                        self._count('transitions avant')
                        continue
            user = self._user_for_step(step)
            transition = self._choice(forwards)
            comment = self._choice(D.COMMENTS_FORWARD)
            if self._safe('transition', lambda: self._as(courrier, user)
                          .do_transition(transition, comment)) is None:
                break
            self._count('transitions avant')
        if scenario['reject'] and courrier.state not in ('ar', 'rj') \
                and courrier.current_step_id:
            user = self._user_for_step(courrier.current_step_id)
            reason = self._choice(D.COMMENTS_REJECT)
            if self._safe('rejet', lambda: self._as(courrier, user)
                          .action_reject(reason)) is not None:
                self._count('courriers rejetés')

    def _unit_courriers(self, index):
        code = COURRIER_CODES[index // self.counts['courriers_per_type']]
        ctype = self.env['aite.courrier.type'].search([('code', '=', code)],
                                                      limit=1)
        if not ctype:
            self._count('ignorés (type %s absent)' % code)
            return
        circuit = self.env['aite.workflow.circuit'].search(
            [('type_id', '=', ctype.id), ('active', '=', True)], limit=1)
        path_len = len(circuit.step_ids) if circuit else 1
        priorities = self.env['aite.courrier.priority'].search([])
        conf = {c.code: c for c in
                self.env['aite.courrier.confidentiality'].search([])}
        agent = self._choice(self.agents)
        partner = self._choice(self.companies if code in ('FACT', 'DEVIS')
                               else self.partners)
        r = self.rnd.random()
        confidentiality = conf.get('SEC') if r < 0.03 else conf.get('CONF') \
            if r < 0.12 else conf.get('PUB') if r < 0.30 else conf.get('INT')
        vals = {
            'subject': self._subject(code, partner),
            'type_id': ctype.id,
            'department_id': self._choice(self.departments).id
            if len(self.departments) else False,
            'priority_id': self._choice(priorities).id if priorities else False,
            'confidentiality_id': confidentiality.id if confidentiality else False,
            'date_received': self._past().date(),
            'responsible_id': self._choice(self.agents + self.managers).id,
        }
        if code != 'INT':
            vals.update({'sender_partner_id': partner.id, 'sender': partner.name,
                         'sender_email': partner.email})
        else:
            vals['sender'] = self._choice(self.actors).name
        courrier = self._safe('création courrier', lambda: self._as(
            self.env['aite.courrier'], agent).create(vals))
        if courrier is None:
            return
        self._xmlid(courrier, 'courrier')
        self._count('courriers %s' % code)
        self._courrier_pieces(courrier, agent, self.rnd.choice([1, 1, 2]))
        if self.rnd.random() < 0.12:
            self._count('courriers brouillon')
            return True
        if self._safe('lancement', lambda: self._as(courrier, agent)
                      .action_launch_circuit()) is None:
            return True
        self._count('circuits lancés')
        self._advance_courrier(courrier, self._scenario(path_len))
        self._safe('datation', lambda: self._backdate_courrier(courrier))
        return True

    def _backdate_courrier(self, courrier):
        start = datetime.combine(courrier.date_received, datetime.min.time()) \
            + timedelta(hours=self.rnd.uniform(8, 17))
        cr = self.env.cr
        cr.execute("UPDATE aite_courrier SET create_date=%s WHERE id=%s",
                   (start, courrier.id))
        history = courrier.step_history_ids.sorted('id')
        t = start
        deadline = None
        last = history[-1:] if history else history
        for line in history:
            entered = t
            left = None
            if line.left_date or line != last:
                t = t + timedelta(hours=self.rnd.uniform(1, 60))
                left = t
            cr.execute("UPDATE aite_courrier_step_history SET entered_date=%s, "
                       "left_date=%s WHERE id=%s", (entered, left, line.id))
            deadline = entered + timedelta(hours=line.step_id.sla_hours) \
                if line.step_id.sla_hours else None
        if courrier.state not in ('draft', 'ar', 'rj') and deadline:
            if self.rnd.random() < 0.30:
                deadline = min(deadline, self.now - timedelta(
                    hours=self.rnd.uniform(2, 120)))
                self._count('courriers en retard SLA')
            elif deadline < self.now:
                deadline = self.now + timedelta(hours=self.rnd.uniform(2, 72))
            cr.execute("UPDATE aite_courrier SET sla_deadline=%s, "
                       "sla_reminder_sent=false, sla_escalated=false WHERE id=%s",
                       (deadline, courrier.id))
        courrier.invalidate_recordset()
        history.invalidate_recordset()

    def _unit_replies(self, _index):
        if 'reply_to_courrier_id' not in self.env['aite.courrier']._fields:
            return True
        origins = self.courriers.filtered(
            lambda c: c.category == 'entrant' and c.state != 'draft')
        candidates = self.courriers.filtered(lambda c: c.type_id.code == 'SORT')
        n = min(self.counts['replies'], len(candidates), len(origins))
        for reply, origin in zip(self.rnd.sample(list(candidates), n),
                                 self.rnd.sample(list(origins), n)):
            subject = self._choice(D.REPLY_SUBJECTS).format(
                ref=origin.reference or origin.subject, subject=origin.subject)
            self.env.cr.execute(
                "UPDATE aite_courrier SET reply_to_courrier_id=%s, subject=%s, "
                "sender_partner_id=%s, sender=%s, sender_email=%s WHERE id=%s",
                (origin.id, subject[:200], origin.sender_partner_id.id or None,
                 origin.sender or None, origin.sender_email or None, reply.id))
            self._count('réponses liées')
        self.courriers.invalidate_recordset()
        return True

    # ================================================================== #
    # Documents ECM (une unité = un document)
    # ================================================================== #
    def _folder(self, name, fallback):
        return self.folders.get(name) or self.folders[fallback]

    def _doc_spec(self, code):
        company = self._choice(self.companies)
        if code == 'CONTRAT':
            obj = self._choice(D.CONTRACT_OBJECTS)
            start = self._past(400).date()
            props = {'contrat_parties': "AITE Consulting / %s" % company.name,
                     'contrat_objet': obj,
                     'contrat_date_effet': fields.Date.to_string(start),
                     'contrat_date_fin': fields.Date.to_string(
                         start + timedelta(days=self.rnd.choice([365, 730, 1095]))),
                     'contrat_montant': round(self.rnd.uniform(5e5, 8e7), -3),
                     'contrat_devise': self._choice(['XAF', 'XAF', 'XAF', 'EUR']),
                     'contrat_reconduction': self.rnd.random() < 0.5}
            title = "Contrat — %s — %s" % (obj, company.name)
            folder = self._choice([
                self._folder('Contrats fournisseurs', 'folder_juridique'),
                self._folder('Baux et immobilier', 'folder_juridique'),
                self.folders['folder_juridique']])
            lines = ["Parties : %s" % props['contrat_parties'], "Objet : %s" % obj,
                     "Montant : %s %s" % (props['contrat_montant'],
                                          props['contrat_devise'])]
        elif code == 'PROC':
            obj = self._choice(D.PROCEDURES)
            props = {'proc_domaine': self._choice(['rh', 'finance', 'achats', 'si',
                                                   'qualite']),
                     'proc_date_application': fields.Date.to_string(
                         self._past(300).date()),
                     'proc_revue': fields.Date.to_string(
                         (self.now + timedelta(days=self.rnd.randint(30, 400))).date()),
                     'proc_proprietaire': self._person_name()}
            title = "%s — v%d" % (obj, self.rnd.randint(1, 4))
            folder = self._folder('Procédures en vigueur', 'folder_qualite')
            lines = ["Domaine : %s" % props['proc_domaine'],
                     "Responsable du processus : %s" % props['proc_proprietaire']]
        elif code == 'FACT':
            amount = round(self.rnd.uniform(5e4, 1.5e7), 0)
            date = self._past(240).date()
            props = {'fact_numero': self._ext_ref(), 'fact_fournisseur': company.name,
                     'fact_montant_ttc': amount,
                     'fact_date': fields.Date.to_string(date),
                     'fact_echeance': fields.Date.to_string(date + timedelta(days=30))}
            title = "Facture %s — %s" % (props['fact_numero'], company.name)
            folder = self._folder('Factures fournisseurs %d' % date.year,
                                  'folder_finance')
            lines = ["Fournisseur : %s" % company.name,
                     "Montant TTC : %s FCFA" % amount]
        elif code == 'RH':
            person = self._choice(self.persons)
            nature = self._choice(D.RH_NATURES)
            props = {'rh_nature': nature,
                     'rh_validite': fields.Date.to_string(
                         (self.now + timedelta(days=self.rnd.randint(-60, 1500))).date())}
            title = "%s — %s" % ({'cni': "Pièce d'identité", 'diplome': "Diplôme",
                                  'contrat': "Contrat de travail",
                                  'medical': "Certificat médical",
                                  'autre': "Attestation"}[nature], person.name)
            folder = self.folders['folder_rh_dossiers']
            lines = ["Salarié : %s" % person.name]
        elif code == 'PV':
            instance = self._choice(D.PV_INSTANCES)
            date = self._past(365).date()
            props = {'pv_instance': instance,
                     'pv_date_seance': fields.Date.to_string(date)}
            title = "PV %s du %s" % (instance, date.strftime('%d/%m/%Y'))
            folder = self._folder('Procès-verbaux', 'folder_direction')
            lines = ["Instance : %s" % instance, "Séance du %s" % date]
        else:
            title = self._choice(["Note d'information", "Rapport d'activité",
                                  "Plan d'action", "Étude de faisabilité",
                                  "Cahier des charges", "Guide utilisateur"]) \
                + " — %s" % self._choice(D.DEPARTMENTS)
            props = {}
            folder = self._choice(list(self.folders.values()))
            lines = []
        return title, folder, props, lines

    def _create_document(self, code, owner=None, folder=None, res=None,
                         versions=None, dup_key=None, title=None, props=None,
                         lines=None, piece=None):
        dtype = self.env['aite.ecm.document.type'].search(
            [('code', '=', code)], limit=1)
        if title is None:
            title, spec_folder, props, lines = self._doc_spec(code)
            folder = folder or spec_folder
        owner = owner or self._choice(self.actors)
        if folder and not folder.user_can(owner, 'write'):
            owner = self._choice(self.managers)
        vals = {'name': title[:180], 'type_id': dtype.id if dtype else False,
                'folder_id': folder.id if folder else False,
                'owner_id': owner.id, 'description': D.LOREM[:120]}
        if props:
            vals['properties'] = props
        if res is not None:
            vals.update({'res_model': res._name, 'res_id': res.id})
        if self.tags and self.rnd.random() < 0.5:
            vals['tag_ids'] = [(6, 0, self.rnd.sample(
                self.tags.ids, min(len(self.tags), self.rnd.randint(1, 2))))]
        Doc = self._as(self.env['aite.ecm.document'], owner)
        if piece is not None:
            Doc = Doc.with_context(default_dossier_piece_id=piece.id)
        doc = self._safe('création document', lambda: Doc.create(vals))
        if doc is None:
            return None
        nv = self.rnd.choice([1, 1, 1, 2, 2, 3]) if versions is None else versions
        for v in range(nv):
            fname = "%s%s.pdf" % (
                ''.join(c if c.isalnum() else '_'
                        for c in self._ascii(title)[:36]),
                "" if v == 0 else "_v%d" % (v + 1))
            content = self._pdf(title, (lines or []) + [D.LOREM],
                                key=dup_key if v == 0 else None)
            comment = "Version %d" % (v + 1) if v else False
            self._safe('version', lambda: doc.add_version(fname, content, comment))
            self._count('versions ECM')
        self._xmlid(doc, 'document')
        self._count('documents ECM')
        return doc

    def _document_mix(self):
        n = self.counts['ecm_documents']
        weights = [('CONTRAT', 22), ('PROC', 15), ('FACT', 22), ('RH', 15),
                   ('PV', 13), ('DOC', 13)]
        mix = []
        for code, w in weights:
            mix += [code] * max(1, round(n * w / 100.0))
        random.Random(SEED).shuffle(mix)
        return (mix * 2)[:n]

    def _unit_documents(self, index):
        code = self._document_mix()[index]
        res = self._choice(self.partners) if self.rnd.random() < 0.4 else None
        versions = 0 if self.rnd.random() < 0.08 else None
        dup_key = 'paire-%d' % (index % 8) if index < 16 else None
        doc = self._create_document(code, res=res, versions=versions,
                                    dup_key=dup_key)
        if doc is None:
            return
        if doc.latest_version_id:
            r = self.rnd.random()
            if r < 0.30:
                if self._safe('finalisation', lambda: self._as(
                        doc, doc.owner_id).action_mark_final()) is not None:
                    self._count('documents finalisés')
            elif r < 0.45:
                archivist = self._user_in('group_archive', 'group_manager')
                if self._safe('archivage', lambda: (
                        self._as(doc, doc.owner_id).action_mark_final(),
                        self._as(doc, archivist).action_mark_archived())) \
                        is not None:
                    self._count('documents archivés')
        # circuits de validation sur les documents (module workflow) et partages nominatifs
        if getattr(doc, 'wf_has_circuit', False) and doc.state == 'draft' \
                and doc.latest_version_id and self.rnd.random() < 0.6:
            if self._safe('circuit document', lambda: self._as(
                    doc, doc.owner_id).action_wf_launch()) is not None:
                self._count('circuits documents lancés')
                step = doc.wf_step_id
                forwards = step.outgoing_transitions().filtered(
                    lambda t: t.direction == 'forward') if step else []
                if forwards and self.rnd.random() < 0.7:
                    user = self._user_for_step(step)
                    self._safe('transition document', lambda: self._as(doc, user)
                               .wf_do_transition(self._choice(forwards),
                                                 self._choice(D.COMMENTS_FORWARD)))
        if self.rnd.random() < 0.15:
            others = [u for u in self.actors if u != doc.owner_id]
            if others:
                self._safe('partage nominatif', lambda: doc.sudo().write({
                    'shared_user_ids': [(4, self._choice(others).id)]}))
                self._count('partages nominatifs')
        self._safe('datation', lambda: self._backdate_document(doc))
        return True

    def _backdate_document(self, doc):
        created = self._past(180)
        cr = self.env.cr
        cr.execute("UPDATE aite_ecm_document SET create_date=%s, write_date=%s "
                   "WHERE id=%s", (created, created + timedelta(days=1), doc.id))
        for i, version in enumerate(doc.version_ids.sorted('id')):
            when = created + timedelta(days=i * self.rnd.uniform(1, 20))
            cr.execute("UPDATE aite_ecm_document_version SET upload_date=%s, "
                       "create_date=%s WHERE id=%s", (when, when, version.id))
        doc.invalidate_recordset()

    # ================================================================== #
    # Dossiers métier (une unité = un dossier)
    # ================================================================== #
    def _unit_dossiers(self, index):
        kind = 'fournisseur' if index < self.counts['dossiers_fournisseur'] \
            else 'salarie'
        dtype = self._ref('aite_ecm_dossier.dossier_type_' + kind)
        agent = self._choice(self.agents)
        if kind == 'fournisseur':
            partner = self._choice(self.companies)
            name = "Agrément fournisseur — %s" % partner.name
            props = {'agr_categorie': self._choice(['fournitures', 'services',
                                                    'travaux', 'it']),
                     'agr_plafond': round(self.rnd.uniform(2e6, 2e8), -5),
                     'agr_validite': fields.Date.to_string(
                         (self.now + timedelta(days=365)).date())}
        else:
            partner = self._choice(self.persons)
            name = "Dossier du personnel — %s" % partner.name
            props = {'rh_matricule': "MAT-%04d" % self.rnd.randint(1, 9999),
                     'rh_date_embauche': fields.Date.to_string(
                         self._past(3000).date()),
                     'rh_poste': self._choice(
                         ["Comptable", "Assistante de direction", "Chauffeur",
                          "Développeur", "Chargé de clientèle", "Technicien réseau",
                          "Juriste", "Agent d'accueil"])}
        vals = {'name': name, 'type_id': dtype.id, 'partner_id': partner.id,
                'responsible_id': self._choice(self.agents + self.managers).id,
                'deadline': (self.now + timedelta(
                    days=self.rnd.randint(-20, 60))).date(),
                'properties': props}
        dossier = self._safe('création dossier', lambda: self._as(
            self.env['aite.ecm.dossier'], agent).create(vals))
        if dossier is None:
            return
        self._xmlid(dossier, 'dossier')
        self._count('dossiers %s' % kind)
        pieces = list(dossier.piece_ids)
        n_provided = self.rnd.choice([0, 1, 2, 3, len(pieces), len(pieces)])
        for piece in self.rnd.sample(pieces, min(n_provided, len(pieces))):
            if not piece.document_type_id:
                continue
            doc = self._create_document(
                piece.document_type_id.code, owner=agent,
                folder=dtype.folder_id or None, res=dossier, versions=1,
                title="%s — %s" % (piece.name, partner.name), props={},
                lines=["Dossier %s" % dossier.reference, "Pièce : %s" % piece.name],
                piece=piece)
            if doc is None:
                continue
            if not piece.document_id:
                piece.document_id = doc.id
            if self.rnd.random() < 0.5:
                piece.validated = True
            self._count('pièces de dossier')
        if self.rnd.random() < 0.2:
            return True
        if self._safe('ouverture dossier', lambda: self._as(dossier, agent)
                      .action_open()) is None:
            return True
        self._count('dossiers ouverts')
        if kind == 'fournisseur':
            self._advance_dossier(dossier)
        elif dossier.is_complete and self.rnd.random() < 0.5:
            manager = self._choice(self.managers)
            if self._safe('clôture', lambda: self._as(dossier, manager)
                          .action_close()) is not None:
                self._count('dossiers clôturés')
        self._safe('datation', lambda: self._backdate_dossier(dossier))
        return True

    def _advance_dossier(self, dossier):
        r = self.rnd.random()
        n = 0 if r < 0.3 else 1 if r < 0.6 else 2
        for _ in range(n):
            step = dossier.wf_step_id
            if dossier.wf_status != 'running' or not step:
                break
            forwards = step.outgoing_transitions().filtered(
                lambda t: t.direction == 'forward')
            if not forwards:
                break
            user = self._user_for_step(step)
            transition = self._choice(forwards)
            comment = self._choice(D.COMMENTS_FORWARD)
            if self._safe('transition dossier', lambda: self._as(dossier, user)
                          .wf_do_transition(transition, comment)) is None:
                break
            self._count('transitions dossier')
            if dossier.state == 'done':
                self._count('dossiers clôturés')
        if dossier.wf_status == 'running' and self.rnd.random() < 0.15:
            step = dossier.wf_step_id
            backs = step.outgoing_transitions().filtered(
                lambda t: t.direction != 'forward')
            if backs:
                user = self._user_for_step(step)
                back = self._choice(backs)
                comment = self._choice(D.COMMENTS_BACKWARD)
                if self._safe('retour dossier', lambda: self._as(dossier, user)
                              .wf_do_transition(back, comment)) is not None:
                    self._count('retours dossier')
        if dossier.wf_status == 'running' and self.rnd.random() < 0.06:
            user = self._user_for_step(dossier.wf_step_id)
            reason = self._choice(D.COMMENTS_REJECT)
            if self._safe('rejet dossier', lambda: self._as(dossier, user)
                          .action_wf_reject(reason)) is not None:
                self._count('dossiers rejetés')

    def _backdate_dossier(self, dossier):
        created = self._past(120)
        cr = self.env.cr
        cr.execute("UPDATE aite_ecm_dossier SET create_date=%s, date_open=%s "
                   "WHERE id=%s", (created, created.date(), dossier.id))
        t = created
        history = dossier.wf_history_ids.sorted('id')
        last = history[-1:] if history else history
        for line in history:
            entered = t
            left = None
            if line.left_date or line != last:
                t = t + timedelta(hours=self.rnd.uniform(2, 48))
                left = t
            cr.execute("UPDATE aite_workflow_history SET entered_date=%s, "
                       "left_date=%s WHERE id=%s", (entered, left, line.id))
        if dossier.wf_status == 'running' and dossier.wf_step_id.sla_hours:
            deadline = t + timedelta(hours=dossier.wf_step_id.sla_hours)
            if self.rnd.random() < 0.3:
                deadline = self.now - timedelta(hours=self.rnd.uniform(1, 72))
                self._count('dossiers en retard SLA')
            cr.execute("UPDATE aite_ecm_dossier SET wf_deadline=%s WHERE id=%s",
                       (deadline, dossier.id))
        dossier.invalidate_recordset()
        history.invalidate_recordset()

    # ================================================================== #
    # Relations, partages, réservations, corbeille (une unité chacune)
    # ================================================================== #
    def _unit_links(self, _index):
        Link = self.env['aite.ecm.document.link']
        types = self.env['aite.ecm.link.type'].search([])
        docs = list(self.documents.filtered(
            lambda d: d.type_id.code in ('CONTRAT', 'PROC', 'PV', 'DOC')))
        if len(docs) < 2 or not types:
            return True
        made, tries = 0, 0
        while made < self.counts['links'] and tries < self.counts['links'] * 4:
            tries += 1
            src, dst = self.rnd.sample(docs, 2)
            vals = {'document_id': src.id, 'target_id': dst.id,
                    'link_type_id': self._choice(types).id,
                    'note': self._choice(["", "", "Voir clause 4",
                                          "Ancienne version",
                                          "Pièce jointe au PV"])}
            link = self._safe('relation', lambda: Link.create(vals))
            if link is not None:
                self._xmlid(link, 'link')
                made += 1
        self._count('relations', made)
        return True

    def _unit_shares(self, _index):
        docs = list(self.documents.filtered(
            lambda d: d.latest_version_id and d.active))
        for doc in self.rnd.sample(docs, min(self.counts['shares'], len(docs))):
            r = self.rnd.random()
            expiry = self.now - timedelta(days=self.rnd.randint(1, 30)) if r < 0.2 \
                else self.now + timedelta(days=self.rnd.randint(1, 60))
            creator = doc.owner_id if doc.owner_id in self.users.values() \
                else self._choice(self.managers)
            vals = {'document_id': doc.id, 'name': "Partage — %s" % doc.reference,
                    'recipient': self._choice(self.partners).name,
                    'expiry_date': expiry,
                    'max_downloads': self._choice([0, 0, 3, 5, 10]),
                    'view_only': self.rnd.random() < 0.25,
                    'watermark': self.rnd.random() < 0.85,
                    'watermark_text': self._choice(D.SHARE_TEXTS)}
            share = self._safe('partage', lambda: self._as(
                self.env['aite.ecm.share'], creator).create(vals))
            if share is None:
                continue
            for _ in range(self.rnd.randint(0, 4)):
                if share._check_valid():
                    self._safe('accès partage', share._register_access)
                    self._count('accès par lien')
            if self.rnd.random() < 0.08:
                share.action_deactivate()
            self._xmlid(share, 'share')
            self._count('partages')
        return True

    def _unit_checkouts(self, _index):
        drafts = list(self.documents.filtered(
            lambda d: d.state == 'draft' and d.active and d.latest_version_id
            and not d.is_checked_out))
        for doc in self.rnd.sample(drafts, min(self.counts['checkouts'],
                                               len(drafts))):
            user = doc.owner_id if doc.owner_id in self.users.values() \
                else self._choice(self.managers)
            if self._safe('réservation', lambda: self._as(doc, user)
                          .action_checkout()) is None:
                continue
            self._count('réservations')
            if self.rnd.random() < 0.25:
                self.env.cr.execute(
                    "UPDATE aite_ecm_document SET checkout_date=%s, "
                    "checkout_expiry=%s WHERE id=%s",
                    (self.now - timedelta(days=5), self.now - timedelta(days=3),
                     doc.id))
                doc.invalidate_recordset()
                self._count('réservations expirées')
        return True

    def _unit_trash(self, _index):
        candidates = list(self.documents.filtered(
            lambda d: d.state == 'draft' and d.active and not d.is_checked_out
            and d.res_model != 'aite.ecm.dossier'))
        manager = self._choice(self.managers)
        for i, doc in enumerate(self.rnd.sample(
                candidates, min(self.counts['trashed'], len(candidates)))):
            if self._safe('corbeille', lambda: self._as(doc, manager)
                          .action_trash()) is None:
                continue
            self._count('documents en corbeille')
            if i < 6:
                self.env.cr.execute(
                    "UPDATE aite_ecm_document SET trashed_date=%s WHERE id=%s",
                    (self.now - timedelta(days=45), doc.id))
                doc.invalidate_recordset()
        return True

    def _unit_done(self, _index):
        return True

    # ================================================================== #
    # Identifiants externes (suppression à la désinstallation)
    # ================================================================== #
    def _register_xmlids(self):
        if not self.xmlids:
            return
        Data = self.env['ir.model.data']
        vals = [{'module': MODULE, 'name': name, 'model': model,
                 'res_id': res_id, 'noupdate': True}
                for model, res_id, name in self.xmlids]
        for i in range(0, len(vals), 500):
            Data.create(vals[i:i + 500])
        self._count('identifiants externes', len(vals))
        self.xmlids = []


def purge(env, log=None):
    """Supprime le jeu de données (équivalent de la désinstallation)."""
    log = log or (lambda m: _logger.info("[aite_ecm_demo] %s", m))
    env = env(su=True)
    Data = env['ir.model.data']
    order = ['aite.ecm.share', 'aite.ecm.document.link', 'aite.ecm.dossier',
             'aite.ecm.document', 'aite.courrier', 'aite.ecm.tag',
             'aite.ecm.folder', 'res.partner', 'hr.department', 'res.users']
    for model in order:
        entries = Data.search([('module', '=', MODULE), ('model', '=', model)])
        if not entries:
            continue
        records = env[model].with_context(active_test=False).browse(
            entries.mapped('res_id')).exists()
        if model == 'res.users':
            records.write({'active': False})
        else:
            records.unlink()
        entries.unlink()
        log("%s : %d supprimé(s)" % (model, len(records)))
    Param = env['ir.config_parameter']
    Param.set_param('aite_ecm_demo.seeded', False)
    Param.set_param(STATE_PARAM, False)
    log("Purge terminée.")
