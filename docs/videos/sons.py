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


def piste(evenements, duree, chemin):
    """Écrit la piste des bruitages : ``evenements`` = [(instant, nom)],
    ``nom`` étant ``ouverture`` ou ``clic``."""
    sons = {'ouverture': ouverture(), 'clic': clic()}
    n = int(math.ceil(duree * TAUX))
    tampon = array.array('h', bytes(2 * n))
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
