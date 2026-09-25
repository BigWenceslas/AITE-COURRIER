# AITE Courrier — Signature électronique sur Odoo Community

> **AITE Consulting · Module `aite_courrier_sign_oca` 18.0.1.0.0**
> Odoo 18 **Community** (fonctionne aussi sur Enterprise). S'appuie sur le
> module communautaire OCA [`sign_oca`](https://github.com/OCA/sign/tree/18.0/sign_oca),
> livré dans le paquet de la suite (dossier `oca\`).
> Septembre 2026.

Parcours complet, paramétrage et recette : `docs/TUTORIEL_SIGNATURE_COMMUNITY.md`.

---

## 1. Ce que fait le module

| Apport | Où |
| --- | --- |
| Case **Signature requise** sur une étape de circuit | Courrier › Configuration › Circuits de traitement |
| Bouton **Demander la signature** | en-tête du courrier, sur une étape cochée, pour qui peut agir sur l'étape |
| E-mail au signataire avec un lien : il signe **sans compte Odoo** | navigateur du signataire |
| **PDF signé versé en GED** (`<pièce>_signe.pdf`, nouvelle version ; l'original reste) | onglet Documents du courrier |
| **Garde serveur** : pas de transition en avant sans la signature du passage en cours | moteur de validation |
| Bouton **Signatures**, résumé des signataires sur la demande | fiche courrier, fiche de la demande |
| Journal d'audit : *Demande de signature*, *Action bloquée*, *Signature complétée* | Courrier › Audit › Journal d'audit |

Le signataire est le **responsable du courrier** ; la pièce soumise est la
**dernière version PDF** du courrier ; la zone de signature est placée page 1,
en bas à droite.

La garde vaut **par passage sur l'étape** : un courrier renvoyé en arrière
puis revenu sur l'étape, ou une seconde étape « Signature requise » du même
circuit, exige une nouvelle signature. Redemander la signature annule et
remplace la demande en attente ; une demande en attente est annulée quand le
courrier quitte l'étape.

## 2. Installation

1. Copier le dossier `oca\sign_oca` du paquet à côté des modules `aite_*`
   (ou dans tout dossier déclaré dans `addons_path`).
2. Installer, service Odoo arrêté :

   ```powershell
   & "C:\Program Files\Odoo 18\python\python.exe" `
     "C:\Program Files\Odoo 18\server\odoo-bin" `
     -c "C:\Program Files\Odoo 18\server\odoo.conf" -d <votre_base> `
     -i aite_courrier_sign_oca --stop-after-init
   ```

   `sign_oca` s'installe avec, ainsi que `base_sparse_field` et
   `web_editor` (modules standard d'Odoo). Aucune bibliothèque Python à
   ajouter.
3. Vérifier le **serveur de messagerie sortant** et le paramètre système
   **`web.base.url`** : le lien de signature est construit dessus.

Ce module et `aite_courrier_sign` (variante Enterprise, Odoo Sign)
s'excluent. Si `aite_courrier_sign` est resté bloqué « à installer », Odoo
refuse l'installation : *Les modules … sont incompatibles*. Cliquer d'abord
**Annuler l'installation** sur `aite_courrier_sign` dans Applications.

## 3. Sécurité

- Un utilisateur interne ne lit que les demandes dont il est le demandeur, un
  abonné ou le signataire (la règle d'origine de `sign_oca` les ouvrait toutes,
  PDF compris).
- Les lignes signataires portent le jeton du lien de signature : elles ne
  sont lisibles que par le signataire lui-même. La règle d'origine les ouvrait
  aux collègues rattachés à une même société partenaire, qui pouvaient alors
  signer à leur place. Le demandeur voit le champ **Signataires** (nom, état),
  sans le jeton.
- `/my/sign/<id>/download` exige désormais un lien avec la demande (droit de
  lecture ou qualité de signataire) ; `sign_oca` y servait n'importe quelle
  demande à tout utilisateur connecté.
- Les droits **Signature** de `sign_oca` (*Utilisateur*, *Gestionnaire*)
  permettent de signer à la place d'autrui : les réserver aux administrateurs
  de la signature. Les agents du courrier n'en ont pas besoin.

## 4. Limites

- **Signature électronique simple** : image de la signature apposée dans le
  PDF, journal horodaté (IP, empreinte chaînée). Ni certificat qualifié, ni
  signature PDF (PAdES). Convient aux visas et validations internes, pas aux
  actes qui exigent une signature avancée ou qualifiée.
- Un seul signataire, le responsable du courrier ; documents PDF seulement ;
  zone de signature fixe.
- `sign_oca` est au statut *Beta* à l'OCA. Version livrée et testée : 18.0.1.4.3
  (commit `2489814`).
- Licence **AGPL-3** (celle de `sign_oca`, dont ce module hérite le code).
