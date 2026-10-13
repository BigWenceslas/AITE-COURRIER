# Vidéos de présentation d'AITE Courrier et d'AITE ECM

Trois vidéos de présentation, tirées des dix-huit scénarios de la recette applicative
(`docs/recette/GUIDE_RECETTE.md`). L'interface y est **rejouée en HTML** avec
les couleurs et les libellés d'Odoo 18 et des modules AITE — jamais filmée,
jamais capturée — puis rendue en MP4 par
[HyperFrames](https://hyperframes.heygen.com), avec une voix off féminine
française :

| Vidéo (`--video`) | Scénario | Fichier livré |
|---|---|---|
| `courrier` (défaut) — AITE Courrier, dix chapitres | `scenarios/presentation.py` | `livrees/aite-courrier-presentation.mp4` |
| `ecm` — AITE ECM, six chapitres | `scenarios/ecm.py` | `livrees/aite-ecm-presentation.mp4` |
| `suite` — Courrier et ECM réunis, onze chapitres | `scenarios/suite.py` | `livrees/aite-suite-courrier-ecm.mp4` |

Méthode et moteur : skill `aite-motion-design-1` (moteur des guides vidéo
PGest), adapté ici à une longue vidéo à chapitres.

| Ce qui est versionné | Où |
|---|---|
| Moteur, écrans, scénario, feuille de style, polices, logos | `docs/videos/` |
| La vidéo compressée et sa vignette | `docs/videos/livrees/` |

Les projets HyperFrames, les rendus pleine qualité et les voix sont des
sorties régénérables, hors du dépôt (`../aite-videos` par défaut).

## Produire

```
python3 docs/videos/produire.py                # voix + projet + check
python3 docs/videos/produire.py --planche      # + planches contact à relire
python3 docs/videos/produire.py --rendu        # + rendu MP4 et compression
python3 docs/videos/produire.py --muet --planche   # sans voix, pour relire vite
python3 docs/videos/produire.py --video ecm --rendu     # la vidéo d'AITE ECM
python3 docs/videos/produire.py --video suite --rendu   # la vidéo combinée
```

Prérequis : Node.js (`npx`), `ffmpeg`, Python 3. Au premier lancement, le
script installe GSAP dans le dossier de travail et Kokoro (voix off locale,
gratuite, voix féminine `ff_siwis`) dans `<dossier>/.venv-tts`. HyperFrames est
figé à la version `0.8.139`.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `scenarios/presentation.py` | Le scénario : ouverture, parcours, rôles, dix chapitres et leurs étapes, recette, fin — avec les phrases de la voix off |
| `scenarios/chapitres_ecm.py` | « Travailler sur un document » (réserver, ouvrir dans Office, libérer, corbeille), propre aux vidéos ECM et suite |
| `scenarios/ecm.py`, `scenarios/suite.py` | Les vidéos ECM et combinée, qui reprennent les chapitres de `presentation.py` |
| `demo.py` | Les données de démonstration, toutes fictives |
| `ecrans.py` | Les écrans d'Odoo 18 rejoués : barre, listes, fiches, barre d'étapes, assistant, fil de discussion, portail, tableau de bord |
| `presentation.py` | Les scènes de la présentation et leur enchaînement |
| `moteur.py` | Les gestes (clic, saisie, changement de vue…) et les durées pilotées par la voix — repris du moteur PGest |
| `produire.py` | Voix off, projet, contrôles, planches, rendu, compression |
| `sons.py` | Le son d'ouverture et le clic, synthétisés par le code |
| `shared/aite.css` | Charte AITE (violet, Space Grotesk, IBM Plex Sans) et composants Odoo 18 (Roboto) |
| `shared/aite-motion.js` | Le plan → timeline GSAP |

## Les règles

- **Rien d'inventé.** Un libellé à l'écran existe dans le code des modules
  (`addons/aite_*/views`, données du circuit, portail) ou sur les captures de
  la recette ; une règle dite par la voix se retrouve dans le code ou dans le
  guide de recette.
- **Personnes fictives.** Les comptes et tiers du jeu de recette
  n'apparaissent pas : noms, organisations et références viennent de `demo.py`.
- **La voix pilote les durées** : chaque scène dure le temps de sa phrase.
  Prononciation : le lexique de `produire.py` écrit les sigles comme ils se
  disent (« Aïte », « E C M », « S L A »…).
- **Contrôles avant rendu** : `check` sans erreur, planches relues, aucune
  alerte « image sans voix ».
