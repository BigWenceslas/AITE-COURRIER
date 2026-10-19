# -*- coding: utf-8 -*-
"""Les tutoriels marketing : une vidéo par fonctionnalité d'AITE Courrier et
d'AITE ECM, au format des vidéos de lancement de logiciels (« explainer »).

Le déroulé, inspiré des deux vidéos d'exemple fournies (Fronter, Madison),
dans la charte AITE :

1. l'accroche — le problème, dit simplement : une question, un
   personnage, et autour de lui le désordre (plis égarés, relances,
   retards) ;
2. la révélation — la marque se pose, avec le nom de la fonctionnalité ;
3. l'aperçu — l'application dans sa fenêtre, sur fond violet, et les
   trois promesses en pastilles ;
4. le tutoriel — la fenêtre glisse à sa place de travail : chaque étape
   est rejouée dans l'application (thème MuK), avec zooms de caméra et
   bulles d'explication, et sa légende à droite ;
5. les bénéfices, puis l'appel à l'action.

Les gestes, la voix qui pilote les durées et la timeline sont ceux de
``moteur.Video`` ; les scénarios sont dans ``scenarios/tutos``.
"""

import json
from html import escape

import presentation
import sons
from ecrans import ICONES, curseur_svg, e
from moteur import AVANT_VOIX, CLIC_SONORE, SORTIE, _g, PUIS

BASE = {'accroche': 8.0, 'revelation': 4.6, 'apercu': 6.5, 'benefices': 7.5, 'cta': 6.5}

# La fenêtre de l'application à sa place de travail (pixels de la vidéo) :
# l'interface est écrite à 1100 × 700 et agrandie d'un facteur ECHELLE.
FEN_X, FEN_Y, FEN_L = 64, 136, 1290
ECHELLE = FEN_L / 1100.0
FEN_H = round(700 * ECHELLE)
BARRE = 36
# Au moment de l'aperçu, elle est plus petite, au centre, sur le fond violet.
HERO = {'s': 0.72, 'cx': 960, 'cy': 640}

PUIS.update({'zoom': 0.15, 'dezoom': 0.1, 'bulle': 0.1})


# ---------------------------------------------------- gestes de caméra --
def zoom(sel, s=1.6, d=0.9, fx=0.5, fy=0.5, **kw):
    """La caméra s'approche de ``sel`` (facteur ``s``), qui vient au centre
    de la fenêtre (ou en ``fx``, ``fy`` de la fenêtre)."""
    return _g('zoom', sel=sel, s=s, d=d, fx=fx, fy=fy, **kw)


def dezoom(d=0.8, **kw):
    return _g('dezoom', d=d, **kw)


def bulle(sel, texte, d=2.6, cote='droite', fx=None, **kw):
    """Une bulle d'explication à côté de ``sel`` (à droite, à gauche ou
    dessous) ; ``fx`` : point d'ancrage dans la largeur de ``sel``."""
    return _g('bulle', sel=sel, texte=texte, d=d, cote=cote, ax=fx, **kw)


# ------------------------------------------------- éléments de l'accroche --
PICTOS = {
    'lettre': '<svg viewBox="0 0 24 24" fill="none" stroke="#8E2A8E" stroke-width="2" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6l8.5 7 8.5-7"/></svg>',
    'alerte': '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2L1 21h22zM11 9h2v6h-2zm0 8h2v2h-2z"/></svg>',
    'bulle': '<svg viewBox="0 0 24 24" fill="#2E8CB2"><path d="M3 5h18v11H9l-5 4v-4H3z"/></svg>',
    'horloge': '<svg viewBox="0 0 24 24" fill="none" stroke="#B5651A" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2.5"/></svg>',
    'dossier': '<svg viewBox="0 0 24 24" fill="#F0921F"><path d="M2 6a2 2 0 012-2h5l2 2h9a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2z"/></svg>',
    'question': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#8E2A8E"/><path d="M9.2 9.3a2.9 2.9 0 015.6.9c0 1.9-2.8 2.3-2.8 4.1" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="17.6" r="1.3" fill="#fff"/></svg>',
    'doc': '<svg viewBox="0 0 24 24" fill="none" stroke="#5E5665" stroke-width="2" stroke-linejoin="round"><path d="M14 2H6v20h12V6z"/><path d="M14 2v4h4M9 12h6M9 16h6"/></svg>',
    'cle': '<svg viewBox="0 0 24 24" fill="none" stroke="#1D6A8A" stroke-width="2.2" stroke-linecap="round"><circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/></svg>',
}
GENRE_PICTO = {'lettre': 'lettre', 'alerte': 'alerte', 'bulle': 'bulle', 'note': 'horloge', 'dossier': 'dossier', 'doc': 'doc'}
# Les emplacements du désordre autour du personnage (décalage depuis son centre).
PLACES = [(-330, -250), (150, -300), (300, -130), (-400, -10), (330, 100), (-320, 230), (40, 300), (300, 280)]

ICONES_GAIN = {
    'temps': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6"/></svg>',
    'trace': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19l5-6 4 3 7-9"/><circle cx="20" cy="7" r="1.6" fill="#fff"/></svg>',
    'bouclier': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linejoin="round"><path d="M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5z"/><path d="M8.5 12l2.5 2.5 4.5-5" stroke-linecap="round"/></svg>',
    'cible': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="#fff"/></svg>',
    'equipe': '<svg viewBox="0 0 24 24" fill="#fff"><circle cx="8" cy="8" r="3.2"/><circle cx="16.5" cy="9" r="2.8"/><path d="M2.5 19c.6-3.6 2.8-5.6 5.5-5.6s4.9 2 5.5 5.6zM12 19c.5-3 2.3-4.7 4.5-4.7S20.5 16 21 19z"/></svg>',
    'doc': '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"><path d="M14 2H6v20h12V6z"/><path d="M14 2v4h4M9 12h6M9 16h6"/></svg>',
    'cadenas': '<svg viewBox="0 0 24 24" fill="#fff"><path d="M7 10V7a5 5 0 0110 0v3h1.5v11h-13V10zm2.4 0h5.2V7a2.6 2.6 0 00-5.2 0z"/></svg>',
    'eclair': '<svg viewBox="0 0 24 24" fill="#fff"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg>',
}


class Tutoriel(presentation.Presentation):

    def __init__(self, scenario, **kw):
        super().__init__(scenario, **kw)
        self.cameras = []
        self.app = None
        self.bulles = []
        self.bulles_actives = []
        self.t_vignette = None

    # ------------------------------------------------------------ outils --
    def _poser(self, g, t):
        k = g['geste']
        cam = '#cam-%s' % self.s['slug']
        if k in ('zoom', 'dezoom'):
            # une bulle ne suivrait pas sa cible pendant un mouvement de caméra :
            # la caméra attend qu'elle ait fini d'être lue
            attente = max([0.0] + [fin + 0.3 - t for _, fin in self.bulles_actives])
            self.bulles_actives = []
            t = round(t + attente, 3)
            if k == 'zoom':
                cle = self.cible(g['sel'])
                self.op(op='camera', sel=cam, cle=cle, s=g['s'], fx=g['fx'], fy=g['fy'], t=t, d=g['d'])
            else:
                self.op(op='camera', sel=cam, s=1, t=t, d=g['d'])
            return attente + g['d']
        if k == 'bulle':
            n = len(self.bulles)
            ident = 'bul-%d' % n
            self.bulles.append('<div class="bulle-tuto %s masque" id="%s"><i></i>%s</div>' % (g['cote'], ident, e(g['texte'])))
            fx, fy, dx, dy = (1, 0.5, 18, 0) if g['cote'] == 'droite' else (0.5, 1, 0, 16)
            if g['cote'] == 'gauche':
                fx, fy, dx, dy = 0, 0.5, -18, 0
            if g.get('ax') is not None:
                fx = g['ax']
            self.bulles_actives.append((ident, t + g['d']))
            xp, yp = {'droite': (0, -50), 'gauche': (-100, -50), 'dessous': (-50, 0)}[g['cote']]
            self.op(op='etiquette', sel='#' + ident, cle=self.cible(g['sel']), fx=fx, fy=fy, dx=dx, dy=dy, xp=xp, yp=yp,
                    t=t, d=g['d'])
            return 0.4
        return super()._poser(g, t)

    def _mots(self, texte, classe='mot'):
        """Les mots d'un titre ; *mot* : en violet."""
        return ' '.join('<span class="%s%s">%s</span>' % (classe, ' v' if m.startswith('*') else '', e(m.strip('*')))
                        for m in texte.split())

    # ----------------------------------------------------------- accroche --
    def scene_accroche(self, t):
        a = self.s['accroche']
        serie = self.s['serie']
        nom, role, couleur = a['personnage']
        chaos = []
        for i, element in enumerate(a['chaos']):
            genre, texte = element[0], element[1]
            picto = element[2] if len(element) > 2 else GENRE_PICTO[genre]
            dx, dy = PLACES[i % len(PLACES)]
            chaos.append('<div class="chaos %s" style="left:%dpx;top:%dpx"><span class="pi">%s</span><span>%s</span></div>'
                         % (genre, 1390 + dx, 560 + dy, PICTOS[picto], e(texte)))
        html = ('<div id="sc-accroche-in" class="clip acc"><div class="acc-gauche"><div class="kicker" id="acc-k">%s</div>'
                '<h1 class="acc-q" id="acc-q">%s</h1><p class="acc-s" id="acc-s">%s</p></div>'
                '<div class="acc-perso" id="acc-p"><div class="acc-av" style="background:%s">%s</div>'
                '<div class="acc-nom">%s</div><div class="acc-role">%s</div></div>%s</div>'
                % (e('Tutoriel %02d · %s' % (serie['numero'], serie['produit'])), self._mots(a['question']), e(a['sous']),
                   couleur, e(nom[0]), e(nom), e(role), ''.join(chaos)))
        d = self.duree('accroche', BASE['accroche'])
        self.clip('sc-accroche', t, d, html, self._piste())
        self.entree('#acc-k', t + 0.15, y=20)
        self.entree('#acc-q .mot', t + 0.3, d=0.6, y=60, decalage=0.06)
        self.entree('#acc-s', t + 1.0, y=24)
        self.entree('#acc-p', t + 0.4, d=0.7, y=40, echelle=0.8)
        self.op(op='fromTo', sel='#sc-accroche-in .chaos', de={'autoAlpha': 0, 'scale': 0.4},
                a={'autoAlpha': 1, 'scale': 1, 'duration': 0.5, 'ease': 'back.out(2)', 'stagger': 0.32, 'immediateRender': True},
                t=round(t + 0.9, 3))
        # le désordre flotte : chaque élément monte et descend, déphasé
        for i in range(len(a['chaos'])):
            self.op(op='fromTo', sel='#sc-accroche-in .chaos:nth-of-type(%d)' % (i + 1), de={'y': 0},
                    a={'y': -12 if i % 2 else 12, 'duration': 1.6 + 0.2 * (i % 3), 'yoyo': True, 'repeat': int(d / 1.6),
                       'ease': 'sine.inOut'}, t=round(t + 1.5 + 0.32 * i, 3))
        # puis il est aspiré vers le personnage, juste avant la révélation
        fin = t + d
        self.op(op='to', sel='#sc-accroche-in .chaos', vars={'autoAlpha': 0, 'scale': 0.2, 'duration': 0.45, 'ease': 'power2.in',
                                                               'stagger': 0.04}, t=round(fin - 0.9, 3))
        self.sortie('#sc-accroche-in', fin - SORTIE)
        self.poser_voix('accroche', t)
        self.reperes.append(round(t + d - 1.2, 2))
        return fin

    # --------------------------------------------------------- révélation --
    def scene_revelation(self, t):
        serie = self.s['serie']
        m1, m2 = serie['marque']
        nom = m1 + ' ' + m2
        lettres = ''.join('<span class="lettre%s">%s</span>' % (' violet' if i > len(m1) else '', '&nbsp;' if c == ' ' else e(c))
                          for i, c in enumerate(nom))
        html = ('<div id="sc-revelation-in" class="clip rev"><div class="rev-a" id="rev-a"></div><div class="rev-b" id="rev-b"></div>'
                '<div class="rev-c" id="rev-c"></div><div class="rev-icone" id="rev-i"><img src="assets/logos/%s" alt=""></div>'
                '<div class="rev-marque" id="rev-m">%s</div><div class="rev-pill" id="rev-p"><b>Tutoriel %02d</b>%s</div></div>'
                % (serie['icone'], lettres, serie['numero'], e(self.s['titre'])))
        d = self.duree('revelation', BASE['revelation'])
        self.clip('sc-revelation', t, d, html, self._piste())
        for sel, de, dt in (('#rev-a', {'scale': 0, 'x': -200}, 0.0), ('#rev-b', {'scale': 0, 'x': 200}, 0.1), ('#rev-c', {'scale': 0}, 0.25)):
            self.op(op='fromTo', sel=sel, de=dict(de, autoAlpha=1),
                    a={'scale': 1, 'x': 0, 'duration': 0.9, 'ease': 'expo.out', 'immediateRender': True}, t=round(t + dt, 3))
        self.op(op='fromTo', sel='#rev-i', de={'autoAlpha': 0, 'y': 40, 'scale': 0.6, 'rotation': -10},
                a={'autoAlpha': 1, 'y': 0, 'scale': 1, 'rotation': 0, 'duration': 0.7, 'ease': 'back.out(1.8)', 'immediateRender': True},
                t=round(t + sons.CARILLON - 0.5, 3))
        self.entree('#rev-m .lettre', t + sons.CARILLON, d=0.5, y=50, decalage=0.04)
        self.entree('#rev-p', t + 1.5, d=0.6, y=24, echelle=0.9)
        self.sons.append((round(t, 3), 'ouverture'))
        self.sortie('#sc-revelation-in', t + d - SORTIE)
        self.poser_voix('revelation', t + 0.6)
        self.reperes.append(round(t + d - 0.6, 2))
        return t + d

    # ---------------------------------------------- aperçu, puis tutoriel --
    def scene_produit(self, t):
        s = self.s
        slug = s['slug']
        app = 'app-' + slug
        self.vues = {app: s['vue_initiale']}
        pills = ''.join('<span class="pill"><i></i>%s</span>' % e(p) for p in s['apercu']['pastilles'])
        da = self.duree('apercu', BASE['apercu'])
        # -- l'aperçu : fond violet, fenêtre au centre, pastilles
        t_fond = t
        self.op(op='fromTo', sel='#pr-fond', de={'autoAlpha': 0}, a={'autoAlpha': 1, 'duration': 0.4, 'immediateRender': True}, t=t)
        self.entree('#pr-k', t + 0.3, y=20)
        self.entree('#pr-t .mot', t + 0.45, d=0.55, y=40, decalage=0.06)
        dx, dy = HERO['cx'] - (FEN_X + FEN_L / 2), HERO['cy'] - (FEN_Y + (FEN_H + BARRE) / 2)
        self.op(op='fromTo', sel='#pr-fen', de={'autoAlpha': 0, 'x': dx, 'y': dy + 260, 'scale': HERO['s'] * 0.92, 'rotationX': 24},
                a={'autoAlpha': 1, 'x': dx, 'y': dy, 'scale': HERO['s'], 'rotationX': 0, 'duration': 1.1, 'ease': 'power3.out',
                   'immediateRender': True}, t=round(t + 0.5, 3))
        self.op(op='fromTo', sel='#pr-pills .pill', de={'autoAlpha': 0, 'y': 30, 'scale': 0.8},
                a={'autoAlpha': 1, 'y': 0, 'scale': 1, 'duration': 0.5, 'ease': 'back.out(2)', 'stagger': 0.45, 'immediateRender': True},
                t=round(t + 1.6, 3))
        self.poser_voix('apercu', t)
        self.reperes.append(round(t + da - 0.8, 2))
        self.t_vignette = round(t + da - 0.8, 2)
        # -- passage au tutoriel : le fond s'efface, la fenêtre glisse à sa place
        tb = t + da
        self.op(op='to', sel='#pr-fond', vars={'autoAlpha': 0, 'duration': 0.6, 'ease': 'power1.inOut'}, t=round(tb, 3))
        self.op(op='to', sel='#pr-haut', vars={'autoAlpha': 0, 'y': -40, 'duration': 0.45, 'ease': 'power2.in'}, t=round(tb - 0.1, 3))
        self.op(op='to', sel='#pr-fen', vars={'x': 0, 'y': 0, 'scale': 1, 'duration': 0.9, 'ease': 'power3.inOut'}, t=round(tb, 3))
        self.op(op='fromTo', sel='#pr-badge', de={'autoAlpha': 0, 'y': -14},
                a={'autoAlpha': 1, 'y': 0, 'duration': 0.5, 'immediateRender': True}, t=round(tb + 0.7, 3))
        self.op(op='set', sel='#curseur', vars={'autoAlpha': 1, 'x': 1450, 'y': 1000}, t=round(tb + 0.8, 3))
        self.op(op='fromTo', sel='#fond .signature', de={'autoAlpha': 0}, a={'autoAlpha': 1, 'duration': 0.4}, t=round(tb + 0.5, 3))
        # -- les étapes
        k = tb + 1.1
        legendes = []
        n = len(s['etapes'])
        for m, et in enumerate(s['etapes'], 1):
            case = 'e%d' % m
            t0 = k
            gestes = [dict(g, groupe=app) if g['geste'] == 'vue' else g for g in et['gestes']]
            fin = self.jouer(gestes, t0 + 0.35)
            d = max(fin - t0 + 0.5, et.get('min', 0))
            dv = self.durees_voix.get(case)
            if dv and d - (AVANT_VOIX + dv) > 3.0:
                self.alertes.append('étape %d : %.1f s d\'image pour %.1f s de voix' % (m, d, dv))
            d = self.duree(case, d)
            self.etapes_t.append((1, m, round(t0, 3), round(d, 3)))
            pas = ''.join('<i class="%s"></i>' % ('on' if i <= m else '') for i in range(1, n + 1))
            legendes.append('<div class="leg tuto masque" id="leg-%d"><div class="ln">%d</div><div class="lk">Étape %d sur %d</div>'
                            '<div class="lt">%s</div><div class="ls">%s</div><div class="lp">%s</div></div>'
                            % (m, m, m, n, e(et['titre']), e(et['texte']), pas))
            self.entree('#leg-%d' % m, t0, d=0.5, x=40, y=0)
            self.sortie('#leg-%d' % m, t0 + d - 0.3, d=0.3)
            self.poser_voix(case, t0)
            self.reperes.append(round(t0 + d - 0.5, 2))
            k = t0 + d
        fin = k + 0.4
        self.sortie('#pr-fen', fin - SORTIE)
        self.sortie('#pr-badge', fin - SORTIE)
        self.op(op='set', sel='#curseur', vars={'autoAlpha': 0}, t=round(fin - SORTIE, 3))
        cam = 'cam-' + slug
        self.cameras.append('#' + cam)
        fenetre = ('<div class="pr-fen masque" id="pr-fen" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx">'
                   '<div class="pr-barre"><i></i><i></i><i></i><span id="pr-url">%s</span></div>'
                   '<div class="pr-vue" style="height:%dpx"><div class="camera" id="%s"><div class="pr-app" style="transform:scale(%.5f)">%s</div>'
                   '</div></div></div>'
                   % (FEN_X, FEN_Y, FEN_L, FEN_H + BARRE, e(s['adresse']), FEN_H, cam, ECHELLE, s['ecran']))
        haut = ('<div class="pr-haut" id="pr-haut"><div class="kicker clair" id="pr-k">%s</div><div class="pr-t" id="pr-t">%s</div>'
                '<div class="pr-pills" id="pr-pills">%s</div></div>'
                % (e(s['apercu']['kicker']), self._mots(s['apercu']['titre']), pills))
        badge = ('<div class="chap-badge masque" id="pr-badge"><b>TUTORIEL %02d</b>%s</div>' % (s['serie']['numero'], e(s['titre'])))
        self.clip('sc-produit', t_fond, fin - t_fond,
                  '<div class="pr-fond masque" id="pr-fond"></div>%s<div class="pr-scene">%s</div>%s' % (haut, fenetre, badge), 3, classes='clip')
        self.clip('legendes', tb, fin - tb, '<div class="legendes">%s</div>' % ''.join(legendes), 4, classes='clip')
        return fin

    # ---------------------------------------------------------- bénéfices --
    def scene_benefices(self, t):
        b = self.s['benefices']
        coul = ['', 'b', 'o']
        cartes = ''.join('<div class="carte gain %s"><div class="gi">%s</div><div class="gc">%s</div><div class="ct">%s</div>'
                         '<div class="cx">%s</div></div>' % (coul[i % 3], ICONES_GAIN[ico], e(chiffre), e(ti), e(tx))
                         for i, (ico, chiffre, ti, tx) in enumerate(b['cartes']))
        html = ('<div id="sc-benefices-in" class="clip"><div class="entete" id="ben-tete"><div class="kicker">Ce que vous y gagnez</div>'
                '<div class="titre-scene">%s</div></div><div class="cartes" style="top:420px;grid-template-columns:repeat(%d,1fr)">%s</div></div>'
                % (self._mots(b['titre']), len(b['cartes']), cartes))
        return self.scene('sc-benefices', t, BASE['benefices'], 'benefices', html,
                          [('#ben-tete', 0.1, {'y': 24}), ('#sc-benefices-in .carte', 0.5, {'d': 0.6, 'y': 50, 'decalage': 0.22})])

    # ---------------------------------------------------- appel à l'action --
    def scene_cta(self, t):
        c = self.s['cta']
        serie = self.s['serie']
        html = ('<div id="sc-cta-in" class="clip cta"><div class="cta-bloc"><div class="cta-icone" id="cta-i"><img src="assets/logos/%s" alt=""></div>'
                '<div class="cta-t" id="cta-t">%s</div><div class="cta-s" id="cta-s">%s</div>'
                '<div class="cta-bt" id="cta-bt">Prendre rendez-vous pour une démo</div><div class="cta-url" id="cta-u">aite-consulting.com'
                '<span>+237 656 801 098 · info@aite-consulting.com</span></div>'
                '<div class="cta-aite" id="cta-a"><img src="assets/logos/aite.jpg" alt=""></div></div></div>'
                % (serie['icone'], self._mots(c['titre']), e(c['sous'])))
        d = self.duree('cta', BASE['cta'])
        self.clip('sc-cta', t, d, html, self._piste())
        self.op(op='fromTo', sel='#sc-cta-in', de={'autoAlpha': 0}, a={'autoAlpha': 1, 'duration': 0.4, 'immediateRender': True}, t=t)
        self.entree('#cta-i', t + 0.2, d=0.6, y=30, echelle=0.8)
        self.entree('#cta-t .mot', t + 0.45, d=0.55, y=50, decalage=0.06)
        self.entree('#cta-s', t + 0.9, y=20)
        self.entree('#cta-bt', t + 1.2, d=0.6, y=20, echelle=0.85)
        self.entree('#cta-u', t + 1.5, y=14)
        self.entree('#cta-a', t + 1.8, y=14)
        # le curseur vient cliquer sur le bouton
        cle = self.cible('#cta-bt', 0.62, 0.6)
        self.op(op='set', sel='#curseur', vars={'autoAlpha': 1, 'x': 1700, 'y': 1040}, t=round(t + 1.6, 3))
        self.op(op='curseur', cle=cle, t=round(t + 1.8, 3), d=0.8)
        self.op(op='clic', cle=cle, t=round(t + 2.7, 3))
        self.op(op='fromTo', sel='#cta-bt', de={'scale': 1}, a={'scale': 0.94, 'duration': 0.1, 'yoyo': True, 'repeat': 1}, t=round(t + 2.7, 3))
        self.poser_voix('cta', t + 0.3)
        self.reperes.append(round(t + d - 0.5, 2))
        return t + d

    # --------------------------------------------------------- assemblage --
    def vignette(self):
        return self.t_vignette or 3.0

    def plages_voix(self):
        return [(debut, debut + duree) for _, _, debut, duree in self.audios]

    def construire(self):
        s = self.s
        t = self.scene_accroche(0.0)
        self.chapitres = [(0.0, 'Le problème')]
        # la signature du fond n'a rien à faire sous les scènes pleines (révélation,
        # aperçu violet, appel à l'action) : masquée, elle n'est plus prise pour
        # un texte illisible par le contrôle de contraste
        self.op(op='set', sel='#fond .signature', vars={'autoAlpha': 0}, t=round(t - 0.3, 3))
        t = self.scene_revelation(t)
        self.chapitres.append((t, 'La solution : ' + s['apercu']['titre'].replace('*', '')))
        t = self.scene_produit(t)
        for (_, m, t0, _), et in zip(self.etapes_t, s['etapes']):
            self.chapitres.append((t0, 'Étape %d — %s' % (m, et['titre'])))
        self.chapitres.append((t, 'Ce que vous y gagnez'))
        t = self.scene_benefices(t)
        self.chapitres.append((t, 'Demander une démonstration'))
        self.op(op='set', sel='#fond .signature', vars={'autoAlpha': 0}, t=round(t, 3))
        t = self.scene_cta(t)
        total = round(t, 2)
        self.couches.append('<div id="couche-curseur" class="clip" data-start="0" data-duration="%.3f" data-track-index="9">'
                            '<div id="curseur" class="masque">%s</div><div id="onde"></div><div class="anneau" id="anneau"></div>%s</div>'
                            % (total, curseur_svg(), ''.join(self.bulles)))
        serie = s['serie']
        fond = ('<div id="fond" class="clip" data-start="0" data-duration="%.3f" data-track-index="0"><div class="halo"></div>'
                '<div class="halo2"></div><div class="signature"><img src="assets/logos/%s" alt="">%s</div></div>'
                % (total, serie['icone'], e(' '.join(serie['marque']))))
        audios = ''.join('<audio id="voix-%s" src="%s" data-start="%.3f" data-duration="%.3f" data-track-index="%d"></audio>'
                         % (case, chemin, debut, max(0.1, duree - 0.06), 20 + (i % 2))
                         for i, (case, chemin, debut, duree) in enumerate(self.audios))
        self.sons.extend(sorted((round(o['t'] + CLIC_SONORE, 3), 'clic') for o in self.ops if o['op'] == 'clic'))
        if self.bruitages:
            audios += ('<audio id="bruitages" src="%s" data-start="0" data-duration="%.3f" data-track-index="19"></audio>'
                       % (self.bruitages, total))
        plan = {'duree': total, 'cibles': self.cibles, 'cameras': self.cameras,
                'defilements': sorted(self.defilements, key=lambda x: x['t']), 'ops': self.ops}
        style = '<style>%s</style>' % s['css'] if s.get('css') else ''
        html = presentation.TEMPLATE % {'titre': escape(s['titre_page']), 'id': s['slug'], 'duree': total,
                                        'couches': style + fond + ''.join(self.couches) + audios,
                                        'plan': json.dumps(plan, ensure_ascii=False).replace('</', '<\\/')}
        return html, total


def fiche_youtube(s, chapitres, total):
    """Le titre, la description (avec chapitres horodatés) et les mots-clés
    à coller dans YouTube, au format des vidéos de la chaîne AITE Consulting."""
    y = s['youtube']
    lignes = ['TITRE', y['titre'], '', 'DESCRIPTION', y['description'], '']
    lignes += ['%d:%02d %s' % (int(t) // 60, int(t) % 60, lib) for t, lib in chapitres]
    lignes += ['', 'Durée : %d min %02d s' % (int(total) // 60, int(total) % 60), '',
               "AITE Consulting — transformation digitale, dématérialisation et GED, ERP Odoo. Makepe Bloc F, Douala, Cameroun.",
               'Prenez rendez-vous pour une démonstration : https://aite-consulting.com/appointment',
               'Téléphone : +237 656 801 098 · E-mail : info@aite-consulting.com',
               'Le blog : https://aite-consulting.com/blog', '',
               'MOTS-CLÉS', ', '.join(y['mots_cles'])]
    return '\n'.join(lignes) + '\n'


def textes_voix(s):
    textes = {k: s[k]['voix'] for k in ('accroche', 'revelation', 'apercu', 'benefices', 'cta')}
    for m, et in enumerate(s['etapes'], 1):
        textes['e%d' % m] = et['voix']
    return textes
