# -*- coding: utf-8 -*-
"""Le moteur des guides vidéo PGest : d'un scénario à une composition HyperFrames.

Un scénario (``scenarios/<profil>.py``) décrit une vidéo de poste : le rôle,
sa mission, sa place dans le circuit, l'écran rejoué et les gestes qu'on y
fait, ce qu'il faut retenir — et le texte de la voix off, scène par scène.
Ce module en tire le HTML de la composition et le *plan* des gestes, que
``shared/pgest-motion.js`` transforme en timeline GSAP.

Le découpage est le même pour les quatorze vidéos :

    ouverture → poste → circuit → connexion → écran (2 à 4 étapes) → retenir → fin

Chaque scène a une durée de base ; quand une voix off est posée, la scène
s'allonge pour que la phrase y tienne en entier (durées pilotées par la
voix, voir ``references/voix-off.md`` du skill).

L'ouverture commence par la signature PGest (``INTRO`` secondes, sans voix,
avec le son d'ouverture de ``sons.py``) ; chaque clic du curseur a son clic
sonore. Les instants des bruitages sont relevés dans ``Video.sons``.
"""

import json
from html import escape

import sons
from ecrans import ICONES, curseur_svg, e

LARGEUR, HAUTEUR = 1920, 1080

# Durées de base des scènes, en secondes.
BASE = {'ouverture': 4.4, 'poste': 7.2, 'circuit': 6.2, 'connexion': 6.8, 'retenir': 6.2, 'fin': 4.6}
INTRO = 2.45          # la signature PGest, avant le titre du rôle
CLIC_SONORE = 0.02    # le son suit d'un souffle l'appui du curseur
AVANT_VOIX = 0.45     # la voix démarre un peu après l'image
APRES_VOIX = 0.65     # et laisse respirer avant la scène suivante
SORTIE = 0.35         # fondu de sortie de chaque scène

# Les nœuds du circuit, dans l'ordre de passage d'une demande.
NOEUDS = [
    ('client', 'Client'), ('crc', 'CRC'), ('chef', "Chef d'agence"), ('fd', 'Front Desk'),
    ('treso', 'Trésorerie'), ('ops', 'Opérations'), ('apu', 'Apurement'), ('fin', 'Validé'),
]
X0, PAS = 220, 211          # abscisse du premier nœud, écart entre nœuds
Y_NOEUD = 430               # haut des cercles


# ------------------------------------------------------------- les gestes --
# Chaque fonction rend un geste ; ``jouer`` les pose l'un après l'autre.
# Options communes : avec=True (en même temps que le précédent),
# decale=s (attendre avant), puis=s (respiration après).

def _g(geste, **kw):
    kw['geste'] = geste
    return kw


def curseur(sel, fx=0.5, fy=0.5, d=0.7, **kw):
    return _g('curseur', sel=sel, fx=fx, fy=fy, d=d, **kw)


def clic(sel, fx=0.5, fy=0.5, d=0.7, deplacer=True, **kw):
    """Amène le curseur sur l'élément et clique."""
    return _g('clic', sel=sel, fx=fx, fy=fy, d=d, deplacer=deplacer, **kw)


def saisir(ident, texte, d=None, **kw):
    """Tape ``texte`` dans le champ ``ident`` (voir ``ecrans.entree``)."""
    return _g('saisir', ident=ident, texte=texte, d=d or max(0.5, 0.055 * len(texte)), **kw)


def vue(ident, groupe='odoo', **kw):
    return _g('vue', ident=ident, groupe=groupe, **kw)


def montrer(sel, d=0.4, y=24, **kw):
    return _g('montrer', sel=sel, d=d, y=y, **kw)


def cacher(sel, d=0.3, **kw):
    return _g('cacher', sel=sel, d=d, **kw)


def ouvrir(ident, **kw):
    """Ouvre un assistant (voir ``ecrans.assistant``)."""
    return _g('ouvrir', ident=ident, **kw)


def fermer(ident, **kw):
    return _g('fermer', ident=ident, **kw)


def classe(sel, ajouter=(), retirer=(), **kw):
    return _g('classe', sel=sel, ajouter=list(ajouter), retirer=list(retirer), **kw)


def texte(sel, apres, **kw):
    return _g('texte', sel=sel, apres=apres, **kw)


def etat(sel, libelle, genre, **kw):
    """Change une pastille d'état : son libellé et sa couleur."""
    return _g('etat', sel=sel, libelle=libelle, genre=genre, **kw)


def compter(sel, de, a, d=1.0, decimales=0, avant='', apres='', **kw):
    return _g('compter', sel=sel, de=de, a=a, d=d, decimales=decimales, avant=avant, apres=apres, **kw)


def pause(d):
    return _g('pause', d=d)


def defiler(sel, y, d=0.8, **kw):
    """Fait défiler un contenu (y négatif : vers le bas de la page)."""
    return _g('defiler', sel=sel, y=y, d=d, **kw)


def anneau(sel, d=1.2, **kw):
    """Entoure un élément d'un anneau doré, sans cliquer."""
    return _g('anneau', sel=sel, d=d, **kw)


def notifier(ident, duree=2.6, **kw):
    """Affiche une notification (``ecrans.toast``) puis la retire, sans bloquer."""
    return _g('notifier', ident=ident, duree=duree, **kw)


def animer(sel, de, a, d=0.5, **kw):
    """Une animation libre (transformations, opacité) : de → a."""
    return _g('animer', sel=sel, de=de, a=a, d=d, **kw)


def choisir(ident, valeur, **kw):
    """Choisit une valeur dans une liste déroulante (champ ``ecrans.entree``)."""
    return _g('choisir', ident=ident, valeur=valeur, **kw)


def cocher(sel, **kw):
    return classe(sel, ajouter=['coche'], **kw)


def survol(sel, **kw):
    return classe(sel, ajouter=['survol'], **kw)


def valider_ligne(ident, d=0.5, libelle='Validé', genre='valide'):
    """Valide une pièce d'un tableau ``ecrans.documents`` : clic sur
    « Valider », la pastille change, puis « Valider » et « Rejeter »
    s'effacent — l'application les masque dès que la pièce n'est plus en
    attente (views/transfer_request_views.xml). Rend une liste de gestes."""
    return [clic('#%s-ok' % ident, d=d), etat('#%s-etat' % ident, libelle, genre, avec=True, decale=d + 0.12),
            cacher('#%s-ok' % ident, d=0.25, avec=True, decale=0.1), cacher('#%s-ko' % ident, d=0.25, avec=True)]


PUIS = {'animer': 0.05, 'choisir': 0.25, 'curseur': 0.05, 'clic': 0.25, 'saisir': 0.2, 'vue': 0.25, 'montrer': 0.15, 'cacher': 0.05,
        'ouvrir': 0.3, 'fermer': 0.2, 'classe': 0.15, 'texte': 0.1, 'etat': 0.35, 'compter': 0.2,
        'pause': 0.0, 'defiler': 0.15, 'anneau': 0.1, 'notifier': 0.3}


# -------------------------------------------------------------- la vidéo --

class Video:
    """Une vidéo de poste, construite à partir de son scénario."""

    def __init__(self, scenario, durees_voix=None, fichiers_voix=None, bruitages=None, presentateur=None):
        self.s = scenario
        self.id = scenario['slug'].split('-', 1)[-1].replace('_', '-')
        self.durees_voix = durees_voix or {}
        self.fichiers_voix = fichiers_voix or {}
        self.bruitages = bruitages     # la piste des bruitages, relative au projet (None : sans)
        # mode présentateur : {'video': piste relative au projet, 'nom', 'fonction'} (voir presentateur.py)
        self.presentateur = presentateur
        self.plages = []               # (case, début de sa scène) : la voix part AVANT_VOIX plus tard
        self.couches = []
        self.ops = []
        self.cibles = {}
        self.defilements = []
        self.audios = []
        self.sons = []                 # (instant, 'ouverture' | 'clic')
        self.vues = dict(scenario.get('vues_initiales', {'odoo': None}))
        self.positions = {}
        self.reperes = []          # instants à photographier (assistants ouverts…)
        self.alertes = []          # étapes où l'image tourne sans voix
        self.etapes_t = []         # (début, durée) de chaque étape de l'écran

    # -- outils
    def op(self, **kw):
        self.ops.append(kw)

    def cible(self, sel, fx=0.5, fy=0.5):
        cle = '%s@%.2f,%.2f' % (sel, fx, fy)
        self.cibles.setdefault(cle, {'sel': sel, 'fx': fx, 'fy': fy})
        return cle

    def entree(self, sel, t, d=0.6, y=30, x=0, echelle=None, decalage=None):
        de = {'autoAlpha': 0, 'y': y, 'x': x}
        # immediateRender : l'élément prend son état de départ dès la
        # construction, sans apparaître un instant avant son entrée.
        a = {'autoAlpha': 1, 'y': 0, 'x': 0, 'duration': d, 'ease': 'power3.out', 'immediateRender': True}
        if echelle:
            de['scale'] = echelle
            a['scale'] = 1
        if decalage:
            a['stagger'] = decalage
        self.op(op='fromTo', sel=sel, de=de, a=a, t=round(t, 3))

    def sortie(self, sel, t, d=SORTIE):
        self.op(op='fromTo', sel=sel, de={'autoAlpha': 1}, a={'autoAlpha': 0, 'duration': d, 'ease': 'power1.in'},
                t=round(t, 3))

    def duree(self, case, base):
        """La durée d'une scène : sa base, ou plus si la voix off l'exige."""
        dv = self.durees_voix.get(case)
        if dv:
            return round(max(base, AVANT_VOIX + dv + APRES_VOIX), 2)
        return base

    def poser_voix(self, case, t):
        self.plages.append((case, round(t, 3)))
        if case in self.fichiers_voix and case in self.durees_voix:
            self.audios.append((case, self.fichiers_voix[case], round(t + AVANT_VOIX, 3), self.durees_voix[case]))

    def clip(self, ident, t, d, contenu, piste, classes='clip scene'):
        self.couches.append('<div id="%s" class="%s" data-start="%.3f" data-duration="%.3f" data-track-index="%d">%s</div>'
                            % (ident, classes, t, d, piste, contenu))

    # ------------------------------------------------------------ scènes --
    def scene_ouverture(self, t):
        """La signature PGest — le fond se pose, le trait d'or se trace, la
        carte BGFI se pose sur le carillon, « PGest » monte —, puis le rôle et
        sa mission. La voix part avec le titre du rôle."""
        s = self.s
        ti = t + INTRO
        d = INTRO + self.duree('ouverture', BASE['ouverture'])
        lettres = ''.join('<span class="lettre">%s</span>' % c for c in 'PGest')
        mots = ' '.join('<span class="mot">%s</span>' % e(m) for m in s['titre'].split())
        html = ('<div class="scene-in" id="ouv-in">'
                '<div class="ouv-intro" id="ouv-intro"><div class="ouv-halo" id="ouv-halo"></div>'
                '<div class="ouv-logo"><div class="logo-carte" id="ouv-logo"><img src="assets/logos/bgfi.png" alt="">'
                '</div></div><div class="ouv-ligne" id="ouv-ligne"><i id="ouv-reflet"></i></div>'
                '<div class="ouv-marque" id="ouv-marque">%s</div>'
                '<div class="ouv-sous" id="ouv-sous">Transferts internationaux &amp; domiciliations</div></div>'
                '<div class="ouv-role"><div class="ouv-bloc"><div class="kicker" id="ouv-k">%s</div>'
                '<h1 class="ouv-titre" id="ouv-t">%s</h1><div class="ouv-trait" id="ouv-trait"></div>'
                '<p class="ouv-mission" id="ouv-m">%s</p></div>'
                '<div class="ouv-pied" id="ouv-pied"><div class="logo-carte"><img src="assets/logos/bgfi.png" alt=""></div>'
                '<span>PGest — Transferts internationaux &amp; domiciliations</span></div></div></div>'
                % (lettres, e(s['kicker']), mots, e(s['mission'])))
        self.clip('sc-ouverture', t, d, html, 1)
        # le fond se pose : le filet d'or, la trame, puis la diagonale sable
        self.op(op='fromTo', sel='#fond .filet-or', de={'scaleX': 0, 'transformOrigin': '0% 50%'},
                a={'scaleX': 1, 'duration': 0.9, 'ease': 'power2.inOut', 'immediateRender': True}, t=t + 0.05)
        self.op(op='fromTo', sel='#fond .points', de={'autoAlpha': 0},
                a={'autoAlpha': 1, 'duration': 1.2, 'ease': 'power1.out', 'immediateRender': True}, t=t + 0.1)
        self.entree('#fond .diag', ti - 0.4, d=0.8, x=160, y=0)
        # la signature, calée sur le son d'ouverture (sons.CARILLON)
        self.op(op='fromTo', sel='#ouv-halo', de={'autoAlpha': 0, 'scale': 0.6},
                a={'autoAlpha': 1, 'scale': 1, 'duration': 1.1, 'ease': 'power2.out', 'immediateRender': True}, t=t + 0.15)
        self.op(op='fromTo', sel='#ouv-ligne', de={'scaleX': 0},
                a={'scaleX': 1, 'duration': 0.7, 'ease': 'power3.inOut', 'immediateRender': True}, t=t + 0.3)
        self.op(op='fromTo', sel='#ouv-logo', de={'autoAlpha': 0, 'y': 26, 'scale': 0.84},
                a={'autoAlpha': 1, 'y': 0, 'scale': 1, 'duration': 0.6, 'ease': 'back.out(1.6)', 'immediateRender': True},
                t=round(t + sons.CARILLON - 0.5, 3))
        self.entree('#ouv-marque .lettre', t + sons.CARILLON, d=0.55, y=46, decalage=0.06)
        self.entree('#ouv-sous', t + 1.2, d=0.45, y=16)
        self.op(op='fromTo', sel='#ouv-reflet', de={'x': 0},
                a={'x': 1040, 'duration': 0.65, 'ease': 'power2.inOut', 'immediateRender': True}, t=t + 1.35)
        self.op(op='fromTo', sel='#ouv-intro', de={'autoAlpha': 1, 'y': 0},
                a={'autoAlpha': 0, 'y': -36, 'duration': 0.4, 'ease': 'power2.in'}, t=round(ti - 0.45, 3))
        self.sons.append((round(t, 3), 'ouverture'))
        self.reperes.append(round(t + 1.75, 2))
        # le rôle et sa mission
        self.entree('#ouv-k', ti + 0.15, y=20)
        self.entree('#ouv-t .mot', ti + 0.35, d=0.7, y=70, decalage=0.07)
        self.op(op='fromTo', sel='#ouv-trait', de={'scaleX': 0, 'transformOrigin': '0% 50%'},
                a={'scaleX': 1, 'duration': 0.6, 'ease': 'power2.out', 'immediateRender': True}, t=round(ti + 1.0, 3))
        self.entree('#ouv-m', ti + 1.2, y=24)
        self.entree('#ouv-pied', ti + 1.6, y=16)
        if self.presentateur:
            # le présentateur entre avec le titre du rôle, juste avant sa première phrase
            self.entree('#presentateur', ti + 0.05, d=0.5, x=40, y=0)
        self.sortie('#ouv-in', t + d - SORTIE)
        self.poser_voix('ouverture', ti)
        return t + d

    def scene_poste(self, t):
        s = self.s
        d = self.duree('poste', BASE['poste'])
        cartes = ''.join('<div class="pos-carte"><div class="verbe">%s</div><div class="txt">%s</div></div>'
                         % (e(v), e(x)) for v, x in s['cartes'])
        lignes = ''.join('<div class="pos-ligne"><span class="lib">%s</span><span class="val">%s</span></div>'
                         % (e(l), e(v)) for l, v in s['poste'])
        html = ('<div class="scene-in" id="pos-in"><div class="pos-tete" id="pos-tete"><div class="kicker">%s</div>'
                '<div class="titre-scene" style="margin-top:14px">%s</div></div>'
                '<div class="pos-cartes">%s</div><div class="pos-table">%s</div></div>'
                % (e(s.get('poste_kicker', '1 · Votre rôle dans le circuit')),
                   e(s.get('poste_titre', "Votre poste en un coup d'œil")), cartes, lignes))
        self.clip('sc-poste', t, d, html, 2)
        self.entree('#pos-tete', t + 0.1, y=20)
        self.entree('#pos-in .pos-carte', t + 0.45, d=0.6, y=40, decalage=0.16)
        self.entree('#pos-in .pos-ligne', t + 1.4, d=0.55, y=20, decalage=0.2)
        self.sortie('#pos-in', t + d - SORTIE)
        self.poser_voix('poste', t)
        return t + d

    def scene_circuit(self, t):
        c = self.s['circuit']
        d = self.duree('circuit', BASE['circuit'])
        actifs = c.get('actifs', [])
        mode = c.get('mode', 'etape')
        xs = [X0 + i * PAS for i in range(len(NOEUDS))]
        cy = Y_NOEUD + 56
        noeuds = []
        for i, (cle, nom) in enumerate(NOEUDS):
            vous = '<span class="cir-vous" id="cir-vous-%s">VOUS</span>' % cle if (cle in actifs and mode != 'transverse') else ''
            noeuds.append('<div class="cir-noeud" id="cir-n-%s" style="left:%dpx;top:%dpx">%s'
                          '<div class="cir-rond%s" id="cir-r-%s">%s</div><div class="cir-nom" id="cir-nom-%s">%s</div></div>'
                          % (cle, xs[i], Y_NOEUD, vous, ' fin' if cle == 'fin' else '', cle,
                             '✓' if cle == 'fin' else i + 1, cle, e(nom)))
        zones = ('<div class="cir-zone" id="cir-z1" style="left:%dpx;width:%dpx;top:290px">Agence</div>'
                 '<div class="cir-zone" id="cir-z2" style="left:%dpx;width:%dpx;top:290px">Direction centrale</div>'
                 % (xs[0] - 95, xs[2] - xs[0] + 190, xs[3] - 95, xs[6] - xs[3] + 190))
        ligne = ('<div class="cir-ligne" id="cir-ligne" style="left:%dpx;top:%dpx;width:%dpx"></div>'
                 '<div class="cir-progres" id="cir-prog" style="left:%dpx;top:%dpx;width:%dpx"></div>'
                 % (xs[0], cy - 3, xs[-1] - xs[0], xs[0], cy - 3, xs[-1] - xs[0]))
        loupe = ''
        if mode == 'transverse':
            loupe = ('<div class="cir-loupe" id="cir-loupe" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx">'
                     '<span class="lib">%s</span></div>' % (xs[0] - 115, Y_NOEUD - 50, xs[-1] - xs[0] + 230, 270,
                                                           e(c.get('loupe', 'Tout le circuit'))))
        html = ('<div class="scene-in" id="cir-in"><div class="cir-tete" id="cir-tete"><div class="kicker">2 · Où vous intervenez</div>'
                '<div class="titre-scene" style="margin-top:14px">%s</div></div>%s%s%s%s'
                '<div class="cir-note" id="cir-note">%s</div></div>'
                % (e(c.get('titre', "Le parcours d'une demande de transfert")), zones, ligne, ''.join(noeuds), loupe,
                   c['note']))
        self.clip('sc-circuit', t, d, html, 3)
        self.entree('#cir-tete', t + 0.1, y=20)
        self.entree('#cir-z1, #cir-z2', t + 0.4, y=12, decalage=0.12)
        # immediateRender : sans lui, la ligne et la progression dorée s'affichent
        # pleines dès l'entrée de la scène, puis repartent de zéro
        self.op(op='fromTo', sel='#cir-ligne', de={'scaleX': 0, 'transformOrigin': '0% 50%'},
                a={'scaleX': 1, 'duration': 0.9, 'ease': 'power2.inOut', 'immediateRender': True}, t=t + 0.5)
        self.entree('#cir-in .cir-noeud', t + 0.55, d=0.45, y=26, decalage=0.08)
        # la progression dorée jusqu'au dernier nœud actif (ou tout le circuit)
        if mode == 'transverse' or not actifs or c.get('progres') == 'tout':
            ratio = 1.0
        else:
            dernier = max(i for i, (cle, _) in enumerate(NOEUDS) if cle in actifs)
            ratio = (xs[dernier] - xs[0]) / float(xs[-1] - xs[0])
        tp = t + 1.5
        self.op(op='fromTo', sel='#cir-prog', de={'scaleX': 0, 'transformOrigin': '0% 50%'},
                a={'scaleX': max(ratio, 0.001), 'duration': 1.1, 'ease': 'power2.inOut', 'immediateRender': True}, t=tp)
        ta = tp + 1.1
        for i, (cle, _) in enumerate(NOEUDS):
            allume = cle in actifs or mode == 'transverse'
            if allume:
                self.op(op='classe', sel='#cir-r-%s' % cle, ajouter=['actif'], retirer=[], t=round(ta, 3))
                self.op(op='classe', sel='#cir-nom-%s' % cle, ajouter=['actif'], retirer=[], t=round(ta, 3))
                self.op(op='fromTo', sel='#cir-r-%s' % cle, de={'scale': 0.85},
                        a={'scale': 1, 'duration': 0.5, 'ease': 'back.out(2.2)'}, t=round(ta, 3))
                if mode != 'transverse':
                    self.entree('#cir-vous-%s' % cle, ta + 0.15, d=0.4, y=14)
        if mode == 'transverse':
            self.entree('#cir-loupe', ta - 0.3, d=0.5, y=0, echelle=1.04)
        self.entree('#cir-note', ta + 0.35, y=20)
        self.sortie('#cir-in', t + d - SORTIE)
        self.poser_voix('circuit', t)
        return t + d

    def scene_connexion(self, t):
        c = self.s['connexion']
        client = c.get('mode') == 'client'
        d = self.duree('connexion', BASE['connexion'])
        if client:
            items = [("Votre matricule client", "Celui que votre agence vous a communiqué, du type CL00001 — pas votre adresse e-mail."),
                     ('Votre mot de passe', 'Choisi à l\'activation de votre espace, depuis le lien d\'invitation.'),
                     ('Le code à six chiffres', 'Reçu par courriel à chaque connexion, valable cinq minutes.')]
            carte = ('<div class="carte-con" id="con-carte"><div class="logo"><img src="assets/logos/bgfi.png" alt=""></div>'
                     '<div class="sur">ESPACE CLIENT</div><div class="h">Connexion à votre espace</div>'
                     '<div class="sous">Transferts internationaux &amp; domiciliations</div>'
                     '<div class="lab">Matricule client</div>%s'
                     '<div class="aide">Matricule communiqué par votre gestionnaire (4 à 7 caractères).</div>'
                     '<div class="lab">Mot de passe</div>%s<div class="bouton-con" id="con-go">Se connecter</div>'
                     '<div class="liens">Mot de passe oublié ? · <b>Vous êtes collaborateur ?</b></div></div>'
                     % (self._entree('con-mat', 'Ex: C012'), self._entree('con-mdp', '')))
        else:
            items = [('Votre matricule', 'Sept caractères, inscrits sur votre fiche — et non votre adresse e-mail.'),
                     ('Votre mot de passe', "Celui du réseau de la banque quand l'annuaire Active Directory est raccordé."),
                     ('Le code à six chiffres', 'Reçu par courriel à chaque connexion, valable cinq minutes.')]
            carte = ('<div class="carte-con" id="con-carte"><div class="logo"><img src="assets/logos/bgfi.png" alt=""></div>'
                     '<div class="lab">Identifiant</div>%s<div class="aide">Saisissez votre matricule collaborateur</div>'
                     '<div class="lab">Mot de passe</div>%s<div class="bouton-con" id="con-go">Se connecter</div>'
                     '<div class="liens">Vous êtes client de la banque ? <b>Accéder à l\'Espace Client</b></div></div>'
                     % (self._entree('con-mat', 'Ex: AG00120'), self._entree('con-mdp', 'Mot de passe')))
        otp = ('<div class="carte-con carte-otp masque" id="con-otp"><div class="h">Vérification en deux étapes</div>'
               '<div class="p">Un code à six chiffres a été envoyé à <strong>%s</strong>. Il est valable cinq minutes.</div>'
               '<div class="lab">Code de vérification</div>%s<div class="bouton-con" id="con-valider">Valider</div>'
               '<div class="renvoi">Je n\'ai rien reçu — renvoyer un code</div></div>'
               % (e(c['courriel']), self._entree('con-code', '000000', classe='entree code')))
        ok = '<div class="con-ok masque" id="con-ok"><span class="pastille">%s Connecté</span></div>' % (
            '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>')
        liste = ''.join('<div class="con-item" id="con-i%d"><span class="con-num">%d</span><div><div class="t">%s</div>'
                        '<div class="s">%s</div></div></div>' % (i + 1, i + 1, e(a), e(b)) for i, (a, b) in enumerate(items))
        html = ('<div class="scene-in" id="con-in"><div class="con-texte" id="con-texte"><div class="kicker">3 · Prise en main</div>'
                '<div class="titre-scene" style="margin-top:14px">Se connecter</div><div class="con-items">%s</div></div>%s%s%s</div>'
                % (liste, carte, otp, ok))
        self.entree('#con-texte', t + 0.1, y=20)
        self.entree('#con-carte', t + 0.25, d=0.7, y=40)
        self.op(op='set', sel='#curseur', vars={'x': 1500, 'y': 1010}, t=round(t, 3))
        k = t + 0.7
        self.op(op='classe', sel='#con-i1', ajouter=['actif'], retirer=[], t=round(k, 3))
        self.op(op='classe', sel='#con-mat', ajouter=['focus'], retirer=[], t=round(k + 0.1, 3))
        self.op(op='set', sel='#con-mat-ph', vars={'autoAlpha': 0}, t=round(k + 0.2, 3))
        self.op(op='saisie', sel='#con-mat-val', texte=c['matricule'], t=round(k + 0.2, 3), d=0.8)
        k += 1.2
        self.op(op='classe', sel='#con-i2', ajouter=['actif'], retirer=[], t=round(k, 3))
        self.op(op='classe', sel='#con-mat', ajouter=[], retirer=['focus'], t=round(k, 3))
        self.op(op='classe', sel='#con-mdp', ajouter=['focus'], retirer=[], t=round(k, 3))
        if not client:
            self.op(op='set', sel='#con-mdp-ph', vars={'autoAlpha': 0}, t=round(k + 0.1, 3))
        self.op(op='saisie', sel='#con-mdp-val', texte='••••••••••', t=round(k + 0.1, 3), d=0.6)
        k += 0.8
        cle = self.cible('#con-go', 0.62, 0.6)
        self.op(op='curseur', cle=cle, t=round(k, 3), d=0.55)
        self.op(op='clic', cle=cle, t=round(k + 0.6, 3))
        k += 0.95
        self.sortie('#con-carte', k, d=0.3)
        self.entree('#con-otp', k + 0.2, d=0.5, y=30)
        self.op(op='classe', sel='#con-i3', ajouter=['actif'], retirer=[], t=round(k + 0.3, 3))
        self.op(op='classe', sel='#con-code', ajouter=['focus'], retirer=[], t=round(k + 0.55, 3))
        self.op(op='set', sel='#con-code-ph', vars={'autoAlpha': 0}, t=round(k + 0.7, 3))
        self.op(op='saisie', sel='#con-code-val', texte='482913', t=round(k + 0.7, 3), d=0.7)
        k += 1.55
        cle = self.cible('#con-valider', 0.62, 0.6)
        self.op(op='curseur', cle=cle, t=round(k, 3), d=0.5)
        self.op(op='clic', cle=cle, t=round(k + 0.55, 3))
        k += 0.85
        self.sortie('#con-otp', k, d=0.3)
        self.entree('#con-ok', k + 0.2, d=0.45, y=10, echelle=0.9)
        # le curseur s'écarte pour laisser lire « Connecté »
        self.op(op='to', sel='#curseur', vars={'x': 1660, 'y': 820, 'duration': 0.6, 'ease': 'power2.inOut'},
                t=round(k + 0.15, 3))
        # et la scène dure jusqu'à 0,8 s de « Connecté » pleinement affiché,
        # même quand la phrase est courte (il n'apparaissait qu'en s'effaçant)
        d = max(d, round(k + 0.2 + 0.45 + 0.8 + SORTIE - t, 2))
        self.clip('sc-connexion', t, d, html, 4)
        self.sortie('#con-in', t + d - SORTIE)
        self.poser_voix('connexion', t)
        return t + d

    def _entree(self, ident, placeholder, classe='entree'):
        ph = '<span class="ph" id="%s-ph">%s</span>' % (ident, e(placeholder))
        return '<div class="%s" id="%s">%s<span class="val" id="%s-val"></span></div>' % (classe, ident, ph, ident)

    def scene_ecran(self, t):
        """L'écran rejoué : la fenêtre, puis les étapes et leur légende."""
        s = self.s
        etapes = s['etapes']
        self.vues = dict(s.get('vues_initiales', {}))
        legendes = []
        debut = t
        k = t + 0.9                      # l'entrée de la fenêtre
        self.entree('#app', t + 0.05, d=0.75, y=50, echelle=0.97)
        # le curseur rejoint la fenêtre
        cle = self.cible('#app', 0.55, 0.55)
        self.op(op='curseur', cle=cle, t=round(t + 0.3, 3), d=0.8)
        for n, etape in enumerate(etapes, 1):
            case = 'etape-%d' % n
            t0 = k
            fin_gestes = self.jouer(etape['gestes'], t0 + 0.35)
            d = max(fin_gestes - t0 + 0.5, etape.get('min', 0))
            dv = self.durees_voix.get(case)
            if dv and d - (AVANT_VOIX + dv) > 3.0:
                self.alertes.append('étape %d : %.1f s d\'image pour %.1f s de voix — allonger la phrase ou scinder'
                                    % (n, d, dv))
            d = self.duree(case, d)
            self.etapes_t.append((round(t0, 3), round(d, 3)))
            pas = ''.join('<i class="%s"></i>' % ('on' if i <= n else '') for i in range(1, len(etapes) + 1))
            legendes.append('<div class="leg masque" id="leg-%d"><div class="num"><small>ÉTAPE</small><b>%d</b></div>'
                            '<div><div class="t">%s</div><div class="s">%s</div></div><div class="pas">%s</div></div>'
                            % (n, n, e(etape['titre']), e(etape['texte']), pas))
            self.entree('#leg-%d' % n, t0, d=0.45, y=20)
            self.sortie('#leg-%d' % n, t0 + d - 0.3, d=0.3)
            self.poser_voix(case, t0)
            self.reperes.append(round(t0 + d / 2.0, 2))
            k = t0 + d
        fin = k + 0.5
        self.sortie('#app', fin - SORTIE)
        self.clip('sc-app', debut, fin - debut, s['ecran'], 5, classes='clip')
        self.clip('legende', debut, fin - debut, ''.join(legendes), 6, classes='clip')
        return fin

    def scene_retenir(self, t):
        r = self.s['retenir']
        d = self.duree('retenir', BASE['retenir'])
        puces = ''.join('<div class="ret-puce"><span class="c">%s</span><span>%s</span></div>' % (ICONES['coche'], e(p))
                        for p in r['puces'])
        sous = '<div class="ret-sous" id="ret-sous">%s</div>' % e(r['sous']) if r.get('sous') else ''
        html = ('<div class="scene-in" id="ret-in"><div class="ret-bloc"><div class="kicker" id="ret-k">%s</div>'
                '<div class="ret-regle" id="ret-regle">%s</div>%s<div class="ret-puces">%s</div></div></div>'
                % (e(r.get('kicker', 'Le verrou du poste')), e(r['regle']), sous, puces))
        self.clip('sc-retenir', t, d, html, 7)
        self.entree('#ret-k', t + 0.1, y=16)
        self.entree('#ret-regle', t + 0.3, d=0.7, x=-60, y=0)
        if r.get('sous'):
            self.entree('#ret-sous', t + 0.8, y=16)
        self.entree('#ret-in .ret-puce', t + 1.3, d=0.5, y=24, decalage=0.3)
        self.sortie('#ret-in', t + d - SORTIE)
        self.poser_voix('retenir', t)
        return t + d

    def scene_fin(self, t):
        s = self.s
        d = self.duree('fin', BASE['fin'])
        html = ('<div class="scene-in" id="fin-in"><div class="fin-bloc"><div class="fin-logos" id="fin-logos">'
                '<div class="logo-carte bgfi"><img src="assets/logos/bgfi.png" alt=""></div>'
                '<div class="logo-carte aite"><img src="assets/logos/aite.png" alt=""></div></div>'
                '<div class="fin-titre" id="fin-t">PGest</div><div class="fin-sous" id="fin-s">Transferts internationaux &amp; domiciliations</div>'
                '<div class="fin-guide" id="fin-g">Guide complet : %s</div></div>'
                '<div class="fin-pied" id="fin-p">BGFI Bank Cameroun · Transformation digitale · AITE Consulting</div></div>'
                % e(s['guide']))
        self.clip('sc-fin', t, d, html, 8)
        self.entree('#fin-logos .logo-carte', t + 0.1, d=0.6, y=30, echelle=0.9, decalage=0.15)
        self.entree('#fin-t', t + 0.6, d=0.6, y=30)
        self.entree('#fin-s', t + 0.85, y=20)
        self.entree('#fin-g', t + 1.15, y=16)
        self.entree('#fin-p', t + 1.4, y=10)
        self.poser_voix('fin', t)
        return t + d

    # ---------------------------------------------------- les gestes posés --
    def jouer(self, gestes, t):
        """Pose une suite de gestes à partir de ``t`` ; rend l'instant de fin."""
        fin = t
        debut_prec = t
        for g in gestes:
            debut = (debut_prec if g.get('avec') else fin) + g.get('decale', 0)
            duree = self._poser(g, round(debut, 3))
            debut_prec = debut
            fin = max(fin, debut + duree + g.get('puis', PUIS[g['geste']]))
        return fin

    def _poser(self, g, t):
        k = g['geste']
        if k == 'curseur':
            cle = self.cible(g['sel'], g['fx'], g['fy'])
            self.op(op='curseur', cle=cle, t=t, d=g['d'])
            return g['d']
        if k == 'clic':
            cle = self.cible(g['sel'], g['fx'], g['fy'])
            dt = 0
            if g['deplacer']:
                self.op(op='curseur', cle=cle, t=t, d=g['d'])
                dt = g['d'] + 0.08
            self.op(op='clic', cle=cle, t=round(t + dt, 3))
            return dt + 0.3
        if k == 'saisir':
            i = g['ident']
            self.op(op='classe', sel='#' + i, ajouter=['focus'], retirer=[], t=t)
            self.op(op='set', sel='#%s-ph' % i, vars={'autoAlpha': 0}, t=t)
            self.op(op='saisie', sel='#%s-val' % i, texte=g['texte'], t=t, d=g['d'])
            self.op(op='classe', sel='#' + i, ajouter=[], retirer=['focus'], t=round(t + g['d'] + 0.4, 3))
            return g['d']
        if k == 'animer':
            a = dict(g['a'], duration=g['d'], ease=g.get('ease', 'power2.inOut'))
            self.op(op='fromTo', sel=g['sel'], de=g['de'], a=a, t=t)
            return g['d']
        if k == 'choisir':
            i = g['ident']
            self.op(op='classe', sel='#' + i, ajouter=['focus'], retirer=[], t=t)
            self.op(op='set', sel='#%s-ph' % i, vars={'autoAlpha': 0}, t=round(t + 0.15, 3))
            self.op(op='texte', sel='#%s-val' % i, apres=g['valeur'], t=round(t + 0.15, 3))
            self.op(op='fromTo', sel='#%s-val' % i, de={'autoAlpha': 0, 'y': 8},
                    a={'autoAlpha': 1, 'y': 0, 'duration': 0.25}, t=round(t + 0.15, 3))
            self.op(op='classe', sel='#' + i, ajouter=[], retirer=['focus'], t=round(t + 0.6, 3))
            return 0.4
        if k == 'vue':
            ancienne = self.vues.get(g['groupe'])
            if ancienne:
                self.op(op='fromTo', sel='#' + ancienne, de={'autoAlpha': 1}, a={'autoAlpha': 0, 'duration': 0.25}, t=t)
            self.op(op='fromTo', sel='#' + g['ident'], de={'autoAlpha': 0, 'x': 30},
                    a={'autoAlpha': 1, 'x': 0, 'duration': 0.4, 'ease': 'power2.out'}, t=round(t + 0.15, 3))
            self.vues[g['groupe']] = g['ident']
            return 0.55
        if k == 'montrer':
            self.entree(g['sel'], t, d=g['d'], y=g['y'])
            return g['d']
        if k == 'cacher':
            self.sortie(g['sel'], t, d=g['d'])
            return g['d']
        if k == 'ouvrir':
            i = g['ident']
            self.reperes.append(round(t + 1.0, 2))
            self.op(op='fromTo', sel='#%s-voile' % i, de={'autoAlpha': 0}, a={'autoAlpha': 1, 'duration': 0.3}, t=t)
            self.op(op='fromTo', sel='#' + i, de={'autoAlpha': 0, 'y': 40, 'scale': 0.97},
                    a={'autoAlpha': 1, 'y': 0, 'scale': 1, 'duration': 0.45, 'ease': 'power3.out'}, t=round(t + 0.05, 3))
            return 0.5
        if k == 'fermer':
            i = g['ident']
            self.sortie('#' + i, t, d=0.25)
            self.sortie('#%s-voile' % i, t + 0.05, d=0.25)
            return 0.3
        if k == 'classe':
            self.op(op='classe', sel=g['sel'], ajouter=g['ajouter'], retirer=g['retirer'], t=t)
            return 0.05
        if k == 'texte':
            self.op(op='texte', sel=g['sel'], apres=g['apres'], t=t)
            return 0.05
        if k == 'etat':
            self.op(op='fromTo', sel=g['sel'], de={'scale': 1}, a={'scale': 1.18, 'duration': 0.15, 'yoyo': True, 'repeat': 1}, t=t)
            self.op(op='texte', sel=g['sel'], apres=g['libelle'], t=round(t + 0.12, 3))
            self.op(op='classe', sel=g['sel'], classe='puce ' + g['genre'], t=round(t + 0.12, 3))
            return 0.3
        if k == 'compter':
            self.op(op='compteur', sel=g['sel'], de=g['de'], a=g['a'], d=g['d'], decimales=g['decimales'],
                    avant=g['avant'], apres=g['apres'], t=t)
            return g['d']
        if k == 'pause':
            return g['d']
        if k == 'defiler':
            avant = self.positions.get(g['sel'], 0)
            self.op(op='fromTo', sel=g['sel'], de={'y': avant}, a={'y': g['y'], 'duration': g['d'], 'ease': 'power2.inOut'}, t=t)
            self.positions[g['sel']] = g['y']
            self.defilements.append({'sel': g['sel'], 't': round(t + g['d'], 3), 'y': g['y']})
            return g['d']
        if k == 'anneau':
            cle = self.cible(g['sel'])
            self.op(op='anneau', sel='#anneau', cle=cle, t=t, d=g['d'])
            return g['d']
        if k == 'notifier':
            i = '#' + g['ident']
            self.op(op='fromTo', sel=i, de={'autoAlpha': 0, 'x': 50},
                    a={'autoAlpha': 1, 'x': 0, 'duration': 0.4, 'ease': 'power3.out'}, t=t)
            self.sortie(i, t + g['duree'], d=0.3)
            return 0.4
        raise ValueError('geste inconnu : %s' % k)

    def vignette(self):
        """L'instant de la vignette, après ``construire`` : ``{'etape': n}``,
        le milieu de l'étape n ; ``{'etape': n, 'apres': s}``, s secondes
        après son début. Les gestes d'une étape sont posés depuis son début,
        quelle que soit la voix : ``apres`` tient quand la voix change. Un
        nombre reste un instant absolu."""
        v = self.s.get('vignette', {'etape': 1})
        if isinstance(v, dict):
            t0, d = self.etapes_t[v['etape'] - 1]
            return round(t0 + v.get('apres', d / 2.0), 2)
        return float(v)

    # -------------------------------------------------------- assemblage --
    def construire(self):
        """Rend (html, durée totale)."""
        t = 0.0
        t = self.scene_ouverture(t)
        t = self.scene_poste(t)
        t = self.scene_circuit(t)
        t_con = t
        t = self.scene_connexion(t)
        t = self.scene_ecran(t)
        t_fin_ecran = t
        t = self.scene_retenir(t)
        t = self.scene_fin(t)
        total = round(t, 2)
        # le curseur vit de la connexion à la fin de l'écran
        self.couches.append(
            '<div id="couche-curseur" class="clip" data-start="%.3f" data-duration="%.3f" data-track-index="9">'
            '<div id="curseur">%s</div><div id="onde"></div><div class="anneau" id="anneau"></div></div>'
            % (t_con, t_fin_ecran - t_con, curseur_svg()))
        if self.presentateur:
            # le médaillon : une piste vidéo de toute la durée, décodée dès t=0, dans des
            # conteneurs non minutés (une vidéo minutée dans un calque minuté montre de
            # mauvaises images : erreur video_nested_in_timed_element de check)
            # (monter une vidéo en cours de route la décale d'une image), muette
            # (sa voix est posée scène par scène, comme la voix de synthèse)
            p = self.presentateur
            self.couches.append(
                '<div id="couche-presentateur">'
                '<div class="presentateur masque" id="presentateur"><div class="pres-cadre">'
                '<video id="pres-video" src="%s" data-start="0" data-duration="%.3f" data-track-index="17" muted '
                'playsinline></video></div><div class="pres-nom">%s</div><div class="pres-fonction">%s</div></div></div>'
                % (p['video'], total, e(p.get('nom', '')), e(p.get('fonction', ''))))
        fond = ('<div id="fond" class="clip" data-start="0" data-duration="%.3f" data-track-index="0">'
                '<div class="points"></div><div class="diag"></div><div class="filet-or"></div></div>' % total)
        audios = ''.join(
            '<audio id="voix-%s" src="%s" data-start="%.3f" data-duration="%.3f" data-track-index="%d"></audio>'
            % (case, chemin, debut, max(0.1, duree - 0.06), 20 + i)
            for i, (case, chemin, debut, duree) in enumerate(self.audios))
        # un clic sonore sur chaque clic du curseur ; la piste est écrite par
        # produire.py (sons.piste), de la durée de la vidéo
        self.sons.extend(sorted((round(o['t'] + CLIC_SONORE, 3), 'clic') for o in self.ops if o['op'] == 'clic'))
        if self.bruitages:
            audios += ('<audio id="bruitages" src="%s" data-start="0" data-duration="%.3f" data-track-index="19"></audio>'
                       % (self.bruitages, total))
        plan = {'duree': total, 'cibles': self.cibles, 'defilements': sorted(self.defilements, key=lambda d: d['t']),
                'ops': self.ops}
        plan_json = json.dumps(plan, ensure_ascii=False).replace('</', '<\\/')
        html = TEMPLATE % {
            'titre': escape('PGest — Guide vidéo — ' + self.s['titre']),
            'id': self.id, 'duree': total,
            'classe': ' class="avec-presentateur"' if self.presentateur else '',
            'couches': fond + ''.join(self.couches) + audios,
            'plan': plan_json,
            'css': '<style>%s</style>' % self.s['css'] if self.s.get('css') else '',
        }
        return html, total


TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920, height=1080">
<title>%(titre)s</title>
<script src="assets/gsap.min.js"></script>
<link rel="stylesheet" href="assets/pgest.css">
%(css)s
</head>
<body>
<div id="root"%(classe)s data-composition-id="%(id)s" data-start="0" data-duration="%(duree).3f" data-width="1920" data-height="1080">
%(couches)s
</div>
<script type="application/json" id="plan">%(plan)s</script>
<script src="assets/pgest-motion.js"></script>
<script>
  window.__timelines = window.__timelines || {};
  document.fonts.ready.then(function () {
    window.__timelines["%(id)s"] = PGEST.construire(JSON.parse(document.getElementById("plan").textContent));
  });
</script>
</body>
</html>
"""
