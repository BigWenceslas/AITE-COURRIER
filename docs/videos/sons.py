# -*- coding: utf-8 -*-
"""Les deux bruitages des guides vidéo, synthétisés ici.

Aucun fichier son dans le dépôt et aucun hasard : le bruit du souffle a sa
graine, deux rendus donnent la même piste.

- ``ouverture`` : un souffle qui monte pendant que le trait d'or se trace,
  puis deux notes de carillon (sol, ré) quand la carte BGFI se pose ;
- ``clic`` : un clic discret, à chaque clic du curseur.

``piste()`` les pose sur une piste mono 48 kHz de la durée de la vidéo, que
la composition joue sous la voix off. Les niveaux sont fixés ici, une fois
pour toute la série : le carillon reste nettement sous la voix, le clic
s'entend à peine.
"""

import array
import math
import random
import wave

TAUX = 48000
CARILLON = 0.85        # le carillon, dans le son d'ouverture : la carte BGFI se pose
NIVEAUX = {'souffle': 0.16, 'carillon': 0.26, 'clic': 0.14}


def _normer(echantillons, crete):
    m = max(abs(v) for v in echantillons) or 1.0
    return [v * crete / m for v in echantillons]


def souffle(duree=1.05, graine=7):
    """Un bruit filtré dont la bande monte de 250 Hz à 3 kHz et qui enfle
    jusqu'à l'arrivée du carillon, puis s'éteint vite."""
    hasard = random.Random(graine)
    bas = bande = 0.0
    sortie = []
    n = int(duree * TAUX)
    for i in range(n):
        t = i / TAUX
        f = 250.0 + 2750.0 * (t / duree) ** 1.5
        k = 2.0 * math.sin(math.pi * f / TAUX)
        haut = hasard.uniform(-1.0, 1.0) - bas - 0.6 * bande
        bande += k * haut
        bas += k * bande
        enveloppe = (t / CARILLON) ** 2 if t < CARILLON else math.exp(-(t - CARILLON) / 0.07)
        sortie.append(bande * enveloppe)
    return _normer(sortie, NIVEAUX['souffle'])


def _note(f, duree):
    """Une note de carillon : quelques partiels qui s'éteignent chacun à son
    rythme, doublés d'un léger désaccord pour la chaleur."""
    partiels = [(1.0, 1.0, 0.9), (2.0, 0.28, 0.45), (3.0, 0.09, 0.25), (4.16, 0.04, 0.15)]
    sortie = []
    for i in range(int(duree * TAUX)):
        t = i / TAUX
        attaque = min(1.0, t / 0.004)
        v = 0.0
        for rapport, amplitude, tenue in partiels:
            p = 2.0 * math.pi * f * rapport * t
            v += amplitude * math.exp(-t / tenue) * (math.sin(p) + math.sin(p * 1.0011)) / 2.0
        sortie.append(v * attaque)
    return sortie


def carillon(duree=1.7):
    """Sol puis ré, une quinte, à 0,12 s d'écart ; fondu sur la fin."""
    n = int(duree * TAUX)
    sortie = [0.0] * n
    for debut, f in ((0.0, 783.99), (0.12, 1174.66)):
        d = int(debut * TAUX)
        for i, v in enumerate(_note(f, duree - debut)):
            sortie[d + i] += v
    fondu = int(0.3 * TAUX)
    for i in range(fondu):
        sortie[n - fondu + i] *= 1.0 - i / fondu
    return _normer(sortie, NIVEAUX['carillon'])


def ouverture():
    """Le souffle, puis le carillon à ``CARILLON`` secondes."""
    s, c = souffle(), carillon()
    d = int(CARILLON * TAUX)
    sortie = s + [0.0] * max(0, d + len(c) - len(s))
    for i, v in enumerate(c):
        sortie[d + i] += v
    return sortie


def clic():
    """Un tic bref : une attaque de bruit, un corps aigu, un léger choc grave."""
    hasard = random.Random(3)
    sortie = []
    for i in range(int(0.06 * TAUX)):
        t = i / TAUX
        v = (math.sin(2 * math.pi * 2000 * t) * math.exp(-t / 0.006)
             + 0.5 * math.sin(2 * math.pi * 3500 * t) * math.exp(-t / 0.003)
             + 0.6 * math.sin(2 * math.pi * 180 * t) * math.exp(-t / 0.012)
             + 0.6 * hasard.uniform(-1.0, 1.0) * math.exp(-t / 0.0008))
        sortie.append(v * min(1.0, t / 0.0004))
    return _normer(sortie, NIVEAUX['clic'])


# ------------------------------------------------------------ musique --
# Une boucle de quatre mesures (ré majeur : I – V – vi – IV, 96 battements
# par minute), synthétisée ici : nappe, basse, arpège pincé, pied et
# souffle léger. Rien à télécharger, aucun droit à payer, et deux rendus
# donnent la même piste. Elle passe sous la voix (ducking) et remonte
# entre les phrases.
TEMPO = 96.0
ACCORDS = [(50, [62, 66, 69]), (45, [61, 64, 69]), (47, [62, 66, 71]), (43, [62, 67, 71])]   # D, A, Bm, G (MIDI)
MUSIQUE = {'sous_voix': 0.075, 'seule': 0.17, 'montee': 0.35}


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def boucle():
    """Quatre mesures, normalisées à 1."""
    temps = 60.0 / TEMPO
    mesure = 4 * temps
    n = int(round(4 * mesure * TAUX))
    out = [0.0] * n
    hasard = random.Random(11)

    def ajouter(debut, echantillons, gain):
        d = int(debut * TAUX)
        for i, v in enumerate(echantillons):
            out[(d + i) % n] += v * gain

    for k, (basse, notes) in enumerate(ACCORDS):
        t0 = k * mesure
        # nappe : trois notes tenues, attaque lente, légère respiration
        longueur = int((mesure + 0.6) * TAUX)
        for note in notes:
            f = _hz(note - 12)
            nap = []
            for i in range(longueur):
                t = i / TAUX
                env = min(1.0, t / 0.45) * (1.0 if t < mesure else max(0.0, 1 - (t - mesure) / 0.6))
                ph = 2 * math.pi * f * t
                nap.append(env * (math.sin(ph) + 0.35 * math.sin(2 * ph + 0.3) + 0.5 * math.sin(ph * 1.003)))
            ajouter(t0, nap, 0.10)
        # basse : temps 1 et 3
        for b in (0, 2):
            f = _hz(basse - 12)
            ech = [math.sin(2 * math.pi * f * (i / TAUX)) * math.exp(-(i / TAUX) / 0.45) * min(1.0, i / 200.0)
                   for i in range(int(1.1 * TAUX))]
            ajouter(t0 + b * temps, ech, 0.30)
        # arpège pincé en croches
        motif = [notes[0], notes[1], notes[2], notes[1] + 12, notes[2], notes[1], notes[0] + 12, notes[2]]
        for j, note in enumerate(motif):
            f = _hz(note + 12)
            ech = []
            for i in range(int(0.55 * TAUX)):
                t = i / TAUX
                ph = 2 * math.pi * f * t
                ech.append((math.sin(ph) + 0.25 * math.sin(2 * ph)) * math.exp(-t / 0.16) * min(1.0, i / 120.0))
            ajouter(t0 + j * temps / 2, ech, 0.11)
        # pied doux (temps 1 et 3) et souffle sur les contretemps
        for b in range(4):
            if b in (0, 2):
                ech, ph = [], 0.0
                for i in range(int(0.25 * TAUX)):
                    t = i / TAUX
                    ph += 2 * math.pi * (48 + 70 * math.exp(-t / 0.03)) / TAUX
                    ech.append(math.sin(ph) * math.exp(-t / 0.09) * min(1.0, i / 150.0))
                ajouter(t0 + b * temps, ech, 0.32)
            ech, bas = [], 0.0
            for i in range(int(0.08 * TAUX)):
                bruit = hasard.uniform(-1, 1)
                bas = 0.6 * bas + 0.4 * bruit
                ech.append((bruit - bas) * math.exp(-(i / TAUX) / 0.025) * min(1.0, i / 90.0))
            ajouter(t0 + (b + 0.5) * temps, ech, 0.05)
    return _normer(out, 1.0)


def musique(duree, voix):
    """La boucle répétée sur ``duree`` ; ``voix`` = [(début, fin)] des
    phrases : le niveau baisse dessous, remonte entre elles."""
    b = boucle()
    n = int(math.ceil(duree * TAUX))
    pas = int(0.05 * TAUX)
    # niveau cible par tranche de 50 ms, puis lissé
    cibles = []
    for k in range(n // pas + 1):
        t = k * pas / TAUX
        sous = any(d - 0.3 <= t <= f + 0.2 for d, f in voix)
        cibles.append(MUSIQUE['sous_voix'] if sous else MUSIQUE['seule'])
    lisse, niveau = [], cibles[0]
    for c in cibles:
        niveau += (c - niveau) * 0.18
        lisse.append(niveau)
    sortie = []
    for i in range(n):
        t = i / TAUX
        k = i // pas
        g = lisse[k] + (lisse[min(k + 1, len(lisse) - 1)] - lisse[k]) * ((i % pas) / pas)
        g *= min(1.0, t / 1.2) * min(1.0, max(0.0, (duree - t) / 2.5))
        sortie.append(b[i % len(b)] * g)
    return sortie


def piste(evenements, duree, chemin, voix=None, avec_musique=False):
    """Écrit la piste des bruitages : ``evenements`` = [(instant, nom)],
    ``nom`` étant ``ouverture`` ou ``clic`` ; avec la musique de fond si
    ``avec_musique`` (``voix`` : les plages de la voix off, pour la baisser
    dessous)."""
    sons = {'ouverture': ouverture(), 'clic': clic()}
    n = int(math.ceil(duree * TAUX))
    tampon = array.array('h', bytes(2 * n))
    if avec_musique:
        for i, v in enumerate(musique(duree, voix or [])):
            tampon[i] = int(round(v * 32767))
    for instant, nom in evenements:
        d = int(round(instant * TAUX))
        for i, v in enumerate(sons[nom]):
            if 0 <= d + i < n:
                tampon[d + i] = max(-32767, min(32767, tampon[d + i] + int(round(v * 32767))))
    with wave.open(chemin, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(TAUX)
        f.writeframes(tampon.tobytes())
    return chemin
