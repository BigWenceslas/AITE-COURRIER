#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère la version PDF du dossier de recette, captures d'écran comprises.

    python3 docs/uat/scripts/generer_pdf.py

Produit ``docs/uat/DOSSIER_UAT.pdf`` à partir de ``docs/uat/DOSSIER_UAT.md``.

Le Markdown est converti en HTML autonome — les captures de ``docs/uat/captures/``
sont incorporées en base64 — puis imprimé par Chromium sans affichage. Les
captures référencées dans un chapitre sont regroupées en planche à la fin de ce
chapitre, chacune sous son étiquette de scénario.

Dépendances : ``playwright`` et un Chromium installé. Aucun convertisseur
Markdown externe n'est requis : le sous-ensemble utilisé par le dossier est géré
ici (titres, tableaux, listes, blocs de code, citations, emphase, code en ligne).
"""
import base64
import html
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UAT = ROOT / 'docs' / 'uat'
SOURCE = UAT / 'DOSSIER_UAT.md'
CAPTURES = UAT / 'captures'
TARGET = UAT / 'DOSSIER_UAT.pdf'

# Légendes des planches de captures, par identifiant de fichier.
LEGENDES = {
    '00_accueil': "Écran d'accueil après connexion",
    'sc01_01_analyse_courrier': "SC-01.1 — Courrier › Analyse",
    'sc01_02_tableau_de_bord': "SC-01.2 — Tableau de bord du courrier",
    'sc01_03_liste_courriers': "SC-01.3 — Liste des courriers",
    'sc01_04_fiche_courrier': "SC-01.4 — Fiche courrier",
    'sc01_05_pieces_courrier': "SC-01.5 — Pièces du courrier",
    'sc01_06_historique_etapes': "SC-01.6 — Historique des étapes",
    'sc01_07_journal_audit': "SC-01.7 — Journal d'audit",
    'sc02_01_explorateur': "SC-02.1 — Explorateur documentaire",
    'sc02_02_liste_documents': "SC-02.2 — Tous les documents",
    'sc02_03_fiche_document': "SC-02.3 — Fiche document",
    'sc02_04_versions': "SC-02.4 — Versions et empreintes SHA-256",
    'sc02_05_relations': "SC-02.5 — Relations entre documents",
    'sc02_06_conservation': "SC-02.6 — Onglet Conservation",
    'sc02_07_preuve': "SC-02.7 — Onglet Preuve",
    'sc03_01_plan_classement': "SC-03.1 — Plan de classement",
    'sc04_01_dossiers_metier': "SC-04.1 — Dossiers métier",
    'sc04_02_fiche_dossier': "SC-04.2 — Fiche dossier et complétude",
    'sc05_01_partages': "SC-05.1 — Partages externes",
    'sc06_01_regles_conservation': "SC-06.1 — Règles de conservation",
    'sc06_02_documents_echus': "SC-06.2 — Documents échus",
    'sc06_03_gels_juridiques': "SC-06.3 — Gels juridiques",
    'sc06_04_bordereaux': "SC-06.4 — Bordereaux d'élimination",
    'sc06_05_archives_physiques': "SC-06.5 — Archives physiques",
    'sc07_01_journal_preuve': "SC-07.1 — Journal de preuve",
    'sc07_02_export_seda': "SC-07.2 — Export SEDA 2.1",
    'sc08_01_circuits': "SC-08.1 — Circuits de traitement",
    'sc08_02_types_documents': "SC-08.2 — Types de documents",
    'sc08_03_corbeille': "SC-08.3 — Corbeille",
    'sc08_04_analyse_fonds': "SC-08.4 — Analyse du fonds",
    'sc11_00_webdav_racine': "SC-11.0 — Racine du lecteur réseau WebDAV",
    'sc11_01_webdav_navigation': "SC-11.1 — Navigation dans un dossier WebDAV",
    'sc12_01_vue_agent': "SC-12.1 — Vue restreinte de l'agent",
    'sc12_02_menus_agent': "SC-12.2 — Menus de l'agent",
    'sc13_01_sceau': "SC-13.1 — Détail d'un sceau de preuve",
    'sc14_01_parametres': "SC-14.1 — Paramètres ECM",
}


# --------------------------------------------------------------------------- #
# Markdown → HTML
# --------------------------------------------------------------------------- #
def inline(text):
    """Emphase, code en ligne et liens, sans toucher au contenu du code."""
    jetons = []

    def garder(match):
        jetons.append('<code>%s</code>' % html.escape(match.group(1)))
        return '\x00%d\x00' % (len(jetons) - 1)

    text = re.sub(r'`([^`]+)`', garder, text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: jetons[int(m.group(1))], text)


def cellules(ligne):
    return [c.strip() for c in ligne.strip().strip('|').split('|')]


class Convertisseur:
    """Analyseur ligne à ligne du sous-ensemble Markdown employé par le dossier."""

    def __init__(self, lignes):
        self.lignes = lignes
        self.i = 0
        self.sortie = []
        self.chapitre = []          # captures citées dans le chapitre courant
        self.vues = set()           # captures déjà présentées

    def convertir(self):
        while self.i < len(self.lignes):
            ligne = self.lignes[self.i]
            if ligne.startswith('```'):
                self.bloc_code()
            elif ligne.startswith('#'):
                self.titre(ligne)
            elif ligne.startswith('>'):
                self.citation()
            elif ligne.startswith('|'):
                self.tableau()
            elif re.match(r'^\s*(\d+\.|[-*])\s+', ligne):
                self.liste()
            elif ligne.strip() in ('---', '***', '___'):
                self.i += 1         # séparateur : rendu par les titres
            elif ligne.strip():
                self.paragraphe()
            else:
                self.i += 1
        self.vider_planche()
        return '\n'.join(self.sortie)

    # -- blocs ------------------------------------------------------------- #
    def bloc_code(self):
        langue = self.lignes[self.i][3:].strip()
        self.i += 1
        corps = []
        while self.i < len(self.lignes) and not self.lignes[self.i].startswith('```'):
            corps.append(self.lignes[self.i])
            self.i += 1
        self.i += 1
        self.sortie.append('<pre class="code %s"><code>%s</code></pre>'
                           % (html.escape(langue), html.escape('\n'.join(corps))))

    def titre(self, ligne):
        niveau = len(ligne) - len(ligne.lstrip('#'))
        texte = ligne[niveau:].strip()
        if niveau <= 2:
            self.vider_planche()
        self.reperer_captures(texte)
        ancre = re.sub(r'[^a-z0-9]+', '-', texte.lower()).strip('-')[:60]
        classe = ' class="rupture"' if niveau == 2 else ''
        self.sortie.append('<h%d id="%s"%s>%s</h%d>'
                           % (niveau, ancre, classe, inline(texte), niveau))
        self.i += 1

    def citation(self):
        corps = []
        while self.i < len(self.lignes) and self.lignes[self.i].startswith('>'):
            corps.append(self.lignes[self.i].lstrip('>').strip())
            self.i += 1
        texte = ' '.join(corps)
        self.reperer_captures(texte)
        self.sortie.append('<blockquote>%s</blockquote>' % inline(texte))

    def tableau(self):
        lignes = []
        while self.i < len(self.lignes) and self.lignes[self.i].startswith('|'):
            lignes.append(self.lignes[self.i])
            self.i += 1
        if len(lignes) < 2:
            return
        entete = cellules(lignes[0])
        corps = [cellules(l) for l in lignes[2:]]
        self.reperer_captures(' '.join(lignes))
        html_ = ['<table><thead><tr>']
        html_ += ['<th>%s</th>' % inline(c) for c in entete]
        html_.append('</tr></thead><tbody>')
        for rang in corps:
            html_.append('<tr>%s</tr>'
                         % ''.join('<td>%s</td>' % inline(c) for c in rang))
        html_.append('</tbody></table>')
        self.sortie.append(''.join(html_))

    def liste(self):
        premiere = self.lignes[self.i]
        ordonnee = bool(re.match(r'^\s*\d+\.', premiere))
        balise = 'ol' if ordonnee else 'ul'
        elements, courant = [], None
        motif = r'^\s*(?:\d+\.|[-*])\s+(.*)$'
        while self.i < len(self.lignes):
            ligne = self.lignes[self.i]
            debut = re.match(motif, ligne)
            if debut:
                if courant is not None:
                    elements.append(courant)
                courant = debut.group(1)
            elif ligne.strip() and ligne.startswith(('  ', '\t')) and courant is not None:
                courant += ' ' + ligne.strip()      # continuation indentée
            else:
                break
            self.i += 1
        if courant is not None:
            elements.append(courant)
        self.reperer_captures(' '.join(elements))
        self.sortie.append('<%s>%s</%s>'
                           % (balise,
                              ''.join('<li>%s</li>' % inline(e) for e in elements),
                              balise))

    def paragraphe(self):
        corps = []
        while self.i < len(self.lignes) and self.lignes[self.i].strip() \
                and not self.lignes[self.i].startswith(('|', '>', '#', '```')) \
                and not re.match(r'^\s*(\d+\.|[-*])\s+', self.lignes[self.i]) \
                and self.lignes[self.i].strip() not in ('---', '***', '___'):
            ligne = self.lignes[self.i]
            # Deux espaces en fin de ligne = retour à la ligne forcé (Markdown).
            corps.append(ligne.strip() + ('\x01' if ligne.endswith('  ') else ''))
            self.i += 1
        texte = ' '.join(corps)
        self.reperer_captures(texte)
        self.sortie.append('<p>%s</p>'
                           % inline(texte).replace('\x01 ', '<br/>')
                                          .replace('\x01', ''))

    # -- planches de captures ---------------------------------------------- #
    def reperer_captures(self, texte):
        for nom in re.findall(r'([A-Za-z0-9_]+)\.png', texte):
            if nom not in self.vues and (CAPTURES / (nom + '.png')).exists():
                self.vues.add(nom)
                self.chapitre.append(nom)

    def vider_planche(self):
        if not self.chapitre:
            return
        self.sortie.append('<section class="planche"><h3>Captures de référence</h3>')
        for nom in self.chapitre:
            chemin = CAPTURES / (nom + '.png')
            mime = mimetypes.guess_type(chemin.name)[0] or 'image/png'
            donnees = base64.b64encode(chemin.read_bytes()).decode('ascii')
            self.sortie.append(
                '<figure><img src="data:%s;base64,%s" alt="%s"/>'
                '<figcaption>%s <span class="fichier">%s.png</span></figcaption>'
                '</figure>'
                % (mime, donnees, html.escape(nom),
                   html.escape(LEGENDES.get(nom, nom)), html.escape(nom)))
        self.sortie.append('</section>')
        self.chapitre = []


FEUILLE_DE_STYLE = """
@page { size: A4; margin: 18mm 15mm 20mm 15mm; }
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif;
       font-size: 9.5pt; line-height: 1.45; color: #1c2733; margin: 0; }
h1 { font-size: 20pt; color: #0b3d63; margin: 0 0 4mm; line-height: 1.2;
     border-bottom: 2.5pt solid #0b3d63; padding-bottom: 3mm; }
h2 { font-size: 14pt; color: #0b3d63; margin: 9mm 0 3mm;
     border-bottom: .8pt solid #b9cbd9; padding-bottom: 1.5mm; }
h2.rupture { break-before: page; }
h1 + h2.rupture, h2.rupture:first-of-type { break-before: auto; }
h3 { font-size: 11.5pt; color: #15537f; margin: 6mm 0 2mm; }
h4 { font-size: 10pt; color: #15537f; margin: 4mm 0 1.5mm; }
h2, h3, h4 { break-after: avoid; }
p { margin: 0 0 2.5mm; text-align: justify; }
strong { color: #0b2b47; }
a { color: #15537f; text-decoration: none; }
code { font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
       font-size: .87em; background: #eef3f7; border: .4pt solid #d5e0ea;
       border-radius: 2pt; padding: 0 .8mm; color: #123; }
pre.code { background: #f7f9fb; border: .5pt solid #d5e0ea;
           border-left: 2.5pt solid #15537f; border-radius: 2pt;
           padding: 2.5mm 3mm; margin: 0 0 3mm; overflow-wrap: anywhere;
           white-space: pre-wrap; break-inside: avoid; }
pre.code code { background: none; border: none; padding: 0; font-size: 8pt;
                line-height: 1.4; }
blockquote { margin: 0 0 3mm; padding: 2.5mm 3mm; background: #fff8e8;
             border-left: 2.5pt solid #d9a441; border-radius: 2pt;
             text-align: justify; break-inside: avoid; }
blockquote p { margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 0 0 3.5mm;
        font-size: 8.4pt; break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: #0b3d63; color: #fff; text-align: left; font-weight: 600;
     padding: 1.4mm 2mm; border: .4pt solid #0b3d63; }
/* `strong` porte une couleur sombre : illisible sur le bandeau d'en-tête. */
th strong, th em, th code { color: #fff; }
th code { background: rgba(255,255,255,.16); border-color: rgba(255,255,255,.3); }
td { padding: 1.3mm 2mm; border: .4pt solid #cfdae4; vertical-align: top; }
tbody tr:nth-child(even) { background: #f4f8fb; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1.2mm; text-align: justify; }
section.planche { break-before: page; }
section.planche h3 { margin-top: 0; }
figure { margin: 0 0 6mm; break-inside: avoid; }
figure img { width: 100%; border: .5pt solid #b9cbd9; border-radius: 2pt;
             display: block; }
figcaption { font-size: 8pt; color: #4a5b6b; margin-top: 1.2mm;
             padding-left: .5mm; }
figcaption .fichier { color: #8b9aa8; font-family: "DejaVu Sans Mono", monospace;
                      font-size: 7.4pt; }
"""

GABARIT = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>%(titre)s</title>
<style>%(style)s</style></head><body>%(corps)s</body></html>"""

EN_TETE = ('<div style="font-size:7pt;color:#8b9aa8;width:100%;padding:0 15mm;'
           'font-family:sans-serif;">AITE Courrier / AITE ECM — Dossier de '
           'recette (UAT) v2.0</div>')
PIED = ('<div style="font-size:7pt;color:#8b9aa8;width:100%;padding:0 15mm;'
        'font-family:sans-serif;text-align:right;">'
        '<span class="pageNumber"></span> / <span class="totalPages"></span>'
        '</div>')


def chromium():
    """Chemin d'un Chromium utilisable, ou ``None`` pour laisser Playwright choisir."""
    candidats = sorted(Path('/opt/pw-browsers').glob('chromium*/chrome-linux/chrome'))
    return str(candidats[0]) if candidats else None


def main():
    if not SOURCE.exists():
        sys.exit("Source introuvable : %s" % SOURCE)
    lignes = SOURCE.read_text(encoding='utf-8').splitlines()
    corps = Convertisseur(lignes).convertir()
    page = GABARIT % {'titre': "Dossier de recette (UAT) — AITE Courrier / AITE ECM",
                      'style': FEUILLE_DE_STYLE, 'corps': corps}
    temporaire = UAT / '.dossier_uat.html'
    temporaire.write_text(page, encoding='utf-8')
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright est requis : pip install playwright")
    try:
        with sync_playwright() as p:
            navigateur = p.chromium.launch(executable_path=chromium(),
                                           args=['--no-sandbox'])
            onglet = navigateur.new_page()
            onglet.goto(temporaire.resolve().as_uri(), wait_until='load')
            onglet.pdf(path=str(TARGET), format='A4', print_background=True,
                       display_header_footer=True, header_template=EN_TETE,
                       footer_template=PIED,
                       margin={'top': '16mm', 'bottom': '16mm',
                               'left': '15mm', 'right': '15mm'})
            navigateur.close()
    finally:
        temporaire.unlink(missing_ok=True)
    print("PDF généré : %s (%.1f Mo)"
          % (TARGET, TARGET.stat().st_size / (1024 * 1024)))


if __name__ == '__main__':
    main()
