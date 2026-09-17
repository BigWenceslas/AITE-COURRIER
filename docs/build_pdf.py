#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend les documents Markdown de ``docs/`` en PDF paginés.

    python3 docs/build_pdf.py                     # les documents WebDAV
    python3 docs/build_pdf.py docs/X.md -o /tmp   # un document précis

Dépendances (hors dépôt, à installer une fois) ::

    pip install weasyprint markdown pygments

Le rendu vise l'impression et la diffusion : A4, en-tête et pied de page
courants, numérotation « n / N », tableaux dont l'en-tête se répète d'une page
à l'autre, blocs de code non tronqués. Les liens vers d'autres fichiers du
dépôt sont aplatis en texte : dans un PDF, ils ne mènent nulle part.
"""
import argparse
import os
import re
import sys
from datetime import date

try:
    import markdown
    from pygments.formatters import HtmlFormatter
    from weasyprint import HTML
except ImportError as error:                       # pragma: no cover
    sys.exit("Dépendance manquante (%s).\n"
             "  pip install weasyprint markdown pygments" % error.name)

HERE = os.path.dirname(os.path.abspath(__file__))

#: Documents rendus quand aucun fichier n'est passé en argument.
DEFAUT = [
    'DEPLOIEMENT_WEBDAV_WINDOWS.md',
    'recette/SCENARIO_WEBDAV.md',
    'recette/GUIDE_TEST_WEBDAV.md',
]

MOIS = ("janvier février mars avril mai juin juillet août septembre "
        "octobre novembre décembre").split()

CSS = """
@page {
    size: A4;
    margin: 20mm 17mm 18mm 17mm;
    @top-left {
        content: "AITE Courrier / AITE ECM";
        font: 500 7.5pt 'DejaVu Sans'; color: #8a96a3;
        padding-bottom: 2mm;
    }
    @top-right {
        content: string(doctitre);
        font: 500 7.5pt 'DejaVu Sans'; color: #8a96a3;
        padding-bottom: 2mm;
    }
    @bottom-left {
        content: "AITE Consulting";
        font: 7.5pt 'DejaVu Sans'; color: #8a96a3;
    }
    @bottom-right {
        content: counter(page) " / " counter(pages);
        font: 7.5pt 'DejaVu Sans'; color: #8a96a3;
    }
}
@page :first {
    @top-left { content: none; }
    @top-right { content: none; }
}

body {
    font-family: 'DejaVu Sans', sans-serif;
    font-size: 9.6pt; line-height: 1.5; color: #1c2530;
    hyphens: auto;
}

/* ---- titres ---------------------------------------------------------- */
h1 {
    string-set: doctitre content();
    font-size: 21pt; line-height: 1.2; color: #14507a;
    margin: 0 0 2mm 0; padding-bottom: 3mm;
    border-bottom: 2.5pt solid #14507a;
}
h2 {
    font-size: 13pt; color: #14507a;
    margin: 9mm 0 3mm 0; padding-bottom: 1.5mm;
    border-bottom: 0.6pt solid #d3dce5;
    break-after: avoid; break-inside: avoid;
}
h3 {
    font-size: 10.8pt; color: #23435c; margin: 6mm 0 2mm 0;
    break-after: avoid;
}
h4 { font-size: 9.8pt; color: #23435c; margin: 4mm 0 1.5mm 0; break-after: avoid; }
p { margin: 0 0 2.6mm 0; orphans: 2; widows: 2; }

/* ---- chapeau : le premier bloc de citation sert de sous-titre -------- */
.chapeau {
    font-size: 10.4pt; color: #4a5a6a; font-style: italic;
    margin: 0 0 6mm 0; padding: 0; border: 0;
}
.signature {
    font-size: 8pt; color: #8a96a3; margin: 0 0 8mm 0;
    padding-bottom: 3mm; border-bottom: 0.6pt solid #e4eaf0;
}

/* ---- listes ---------------------------------------------------------- */
ul, ol { margin: 0 0 2.6mm 0; padding-left: 6mm; }
li { margin-bottom: 1.2mm; }
li > ul, li > ol { margin-top: 1.2mm; }

/* ---- tableaux -------------------------------------------------------- */
table {
    width: 100%; border-collapse: collapse;
    margin: 3mm 0 4mm 0; font-size: 8.7pt;
}
thead { display: table-header-group; }
th {
    background: #eaf1f7; color: #14507a; text-align: left;
    font-weight: 600; padding: 1.8mm 2mm;
    border: 0.5pt solid #c3d2df;
}
td {
    padding: 1.6mm 2mm; border: 0.5pt solid #d8e1e9;
    vertical-align: top;
}
tbody tr:nth-child(even) { background: #f7fafc; }
tr { break-inside: avoid; }

/* ---- code ------------------------------------------------------------ */
code {
    font-family: 'DejaVu Sans Mono', monospace; font-size: 8.4pt;
    background: #eef2f6; padding: 0.2mm 0.6mm; border-radius: 1mm;
    /* Jamais de césure dans du code : un identifiant coupé par un trait
       d'union se recopie faux. On autorise seulement le retour à la ligne. */
    hyphens: none; overflow-wrap: break-word;
}
pre {
    background: #f6f8fa; border: 0.5pt solid #dde5ec;
    border-left: 2pt solid #14507a;
    padding: 2.5mm 3mm; margin: 2.5mm 0 3.5mm 0;
    break-inside: avoid;
}
pre code {
    background: none; padding: 0; font-size: 8.1pt; line-height: 1.42;
    white-space: pre-wrap; hyphens: none; overflow-wrap: break-word;
}

/* ---- citations ------------------------------------------------------- */
blockquote {
    margin: 3mm 0; padding: 2mm 0 2mm 4mm;
    border-left: 2pt solid #f0b429; background: #fffdf6;
    color: #4a4235; font-size: 9.1pt;
}
blockquote p:last-child { margin-bottom: 0; }

hr { border: 0; border-top: 0.6pt solid #e4eaf0; margin: 7mm 0; }

/* ---- divers ---------------------------------------------------------- */
a { color: #14507a; text-decoration: none; }
.xref { color: #23435c; font-family: 'DejaVu Sans Mono', monospace;
        font-size: 8.4pt; }
em { color: inherit; }
strong { color: #0f3c5c; }
"""


def lire(chemin):
    with open(chemin, encoding='utf-8') as flux:
        return flux.read()


def aplatir_liens(html):
    """Neutralise les liens vers des fichiers du dépôt.

    Dans un PDF distribué seul, un lien relatif vers un ``.md`` ou un dossier
    du dépôt ne mène nulle part : on garde le libellé, on retire l'ancre.
    """
    motif = re.compile(r'<a href="(?!https?:)[^"]*">(.*?)</a>', re.S)
    return motif.sub(lambda m: '<span class="xref">%s</span>' % m.group(1), html)


def chapeau(html):
    """Le premier blockquote, juste après le titre, devient le chapeau."""
    return re.sub(r'(</h1>\s*)<blockquote>\s*<p>(.*?)</p>\s*</blockquote>',
                  r'\1<div class="chapeau">\2</div>', html, count=1, flags=re.S)


def rendre(source, destination):
    texte = lire(source)
    corps = markdown.markdown(texte, extensions=[
        'tables', 'fenced_code', 'sane_lists', 'attr_list',
        'codehilite', 'md_in_html'],
        extension_configs={'codehilite': {'guess_lang': False,
                                          'noclasses': False}})
    corps = chapeau(aplatir_liens(corps))

    aujourdhui = date.today()
    signature = '%s — %d %s %d' % (
        os.path.basename(source), aujourdhui.day,
        MOIS[aujourdhui.month - 1], aujourdhui.year)
    corps = re.sub(r'(</h1>)', r'\1\n<div class="signature">%s</div>' % signature,
                   corps, count=1)

    document = ('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>'
                '<style>%s\n%s</style></head><body>%s</body></html>'
                % (CSS, HtmlFormatter().get_style_defs('.codehilite'), corps))
    HTML(string=document, base_url=os.path.dirname(source) or '.').write_pdf(
        destination)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rend des documents Markdown du dépôt en PDF A4.")
    parser.add_argument('fichiers', nargs='*',
                        help="documents à rendre (défaut : les documents WebDAV)")
    parser.add_argument('-o', '--sortie', default=os.path.join(HERE, 'pdf'),
                        help="dossier de destination (défaut : docs/pdf)")
    args = parser.parse_args(argv)

    sources = args.fichiers or [os.path.join(HERE, nom) for nom in DEFAUT]
    os.makedirs(args.sortie, exist_ok=True)
    for source in sources:
        if not os.path.isfile(source):
            sys.exit("Introuvable : %s" % source)
        cible = os.path.join(
            args.sortie,
            os.path.splitext(os.path.basename(source))[0] + '.pdf')
        rendre(source, cible)
        print('%-42s → %s (%.0f Ko)'
              % (os.path.basename(source), cible,
                 os.path.getsize(cible) / 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
