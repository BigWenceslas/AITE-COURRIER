# -*- coding: utf-8 -*-
"""La vidéo de présentation d'AITE Courrier : une longue vidéo à chapitres.

Le moteur de référence (``moteur.py``) produit une vidéo courte par profil.
Celle-ci présente toute la solution : une ouverture, le parcours d'un
courrier, les rôles, puis des chapitres, chacun annoncé par un carton et
rejoué dans l'application, étape par étape. Elle se termine par les
interfaces, la recette, ce qu'il faut retenir et la signature.

Les gestes, les durées pilotées par la voix et la timeline sont ceux de
``moteur.Video`` ; seules les scènes changent. Le scénario est dans
``scenarios/presentation.py``.
"""

import json
from html import escape

import moteur
import sons
from ecrans import ICONES, curseur_svg, e
from moteur import AVANT_VOIX, APRES_VOIX, CLIC_SONORE, SORTIE

INTRO = 2.6
BASE = {'ouverture': 5.0, 'cartes': 6.0, 'parcours': 8.0, 'roles': 7.0, 'sommaire': 7.0, 'chapitre': 3.4,
        'interfaces': 7.0, 'recette': 8.0, 'retenir': 7.0, 'fin': 6.0}


class Presentation(moteur.Video):

    def __init__(self, scenario, **kw):
        super().__init__(scenario, **kw)
        self.piste = 1
        self.etapes_t = []
        self.fenetres_curseur = []

    # ------------------------------------------------------------ outils --
    def _piste(self):
        self.piste = 2 if self.piste == 1 else 1
        return self.piste

    def scene(self, ident, t, base, case, html, entrees, classes='clip scene'):
        """Une scène fixe : ``entrees`` = [(sélecteur, décalage, options)]."""
        d = self.duree(case, base) if case else base
        self.clip(ident, t, d, html, self._piste(), classes)
        for sel, dt, opts in entrees:
            self.entree(sel, t + dt, **opts)
        self.sortie('#%s-in' % ident, t + d - SORTIE)
        if case:
            self.poser_voix(case, t)
        self.reperes.append(round(t + d - 0.6, 2))
        return t + d

    # ---------------------------------------------------------- ouverture --
    def scene_ouverture(self, t):
        s = self.s['ouverture']
        ti = t + INTRO
        d = INTRO + self.duree('ouverture', BASE['ouverture'])
        lettres = ''.join('<span class="lettre%s">%s</span>' % (' violet' if i >= 5 else '', '&nbsp;' if c == ' ' else e(c))
                          for i, c in enumerate('AITE Courrier'))
        mots = ' '.join('<span class="mot%s">%s</span>' % (' v' if m.startswith('*') else '', e(m.strip('*')))
                        for m in s['titre'].split())
        html = ('<div class="ouv" id="ouv-in"><div class="ouv-signe" id="ouv-signe">'
                '<div class="ouv-icone" id="ouv-icone"><img src="assets/logos/aite_courrier.png" alt=""></div>'
                '<div class="ouv-marque" id="ouv-marque">%s</div><div class="ouv-ligne" id="ouv-ligne"></div>'
                '<div class="ouv-sous" id="ouv-sous">%s</div></div>'
                '<div class="ouv-titre-bloc"><div class="kicker" id="ouv-k">%s</div><h1 class="ouv-titre" id="ouv-t">%s</h1>'
                '<div class="tirets" id="ouv-tirets"><i></i><i></i><i></i></div><p class="ouv-mission" id="ouv-m">%s</p></div></div>'
                % (lettres, e(s['sous']), e(s['kicker']), mots, e(s['mission'])))
        self.clip('sc-ouverture', t, d, html, self._piste())
        self.op(op='fromTo', sel='#fond .halo', de={'autoAlpha': 0, 'scale': 0.7},
                a={'autoAlpha': 1, 'scale': 1, 'duration': 1.4, 'ease': 'power2.out', 'immediateRender': True}, t=t)
        self.op(op='fromTo', sel='#ouv-icone', de={'autoAlpha': 0, 'y': 40, 'scale': 0.8, 'rotation': -8},
                a={'autoAlpha': 1, 'y': 0, 'scale': 1, 'rotation': 0, 'duration': 0.7, 'ease': 'back.out(1.7)',
                   'immediateRender': True}, t=round(t + sons.CARILLON - 0.55, 3))
        self.entree('#ouv-marque .lettre', t + sons.CARILLON, d=0.5, y=50, decalage=0.045)
        self.op(op='fromTo', sel='#ouv-ligne', de={'scaleX': 0},
                a={'scaleX': 1, 'duration': 0.7, 'ease': 'power3.inOut', 'immediateRender': True}, t=t + 1.35)
        self.entree('#ouv-sous', t + 1.55, d=0.45, y=16)
        self.op(op='fromTo', sel='#ouv-signe', de={'autoAlpha': 1, 'y': 0},
                a={'autoAlpha': 0, 'y': -40, 'duration': 0.45, 'ease': 'power2.in'}, t=round(ti - 0.5, 3))
        self.sons.append((round(t, 3), 'ouverture'))
        self.reperes.append(round(t + 2.0, 2))
        self.entree('#ouv-k', ti + 0.1, y=20)
        self.entree('#ouv-t .mot', ti + 0.3, d=0.7, y=70, decalage=0.07)
        self.entree('#ouv-tirets i', ti + 0.95, d=0.4, x=-30, y=0, decalage=0.1)
        self.entree('#ouv-m', ti + 1.2, y=24)
        self.sortie('#ouv-in', t + d - SORTIE)
        self.poser_voix('ouverture', ti)
        self.reperes.append(round(t + d - 0.6, 2))
        return t + d

    # ------------------------------------------------------------- cartes --
    def scene_cartes(self, t, bloc, n):
        ident = 'sc-cartes-%d' % n
        cartes = ''.join('<div class="carte %s"><div class="pt"><i></i><span>%s</span></div><div class="ct">%s</div>'
                         '<div class="cx">%s</div></div>' % ('vob'[i % 3].replace('v', ''), e(k), e(ti), e(tx))
                         for i, (k, ti, tx) in enumerate(bloc['cartes']))
        html = ('<div id="%s-in" class="clip"><div class="entete" id="%s-tete"><div class="kicker">%s</div>'
                '<div class="titre-scene">%s</div>%s</div><div class="cartes" style="grid-template-columns:repeat(%d,1fr);%s">%s</div></div>'
                % (ident, ident, e(bloc['kicker']), e(bloc['titre']),
                   '<div class="sous">%s</div>' % e(bloc['sous']) if bloc.get('sous') else '', len(bloc['cartes']),
                   'top:%dpx' % bloc.get('haut', 430), cartes))
        return self.scene(ident, t, BASE['cartes'], bloc['voix_cle'], html,
                          [('#%s-tete' % ident, 0.1, {'y': 24}),
                           ('#%s-in .carte' % ident, 0.5, {'d': 0.6, 'y': 40, 'decalage': 0.18})])

    # ----------------------------------------------------------- parcours --
    def scene_parcours(self, t):
        p = self.s['parcours']
        n = len(p['etapes'])
        x0, x1, y = 260, 1660, 470
        xs = [x0 + i * (x1 - x0) / (n - 1) for i in range(n)]
        noeuds = ''.join(
            '<div class="par-noeud" id="par-n%d" style="left:%dpx;top:%dpx"><div class="par-rond" id="par-r%d">%d</div>'
            '<div class="par-nom">%s</div><div class="par-role">%s</div><div class="par-sla">SLA %s h</div></div>'
            % (i, xs[i], y, i, i + 1, e(nom), e(role), e(sla)) for i, (nom, role, sla) in enumerate(p['etapes']))
        html = ('<div id="sc-parcours-in" class="clip"><div class="entete" id="par-tete"><div class="kicker">%s</div>'
                '<div class="titre-scene">%s</div></div>'
                '<div class="par-ligne" id="par-ligne" style="left:%dpx;top:%dpx;width:%dpx"></div>'
                '<div class="par-prog" id="par-prog" style="left:%dpx;top:%dpx;width:%dpx"></div>%s'
                '<div class="par-note" id="par-note">%s</div></div>'
                % (e(p['kicker']), e(p['titre']), x0, y + 45, x1 - x0, x0, y + 45, x1 - x0, noeuds, p['note']))
        d = self.duree('parcours', BASE['parcours'])
        self.clip('sc-parcours', t, d, html, self._piste())
        self.entree('#par-tete', t + 0.1, y=24)
        self.op(op='fromTo', sel='#par-ligne', de={'scaleX': 0, 'transformOrigin': '0% 50%'},
                a={'scaleX': 1, 'duration': 0.8, 'ease': 'power2.inOut', 'immediateRender': True}, t=t + 0.4)
        self.entree('#sc-parcours-in .par-noeud', t + 0.5, d=0.5, y=30, decalage=0.14)
        tp = t + 1.6
        self.op(op='fromTo', sel='#par-prog', de={'scaleX': 0, 'transformOrigin': '0% 50%'},
                a={'scaleX': 1, 'duration': 2.6, 'ease': 'none', 'immediateRender': True}, t=tp)
        for i in range(n):
            ta = round(tp + 2.6 * i / (n - 1), 3)
            self.op(op='classe', sel='#par-r%d' % i, ajouter=['actif'], retirer=[], t=ta)
            self.op(op='fromTo', sel='#par-r%d' % i, de={'scale': 0.85}, a={'scale': 1, 'duration': 0.45, 'ease': 'back.out(2.2)'}, t=ta)
        self.entree('#par-note', tp + 2.8, y=20)
        self.sortie('#sc-parcours-in', t + d - SORTIE)
        self.poser_voix('parcours', t)
        self.reperes.append(round(t + d - 0.6, 2))
        return t + d

    # -------------------------------------------------------------- rôles --
    def scene_roles(self, t):
        r = self.s['roles']
        cartes = ''.join('<div class="role"><div class="rb"></div><div class="rn">%s</div><div class="rd">%s</div></div>'
                         % (e(n), e(dsc)) for n, dsc in r['liste'])
        html = ('<div id="sc-roles-in" class="clip"><div class="entete" id="rol-tete"><div class="kicker">%s</div>'
                '<div class="titre-scene">%s</div><div class="sous">%s</div></div><div class="roles">%s</div></div>'
                % (e(r['kicker']), e(r['titre']), e(r['sous']), cartes))
        return self.scene('sc-roles', t, BASE['roles'], 'roles', html,
                          [('#rol-tete', 0.1, {'y': 24}), ('#sc-roles-in .role', 0.6, {'d': 0.5, 'y': 30, 'decalage': 0.12})])

    # ----------------------------------------------------------- sommaire --
    def scene_sommaire(self, t):
        items = ''.join('<div class="som-it"><b>%d</b><span>%s</span><em>%s</em></div>' % (i + 1, e(c['titre']), e(c['qui']))
                        for i, c in enumerate(self.s['chapitres']))
        html = ('<div id="sc-sommaire-in" class="clip"><div class="entete" id="som-tete"><div class="kicker">Le programme</div>'
                '<div class="titre-scene">%s</div></div><div class="som">%s</div></div>' % (e(self.s['sommaire_titre']), items))
        return self.scene('sc-sommaire', t, BASE['sommaire'], 'sommaire', html,
                          [('#som-tete', 0.1, {'y': 24}), ('#sc-sommaire-in .som-it', 0.5, {'d': 0.45, 'x': -40, 'y': 0, 'decalage': 0.1})])

    # ------------------------------------------------------- un chapitre --
    def scene_chapitre(self, t, n, c):
        ident = 'sc-chap-%d' % n
        mots = ' '.join('<span class="mot">%s</span>' % e(m) for m in c['titre'].split())
        roles = ''.join('<span>%s</span>' % e(x) for x in c.get('roles', []))
        html = ('<div id="%s-in" class="chap"><div class="chap-bloc"><div class="chap-k" id="%s-k">Chapitre %d</div>'
                '<div class="chap-t" id="%s-t">%s</div><div class="chap-trait" id="%s-tr"></div>'
                '<div class="chap-s" id="%s-s">%s</div></div><div class="chap-role" id="%s-r">%s</div></div>'
                % (ident, ident, n, ident, mots, ident, ident, e(c['sous']), ident, roles))
        case = 'chap-%d' % n
        d = self.duree(case, BASE['chapitre'])
        self.clip(ident, t, d, html, self._piste())
        self.op(op='fromTo', sel='#%s-in' % ident, de={'autoAlpha': 0}, a={'autoAlpha': 1, 'duration': 0.35, 'immediateRender': True}, t=t)
        self.entree('#%s-k' % ident, t + 0.2, y=20)
        self.entree('#%s-t .mot' % ident, t + 0.35, d=0.6, y=60, decalage=0.08)
        self.op(op='fromTo', sel='#%s-tr' % ident, de={'scaleX': 0}, a={'scaleX': 1, 'duration': 0.5, 'immediateRender': True}, t=t + 0.9)
        self.entree('#%s-s' % ident, t + 1.0, y=20)
        if roles:
            self.entree('#%s-r span' % ident, t + 1.25, d=0.4, y=16, decalage=0.1)
        self.sortie('#%s-in' % ident, t + d - SORTIE)
        self.poser_voix(case, t)
        self.reperes.append(round(t + d - 0.6, 2))
        return t + d

    def scene_ecran(self, t, n, c):
        """L'application rejouée, à gauche ; la légende de l'étape, à droite."""
        app = 'app-%d' % n
        self.vues = {app: c['vue_initiale']}
        legendes = []
        debut = t
        k = t + 0.9
        self.entree('#cadre-%d' % n, t + 0.05, d=0.7, y=50, echelle=0.97)
        self.entree('#badge-%d' % n, t + 0.2, d=0.5, y=14)
        self.op(op='set', sel='#curseur', vars={'autoAlpha': 1, 'x': 1180, 'y': 960}, t=round(t + 0.3, 3))
        self.fenetres_curseur.append(round(t, 3))
        for m, et in enumerate(c['etapes'], 1):
            case = 'c%d-e%d' % (n, m)
            t0 = k
            gestes = [dict(g, groupe=app) if g['geste'] == 'vue' else g for g in et['gestes']]
            fin = self.jouer(gestes, t0 + 0.35)
            d = max(fin - t0 + 0.5, et.get('min', 0))
            dv = self.durees_voix.get(case)
            if dv and d - (AVANT_VOIX + dv) > 3.0:
                self.alertes.append('chapitre %d, étape %d : %.1f s d\'image pour %.1f s de voix' % (n, m, d, dv))
            d = self.duree(case, d)
            self.etapes_t.append((n, m, round(t0, 3), round(d, 3)))
            pas = ''.join('<i class="%s"></i>' % ('on' if i <= m else '') for i in range(1, len(c['etapes']) + 1))
            legendes.append('<div class="leg masque" id="leg-%d-%d"><div class="lk">%s</div><div class="lt">%s</div>'
                            '<div class="ls">%s</div><div class="lp">%s</div></div>'
                            % (n, m, e(et['qui']), e(et['titre']), e(et['texte']), pas))
            self.entree('#leg-%d-%d' % (n, m), t0, d=0.5, x=40, y=0)
            self.sortie('#leg-%d-%d' % (n, m), t0 + d - 0.3, d=0.3)
            self.poser_voix(case, t0)
            self.reperes.append(round(t0 + d - 0.5, 2))
            k = t0 + d
        fin = k + 0.5
        self.sortie('#cadre-%d' % n, fin - SORTIE)
        self.sortie('#badge-%d' % n, fin - SORTIE)
        self.op(op='set', sel='#curseur', vars={'autoAlpha': 0}, t=round(fin - SORTIE, 3))
        badge = '<div class="chap-badge masque" id="badge-%d"><b>CHAPITRE %d</b>%s</div>' % (n, n, e(c['titre']))
        self.clip('sc-app-%d' % n, debut, fin - debut,
                  '<div class="cadre-app masque" id="cadre-%d">%s</div>%s' % (n, c['ecran'], badge), 3, classes='clip')
        self.clip('legende-%d' % n, debut, fin - debut, '<div class="legendes">%s</div>' % ''.join(legendes), 4, classes='clip')
        return fin

    # ---------------------------------------------- interfaces et recette --
    def scene_recette(self, t):
        r = self.s['recette']
        items = ''.join('<div class="rec-it"><span class="ok">%s</span><em>%s</em><span>%s</span></div>'
                        % (ICONES['coche'], e(code), e(lib)) for code, lib in r['scenarios'])
        chiffres = ''.join('<div class="chiffre"><b id="rec-c%d">%s</b><span>%s</span></div>' % (i, e(v), e(l))
                           for i, (v, l) in enumerate(r['chiffres']))
        html = ('<div id="sc-recette-in" class="clip"><div class="entete" id="rec-tete"><div class="kicker">%s</div>'
                '<div class="titre-scene">%s</div></div><div class="rec">%s</div><div class="chiffres" id="rec-ch">%s</div></div>'
                % (e(r['kicker']), e(r['titre']), items, chiffres))
        return self.scene('sc-recette', t, BASE['recette'], 'recette', html,
                          [('#rec-tete', 0.1, {'y': 24}), ('#sc-recette-in .rec-it', 0.5, {'d': 0.35, 'y': 16, 'decalage': 0.07}),
                           ('#rec-ch .chiffre', 2.2, {'d': 0.5, 'y': 30, 'decalage': 0.18})])

    def scene_retenir(self, t):
        r = self.s['retenir']
        cartes = ''.join('<div class="carte %s"><div class="pt"><i></i><span>%s</span></div><div class="cx">%s</div></div>'
                         % (['', 'b', 'o'][i % 3], e(k), e(x)) for i, (k, x) in enumerate(r['cartes']))
        html = ('<div id="sc-retenir-in" class="clip"><div class="entete" id="ret-k"><div class="kicker">À retenir</div></div>'
                '<div class="ret-regle" id="ret-regle">%s</div><div class="cartes" style="top:640px;grid-template-columns:repeat(%d,1fr)">%s</div></div>'
                % (r['regle'], len(r['cartes']), cartes))
        return self.scene('sc-retenir', t, BASE['retenir'], 'retenir', html,
                          [('#ret-k', 0.1, {'y': 16}), ('#ret-regle', 0.3, {'d': 0.7, 'x': -60, 'y': 0}),
                           ('#sc-retenir-in .carte', 1.2, {'d': 0.5, 'y': 30, 'decalage': 0.2})])

    def scene_fin(self, t):
        f = self.s['fin']
        html = ('<div id="sc-fin-in" class="clip"><div class="fin-bloc"><div class="fin-icone" id="fin-i">'
                '<img src="assets/logos/aite_courrier.png" alt=""></div><div class="fin-t" id="fin-t">AITE <span class="violet">Courrier</span></div>'
                '<div class="fin-s" id="fin-s">%s</div><div class="fin-aite" id="fin-a"><img src="assets/logos/aite.jpg" alt=""></div>'
                '<div class="fin-p" id="fin-p">%s</div></div></div>' % (e(f['sous']), e(f['pied'])))
        d = self.duree('fin', BASE['fin'])
        self.clip('sc-fin', t, d, html, self._piste())
        self.entree('#fin-i', t + 0.1, d=0.6, y=30, echelle=0.85)
        self.entree('#fin-t', t + 0.5, d=0.6, y=30)
        self.entree('#fin-s', t + 0.8, y=20)
        self.entree('#fin-a', t + 1.1, y=20)
        self.entree('#fin-p', t + 1.4, y=12)
        self.poser_voix('fin', t)
        self.reperes.append(round(t + d - 0.4, 2))
        return t + d

    # --------------------------------------------------------- assemblage --
    def vignette(self):
        v = self.s.get('vignette', {'chapitre': 1, 'etape': 1})
        for n, m, t0, d in self.etapes_t:
            if n == v['chapitre'] and m == v['etape']:
                return round(t0 + v.get('apres', d / 2.0), 2)
        return 3.0

    def construire(self):
        s = self.s
        t = self.scene_ouverture(0.0)
        for i, bloc in enumerate(s.get('cartes_intro', [])):
            t = self.scene_cartes(t, bloc, i)
        t = self.scene_parcours(t)
        t = self.scene_roles(t)
        t = self.scene_sommaire(t)
        for n, c in enumerate(s['chapitres'], 1):
            t = self.scene_chapitre(t, n, c)
            t = self.scene_ecran(t, n, c)
        for i, bloc in enumerate(s.get('cartes_fin', []), 10):
            t = self.scene_cartes(t, bloc, i)
        t = self.scene_recette(t)
        t = self.scene_retenir(t)
        t = self.scene_fin(t)
        total = round(t, 2)
        self.couches.append('<div id="couche-curseur" class="clip" data-start="0" data-duration="%.3f" data-track-index="9">'
                            '<div id="curseur" class="masque">%s</div><div id="onde"></div><div class="anneau" id="anneau"></div></div>'
                            % (total, curseur_svg()))
        fond = ('<div id="fond" class="clip" data-start="0" data-duration="%.3f" data-track-index="0"><div class="halo"></div>'
                '<div class="halo2"></div><div class="signature"><img src="assets/logos/aite_courrier.png" alt="">AITE Courrier</div></div>'
                % total)
        audios = ''.join('<audio id="voix-%s" src="%s" data-start="%.3f" data-duration="%.3f" data-track-index="%d"></audio>'
                         % (case, chemin, debut, max(0.1, duree - 0.06), 20 + (i % 2))
                         for i, (case, chemin, debut, duree) in enumerate(self.audios))
        self.sons.extend(sorted((round(o['t'] + CLIC_SONORE, 3), 'clic') for o in self.ops if o['op'] == 'clic'))
        if self.bruitages:
            audios += ('<audio id="bruitages" src="%s" data-start="0" data-duration="%.3f" data-track-index="19"></audio>'
                       % (self.bruitages, total))
        plan = {'duree': total, 'cibles': self.cibles, 'defilements': sorted(self.defilements, key=lambda x: x['t']), 'ops': self.ops}
        html = TEMPLATE % {'titre': escape(s['titre_page']), 'id': 'presentation', 'duree': total,
                           'couches': fond + ''.join(self.couches) + audios,
                           'plan': json.dumps(plan, ensure_ascii=False).replace('</', '<\\/')}
        return html, total


TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920, height=1080">
<title>%(titre)s</title>
<script src="assets/gsap.min.js"></script>
<link rel="stylesheet" href="assets/aite.css">
</head>
<body>
<div id="root" data-composition-id="%(id)s" data-start="0" data-duration="%(duree).3f" data-width="1920" data-height="1080">
%(couches)s
</div>
<script type="application/json" id="plan">%(plan)s</script>
<script src="assets/aite-motion.js"></script>
<script>
  window.__timelines = window.__timelines || {};
  document.fonts.ready.then(function () {
    window.__timelines["%(id)s"] = PGEST.construire(JSON.parse(document.getElementById("plan").textContent));
  });
</script>
</body>
</html>
"""
