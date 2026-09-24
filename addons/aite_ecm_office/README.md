# aite_ecm_office — Édition Office et Google Docs

Quatre voies pour modifier un document ECM dans une suite bureautique, toutes
compatibles Odoo Community. Dans tous les cas, **enregistrer crée une
version**, la **réservation** (check-out) protège l'édition, et le journal
d'audit trace l'ouverture.

| Voie | Mise en place | Comment ça marche |
|---|---|---|
| **Word / Excel / PowerPoint de bureau** | rien à installer côté serveur ; l'application Office est sur le poste, qui doit **autoriser le serveur** une fois (voir *Word, Excel, PowerPoint : autoriser le serveur sur le poste*) | bouton *Ouvrir dans Word* → protocole `ms-word:ofe\|u\|<URL WebDAV>` ; Office demande une fois les identifiants Odoo, ouvre le fichier, pose un verrou (= réservation), *Enregistrer* → nouvelle version |
| **LibreOffice de bureau** | LibreOffice ≥ 7 sur le poste | protocole `vnd.libreoffice.command:ofe\|u\|` sur la même adresse WebDAV |
| **Lecteur réseau** | connecter `https://<odoo>/webdav/aite_ecm/` comme lecteur (Windows : « Connecter un lecteur réseau ») ; ouvrir un fichier du lecteur dans Word, Excel ou PowerPoint suppose le même réglage de poste que le bouton | plan de classement = dossiers, documents = fichiers `REF - Titre.ext`, dépôt d'un nouveau fichier = nouveau document, dossier « Sans classement » |
| **Navigateur (Collabora Online / OnlyOffice)** | serveur WOPI auto-hébergé (voir ci-dessous) ; URL dans ECM › Configuration › Paramètres › *Édition Office* | bouton *Modifier en ligne* → page hôte Odoo avec jeton temporaire → éditeur en iframe ; verrou WOPI = réservation ; sauvegarde = version ; *Voir en ligne* pour les documents verrouillés |
| **Google Docs / Sheets / Slides** | client OAuth Google (ID + secret) dans les paramètres ; chaque utilisateur autorise une fois son compte | bouton *Ouvrir dans Google* → copie déposée dans le Drive de l'utilisateur (dossier « AITE ECM »), édition dans Google ; *Récupérer* ou tâche planifiée (10 min) → version ; *Terminer* → dernière version, suppression de la copie, libération |

## Word, Excel, PowerPoint : autoriser le serveur sur le poste

Depuis la version 2311 (Current Channel, décembre 2023 ; Monthly Enterprise
Channel, janvier 2024 ; Semi-Annual Enterprise Channel 2402, juillet 2024 ;
Office 2016, 2019 et 2021 vendus au détail, au rythme du Current Channel),
Word, Excel et PowerPoint sous Windows bloquent par défaut les demandes
d'identifiants en authentification **Basic**, la seule que propose le serveur
WebDAV d'Odoo : « Microsoft Office a bloqué l'accès aux … car la source
utilise une méthode de connexion qui peut être non sécurisée ». Le blocage
porte sur la méthode, pas sur le transport : il vaut en `https` comme en
`http`, pour le bouton comme pour un fichier ouvert depuis le lecteur réseau
(Word convertit le chemin du lecteur en adresse `http(s)` et télécharge
lui-même le fichier). Les versions en licence en volume (LTSC) ne sont pas
concernées.

Remède, une fois par poste : la stratégie *Allow specified hosts to show Basic
Authentication prompts to Office apps* (GPO : *User Configuration › Policies ›
Administrative Templates › Microsoft Office 2016 › Security Settings*, modèles
ADMX Office 5359.1000 ou plus récents ; ou Cloud Policy), ou son équivalent
registre. **Fermer toutes les applications Office**, puis, dans PowerShell
ouvert **dans la session du compte Windows qui utilise Word** (*en tant
qu'administrateur* si ce compte est administrateur du poste ; jamais avec un
autre compte : `HKCU` désignerait alors le profil de cet autre compte) :

```powershell
reg add "HKCU\Software\Policies\Microsoft\Office\16.0\Common\Identity" /v basichostallowlist /t REG_EXPAND_SZ /d "localhost;localhost:8069" /f
```

Rouvrir Word : il demande alors les identifiants (login Odoo et mot de passe,
ou clé d'API). `/d` liste des noms d'hôtes séparés par `;`, sans `https://` :
en production, le nom du serveur (par exemple `ecm.client.fr`) ; `hôte:port`
s'ajoute par prudence, faute de source sur la prise en compte du port. Les
guillemets sont obligatoires en PowerShell, où `;` sépare les instructions ;
`/f` remplace une valeur existante, dont il faut reprendre les hôtes. Selon
son libellé, la stratégie ne s'applique qu'aux versions sur abonnement ; une
Cloud Policy du tenant (`HKCU\Software\Policies\Microsoft\Cloud\Office\16.0`)
ou le Baseline Security Mode peuvent primer. HTTPS reste recommandé (il
protège le mot de passe) mais ne dispense pas de ce réglage. Microsoft ne
recommande cette autorisation qu'à titre transitoire. Détails et dépannage :
[`docs/WEBDAV.md`](docs/WEBDAV.md) §3.5.

## Serveur d'édition en ligne (WOPI)

```bash
# Collabora Online (CODE)
docker run -d -p 9980:9980 --name collabora --restart always \
  -e "aliasgroup1=https://ecm.exemple.cm:443" -e "username=admin" -e "password=secret" \
  collabora/code
# ou ONLYOFFICE Docs (activer WOPI : /etc/onlyoffice/documentserver/local.json → "wopi": {"enable": true})
docker run -d -p 8080:80 --name onlyoffice --restart always onlyoffice/documentserver
```

Exposez le serveur en HTTPS derrière un reverse proxy (`https://office.exemple.cm`)
et déclarez cette URL dans les paramètres ; **Tester le serveur** vérifie la
découverte (`/hosting/discovery`) et liste les formats. Odoo doit joindre le
serveur, et le serveur doit joindre l'URL publique d'Odoo (`web.base.url`).
Formats : Writer (docx, doc, odt, rtf, txt), Calc (xlsx, xls, ods, csv),
Impress (pptx, ppt, odp), PDF en lecture.

## Google

Dans Google Cloud Console : projet, API Drive activée, client OAuth « application
web », URI de redirection = valeur affichée dans les paramètres
(`<odoo>/ecm/google/callback`), écran de consentement avec le périmètre
`drive.file`. Les fichiers Office sont convertis au format Google à l'ouverture
et réexportés au format d'origine au rapatriement.

## Tests

`--test-tags /aite_ecm_office` : arborescence WebDAV, PUT, verrous ↔
réservations, MOVE, URI Office, aller-retour Google (simulé), WOPI (découverte
simulée, jetons, CheckFileInfo, verrous, sauvegarde).
