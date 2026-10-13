/* ==========================================================================
   AITE Courrier — moteur d'animation (repris du moteur PGest).

   Lit le plan JSON écrit par docs/videos/presentation.py (balise #plan) et en tire
   la timeline GSAP que HyperFrames pilote image par image. Aucune horloge,
   aucun hasard : deux rendus du même plan donnent la même vidéo.

   Le plan porte :
   - `cibles`      : les éléments que vise le curseur, mesurés ici une fois
                     les polices chargées (une cible mesurée avant le
                     chargement des polices est décalée de quelques pixels) ;
   - `defilements` : les défilements de contenu, pour qu'un curseur qui vise
                     un bouton situé plus bas tienne compte du décalage ;
   - `ops`         : la liste des gestes, chacun à son instant absolu.
   ========================================================================== */
(function () {
  'use strict';

  function el(sel) {
    var e = document.querySelector(sel);
    if (!e) { throw new Error('PGEST : élément introuvable ' + sel); }
    return e;
  }

  /* Les calques hors de leur fenêtre peuvent être masqués par le moteur de
     rendu : on les affiche le temps de mesurer, puis on rend leur style. */
  function mesurer(plan) {
    var couches = Array.prototype.slice.call(document.querySelectorAll('#root > .clip'));
    var styles = couches.map(function (c) { return c.getAttribute('style'); });
    couches.forEach(function (c) { c.style.display = 'block'; c.style.visibility = 'visible'; });
    var P = {};
    Object.keys(plan.cibles).forEach(function (cle) {
      var c = plan.cibles[cle];
      var e = el(c.sel);
      var r = e.getBoundingClientRect();
      P[cle] = { x: r.left + r.width * c.fx, y: r.top + r.height * c.fy, w: r.width, h: r.height, l: r.left, t: r.top, el: e };
    });
    couches.forEach(function (c, i) {
      if (styles[i] === null) { c.removeAttribute('style'); } else { c.setAttribute('style', styles[i]); }
    });
    return P;
  }

  /* Décalage vertical d'une cible à l'instant t : le dernier défilement de
     chaque conteneur qui la contient. */
  function decalage(plan, cible, t) {
    var dy = 0, vus = {};
    for (var i = plan.defilements.length - 1; i >= 0; i--) {
      var d = plan.defilements[i];
      if (d.t > t + 1e-6 || vus[d.sel]) { continue; }
      vus[d.sel] = true;
      if (el(d.sel).contains(cible)) { dy += d.y; }
    }
    return dy;
  }

  function nombre(v, decimales) {
    return v.toLocaleString('fr-FR', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })
      .replace(/ /g, ' ');
  }

  var OPS = {
    fromTo: function (tl, o) {
      var a = Object.assign({ immediateRender: false }, o.a);
      tl.fromTo(o.sel, o.de, a, o.t);
    },
    to: function (tl, o) { tl.to(o.sel, o.vars, o.t); },
    set: function (tl, o) { tl.set(o.sel, o.vars, o.t); },

    curseur: function (tl, o, P, plan) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t + o.d);
      tl.to('#curseur', { x: p.x, y: p.y + dy, duration: o.d, ease: o.ease || 'power2.inOut' }, o.t);
    },

    clic: function (tl, o, P, plan) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t);
      tl.fromTo('#curseur-fleche', { scale: 1 },
        { scale: 0.8, duration: 0.09, yoyo: true, repeat: 1, ease: 'power1.inOut', transformOrigin: '8px 6px', immediateRender: false }, o.t);
      tl.set('#onde', { x: p.x - 45, y: p.y + dy - 45 }, o.t);
      tl.fromTo('#onde', { scale: 0.25, autoAlpha: 0.95 },
        { scale: 1.3, autoAlpha: 0, duration: 0.55, ease: 'power2.out', immediateRender: false }, o.t);
    },

    /* Un anneau doré autour d'une cible, pour la désigner sans cliquer. */
    anneau: function (tl, o, P, plan) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t);
      var m = 10;
      tl.set(o.sel, { x: p.l - m, y: p.t + dy - m, width: p.w + 2 * m, height: p.h + 2 * m }, o.t);
      tl.fromTo(o.sel, { autoAlpha: 0, scale: 1.08 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'power2.out', immediateRender: false }, o.t);
      tl.to(o.sel, { autoAlpha: 0, duration: 0.3 }, o.t + o.d);
    },

    saisie: function (tl, o) {
      var cible = el(o.sel);
      var texte = o.texte;
      var p = { n: 0 };
      tl.fromTo(p, { n: 0 }, {
        n: texte.length, duration: o.d, ease: 'none', immediateRender: false,
        onUpdate: function () { cible.textContent = texte.slice(0, Math.round(p.n)); }
      }, o.t);
    },

    /* Le texte « avant » est celui que porte l'élément à cet instant du plan :
       les changements successifs s'enchaînent sans que Python les connaisse. */
    texte: function (tl, o, P, plan, etat) {
      var cible = el(o.sel);
      if (!(o.sel in etat.textes)) { etat.textes[o.sel] = cible.textContent; }
      var avant = o.avant !== undefined ? o.avant : etat.textes[o.sel];
      etat.textes[o.sel] = o.apres;
      var p = { n: 0 };
      tl.fromTo(p, { n: 0 }, {
        n: 1, duration: 0.01, ease: 'none', immediateRender: false,
        onUpdate: function () { cible.textContent = p.n >= 1 ? o.apres : avant; }
      }, o.t);
    },

    compteur: function (tl, o) {
      var cible = el(o.sel);
      var p = { v: o.de };
      tl.fromTo(p, { v: o.de }, {
        v: o.a, duration: o.d, ease: 'power2.out', immediateRender: false,
        onUpdate: function () { cible.textContent = (o.avant || '') + nombre(p.v, o.decimales || 0) + (o.apres || ''); }
      }, o.t);
    },

    /* Une classe se pose entière (o.classe) ou par ajout / retrait, à partir
       des classes que l'élément porte à cet instant du plan. */
    classe: function (tl, o, P, plan, etat) {
      var cible = el(o.sel);
      if (!(o.sel in etat.classes)) { etat.classes[o.sel] = (cible.getAttribute('class') || '').split(/\s+/).filter(Boolean); }
      var liste;
      if (o.classe !== undefined) {
        liste = o.classe.split(/\s+/).filter(Boolean);
      } else {
        liste = etat.classes[o.sel].filter(function (c) { return (o.retirer || []).indexOf(c) < 0; });
        (o.ajouter || []).forEach(function (c) { if (liste.indexOf(c) < 0) { liste.push(c); } });
      }
      etat.classes[o.sel] = liste;
      tl.set(o.sel, { attr: { 'class': liste.join(' ') } }, o.t);
    }
  };

  /* L'écran rejoué superpose par nature : un assistant se pose sur la page,
     une notification sur la barre du haut, le contenu défile sous la bande
     d'actions. `hyperframes check` lit ses dérogations sur chaque élément de
     texte (elles ne s'héritent pas) : on les pose ici sur la page et la barre
     du haut seulement. Le contenu des assistants, les scènes, les légendes,
     le contraste et les débordements du cadre restent contrôlés. */
  function deroger() {
    var sel = '.o-app *';
    Array.prototype.forEach.call(document.querySelectorAll(sel), function (n) {
      n.setAttribute('data-layout-allow-overlap', '');
      n.setAttribute('data-layout-allow-occlusion', '');
    });
  }

  function construire(plan) {
    var tl = gsap.timeline({ paused: true });
    deroger();
    var P = mesurer(plan);
    var etat = { textes: {}, classes: {} };
    /* Les gestes sont posés dans l'ordre du temps : l'état suivi (textes,
       classes) est alors celui que l'écran affiche à cet instant. */
    var ops = plan.ops.slice().sort(function (a, b) { return a.t - b.t; });
    ops.forEach(function (o) {
      var f = OPS[o.op];
      if (!f) { throw new Error('PGEST : geste inconnu ' + o.op); }
      f(tl, o, P, plan, etat);
    });
    /* La timeline couvre toute la vidéo, même si le dernier geste tombe tôt. */
    tl.set({}, {}, plan.duree);
    return tl;
  }

  window.PGEST = { construire: construire };
})();
