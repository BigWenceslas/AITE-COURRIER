# Écrire un tutoriel marketing (AITE Courrier, AITE ECM)

Une vidéo par fonctionnalité, de 70 à 110 secondes, au format « explainer »
(`tutoriel.py`) : **accroche** (le problème, un personnage, le désordre
autour de lui) → **révélation** de la marque → **aperçu** (l'application sur
fond violet, trois pastilles) → **tutoriel** en 3 ou 4 étapes, rejoué dans
l'application (thème MuK), avec zooms de caméra et bulles → **bénéfices**
(trois cartes) → **appel à l'action** (rendez-vous sur aite-consulting.com).

Exemples à lire avant d'écrire : `t01_enregistrer.py` (écran repris tel
quel), `t02_traiter.py` (étapes reprises d'un chapitre avec `etape()`),
`t04_cachet.py` (deux applications dans la même fenêtre, l'adresse qui
change).

## Produire et contrôler

```
cd docs/videos
python3 tutoriels.py 07 --planche          # voix + projet + check + planche contact
python3 tutoriels.py 07 --muet --planche --dossier /home/user/aite-videos/muet   # sans voix, plus rapide
python3 tutoriels.py 07 --rendu            # rendu MP4 + compression + fiche YouTube
```

Un tutoriel est prêt quand :

1. `check ok` (les avertissements `nested_structure…`, `timeline_track_too_dense`,
   `duplicate_media…` sont attendus ; un contraste signalé pendant un fondu
   aussi) ;
2. **aucune alerte** `⚠ étape N : … d'image pour … de voix` (seulement visible
   avec la voix) : allonger la phrase ou retirer des gestes ;
3. **chaque image de la planche** est relue (`Read` sur
   `…/snapshots/contact-sheet*.jpg`) : rien ne déborde de la fenêtre ni de
   l'écran, une bulle ne cache pas ce qu'elle explique, le curseur tombe sur sa
   cible, un zoom montre bien sa cible, la légende correspond à l'image.
   Pour voir un instant précis :
   `npx --yes hyperframes@0.8.139 snapshot --at 31.5,33 --no-end` dans le
   dossier du projet (`/home/user/aite-videos/fr/<slug>`).

## Les règles

- **Rien d'inventé.** Chaque libellé à l'écran (menus, boutons, champs,
  titres d'assistants, états, colonnes) existe mot pour mot dans le code :
  `addons/aite_*/views/*.xml`, chaînes des champs (`string=`) dans
  `models/*.py`, `wizard/*`, `data/*.xml`, gabarits OWL
  `static/src/**/*.xml`, contrôleurs du portail. Chaque règle dite par la voix
  (délais, durées par défaut, comportements) se retrouve dans le code ou dans
  `docs/` (guides, fiches produit, `docs/recette/GUIDE_RECETTE.md`). Citer les
  sources dans la docstring du module. Un doute se **signale**, il ne s'écrit
  pas. Pas de chiffre marketing inventé (« 50 % de temps gagné ») : les
  « chiffres » des cartes de bénéfices sont des libellés ou des valeurs réelles
  (« 48 h », « 4 niveaux », « COUR-2026-0141 »).
- **Personnes et organisations fictives**, toutes dans `demo.py`
  (`PERSONNES` : agent, assistante, manager, archiviste, audit, compta,
  signataire, admin ; `TIERS`, `FOURNISSEUR`). Jamais les noms du jeu de
  recette ni ceux de la base de démonstration (Aurélie Mbarga, Serge
  Kamdem…). Références plausibles : `COUR-2026-NNNN`, `DOC-2026-NNNNN`.
- **La voix pilote les durées** : ~15 caractères par seconde ; elle dit ce que
  l'image montre, sans la lire mot à mot ; ton commercial mais exact. Écrire
  « Aïte », « E C M », « A P I », « P D F » dans les voix (le lexique de
  `produire.py` corrige aussi AITE, ECM, API, PDF, SLA, OCR, WebDAV, Odoo) ;
  à l'écran, la graphie normale (« API »).

## Le dictionnaire `TUTO`

| Clé | Contenu |
|---|---|
| `slug` | `tuto-NN-titre-en-minuscules` (nom des fichiers livrés) |
| `titre_page`, `titre` | « AITE Courrier — Tutoriel NN : … », titre court (≤ 32 caractères) |
| `serie` | `dict(COURRIER, numero=NN)` ou `dict(ECM, numero=NN)` |
| `adresse` | barre d'adresse de la fenêtre : `ADRESSE % 'courrier'` ou `'ecm'`, ou une adresse de portail |
| `accroche` | `question` (≤ 50 caractères, `*mot*` en violet), `sous` (une phrase), `personnage` = (nom, rôle affiché, couleur), `chaos` = 8 × (genre, texte ≤ 26 caractères) avec genre ∈ `lettre`, `alerte`, `bulle`, `note`, `dossier`, `doc` ; `voix` (8 à 11 s) |
| `revelation` | `voix` : « Avec Aïte Courrier, … » (une phrase) |
| `apercu` | `kicker`, `titre` (`*mot*` en orange), `pastilles` (3, ≤ 28 caractères), `voix` |
| `ecran`, `vue_initiale` | le HTML de l'application (une ou plusieurs `fenetre()`), l'id de la vue affichée au départ (celle qui porte la classe `initiale`) |
| `etapes` | 3 ou 4 × {`titre` (≤ 40), `texte` (légende, ≤ 110), `voix` (10 à 18 s), `gestes`} |
| `benefices` | `titre`, `voix`, `cartes` = 3 × (icône, chiffre ≤ 14, titre, texte ≤ 80) ; icônes : `temps`, `trace`, `bouclier`, `cible`, `equipe`, `doc`, `cadenas`, `eclair` |
| `cta` | `cta('courrier' \| 'ecm', titre avec *mots*, phrase de début de voix)` |
| `youtube` | `youtube(TITRE EN MAJUSCULES « COMMENT … AVEC AITE COURRIER (ODOO 18) », description, mots-clés)` |
| `css` (facultatif) | règles propres à ce tutoriel, préfixées par un id du tutoriel |

Outils de `scenarios/tutos/__init__.py` : `etape(chapitre, i, titre, texte,
voix, avant=, apres=, inserer={k: [...]}, retirer=)` reprend les gestes de
l'étape `i` d'un chapitre de `scenarios/presentation.py` (ou de
`scenarios/chapitres_ecm.py`) ; `initiale(ecran, id, ancienne)` change la vue
de départ ; `cta()`, `youtube()`.

## Les gestes

`moteur.py` : `clic(sel, fx, fy)`, `curseur(sel)`, `survol(sel)`,
`saisir(id, texte, d)` et `choisir(id, valeur)` (sur un `entree(id)`),
`vue(id)` (importée sous le nom `aller` : change de vue), `montrer(sel)`,
`cacher(sel)`, `ouvrir(id)` / `fermer(id)` (un `assistant(id, …)`),
`classe(sel, ajouter, retirer)`, `texte(sel, apres)`, `etat(sel, libelle,
genre)` (une pastille), `compter(sel, de, a)`, `anneau(sel, d)` (désigne sans
cliquer), `pause(d)`, `defiler(sel, y)`, `cocher(sel)`, `animer(sel, de, a)`.
Options : `avec=True` (en même temps que le geste précédent), `decale=0.3`.

`tutoriel.py` : `zoom(sel, s=1.6, fx=0.5, fy=0.5)` (la caméra s'approche,
`sel` vient au point fx, fy de la fenêtre ; le cadrage reste dans l'écran),
`dezoom()`, `bulle(sel, texte ≤ 28, cote='droite' | 'gauche' | 'dessous',
fx=None, d=2.4)`. Une bulle ne bloque pas les gestes suivants ; un zoom attend
qu'elle ait été lue. Toujours `dezoom()` avant de quitter une zone zoomée.
`texte('#pr-url', '…')` change l'adresse de la fenêtre.

## Les écrans

Composants de `ecrans.py` (lire le fichier) : `fenetre(app, menus, vues,
avatar, couleur, calques, ident)`, `vue(id, html, initiale)`,
`panneau_liste`, `panneau_fiche`, `panneau_lateral`, `liste`, `bande(boutons,
statusbar, id, apres)` (la bande qui change après un geste : groupes
`<id>-a`, `<id>-b`…), `statusbar`, `feuille`, `grille2`, `champ`, `v`,
`entree`, `bouton`, `bouton_stat`, `onglets`, `table`, `chatter`, `message`,
`activite`, `assistant` (une boîte de dialogue : ids `<id>`, `<id>-voile`),
`bandeau`, `puce`, `case`, `interrupteur`, `portail`, `tuile`, `barres`.
L'application est écrite à **1100 × 700 px** ; avec MuK, la barre
d'applications prend 104 px à gauche et le fil de discussion 236 px.

Une base Odoo 18 réelle (thème MuK, données générées) sert de **modèle
visuel**, jamais incrusté : `http://localhost:8069`, base `demo18`, comptes
`demo.agent1`, `demo.assist1`, `demo.manager1`, `demo.compta`, `demo.signer`,
`demo.archive`, `demo.audit`, `demo.admin`, mot de passe `demo`. Capture :
`LOGIN=demo.admin /home/user/odoo-env/venv/bin/python /home/user/odoo-env/outils/capture.py nom=/odoo/action-<module>.<xmlid_action>[/<id>]`
→ `/home/user/odoo-env/captures/nom.png`.

Ne pas modifier les fichiers communs (`ecrans.py`, `moteur.py`,
`tutoriel.py`, `presentation.py`, `shared/*`, `demo.py`, `__init__.py`,
`scenarios/presentation.py`) depuis un module de tutoriel : composer ce qui
manque dans le module (HTML avec les classes existantes, `css` du tutoriel).
