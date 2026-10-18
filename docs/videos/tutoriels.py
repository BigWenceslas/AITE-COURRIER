# -*- coding: utf-8 -*-
"""Produire les tutoriels marketing (une vidéo par fonctionnalité).

    python3 docs/videos/tutoriels.py 01 --muet --planche   # sans voix, pour relire vite
    python3 docs/videos/tutoriels.py 01 --planche          # voix + projet + check + planche
    python3 docs/videos/tutoriels.py 01 --rendu            # + rendu MP4 et compression
    python3 docs/videos/tutoriels.py --tout --rendu        # toute la série

Même chaîne que ``produire.py`` (voix Kokoro ff_siwis mise en cache,
HyperFrames, compression), avec en plus la musique de fond synthétisée par
``sons.py`` et baissée sous la voix. Les écrans sont rejoués avec le thème
MuK. Vidéos livrées dans ``docs/videos/livrees/tutoriels``.
"""

import argparse
import importlib
import json
import os
import shutil
import glob
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import ecrans  # noqa: E402
ecrans.THEME = 'muk'

import produire  # noqa: E402
import sons  # noqa: E402
import tutoriel  # noqa: E402
from scenarios.tutos import SERIE  # noqa: E402

SORTIE = os.path.join(ICI, 'livrees', 'tutoriels')
# La musique sous la voix fait monter les crêtes réelles après encodage AAC :
# plafond plus bas que pour les présentations (−4 dBFS au lieu de −2).
produire.PLAFOND = 0.63
journal = produire.journal


def charger(module):
    return importlib.import_module('scenarios.tutos.' + module).TUTO


def ecrire_projet(dossier, s, gsap, voix):
    nom = s['slug']
    projet = os.path.join(dossier, 'fr', nom)
    assets = os.path.join(projet, 'assets')
    for sous in ('fonts', 'logos', 'voix', 'sons'):
        shutil.rmtree(os.path.join(assets, sous), ignore_errors=True)
        os.makedirs(os.path.join(assets, sous), exist_ok=True)
    shutil.copy(os.path.join(ICI, 'shared', 'aite.css'), assets)
    shutil.copy(os.path.join(ICI, 'shared', 'aite-motion.js'), assets)
    shutil.copy(gsap, assets)
    for f in glob.glob(os.path.join(ICI, 'assets', 'fonts', '*.woff2')):
        shutil.copy(f, os.path.join(assets, 'fonts'))
    for f in glob.glob(os.path.join(ICI, 'assets', 'logos', '*')):
        shutil.copy(f, os.path.join(assets, 'logos'))
    fichiers, durees = voix if voix else ({}, {})
    relatifs = {}
    for case, chemin in fichiers.items():
        shutil.copy(chemin, os.path.join(assets, 'voix', os.path.basename(chemin)))
        relatifs[case] = 'assets/voix/' + os.path.basename(chemin)
    video = tutoriel.Tutoriel(s, durees_voix=durees, fichiers_voix=relatifs,
                              bruitages='assets/sons/bruitages.wav' if voix else None)
    html, total = video.construire()
    if video.bruitages:
        sons.piste(video.sons, total, os.path.join(projet, video.bruitages), video.plages_voix(), avec_musique=True)
    with open(os.path.join(projet, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    with open(os.path.join(projet, 'hyperframes.json'), 'w') as f:
        json.dump({'paths': {'blocks': 'compositions', 'components': 'compositions/components', 'assets': 'assets'},
                   'media': {'autoProxy': True}}, f, indent=2)
    with open(os.path.join(projet, 'meta.json'), 'w') as f:
        json.dump({'id': nom, 'name': s['titre_page']}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(projet, 'package.json'), 'w') as f:
        json.dump({'name': nom, 'private': True, 'type': 'module'}, f, indent=2)
    with open(os.path.join(projet, 'plan-scenes.json'), 'w') as f:
        json.dump(sorted(set(video.reperes)), f)
    return projet, total, video


def produire_un(numero, module, args, gsap):
    s = charger(module)
    produire.NOM = s['slug']
    textes = tutoriel.textes_voix(s)
    journal('▶ tutoriel', numero, '—', s['titre'], '·', len(textes), 'phrases,', sum(len(x) for x in textes.values()), 'caractères')
    voix = None if args.muet else produire.synthetiser(args.dossier, textes)
    projet, total, video = ecrire_projet(args.dossier, s, gsap, voix)
    journal('  projet', projet, '— %d min %02d s' % (int(total) // 60, int(total) % 60))
    for a in video.alertes:
        journal('  ⚠', a)
    if not args.sans_check:
        code, resume = produire.verifier(projet)
        for l in resume:
            journal('   ', l.strip())
        journal('  check', 'ok' if code == 0 else 'en échec (check.log)')
    if args.planche:
        planches, _ = produire.planche(projet)
        journal('  planches', ', '.join(planches))
    if args.rendu:
        source = produire.rendre(projet)
        cible, image = produire.compresser(source, video.vignette(), args.sortie)
        journal('  vidéo', cible, '— %.1f Mo' % (os.path.getsize(cible) / 1e6), '· vignette', image)
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('numeros', nargs='*', help='numéros des tutoriels (01, 02…)')
    p.add_argument('--tout', action='store_true')
    p.add_argument('--dossier', default=os.path.abspath(os.path.join(produire.RACINE, '..', 'aite-videos')))
    p.add_argument('--muet', action='store_true')
    p.add_argument('--planche', action='store_true')
    p.add_argument('--rendu', action='store_true')
    p.add_argument('--sans-check', action='store_true')
    p.add_argument('--sortie', default=SORTIE)
    args = p.parse_args()
    args.dossier = os.path.abspath(args.dossier)
    choisis = [(n, m) for n, m in SERIE if args.tout or n in args.numeros]
    if not choisis:
        sys.exit('Aucun tutoriel choisi : %s' % ', '.join(n for n, _ in SERIE))
    gsap = produire.preparer(args.dossier)
    for numero, module in choisis:
        produire_un(numero, module, args, gsap)


if __name__ == '__main__':
    main()
