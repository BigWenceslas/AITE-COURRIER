# aite_ecm_office — Édition Office et Google Docs

Quatre voies pour modifier un document ECM dans une suite bureautique, toutes
compatibles Odoo Community. Dans tous les cas, **enregistrer crée une
version**, la **réservation** (check-out) protège l'édition, et le journal
d'audit trace l'ouverture.

| Voie | Mise en place | Comment ça marche |
|---|---|---|
| **Word / Excel / PowerPoint de bureau** | rien à installer côté serveur ; l'application Office est sur le poste | bouton *Ouvrir dans Word* → protocole `ms-word:ofe\|u\|<URL WebDAV>` ; Office demande une fois les identifiants Odoo, ouvre le fichier, pose un verrou (= réservation), *Enregistrer* → nouvelle version |
| **LibreOffice de bureau** | LibreOffice ≥ 7 sur le poste | protocole `vnd.libreoffice.command:ofe\|u\|` sur la même adresse WebDAV |
| **Lecteur réseau** | connecter `https://<odoo>/webdav/aite_ecm/` comme lecteur (Windows : « Connecter un lecteur réseau ») | plan de classement = dossiers, documents = fichiers `REF - Titre.ext`, dépôt d'un nouveau fichier = nouveau document, dossier « Sans classement » |
| **Navigateur (Collabora Online / OnlyOffice)** | serveur WOPI auto-hébergé (voir ci-dessous) ; URL dans ECM › Configuration › Paramètres › *Édition Office* | bouton *Modifier en ligne* → page hôte Odoo avec jeton temporaire → éditeur en iframe ; verrou WOPI = réservation ; sauvegarde = version ; *Voir en ligne* pour les documents verrouillés |
| **Google Docs / Sheets / Slides** | client OAuth Google (ID + secret) dans les paramètres ; chaque utilisateur autorise une fois son compte | bouton *Ouvrir dans Google* → copie déposée dans le Drive de l'utilisateur (dossier « AITE ECM »), édition dans Google ; *Récupérer* ou tâche planifiée (10 min) → version ; *Terminer* → dernière version, suppression de la copie, libération |

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
