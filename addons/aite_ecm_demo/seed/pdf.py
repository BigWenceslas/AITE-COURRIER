# -*- coding: utf-8 -*-
"""Génération de petits PDF valides (une page, texte Helvetica) sans dépendance.

Les fichiers sont volontairement légers (≈ 1,5 Ko) et contiennent du texte
réel : ils exercent l'indexation plein texte, l'empreinte SHA-256 (doublons)
et le filigrane des partages.
"""
import textwrap


def _esc(text):
    return (text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)'))


def make_pdf(title, lines, footer="AITE ECM — jeu de données de test"):
    content = ["BT", "/F1 16 Tf", "50 790 Td", "(%s) Tj" % _esc(title[:90]),
               "/F1 10 Tf", "0 -30 Td"]
    for raw in lines:
        for ln in textwrap.wrap(raw, 95) or [""]:
            content += ["(%s) Tj" % _esc(ln), "0 -14 Td"]
    content += ["/F1 8 Tf", "0 -20 Td", "(%s) Tj" % _esc(footer), "ET"]
    stream = "\n".join(content).encode('cp1252', 'replace')
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref))
    return bytes(out)
