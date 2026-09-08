# aite_ecm_demo — jeu de données de test

Génère, de façon **déterministe** (graine 2026), un jeu de données réaliste
exerçant tous les flux de la suite AITE Courrier / AITE ECM. Les
enregistrements sont créés **par les méthodes métier** (lancement de circuit,
transitions, versions, réservations, partages…) sous l'identité de 12
utilisateurs de démonstration, puis leurs dates sont réparties sur les six
derniers mois.

## Installation rapide, génération en arrière-plan

Le module s'installe **depuis l'interface ou en ligne de commande** : le hook
d'installation enregistre un plan de génération, exécute un **premier lot de
25 secondes** (paramètre `aite_ecm_demo.install_seconds`) — utilisateurs,
services, tiers, plan de classement et premiers courriers sont donc visibles
dès la fin de l'installation — puis arme une tâche planifiée. Celle-ci
poursuit par **lots de 40 secondes** (`aite_ecm_demo.batch_seconds`), reprend
là où elle s'est arrêtée à chaque passage, puis se désactive. Un profil léger
est complet en 5 à 10 minutes ; l'avancement s'affiche dans le journal serveur
(`Lot : … — phase « courriers » (45/150)`, puis `Génération terminée : …`).

## Tableau de bord (ECM › Configuration › Jeu de données de test)

Réservé aux managers, administrateurs AITE et administrateurs Odoo. Il affiche
le profil, la phase en cours (`courriers : 45 / 150`), les compteurs et la
dernière erreur rencontrée (avec sa trace), et propose :

* **Démarrer** — enregistre le plan avec le profil choisi et génère un premier
  lot de 30 s ;
* **Générer un lot (30 s)** — un lot par clic, sans dépendre de la tâche
  planifiée ;
* **Tout générer maintenant** — enchaîne les lots jusqu'à la fin dans la
  même requête (plusieurs minutes ; pour les instances sans proxy ni limite
  de temps, comme une configuration de base accédée directement) ;
* **Relancer la tâche planifiée** — poursuite en arrière-plan ;
* **Purger** — suppression complète du jeu de données.

## Diagnostic

* **État d'avancement** : paramètre système `aite_ecm_demo.state` (phase,
  index, compteurs `stats`, dernière unité en échec `last_error`).
* **Journal serveur** : lignes préfixées `[aite_ecm_demo]` ; la première
  erreur de chaque type est accompagnée de sa trace complète.
* **Relancer à la main** : Paramètres › Technique › Actions planifiées ›
  « AITE ECM : génération du jeu de données de test » › activer si besoin ›
  *Exécuter manuellement* (un lot par clic), ou lancer `scripts/seed_demo.py`
  qui reprend la génération en cours jusqu'au bout.
* Après une **mise à jour du module** (`-u`), le hook ne se rejoue pas : la
  génération en cours reprend via la tâche planifiée ou le script `shell`.

## Profils de volume

Choisissez le profil **avant** l'installation via le paramètre système
`aite_ecm_demo.profile` (Paramètres › Technique › Paramètres système), ou en
argument du script `shell`. Défaut : `leger`.

| Flux | leger | standard | complet |
|---|---|---|---|
| Utilisateurs de démonstration (`demo.*`) / services | 12 / 8 | 12 / 8 | 12 / 8 |
| Tiers (entreprises, administrations, particuliers) | 60 | 100 | 130 |
| Courriers (par type × 5 types : Entrant, Facture, Sortant, Devis, Interne) | 30 × 5 = **150** | 60 × 5 = 300 | 100 × 5 = 500 |
| Réponses liées à un courrier d'origine | 15 | 30 | 60 |
| Documents ECM autonomes (6 types, métadonnées, versions, 8 paires de doublons) | 60 | 120 | 200 |
| Dossiers métier (agréments fournisseur avec circuit + dossiers du personnel) | 20 + 20 | 50 + 50 | 100 + 100 |
| Relations entre documents | 40 | 80 | 120 |
| Partages externes (dont expirés, quotas, accès journalisés) | 30 | 60 | 100 |
| Réservations (dont ≈ 25 % expirées) / corbeille (dont 6 purgeables) | 12 / 8 | 25 / 12 | 40 / 20 |

Dans tous les profils : ≈ 12 % de courriers en brouillon, ≈ 40 % en cours
(retours commentés, ≈ 30 % en retard SLA), ≈ 8 % rejetés, ≈ 37 % archivés ;
1 à 2 pièces PDF par courrier ; pièces de dossiers rattachées et validées à
50 % ; 12 sous-dossiers de classement (dont « Contentieux » et
« Recrutements » réservés aux managers) ; 15 étiquettes. Tous les PDF
contiennent du texte (indexation plein texte, empreintes, filigrane).

## Commandes

```bash
# Installation (interface : Apps › AITE ECM - Jeu de données de test › Installer)
./odoo-bin -c odoo.conf -d <base> -i aite_ecm_demo --stop-after-init
# → les données sont générées par la tâche planifiée une fois le serveur démarré

# Génération synchrone (base où la suite est installée, ou profil plus gros) :
#   modifiez PROFILE dans le script puis
./odoo-bin -c odoo.conf -d <base> shell < addons/aite_ecm_demo/scripts/seed_demo.py

# Suppression du jeu de données (ou : désinstaller le module)
./odoo-bin -c odoo.conf -d <base> shell < addons/aite_ecm_demo/scripts/purge_demo.py
```

Si une tentative d'installation précédente a échoué, désinstallez le module
(ou lancez la purge) avant de réinstaller. Les erreurs métier rencontrées
pendant la génération sont isolées, comptées (« ignorés (…) ») et
journalisées avec leur trace ; elles n'interrompent pas la génération.

## Vérifications suggérées

1. Courrier › filtre « En retard (SLA) », puis lancer le cron de relance.
2. ECM › Documents : facettes, bouton « Doublons » (16 documents), corbeille
   et cron de purge (6 documents éliminés).
3. ECM › Dossiers métier : complétude, circuit, filtre « En retard (SLA) ».
4. Partages externes : liens expirés → page « lien indisponible ».
5. Connexion avec `demo.agent1` (mot de passe à définir par l'administrateur) :
   absence des documents « Contentieux » / « Recrutements » et des documents
   Confidentiel d'autres propriétaires.
