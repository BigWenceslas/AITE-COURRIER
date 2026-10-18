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
    (plan.cameras || []).forEach(function (sel) {
      var r = el(sel).getBoundingClientRect();
      P['cam:' + sel] = { x: r.left, y: r.top, w: r.width, h: r.height };
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


  /* Les caméras : un zoom sur l'écran rejoué (op `camera`) agrandit un
     conteneur d'un facteur s autour de son coin haut-gauche O, puis le
     décale de T. Un point mesuré p (caméra au repos) s'affiche alors en
     O + (p − O)·s + T. Le curseur, l'onde, l'anneau et les étiquettes
     vivent hors de la caméra : on leur applique la même transformation. */
  function camera(P, plan, etat, e) {
    var cams = plan.cameras || [];
    for (var i = 0; i < cams.length; i++) {
      var c = etat.cams[cams[i]];
      if (c && el(cams[i]).contains(e)) { return { O: P['cam:' + cams[i]], s: c.s, x: c.x, y: c.y }; }
    }
    return null;
  }

  function projeter(cam, x, y) {
    if (!cam) { return { x: x, y: y, s: 1 }; }
    return { x: cam.O.x + (x - cam.O.x) * cam.s + cam.x, y: cam.O.y + (y - cam.O.y) * cam.s + cam.y, s: cam.s };
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

    curseur: function (tl, o, P, plan, etat) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t + o.d);
      etat.cur = { x: p.x, y: p.y + dy, el: p.el };
      var q = projeter(camera(P, plan, etat, p.el), p.x, p.y + dy);
      tl.to('#curseur', { x: q.x, y: q.y, duration: o.d, ease: o.ease || 'power2.inOut' }, o.t);
    },

    /* Zoom de caméra : `cle` (le point visé) vient au centre du conteneur
       (ou en cx, cy), facteur `s` ; s = 1 et sans cle : retour au plan large.
       Le décalage est borné pour que l'écran remplisse toujours sa fenêtre.
       Le curseur suit la caméra s'il pointe un élément qu'elle contient. */
    camera: function (tl, o, P, plan, etat) {
      var O = P['cam:' + o.sel];
      var s = o.s || 1, x = 0, y = 0;
      if (o.cle && s !== 1) {
        var f = P[o.cle];
        var dy = decalage(plan, f.el, o.t);
        var cx = O.x + O.w * (o.fx === undefined ? 0.5 : o.fx), cy = O.y + O.h * (o.fy === undefined ? 0.5 : o.fy);
        x = cx - O.x - (f.x - O.x) * s;
        y = cy - O.y - (f.y + dy - O.y) * s;
        x = Math.min(0, Math.max(O.w * (1 - s), x));
        y = Math.min(0, Math.max(O.h * (1 - s), y));
      }
      etat.cams[o.sel] = { s: s, x: x, y: y };
      tl.to(o.sel, { x: x, y: y, scale: s, transformOrigin: '0 0', duration: o.d, ease: o.ease || 'power2.inOut' }, o.t);
      if (etat.cur && el(o.sel).contains(etat.cur.el)) {
        var q = projeter(camera(P, plan, etat, etat.cur.el), etat.cur.x, etat.cur.y);
        tl.to('#curseur', { x: q.x, y: q.y, duration: o.d, ease: o.ease || 'power2.inOut' }, o.t);
      }
    },

    /* Une étiquette (bulle d'explication) posée à côté d'une cible. */
    etiquette: function (tl, o, P, plan, etat) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t);
      var cam = camera(P, plan, etat, p.el);
      var q = projeter(cam, p.l + p.w * (o.fx === undefined ? 1 : o.fx), p.t + dy + p.h * (o.fy === undefined ? 0.5 : o.fy));
      tl.set(o.sel, { x: q.x + (o.dx || 0), y: q.y + (o.dy || 0) }, o.t);
      tl.fromTo(o.sel, { autoAlpha: 0, scale: 0.85 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'back.out(1.8)', immediateRender: false }, o.t);
      tl.to(o.sel, { autoAlpha: 0, duration: 0.25 }, o.t + o.d);
    },

    clic: function (tl, o, P, plan, etat) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t);
      var q = projeter(camera(P, plan, etat, p.el), p.x, p.y + dy);
      tl.fromTo('#curseur-fleche', { scale: 1 },
        { scale: 0.8, duration: 0.09, yoyo: true, repeat: 1, ease: 'power1.inOut', transformOrigin: '8px 6px', immediateRender: false }, o.t);
      tl.set('#onde', { x: q.x - 45, y: q.y - 45 }, o.t);
      tl.fromTo('#onde', { scale: 0.25, autoAlpha: 0.95 },
        { scale: 1.3, autoAlpha: 0, duration: 0.55, ease: 'power2.out', immediateRender: false }, o.t);
    },

    /* Un anneau doré autour d'une cible, pour la désigner sans cliquer. */
    anneau: function (tl, o, P, plan, etat) {
      var p = P[o.cle];
      var dy = decalage(plan, p.el, o.t);
      var m = 10;
      var q = projeter(camera(P, plan, etat, p.el), p.l, p.t + dy);
      tl.set(o.sel, { x: q.x - m, y: q.y - m, width: p.w * q.s + 2 * m, height: p.h * q.s + 2 * m }, o.t);
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
    /* Les libellés coupés par « … » le sont aussi dans Odoo : voulu. */
    Array.prototype.forEach.call(document.querySelectorAll('.o-app .ell'), function (n) {
      n.setAttribute('data-layout-allow-overflow', '');
    });
  }

  function construire(plan) {
    var tl = gsap.timeline({ paused: true });
    deroger();
    var P = mesurer(plan);
    var etat = { textes: {}, classes: {}, cams: {}, cur: null };
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
