# -*- coding: utf-8 -*-
"""Produire la vidéo de présentation d'AITE Courrier.

    python3 docs/videos/produire.py                  # voix + projet + check
    python3 docs/videos/produire.py --planche        # + planche contact
    python3 docs/videos/produire.py --rendu          # + rendu MP4 et compression

Adapté du moteur des guides vidéo (skill aite-motion-design-1). Les projets,
les rendus et les voix vivent hors du dépôt, dans le dossier de travail
(``--dossier``, par défaut ``../aite-videos`` à côté du dépôt). La vidéo
compressée et sa vignette sortent dans ``docs/videos/livrees``.

Voix off : Kokoro, gratuit et local, voix féminine française ``ff_siwis``,
installée au premier lancement dans ``<dossier>/.venv-tts``. Chaque phrase
est mise en cache : relancer ne resynthétise que les phrases modifiées.
"""

import argparse
import glob
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import presentation  # noqa: E402
import sons  # noqa: E402

RACINE = os.path.abspath(os.path.join(ICI, '..', '..'))
HYPERFRAMES = 'hyperframes@0.8.139'
GSAP = 'gsap@3.14.2'
VOIX = 'ff_siwis'
VITESSE = '1.0'
SORTIE_DEPOT = os.path.join(ICI, 'livrees')
NOM = 'aite-courrier-presentation'

# Ce que Kokoro (phonétiseur espeak) lit mal : on l'écrit comme il se dit.
LEXIQUE = [
    (r'\bAITE\b', 'Aïte'), (r'\bECM\b', 'E C M'), (r'\bGED\b', 'G E D'), (r'\bSLA\b', 'S L A'),
    (r'\bAPI\b', 'A P I'), (r'\bPDF/A\b', 'P D F A'), (r'\bPDF\b', 'P D F'), (r'\bOCR\b', 'O C R'),
    (r'\bWebDAV\b', 'Web Dav'), (r'\bOdoo\b', 'Odou'), (r'\bOHADA\b', 'O H A D A'), (r'\bREST\b', 'Rest'),
    (r'\bSHA-256\b', 'S H A deux cent cinquante-six'), (r'\bOpenAPI\b', 'Open A P I'),
]


def journal(*m):
    print(' '.join(str(x) for x in m), flush=True)


def lancer(commande, dossier=None, env=None, delai=3600):
    return subprocess.run(commande, cwd=dossier, env=env, capture_output=True, text=True, timeout=delai)


def sans_couleurs(t):
    return re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', t or '')


NAVIGATEURS_LOCAUX = ['/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell']


def navigateur():
    if os.environ.get('HYPERFRAMES_BROWSER_PATH'):
        return
    cache = os.path.expanduser('~/.cache/hyperframes/chrome')
    if os.path.isdir(cache) and os.listdir(cache):
        return
    for motif in NAVIGATEURS_LOCAUX:
        trouves = sorted(glob.glob(motif))
        if trouves:
            os.environ['HYPERFRAMES_BROWSER_PATH'] = trouves[-1]
            return


def preparer(dossier):
    os.makedirs(dossier, exist_ok=True)
    navigateur()
    gsap = os.path.join(dossier, 'node_modules', 'gsap', 'dist', 'gsap.min.js')
    if not os.path.exists(gsap):
        if not os.path.exists(os.path.join(dossier, 'package.json')):
            with open(os.path.join(dossier, 'package.json'), 'w') as f:
                f.write('{"name": "aite-videos", "private": true}\n')
        r = lancer(['npm', 'install', '--no-audit', '--no-fund', GSAP], dossier)
        if r.returncode != 0:
            sys.exit('npm install %s a échoué :\n%s' % (GSAP, r.stderr))
    return gsap


def python_tts(dossier):
    venv = os.path.join(dossier, '.venv-tts')
    py = os.path.join(venv, 'bin', 'python')
    if not os.path.exists(py):
        journal('· installation de Kokoro (voix off locale)')
        lancer([sys.executable, '-m', 'venv', venv])
        r = lancer([os.path.join(venv, 'bin', 'pip'), 'install', '-q', 'kokoro-onnx', 'soundfile'])
        if r.returncode != 0:
            sys.exit('Installation de Kokoro impossible :\n%s' % r.stderr)
    return py


def duree_media(chemin):
    r = lancer(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', chemin])
    return float(r.stdout.strip())


def prononcer(texte):
    for motif, dit in LEXIQUE:
        texte = re.sub(motif, dit, texte)
    return texte


ORDINAUX = ['Premier', 'Deuxième', 'Troisième', 'Quatrième', 'Cinquième', 'Sixième', 'Septième', 'Huitième',
            'Neuvième', 'Dixième', 'Onzième', 'Douzième']


def textes_voix(s):
    textes = dict(s['voix'])
    for n, c in enumerate(s['chapitres'], 1):
        textes['chap-%d' % n] = '%s chapitre : %s' % (ORDINAUX[n - 1], c['voix'])
        for m, et in enumerate(c['etapes'], 1):
            textes['c%d-e%d' % (n, m)] = et['voix']
    for bloc in s.get('cartes_intro', []) + s.get('cartes_fin', []):
        textes[bloc['voix_cle']] = bloc['voix']
    return textes


def synthetiser(dossier, textes):
    cache = os.path.join(dossier, 'voix-cache')
    os.makedirs(cache, exist_ok=True)
    env = dict(os.environ, HYPERFRAMES_PYTHON=python_tts(dossier))
    fichiers, durees = {}, {}
    for case, texte in textes.items():
        dit = prononcer(texte)
        empreinte = hashlib.sha256(json.dumps([VOIX, VITESSE, dit]).encode()).hexdigest()[:16]
        brut = os.path.join(cache, empreinte + '.wav')
        norme = os.path.join(cache, empreinte + '-n.wav')
        if not os.path.exists(norme):
            journal('  voix', case, '—', dit[:70] + ('…' if len(dit) > 70 else ''))
            r = lancer(['npx', '--yes', HYPERFRAMES, 'tts', dit, '-v', VOIX, '-s', VITESSE, '-o', brut], dossier, env=env)
            if r.returncode != 0 or not os.path.exists(brut):
                sys.exit('Synthèse impossible pour %s :\n%s' % (case, sans_couleurs(r.stdout + r.stderr)[-2000:]))
            r = lancer(['ffmpeg', '-v', 'error', '-y', '-i', brut, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7',
                        '-ar', '48000', '-ac', '1', norme])
            if r.returncode != 0:
                sys.exit('Normalisation impossible pour %s :\n%s' % (case, r.stderr))
        fichiers[case] = norme
        durees[case] = round(duree_media(norme), 3)
    return fichiers, durees


VIDEOS = {'courrier': ('scenarios.presentation', 'aite-courrier-presentation'),
          'ecm': ('scenarios.ecm', 'aite-ecm-presentation'),
          'suite': ('scenarios.suite', 'aite-suite-courrier-ecm')}
MODULE = VIDEOS['courrier'][0]


def charger():
    module = importlib.import_module(MODULE)
    importlib.reload(module)
    return module.SCENARIO


def ecrire_projet(dossier, scenario, gsap, voix):
    projet = os.path.join(dossier, 'fr', NOM)
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
    video = presentation.Presentation(scenario, durees_voix=durees, fichiers_voix=relatifs,
                                      bruitages='assets/sons/bruitages.wav' if voix else None)
    html, total = video.construire()
    if video.bruitages:
        sons.piste(video.sons, total, os.path.join(projet, video.bruitages))
    with open(os.path.join(projet, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    with open(os.path.join(projet, 'hyperframes.json'), 'w') as f:
        json.dump({'paths': {'blocks': 'compositions', 'components': 'compositions/components', 'assets': 'assets'},
                   'media': {'autoProxy': True}}, f, indent=2)
    with open(os.path.join(projet, 'meta.json'), 'w') as f:
        json.dump({'id': scenario.get('id', 'presentation'), 'name': scenario.get('titre_page', NOM)}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(projet, 'package.json'), 'w') as f:
        json.dump({'name': NOM, 'private': True, 'type': 'module'}, f, indent=2)
    with open(os.path.join(projet, 'plan-scenes.json'), 'w') as f:
        json.dump(sorted(set(video.reperes)), f)
    return projet, total, video


def verifier(projet):
    r = lancer(['npx', '--yes', HYPERFRAMES, 'check'], projet)
    sortie = sans_couleurs(r.stdout + r.stderr)
    with open(os.path.join(projet, 'check.log'), 'w') as f:
        f.write(sortie)
    resume = [l for l in sortie.splitlines() if re.search(r'error|✗|issues|checks pass|Check (passed|failed)', l)]
    return r.returncode, resume


def planche(projet, instants=None, par=30):
    if instants is None:
        with open(os.path.join(projet, 'plan-scenes.json')) as f:
            instants = json.load(f)
    shutil.rmtree(os.path.join(projet, 'snapshots'), ignore_errors=True)
    r = lancer(['npx', '--yes', HYPERFRAMES, 'snapshot', '--at', ','.join('%.2f' % t for t in instants), '--no-end',
                '--timeout', '20000'], projet)
    planches = sorted(glob.glob(os.path.join(projet, 'snapshots', 'contact-sheet*.jpg')))
    return planches, sans_couleurs(r.stdout + r.stderr)


def rendre(projet):
    sortie = os.path.join(projet, 'renders', NOM + '.mp4')
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    r = lancer(['npx', '--yes', HYPERFRAMES, 'render', '-o', sortie, '-w', '2', '-q', 'high'], projet, delai=14400)
    if r.returncode != 0 or not os.path.exists(sortie):
        sys.exit('Rendu impossible :\n%s' % sans_couleurs(r.stdout + r.stderr)[-3000:])
    return sortie


MONO = 'pan=mono|c0=0.5*c0+0.5*c1'
SONIE = -16.0
PLAFOND = 0.794


def sonie(source):
    r = lancer(['ffmpeg', '-hide_banner', '-nostats', '-i', source, '-vn', '-af', MONO + ',ebur128', '-f', 'null', '-'])
    valeurs = re.findall(r'^\s+I:\s+(-?[\d.]+) LUFS', r.stderr, re.M)
    if not valeurs:
        sys.exit('Sonie illisible :\n%s' % r.stderr[-1500:])
    return float(valeurs[-1])


def compresser(source, instant, sortie=SORTIE_DEPOT):
    os.makedirs(sortie, exist_ok=True)
    cible = os.path.join(sortie, NOM + '.mp4')
    gain = SONIE - sonie(source)
    r = lancer(['ffmpeg', '-v', 'error', '-y', '-i', source, '-c:v', 'libx264', '-preset', 'slow', '-crf', '28',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                '-af', '%s,volume=%.2fdB,alimiter=limit=%.3f:level=false' % (MONO, gain, PLAFOND),
                '-c:a', 'aac', '-b:a', '96k', cible])
    if r.returncode != 0:
        sys.exit('Compression impossible :\n%s' % r.stderr)
    image = os.path.splitext(cible)[0] + '.jpg'
    lancer(['ffmpeg', '-v', 'error', '-y', '-ss', '%.2f' % instant, '-i', cible, '-frames:v', '1', '-q:v', '3',
            '-vf', 'scale=1280:-2', image])
    return cible, image


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dossier', default=os.path.abspath(os.path.join(RACINE, '..', 'aite-videos')))
    p.add_argument('--muet', action='store_true')
    p.add_argument('--planche', action='store_true')
    p.add_argument('--rendu', action='store_true')
    p.add_argument('--sans-check', action='store_true')
    p.add_argument('--sortie', default=SORTIE_DEPOT)
    p.add_argument('--video', choices=sorted(VIDEOS), default='courrier',
                   help='courrier (par défaut), ecm, ou suite (Courrier et ECM réunis)')
    args = p.parse_args()
    global MODULE, NOM
    MODULE, NOM = VIDEOS[args.video]
    args.dossier = os.path.abspath(args.dossier)
    gsap = preparer(args.dossier)
    scenario = charger()
    textes = textes_voix(scenario)
    journal('▶ présentation —', len(textes), 'phrases,', sum(len(x) for x in textes.values()), 'caractères')
    voix = None if args.muet else synthetiser(args.dossier, textes)
    projet, total, video = ecrire_projet(args.dossier, scenario, gsap, voix)
    journal('  projet', projet, '— %d min %02d s' % (int(total) // 60, int(total) % 60))
    for a in video.alertes:
        journal('  ⚠', a)
    if not args.sans_check:
        code, resume = verifier(projet)
        for l in resume:
            journal('   ', l.strip())
        journal('  check', 'ok' if code == 0 else 'en échec (check.log)')
    if args.planche:
        planches, _ = planche(projet)
        journal('  planches', ', '.join(planches))
    if args.rendu:
        source = rendre(projet)
        cible, image = compresser(source, video.vignette(), args.sortie)
        journal('  vidéo', cible, '— %.1f Mo' % (os.path.getsize(cible) / 1e6), '· vignette', image)


if __name__ == '__main__':
    main()
