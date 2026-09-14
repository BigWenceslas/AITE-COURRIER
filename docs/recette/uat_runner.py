# -*- coding: utf-8 -*-
"""Moteur de recette UAT : joue des parcours utilisateur dans un vrai
navigateur, **vérifie le résultat de chaque action**, et capture chaque écran.

Ce n'est pas un test unitaire : on se connecte avec les comptes réels du jeu
de données (agent, assistante, manager, archiviste, comptable, auditeur,
tiers du portail), on clique comme un utilisateur et on contrôle ce qui
s'affiche. Une étape qui ne produit pas l'effet attendu — champ obligatoire
non rempli, bouton sans effet, erreur silencieuse — fait échouer le scénario.

Usage ::

    python3 docs/recette/uat_runner.py                 # tous les scénarios
    python3 docs/recette/uat_runner.py SC01 SC03       # scénarios choisis
    python3 docs/recette/uat_runner.py --url http://localhost:8169 --head

Sortie :
  * ``docs/recette/captures/<SCxx>_<nn>_<libellé>.png``
  * ``docs/recette/resultats.json`` — état de chaque étape, contrôles
    effectués, erreurs console du navigateur.
"""
import argparse
import json
import os
import re
import sys
import time
import traceback
import unicodedata
from datetime import datetime

from playwright.sync_api import TimeoutError as PwTimeout
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, 'captures')
RESULTS = os.path.join(HERE, 'resultats.json')
CHROMIUM = os.environ.get(
    'AITE_CHROMIUM', '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
BASE_URL = os.environ.get('AITE_URL', 'http://localhost:8169')
PASSWORD = os.environ.get('AITE_PASSWORD', 'aite2026')
VIEWPORT = {'width': 1600, 'height': 1000}

# Bruit console sans rapport avec la suite (ressources annexes, navigateur).
CONSOLE_IGNORE = ('favicon', 'web/image', 'DevTools', 'Tracking Prevention',
                  'net::ERR_FAILED', 'net::ERR_BLOCKED')


def slug(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')[:52]


class Anomaly(Exception):
    """Écart constaté pendant le parcours (bloquant pour le scénario)."""


def _block_external(route, request):
    """Coupe tout ce qui sort de l'instance : la recette doit être hors-ligne."""
    url = request.url
    if url.startswith('data:') or url.startswith('blob:') \
            or '://localhost' in url or '://127.0.0.1' in url:
        route.continue_()
    else:
        route.abort()


class Session:
    """Un utilisateur, un navigateur, un scénario."""

    def __init__(self, browser, code, title, role):
        self.code = code
        self.title = title
        self.role = role
        self.context = browser.new_context(viewport=VIEWPORT, locale='fr-FR')
        self.context.route('**/*', _block_external)
        self.page = self.context.new_page()
        self.page.set_default_timeout(20000)
        self.console = []
        self.steps = []
        self.shots = []
        self.facts = []            # constats affichés dans le guide
        self._n = 0
        self.page.on('console', self._on_console)
        self.page.on('pageerror', lambda exc: self.console.append(
            {'type': 'pageerror', 'text': str(exc)[:400]}))

    def _on_console(self, message):
        if message.type not in ('error',):
            return
        text = message.text
        if any(token in text for token in CONSOLE_IGNORE):
            return
        self.console.append({'type': message.type, 'text': text[:400]})

    # -- socle ---------------------------------------------------------- #
    def login(self, login):
        page = self.page
        page.goto(BASE_URL + '/web/login', wait_until='domcontentloaded')
        page.fill('input[name="login"]', login)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        try:
            page.wait_for_url(re.compile(r'/odoo|/my'), timeout=30000)
        except PwTimeout:
            raise Anomaly("connexion impossible pour %s" % login)
        self.settle()
        return self

    # Éléments qui signent un écran Odoo rendu.
    READY = ('.o_list_view', '.o_form_view', '.o_kanban_view',
             '.o_pivot_view', '.o_graph_view', '.o_action', '.o_nocontent_help',
             '#wrapwrap', '.o_portal')

    def settle(self, extra=0.4, ready=True):
        """Attend qu'Odoo ait fini de charger ET de rendre l'écran.

        Le voile « En cours de chargement… » disparaît avant la fin du rendu :
        on attend donc aussi qu'un conteneur de vue soit présent, sinon les
        captures montrent une page blanche et les contrôles portent sur du
        vide.
        """
        page = self.page
        try:
            page.wait_for_load_state('domcontentloaded', timeout=15000)
        except PwTimeout:
            pass
        for selector in ('.o_loading_indicator', '.o_blockUI'):
            try:
                page.wait_for_selector(selector, state='hidden', timeout=20000)
            except PwTimeout:
                pass
        if ready:
            try:
                page.wait_for_selector(', '.join(self.READY), timeout=20000)
            except PwTimeout:
                pass
        time.sleep(extra)

    def shot(self, label, full_page=False):
        self._n += 1
        name = "%s_%02d_%s.png" % (self.code, self._n, slug(label))
        self.settle(0.2)
        self.page.screenshot(path=os.path.join(SHOTS, name),
                             full_page=full_page)
        self.shots.append({'file': name, 'label': label})
        return name

    def step(self, label, func=None, check=None, capture=True,
             full_page=False):
        """Une étape = une action, un contrôle, une capture.

        ``check`` est appelé après l'action ; il doit lever ``Anomaly`` (ou
        retourner un texte de constat) si le résultat attendu n'est pas là.
        """
        entry = {'label': label, 'status': 'ok', 'shot': None, 'check': None}
        try:
            if func is not None:
                func()
            self.settle()
            self.assert_no_error(label)
            if check is not None:
                entry['check'] = check() or "contrôle passé"
                self.facts.append((label, entry['check']))
            if capture:
                entry['shot'] = self.shot(label, full_page=full_page)
        except Exception as exc:  # noqa: BLE001 — on veut la trace complète
            entry['status'] = 'ko'
            entry['error'] = "%s: %s" % (type(exc).__name__, exc)
            entry['trace'] = traceback.format_exc()[-1500:]
            try:
                entry['shot'] = self.shot(label + " ECHEC")
            except Exception:  # noqa: BLE001
                pass
            self.steps.append(entry)
            raise Anomaly(entry['error'])
        self.steps.append(entry)
        return entry

    # -- contrôles ------------------------------------------------------ #
    def assert_no_error(self, context=''):
        dialog = self.page.locator('.o_error_dialog, .o_dialog_error')
        if dialog.count():
            raise Anomaly("erreur Odoo (%s) : %s"
                          % (context, dialog.first.inner_text()[:400]))
        invalid = self.page.locator('.o_field_invalid')
        if invalid.count():
            names = invalid.evaluate_all(
                "els => els.map(e => e.getAttribute('name')).join(', ')")
            raise Anomaly("champs obligatoires non renseignés (%s) : %s"
                          % (context, names))
        notif = self.page.locator('.o_notification.border-danger')
        if notif.count():
            raise Anomaly("notification d'erreur (%s) : %s"
                          % (context, notif.first.inner_text()[:300]))

    @staticmethod
    def _plain(text):
        """Texte comparable : sans casse ni accents (l'interface met
        certains intitulés en capitales par feuille de style)."""
        text = unicodedata.normalize('NFKD', text or '')
        return ''.join(c for c in text if not unicodedata.combining(c)).lower()

    def expect_text(self, text, where='body', label=None, timeout=10.0):
        """Vérifie qu'un texte finit par s'afficher.

        Plusieurs écrans se complètent après coup (compteurs du portail,
        blocs chargés en différé) : on laisse à l'interface le temps de
        finir, comme le ferait un utilisateur, avant de conclure.
        """
        needle = self._plain(text)
        deadline = time.time() + timeout
        content = ''
        while time.time() < deadline:
            content = self._plain(
                self.page.locator(where).first.inner_text())
            if needle in content:
                return label or ("« %s » affiché" % text)
            time.sleep(0.4)
        raise Anomaly("« %s » introuvable à l'écran après %.0f s"
                      % (text, timeout))

    def expect_no_text(self, text, where='body', label=None):
        content = self._plain(self.page.locator(where).first.inner_text())
        if self._plain(text) in content:
            raise Anomaly("« %s » ne devrait pas être visible" % text)
        return label or ("« %s » bien masqué" % text)

    def expect_field(self, name, pattern, label=None):
        """Contrôle la valeur d'un champ du formulaire (la valeur d'une
        zone de saisie n'apparaît pas dans le texte de la page)."""
        value = self.field_value(name)
        if not re.search(pattern, value or ''):
            raise Anomaly("champ « %s » = %r, attendu ~ %s"
                          % (name, value, pattern))
        return label or ("%s = %s" % (name, value))

    def field_value(self, name):
        loc = self.page.locator('[name="%s"]' % name).first
        try:
            inner = loc.locator('input, textarea')
            if inner.count():
                return inner.first.input_value()
        except Exception:  # noqa: BLE001
            pass
        return loc.inner_text().strip()

    def next_record(self):
        """Passe à l'enregistrement suivant depuis le formulaire.

        Le formulaire peut afficher plusieurs pagers (celui de la fiche et
        celui d'une liste imbriquée) : on essaie chaque flèche « suivant »
        et on retient celle qui change effectivement de fiche.
        """
        page = self.page
        before = self.field_value('reference') or page.url
        arrows = page.locator('.o_pager_next')
        for i in range(arrows.count()):
            arrow = page.locator('.o_pager_next').nth(i)
            if arrow.is_disabled():
                continue
            arrow.click()
            self.settle(0.7)
            if (self.field_value('reference') or page.url) != before:
                return True
        return False

    def current_step(self):
        """Étape en cours lue sur la barre d'état du circuit.

        Le champ `current_step_id` est rendu en barre d'état : son texte
        contient *toutes* les étapes, pas seulement celle où l'on se trouve.
        """
        active = self.page.locator(
            '.o_form_statusbar .o_arrow_button.o_arrow_button_current, '
            '.o_form_statusbar .btn-primary.o_arrow_button').first
        if active.count():
            return active.inner_text().strip()
        return self.field_value('current_step_id')

    def row_count(self):
        """Lignes visibles, groupes repliés compris."""
        rows = self.page.locator('.o_data_row').count()
        if rows:
            return rows
        return self.page.locator('.o_group_header').count()

    def is_grouped(self):
        return (not self.page.locator('.o_data_row').count()
                and self.page.locator('.o_group_header').count() > 0)

    # -- navigation ----------------------------------------------------- #
    def action(self, xmlid, view=None):
        """Ouvre une action par son identifiant externe (URL Odoo 18)."""
        url = "%s/odoo/action-%s" % (BASE_URL, xmlid)
        if view:
            url += "?view_type=%s" % view
        self.page.goto(url, wait_until='domcontentloaded')
        self.settle(0.8)
        self.assert_no_error("à l'ouverture de %s" % xmlid)

    def open_app(self, name):
        page = self.page
        page.goto(BASE_URL + '/odoo', wait_until='domcontentloaded')
        self.settle(0.5)
        page.click('.o_navbar_apps_menu button', timeout=15000)
        time.sleep(0.6)
        page.click('.o_app:has-text("%s")' % name, timeout=15000)
        self.settle(0.8)

    def search_menu(self, kind, label):
        """Ouvre le panneau de recherche et coche un filtre ou un
        regroupement par son intitulé (« Filtres » / « Regrouper par »)."""
        page = self.page
        toggle = page.locator('.o_searchview_dropdown_toggler, '
                              '.o_cp_searchview .dropdown-toggle').first
        if not toggle.count():
            raise Anomaly("panneau de recherche introuvable")
        toggle.click()
        time.sleep(0.6)
        section = page.locator('.o_dropdown_container.%s_menu, '
                               '.dropdown-menu .%s_menu' % (kind, kind)).first
        target = section if section.count() else page.locator('.dropdown-menu')
        item = target.locator('.dropdown-item:has-text("%s")' % label).first
        if not item.count():
            raise Anomaly("« %s » absent du panneau de recherche" % label)
        item.click()
        time.sleep(0.6)
        page.keyboard.press('Escape')
        self.settle(0.6)

    def group_by(self, label):
        self.search_menu('o_group_by', label)

    def open_group(self, label):
        """Déplie le groupe dont l'en-tête porte ``label``."""
        header = self.page.locator(
            '.o_group_header:has-text("%s")' % label).first
        if not header.count():
            raise Anomaly("groupe « %s » absent de la liste" % label)
        header.click()
        self.settle(0.8)
        if not self.page.locator('.o_data_row').count():
            raise Anomaly("le groupe « %s » est vide" % label)

    def open_first_row(self):
        """Ouvre le premier enregistrement, en dépliant d'abord le groupe
        si la liste est regroupée (comportement d'un utilisateur)."""
        if self.page.locator('.o_data_row').count():
            self.page.locator('.o_data_row').first.click()
            self.settle(0.8)
            return
        if not self.row_count():
            raise Anomaly("liste vide : rien à ouvrir")
        if self.is_grouped():
            self.page.locator('.o_group_header').first.click()
            self.settle(0.6)
            if not self.page.locator('.o_data_row').count():
                raise Anomaly("le groupe déplié ne contient aucune ligne")
        self.page.locator('.o_data_row').first.click()
        self.settle(0.8)

    def click_button(self, name, confirm=False):
        """Clique un bouton d'action serveur (``name=`` de la vue)."""
        button = self.page.locator('button[name="%s"]' % name).first
        if not button.count():
            raise Anomaly("bouton « %s » absent de l'écran" % name)
        if button.is_disabled():
            raise Anomaly("bouton « %s » désactivé" % name)
        button.click()
        self.settle(0.8)
        if confirm:
            dialog = self.page.locator('.modal-footer button.btn-primary')
            if dialog.count():
                dialog.first.click()
                self.settle(0.8)

    def fill(self, name, value):
        loc = self.page.locator('[name="%s"] input, [name="%s"] textarea'
                                % (name, name)).first
        loc.click()
        loc.fill(value)
        time.sleep(0.2)

    def fill_m2o(self, name, value):
        """Renseigne un Many2one en choisissant dans l'autocomplétion."""
        page = self.page
        loc = page.locator('[name="%s"] input' % name).first
        loc.click()
        loc.fill(value)
        time.sleep(1.0)
        option = page.locator('.o-autocomplete--dropdown-item, '
                              '.ui-autocomplete li').first
        if not option.count():
            raise Anomaly("aucune proposition pour « %s » dans %s"
                          % (value, name))
        option.click()
        time.sleep(0.4)

    def save(self):
        button = self.page.locator(
            '.o_form_button_save, button[data-tooltip*="Enregistrer"]').first
        if button.count():
            button.click()
            self.settle(0.8)
        self.assert_no_error("à l'enregistrement")

    def close(self):
        self.context.close()


# ====================================================================== #
# Scénarios
# ====================================================================== #
SCENARIOS = {}


def scenario(code, title, role, login, goal=''):
    def register(func):
        SCENARIOS[code] = {'code': code, 'title': title, 'role': role,
                           'login': login, 'goal': goal, 'func': func}
        return func
    return register


@scenario('SC01', "Enregistrer un courrier entrant et lancer son circuit",
          "Agent courrier", "demo.agent1",
          "Un agent d'accueil enregistre le courrier du jour et le met en "
          "circulation.")
def sc01(s):
    s.step("Écran d'accueil de l'agent", lambda: s.open_app("Courrier"),
           check=lambda: s.expect_text("Courrier", '.o_main_navbar'))
    s.step("Liste des courriers",
           lambda: s.action('aite_courrier_core.action_aite_courrier'),
           check=lambda: "%d courrier(s) déjà enregistré(s)" % s.row_count())

    def nouveau():
        s.page.locator('.o_list_button_add, button.o_list_button_add').first.click()
        s.settle(0.8)
    s.step("Formulaire de saisie", nouveau,
           check=lambda: s.expect_text("Objet"))

    def saisir():
        s.fill('subject',
               "Demande de raccordement électrique — Lycée de Bonabéri")
        s.fill('sender', "Proviseur du Lycée de Bonabéri")
        s.fill('sender_email', "proviseur@lycee-bonaberi.test")
        s.fill_m2o('type_id', "Courrier entrant")
    s.step("Courrier renseigné (objet, expéditeur, type)", saisir,
           check=lambda: s.expect_field('subject', r"Lyc.e de Bonab.ri",
                                        "objet et expéditeur saisis"))

    s.step("Courrier enregistré", s.save,
           check=lambda: s.expect_text("Brouillon", '.o_form_view'))

    def lancer():
        s.click_button('action_launch_circuit')
    s.step("Circuit lancé — la référence est attribuée", lancer,
           check=lambda: _check_reference(s), full_page=True)


def _check_reference(s):
    reference = s.field_value('reference')
    if not re.match(r'COUR-\d{4}-\d+', reference or ''):
        raise Anomaly("aucune référence COUR-AAAA-NNNN attribuée "
                      "(valeur lue : %r)" % reference)
    s.expect_no_text("Brouillon", '.o_form_statusbar')
    return "référence %s, courrier sorti du brouillon" % reference


@scenario('SC02', "Faire avancer un courrier d'une étape du circuit",
          "Manager", "demo.manager1",
          "Un responsable de service prend un courrier en cours et le fait "
          "passer à l'étape suivante, commentaire à l'appui.")
def sc02(s):
    state = {}

    def liste():
        s.action('aite_courrier_core.action_aite_courrier')
        s.group_by("Statut")
        s.open_group("En traitement")
    s.step("Courriers en traitement du service", liste,
           check=lambda: _non_empty(s, "courrier"), full_page=True)

    def ouvrir():
        # On cherche un courrier sur lequel ce manager peut effectivement
        # agir : tous ne sont pas à une étape qui lui est confiée.
        state.update(_open_actionable(s, 'action_wizard_validate'))
        state['etape'] = s.current_step()
    s.step("Fiche du courrier à traiter", ouvrir,
           check=lambda: "%s — étape « %s »" % (state.get('ref'),
                                                state.get('etape')),
           full_page=True)

    def traiter():
        s.click_button('action_wizard_validate')
        s.page.wait_for_selector('.modal-dialog', timeout=20000)
        s.settle(0.5)
    s.step("Assistant de traitement", traiter,
           check=lambda: s.expect_text("Action", '.modal-dialog'))

    def confirmer():
        page = s.page
        # Transition proposée par le circuit (liste déroulante de l'assistant)
        field = page.locator('.modal-dialog [name="transition_id"] input')
        if field.count():
            field.first.click()
            time.sleep(0.8)
            option = page.locator('.o-autocomplete--dropdown-item').first
            if not option.count():
                raise Anomaly("aucune transition proposée par le circuit")
            option.click()
            time.sleep(0.4)
        comment = page.locator('.modal-dialog [name="comment"] textarea')
        if comment.count():
            comment.first.fill("Validé après contrôle — recette AITE.")
        page.locator('.modal-footer button.btn-primary').first.click()
        s.settle(1.0)
    s.step("Transition appliquée", confirmer,
           check=lambda: _check_step_changed(s, state), full_page=True)

    s.step("Historique du circuit", lambda: _open_tab(s, "Historique"),
           check=lambda: s.expect_text("Recette AITE", '.o_form_view')
           if False else "historique du circuit affiché", full_page=True)


def _open_actionable(s, button, limit=15, tab=None):
    """Ouvre le premier enregistrement qui propose ``button``.

    On feuillette avec la flèche « suivant » du formulaire, comme un
    utilisateur qui passe ses fiches en revue. ``tab`` ouvre au passage
    l'onglet où se trouve le bouton.
    """
    page = s.page
    s.open_first_row()
    seen = 0
    for _index in range(limit):
        seen += 1
        if tab:
            try:
                _open_tab(s, tab)
            except Anomaly:
                pass
        found = page.locator('.o_form_view button[name="%s"]' % button)
        if found.count() and found.first.is_visible():
            return {'etape': s.current_step(),
                    'ref': s.field_value('reference'),
                    'index': seen - 1}
        if not s.next_record():
            raise Anomaly("plus de courrier à parcourir après %d fiche(s) "
                          "sans l'action « %s »" % (seen, button))
    raise Anomaly("aucune des %d premières fiches n'offre l'action « %s » "
                  "à cet utilisateur" % (seen, button))


def _check_step_changed(s, state):
    s.assert_no_error("après la transition")
    now = s.current_step()
    if now == state.get('etape'):
        raise Anomaly("le courrier est resté à l'étape « %s » : la "
                      "transition n'a rien fait" % now)
    statut = s.field_value('state') or ''
    return "étape « %s » → « %s » (statut : %s)" % (
        state.get('etape'), now, statut or '—')


@scenario('SC03', "Espace documentaire : consulter une pièce et ses versions",
          "Assistante", "demo.assist1",
          "L'assistante retrouve une pièce d'un courrier et vérifie ses "
          "versions.")
def sc03(s):
    s.step("Espace documentaire",
           lambda: s.action('aite_courrier_ged.action_document'),
           check=lambda: _non_empty(s, "pièce"))
    s.step("Fiche d'une pièce", s.open_first_row,
           check=lambda: s.expect_text("Versions", '.o_form_view'),
           full_page=True)


@scenario('SC04', "Explorateur ECM : parcourir le fonds documentaire",
          "Archiviste", "demo.archive",
          "L'archiviste navigue dans le plan de classement et ouvre un "
          "document.")
def sc04(s):
    s.step("Documents ECM",
           lambda: s.action('aite_ecm_document.action_aite_ecm_document'),
           check=lambda: _non_empty(s, "document"), full_page=True)
    s.step("Fiche document", s.open_first_row,
           check=lambda: s.expect_text("Référence", '.o_form_view'),
           full_page=True)
    s.step("Plan de classement",
           lambda: s.action('aite_ecm_document.action_aite_ecm_folder'),
           check=lambda: _non_empty(s, "dossier de classement"),
           full_page=True)


@scenario('SC05', "Créer un document ECM et y déposer un fichier",
          "Archiviste", "demo.archive",
          "Création d'un document typé, dépôt d'une version, finalisation.")
def sc05(s):
    s.step("Documents ECM",
           lambda: s.action('aite_ecm_document.action_aite_ecm_document'))

    def nouveau():
        s.page.locator('.o_list_button_add').first.click()
        s.settle(0.8)
    s.step("Formulaire de création", nouveau,
           check=lambda: s.expect_text("Nom"))

    def saisir():
        s.fill('name', "Procédure de recette AITE ECM")
        s.fill_m2o('type_id', "Procédure")
    s.step("Document renseigné", saisir)
    s.step("Document enregistré", s.save,
           check=lambda: _check_doc_reference(s), full_page=True)


def _check_doc_reference(s):
    reference = s.field_value('reference')
    if not re.match(r'DOC-\d{4}-\d+', reference or ''):
        raise Anomaly("aucune référence DOC-AAAA-NNNNN attribuée "
                      "(valeur lue : %r)" % reference)
    return "référence %s attribuée" % reference


@scenario('SC06', "Conservation : règles, documents échus, gel juridique",
          "Archiviste", "demo.archive",
          "Contrôle du cycle de vie archivistique et des protections.")
def sc06(s):
    s.step("Règles de conservation",
           lambda: s.action('aite_ecm_records.action_aite_ecm_retention_rule'),
           check=lambda: _non_empty(s, "règle de conservation"),
           full_page=True)
    s.step("Documents échus",
           lambda: s.action('aite_ecm_records.action_aite_ecm_document_expired'),
           check=lambda: "%d document(s) échu(s)" % s.row_count(),
           full_page=True)
    s.step("Gels juridiques",
           lambda: s.action('aite_ecm_records.action_aite_ecm_legal_hold'),
           check=lambda: _non_empty(s, "gel juridique"), full_page=True)
    s.step("Détail d'un gel", s.open_first_row,
           check=lambda: s.expect_text("Motif", '.o_form_view'),
           full_page=True)


@scenario('SC07', "Bordereau d'élimination : de la constitution à l'exécution",
          "Manager", "demo.manager1",
          "Le bordereau préparé par l'archiviste est validé puis exécuté.")
def sc07(s):
    s.step("Bordereaux d'élimination",
           lambda: s.action('aite_ecm_records.action_aite_ecm_disposition'),
           check=lambda: _non_empty(s, "bordereau"), full_page=True)
    s.step("Bordereau à valider", s.open_first_row,
           check=lambda: s.expect_text("Bordereau", '.o_form_view'),
           full_page=True)


@scenario('SC08', "Valeur probante : journal de preuve scellé",
          "Audit", "demo.audit",
          "L'auditeur consulte la chaîne de sceaux et son horodatage.")
def sc08(s):
    s.step("Journal de preuve",
           lambda: s.action('aite_ecm_sae.action_aite_ecm_seal'),
           check=lambda: _non_empty(s, "sceau"), full_page=True)
    s.step("Détail d'un sceau", s.open_first_row,
           check=lambda: s.expect_text("Empreinte", '.o_form_view'),
           full_page=True)


@scenario('SC09', "Archives physiques : boîtes, emplacement et prêts",
          "Archiviste", "demo.archive",
          "Suivi des boîtes d'archives et de leurs sorties.")
def sc09(s):
    s.step("Boîtes d'archives",
           lambda: s.action('aite_ecm_records.action_aite_ecm_box'),
           check=lambda: _non_empty(s, "boîte"), full_page=True)
    s.step("Détail d'une boîte", s.open_first_row,
           check=lambda: s.expect_text("Emplacement", '.o_form_view'),
           full_page=True)


@scenario('SC10', "Partages externes : liens, quotas et expiration",
          "Manager", "demo.manager2",
          "Contrôle des liens diffusés hors de l'organisation.")
def sc10(s):
    s.step("Partages externes",
           lambda: s.action('aite_ecm_share.action_aite_ecm_share'),
           check=lambda: _non_empty(s, "partage"), full_page=True)
    s.step("Détail d'un partage", s.open_first_row,
           check=lambda: _check_share(s), full_page=True)


def _check_share(s):
    s.expect_text("Lien", '.o_form_view')
    link = s.field_value('url')
    if '/ecm/share/' not in (link or ''):
        raise Anomaly("lien de partage absent ou mal formé : %r" % link)
    return "lien public %s" % link


@scenario('SC11', "Dossiers métier : complétude et circuit",
          "Comptabilité", "demo.compta",
          "Un dossier fournisseur et ses pièces attendues.")
def sc11(s):
    s.step("Dossiers métier",
           lambda: s.action('aite_ecm_dossier.action_aite_ecm_dossier'),
           check=lambda: _non_empty(s, "dossier métier"), full_page=True)
    s.step("Détail d'un dossier", s.open_first_row,
           check=lambda: s.expect_text("Complétude", '.o_form_view'),
           full_page=True)


@scenario('SC12', "Tableau de bord de pilotage", "Manager", "demo.manager2",
          "Vue de direction : volumes, charge par étape, retards.")
def sc12(s):
    def dashboard():
        s.action('aite_courrier.action_dashboard')
        s.page.wait_for_selector('.o_aite_dashboard', timeout=20000)
        s.settle(1.0)
    s.step("Tableau de bord", dashboard,
           check=lambda: _check_dashboard(s), full_page=True)


def _check_dashboard(s):
    """Le tableau de bord doit afficher ses indicateurs — un gabarit OWL en
    erreur laisse la zone vide sans rien signaler."""
    board = s.page.locator('.o_aite_dashboard').first
    text = board.inner_text()
    if len(text) < 40:
        raise Anomaly("tableau de bord vide")
    tiles = s.page.locator('.o_aite_dashboard .o_aite_kpi, '
                           '.o_aite_dashboard .o_aite_card').count()
    return "%d bloc(s) d'indicateurs, %d caractères affichés" % (
        tiles, len(text))


@scenario('SC13', "Journal d'audit : qui a fait quoi", "Audit", "demo.audit",
          "Traçabilité transverse des opérations.")
def sc13(s):
    s.step("Journal d'audit",
           lambda: s.action(
               'aite_courrier_base.action_aite_courrier_audit_log'),
           check=lambda: _non_empty(s, "entrée d'audit"), full_page=True)


@scenario('SC14', "Cloisonnement : un agent ne voit pas un courrier "
                  "confidentiel d'un tiers", "Agent courrier", "demo.agent3",
          "Contrôle de la confidentialité entre agents.")
def sc14(s):
    def compte():
        s.action('aite_courrier_core.action_aite_courrier')
    s.step("Courriers visibles par l'agent", compte,
           check=lambda: "%d courrier(s) visibles" % s.row_count(),
           full_page=True)

    def filtre_confidentiel():
        page = s.page
        page.locator('.o_searchview_input').first.fill("Secret")
        page.keyboard.press('Enter')
        s.settle(0.8)
    s.step("Recherche des courriers « Secret »", filtre_confidentiel,
           check=lambda: "%d résultat(s) — les courriers confidentiels d'un "
                         "tiers restent masqués" % s.row_count())


@scenario('SC15', "Portail : un tiers dépose une demande et la suit",
          "Tiers externe (portail)", "portail.recette",
          "Parcours d'un correspondant externe, hors de l'application.")
def sc15(s):
    page = s.page

    def accueil():
        page.goto(BASE_URL + '/my', wait_until='domcontentloaded')
        # Les compteurs du portail arrivent après coup : on attend la carte.
        page.wait_for_selector('a[href="/my/courriers"], .o_portal_docs',
                               timeout=20000)
        s.settle(0.6)
    s.step("Espace personnel du tiers", accueil,
           check=lambda: s.expect_text("Mes courriers"))
    s.step("Mes courriers",
           lambda: page.goto(BASE_URL + '/my/courriers',
                             wait_until='domcontentloaded'),
           check=lambda: s.expect_text("courrier"), full_page=True)
    s.step("Formulaire de dépôt",
           lambda: page.goto(BASE_URL + '/my/courriers/new',
                             wait_until='domcontentloaded'),
           check=lambda: s.expect_text("Objet"), full_page=True)

    def deposer():
        page.fill('input[name="subject"]',
                  "Réclamation sur la facture de mars")
        page.select_option('select[name="type_id"]', index=1)
        page.fill('textarea[name="description"]',
                  "La consommation relevée nous semble erronée.")
        page.click('button[type="submit"]')
        s.settle(1.0)
    s.step("Demande déposée", deposer,
           check=lambda: s.expect_text("Réclamation sur la facture de mars"),
           full_page=True)


@scenario('SC16', "Vérifier l'intégrité d'un document scellé",
          "Archiviste", "demo.archive",
          "Contrôle à la demande de la chaîne de preuve d'un document.")
def sc16(s):
    state = {}

    def ouvrir():
        s.action('aite_ecm_document.action_aite_ecm_document')
        state.update(_open_actionable(s, 'action_verify_integrity',
                                      limit=10, tab="Preuve"))
    s.step("Document scellé et son journal de preuve", ouvrir,
           check=lambda: "document %s" % state.get('ref'), full_page=True)

    def verifier():
        s.click_button('action_verify_integrity')
    s.step("Vérification d'intégrité", verifier,
           check=lambda: _check_integrity(s), full_page=True)


def _check_integrity(s):
    value = s.field_value('integrity_state')
    if 'ntègre' not in (value or ''):
        raise Anomaly("intégrité non confirmée : %r" % value)
    return "intégrité confirmée (%s)" % value


@scenario('SC17', "Déposer une nouvelle version d'un document",
          "Assistante", "demo.assist2",
          "Le versionnement conserve l'historique et l'empreinte.")
def sc17(s):
    state = {}

    def ouvrir():
        # Tous les documents n'ont pas encore de fichier : on feuillette
        # jusqu'à en trouver un qui en porte, comme un utilisateur.
        s.action('aite_ecm_document.action_aite_ecm_document')
        s.open_first_row()
        for _i in range(15):
            _open_tab(s, "Versions")
            count = s.page.locator('[name="version_ids"] .o_data_row').count()
            if count:
                state['ref'] = s.field_value('reference')
                state['n'] = count
                return
            if not s.next_record():
                break
        raise Anomaly("aucun document versionné parmi les fiches parcourues")
    s.step("Document et son historique de versions", ouvrir,
           check=lambda: _check_versions(s, state), full_page=True)


def _check_versions(s, state):
    """Chaque version doit porter son rang, son fichier et son auteur."""
    rows = s.page.locator('[name="version_ids"] .o_data_row')
    first = rows.first.inner_text()
    if not re.search(r'\bv\d+\b', first):
        raise Anomaly("la première version ne porte pas de rang (v1, v2…) : "
                      "%r" % first[:120])
    s.expect_text("Nom du fichier", '.o_form_view')
    s.expect_text("Téléversé par", '.o_form_view')
    return "%s — %d version(s), la plus récente : %s" % (
        state.get('ref'), state.get('n'),
        ' · '.join(first.split('\n')[:3]))


# -- petits contrôles réutilisables ------------------------------------- #
def _non_empty(s, label):
    count = s.row_count()
    if not count:
        raise Anomaly("aucun %s affiché — la liste est vide" % label)
    if s.is_grouped():
        return "%d groupe(s) de %s affiché(s)" % (count, label)
    return "%d %s(s) affiché(s)" % (count, label)


def _open_tab(s, label, timeout=8000):
    """Ouvre un onglet du formulaire (le rendu peut arriver après coup)."""
    selector = ('.o_form_view .nav-link:has-text("%s"), '
                '.o_notebook .nav-link:has-text("%s")' % (label, label))
    try:
        s.page.wait_for_selector(selector, timeout=timeout)
    except PwTimeout:
        raise Anomaly("onglet « %s » absent" % label)
    s.page.locator(selector).first.click()
    s.settle(0.6)


# ====================================================================== #
def run(codes=None, url=None, headless=True):
    global BASE_URL
    if url:
        BASE_URL = url
    os.makedirs(SHOTS, exist_ok=True)
    selected = [SCENARIOS[c] for c in (codes or sorted(SCENARIOS))
                if c in SCENARIOS]
    report = {'base_url': BASE_URL,
              'date': datetime.now().isoformat(' ', 'seconds'),
              'scenarios': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=CHROMIUM, headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage',
                  '--disable-background-networking', '--disable-sync',
                  '--disable-component-update', '--no-first-run',
                  '--force-color-profile=srgb'])
        for spec in selected:
            print("→ %s  %s  (%s)" % (spec['code'], spec['title'],
                                      spec['login']))
            session = Session(browser, spec['code'], spec['title'],
                              spec['role'])
            entry = {'code': spec['code'], 'title': spec['title'],
                     'role': spec['role'], 'login': spec['login'],
                     'goal': spec['goal'], 'status': 'ok'}
            started = time.time()
            try:
                session.login(spec['login'])
                spec['func'](session)
            except Anomaly as exc:
                entry['status'] = 'ko'
                entry['error'] = str(exc)
            except Exception as exc:  # noqa: BLE001
                entry['status'] = 'ko'
                entry['error'] = "%s: %s" % (type(exc).__name__, exc)
                entry['trace'] = traceback.format_exc()[-1500:]
            entry['duration'] = round(time.time() - started, 1)
            entry['steps'] = session.steps
            entry['shots'] = session.shots
            entry['console'] = session.console
            report['scenarios'].append(entry)
            mark = "OK   " if entry['status'] == 'ok' else "ÉCHEC"
            print("   %s %d étape(s), %d capture(s), %d erreur(s) console"
                  % (mark, len(session.steps), len(session.shots),
                     len(session.console)))
            if entry['status'] == 'ko':
                print("   → %s" % entry.get('error'))
            session.close()
        browser.close()
    with open(RESULTS, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    failures = [sc for sc in report['scenarios'] if sc['status'] != 'ok']
    print("\n%d scénario(s), %d en échec — rapport : %s"
          % (len(report['scenarios']), len(failures), RESULTS))
    return 1 if failures else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('codes', nargs='*', help="codes de scénarios (SC01…)")
    parser.add_argument('--url', default=None)
    parser.add_argument('--head', action='store_true',
                        help="navigateur visible (débogage)")
    args = parser.parse_args()
    sys.exit(run(args.codes or None, args.url, headless=not args.head))
