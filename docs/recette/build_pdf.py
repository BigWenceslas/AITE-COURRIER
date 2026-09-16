# -*- coding: utf-8 -*-
"""GUIDE_RECETTE.md -> HTML paginé -> PDF (Chromium sans interface)."""
import os
import pathlib
import re
import subprocess
import sys

import markdown

RECETTE = pathlib.Path(__file__).resolve().parent
SRC = RECETTE / 'GUIDE_RECETTE.md'
TMP_HTML = RECETTE / '_impression.html'
PDF = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RECETTE / 'GUIDE_RECETTE.pdf'
# Chromium fourni par Playwright ; surchargeable pour une autre installation.
CHROME = os.environ.get(
    'AITE_CHROMIUM', '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')

CSS = """
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }

html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "Liberation Sans", "DejaVu Sans", sans-serif;
  font-size: 10pt; line-height: 1.5; color: #1a1a1a; margin: 0;
}

h1 {
  font-size: 23pt; line-height: 1.2; margin: 0 0 4mm; color: #14304f;
  border-bottom: 2.5pt solid #14304f; padding-bottom: 3mm;
}
h2 {
  font-size: 14pt; color: #14304f; margin: 0 0 4mm;
  border-bottom: 0.8pt solid #c8d4e0; padding-bottom: 2mm;
  break-before: page; break-after: avoid;
}
h1 + h2, body > h2:first-of-type { break-before: auto; }
h3 {
  font-size: 11pt; color: #23486b; margin: 4mm 0 1.5mm;
  break-after: avoid; break-inside: avoid;
}

blockquote {
  margin: 0 0 3mm; padding: 2mm 3mm; background: #f4f7fa;
  border-left: 2.5pt solid #7f9dbb; color: #33506d; break-inside: avoid;
}
blockquote p { margin: 0; }

p { margin: 0 0 2.5mm; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1mm; }
strong { color: #14304f; }

code {
  font-family: "DejaVu Sans Mono", monospace; font-size: 8.6pt;
  background: #f1f4f7; padding: 0.3mm 1mm; border-radius: 1mm;
}
pre {
  background: #f1f4f7; border-left: 2.5pt solid #9fb3c8; padding: 2.5mm 3mm;
  font-size: 8.4pt; overflow-wrap: break-word; white-space: pre-wrap;
  break-inside: avoid; margin: 0 0 3mm;
}
pre code { background: none; padding: 0; }

table {
  border-collapse: collapse; width: 100%; margin: 0 0 4mm; font-size: 9pt;
  break-inside: avoid;
}
thead { display: table-header-group; }
th, td {
  border: 0.5pt solid #c8d4e0; padding: 1.6mm 2.2mm;
  text-align: left; vertical-align: top;
}
th { background: #eef2f6; color: #14304f; font-weight: 600; }
tbody tr:nth-child(even) td { background: #fafbfc; }

/* 165mm de large -> environ 103mm de haut : deux étapes tiennent par page. */
img {
  display: block; width: 165mm; max-width: 100%;
  border: 0.5pt solid #c8d4e0; border-radius: 1mm;
  margin: 1.5mm auto 3mm; break-before: avoid; break-inside: avoid;
}

hr { border: none; border-top: 0.5pt solid #d8e0e8; margin: 5mm 0; }
a { color: #14304f; }

.chapeau {
  font-size: 9.5pt; color: #40566d; margin-bottom: 5mm;
  break-after: avoid;
}
"""


def build_html():
    text = SRC.read_text(encoding='utf-8')
    body = markdown.markdown(
        text, extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'])

    # Les tableaux « sans en-tête » (| | |) produisent une ligne de th vides :
    # on la retire pour que le tableau de méta-données reste lisible.
    body = re.sub(r'<thead>\s*<tr>\s*(?:<th[^>]*>\s*</th>\s*)+</tr>\s*</thead>',
                  '', body)

    return ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<title>Guide de recette — AITE ECM &amp; AITE Courrier</title>'
            '<style>%s</style></head><body>%s</body></html>' % (CSS, body))


def main():
    TMP_HTML.write_text(build_html(), encoding='utf-8')
    subprocess.run(
        [CHROME, '--headless', '--no-sandbox', '--disable-gpu',
         '--no-pdf-header-footer', '--generate-pdf-document-outline',
         '--print-to-pdf=%s' % PDF, TMP_HTML.as_uri()],
        check=True, capture_output=True, timeout=300)
    TMP_HTML.unlink(missing_ok=True)
    print("%s — %.1f Mo" % (PDF, PDF.stat().st_size / 1048576))


if __name__ == '__main__':
    main()
