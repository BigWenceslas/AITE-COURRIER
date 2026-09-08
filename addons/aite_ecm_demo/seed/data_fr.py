# -*- coding: utf-8 -*-
"""Référentiels de génération (contexte camerounais francophone)."""

FIRST_NAMES_M = [
    "Achille", "Alain", "Armand", "Bertrand", "Boris", "Charles", "Cyrille",
    "Didier", "Emmanuel", "Éric", "Franck", "Gaston", "Hervé", "Jean-Paul",
    "Joseph", "Landry", "Martial", "Olivier", "Patrick", "Paul", "Rodrigue",
    "Serge", "Thierry", "Valentin", "Yannick",
]
FIRST_NAMES_F = [
    "Adèle", "Agnès", "Alice", "Berthe", "Carine", "Chantal", "Christelle",
    "Clarisse", "Diane", "Édith", "Estelle", "Florence", "Gisèle", "Hortense",
    "Irène", "Josiane", "Laure", "Madeleine", "Mireille", "Nadège", "Pauline",
    "Rosine", "Solange", "Sylvie", "Viviane",
]
LAST_NAMES = [
    "Mbarga", "Fotso", "Essomba", "Ngo Bassong", "Kamdem", "Tchoumi", "Nkolo",
    "Abena", "Onana", "Tchamba", "Manga", "Njoya", "Atangana", "Bilong",
    "Djomo", "Ekani", "Etoundi", "Fouda", "Kenfack", "Mballa", "Mvondo",
    "Ndongo", "Ngassa", "Nguimfack", "Nyobe", "Ondoa", "Ouandji", "Sadjo",
    "Tamba", "Tchinda", "Wandji", "Zambo", "Ayissi", "Bekolo", "Dikongue",
    "Eyenga", "Kouam", "Mefire", "Ngono", "Tabi",
]
COMPANIES = [
    ("ETS KAMDEM & FILS", "fournisseur"), ("SOCAMEX SA", "fournisseur"),
    ("CAMTECH SOLUTIONS SARL", "fournisseur"), ("Imprimerie du Wouri", "fournisseur"),
    ("Groupe MODAF Logistique", "fournisseur"), ("Bureautique Plus SARL", "fournisseur"),
    ("Sécuritas Cameroun", "fournisseur"), ("Pharmacie de la Liberté", "fournisseur"),
    ("Garage Auto-Service Bonabéri", "fournisseur"), ("Elite Nettoyage SARL", "fournisseur"),
    ("Mobilier Design Afrique", "fournisseur"), ("TransCam Express", "fournisseur"),
    ("Quincaillerie Centrale Akwa", "fournisseur"), ("NetLink Télécoms", "fournisseur"),
    ("Cabinet Ngo Bassong Avocats", "partenaire"), ("Cabinet ACG Expertise Comptable", "partenaire"),
    ("Assurances Sécurité Vie", "partenaire"), ("Banque Régionale de l'Atlantique", "partenaire"),
    ("Crédit Communautaire du Littoral", "partenaire"), ("Fondation Santé pour Tous", "partenaire"),
    ("Université Privée du Golfe", "partenaire"), ("Radio Nostalgie Douala", "partenaire"),
    ("Hôtel Résidence Palmiers", "client"), ("Clinique La Providence", "client"),
    ("Coopérative Agricole du Moungo", "client"), ("Société Immobilière Bonanjo", "client"),
    ("Brasserie du Littoral", "client"), ("Scierie des Hauts Plateaux", "client"),
    ("École Internationale Les Cèdres", "client"), ("Minoterie du Sud", "client"),
    ("Groupe JMB Distribution", "client"), ("SOPECAM Négoce", "client"),
    ("Régie des Transports Urbains", "client"), ("Complexe Sportif de Bépanda", "client"),
    ("Mairie de Douala 5e", "administration"), ("Préfecture du Wouri", "administration"),
    ("Direction Générale des Impôts — Centre de Douala", "administration"),
    ("Caisse Nationale de Prévoyance Sociale — Agence Akwa", "administration"),
    ("Ministère du Commerce — Délégation régionale", "administration"),
    ("Chambre de Commerce et d'Industrie", "administration"),
    ("Agence de Régulation des Marchés Publics", "administration"),
    ("Délégation régionale du Travail", "administration"),
    ("Tribunal de Première Instance de Bonanjo", "administration"),
    ("Port Autonome — Direction des concessions", "administration"),
    ("Communauté Urbaine — Service urbanisme", "administration"),
    ("Inspection du Travail du Littoral", "administration"),
    ("Association des Commerçants d'Akwa", "partenaire"),
    ("ONG Espoir et Développement", "partenaire"),
    ("Syndicat des Transporteurs Routiers", "partenaire"),
    ("Cabinet d'Architecture Lumière", "fournisseur"),
    ("Studio Graphique Kwaba", "fournisseur"), ("Imprimerie Nationale — Annexe", "administration"),
    ("Compagnie d'Électricité — Agence Bonabéri", "fournisseur"),
    ("Société des Eaux — Agence Akwa", "fournisseur"), ("CamPost — Agence centrale", "administration"),
    ("Lycée Bilingue de Deïdo", "administration"), ("Centre Médical Saint-Luc", "client"),
    ("Agro-Industries du Nkam", "client"), ("Bois et Dérivés du Sud", "client"),
    ("Ferronnerie Moderne", "fournisseur"), ("Pressing Royal", "fournisseur"),
    ("Traiteur Les Délices", "fournisseur"), ("Sono Événements Pro", "fournisseur"),
    ("Papeterie du Centre", "fournisseur"), ("Climatisation Fraîcheur", "fournisseur"),
    ("Assainissement Propre Cité", "fournisseur"), ("Formation Excellence RH", "partenaire"),
    ("Institut de Langues Panafricain", "partenaire"), ("Cabinet Vétérinaire du Nord", "client"),
    ("Pêcheries du Golfe", "client"),
]
CITIES = [
    ("Douala", ["Akwa", "Bonanjo", "Bonapriso", "Bonabéri", "Makepe", "Deïdo",
                "Logpom", "Bépanda", "Ndokoti", "Kotto"]),
    ("Yaoundé", ["Bastos", "Nlongkak", "Mvog-Ada", "Essos", "Biyem-Assi",
                 "Omnisports", "Ekounou"]),
    ("Bafoussam", ["Tamdja", "Djeleng", "Banengo"]),
    ("Garoua", ["Roumdé Adjia", "Lopéré"]),
    ("Bamenda", ["Up Station", "Nkwen"]),
    ("Kribi", ["Mpangou", "Centre"]),
    ("Limbé", ["Down Beach", "Mile 4"]),
]
STREETS = ["Rue", "Avenue", "Boulevard", "Carrefour", "Rond-point"]
STREET_NAMES = ["de la Liberté", "de l'Indépendance", "des Cocotiers", "du Marché",
                "de la Poste", "Joss", "de la Gare", "des Palmiers", "de Nachtigal",
                "du 20 Mai", "Charles de Gaulle", "de Bonanjo"]

DEPARTMENTS = [
    "Direction générale", "Achats et logistique", "Ressources humaines",
    "Finance et comptabilité", "Juridique", "Systèmes d'information",
    "Commercial", "Communication",
]

# Objets de courrier par type (code) ; {p} = tiers, {ref} = référence externe
SUBJECTS = {
    'ENTR': [
        "Demande d'agrément fournisseur — {p}", "Réclamation sur livraison n° {ref}",
        "Demande de partenariat — {p}", "Notification de contrôle fiscal",
        "Convocation à l'assemblée générale — {p}", "Demande d'attestation de travail",
        "Mise en demeure — facture {ref}", "Candidature spontanée — poste de comptable",
        "Demande de rendez-vous avec la Direction", "Invitation au forum des entreprises",
        "Rappel de cotisations sociales — période {ref}", "Demande de devis pour travaux",
        "Accusé de réception de votre courrier {ref}", "Demande d'autorisation d'accès au site",
        "Résiliation de contrat de prestation", "Plainte pour nuisance sonore",
        "Demande de stage académique", "Notification de changement de RIB",
        "Proposition commerciale — {p}", "Demande de copie de contrat {ref}",
    ],
    'FACT': [
        "Facture {ref} — fournitures de bureau", "Facture {ref} — maintenance climatisation",
        "Facture {ref} — abonnement Internet", "Facture {ref} — prestation de gardiennage",
        "Facture {ref} — carburant flotte", "Facture {ref} — impression plaquettes",
        "Facture {ref} — nettoyage des locaux", "Facture {ref} — honoraires juridiques",
        "Facture {ref} — location de véhicules", "Facture {ref} — consommables informatiques",
        "Facture {ref} — électricité", "Facture {ref} — eau", "Facture {ref} — formation RH",
        "Facture {ref} — mobilier de bureau", "Facture {ref} — travaux de peinture",
    ],
    'SORT': [
        "Réponse à votre demande d'agrément", "Notification d'attribution de marché",
        "Lettre de relance — facture impayée {ref}", "Attestation de bonne exécution",
        "Convocation à l'entretien de recrutement", "Réponse à votre réclamation {ref}",
        "Transmission de pièces contractuelles", "Demande de renseignements — {p}",
        "Résiliation de contrat de prestation", "Lettre de félicitations",
        "Notification de fin de période d'essai", "Invitation à la cérémonie de signature",
        "Demande de report d'échéance", "Courrier de mise en garde", "Réponse à l'appel d'offres {ref}",
    ],
    'DEVIS': [
        "Devis {ref} — mise en place d'un ERP Odoo", "Devis {ref} — audit de sécurité SI",
        "Devis {ref} — câblage réseau du siège", "Devis {ref} — déploiement Microsoft 365",
        "Devis {ref} — solution de gestion documentaire", "Devis {ref} — vidéosurveillance IP",
        "Devis {ref} — connectivité satellitaire", "Devis {ref} — site web institutionnel",
        "Devis {ref} — maintenance annuelle", "Devis {ref} — formation des utilisateurs",
        "Devis {ref} — application mobile terrain", "Devis {ref} — contrôle d'accès biométrique",
    ],
    'INT': [
        "Note de service — horaires de la période des fêtes", "Demande de congé annuel",
        "Rapport de mission — {p}", "Demande d'achat — {ref}", "Compte rendu de réunion de direction",
        "Note d'information — nouvelle procédure d'achat", "Demande de remboursement de frais",
        "Rapport d'incident informatique", "Demande de formation", "Proposition d'amélioration qualité",
        "Demande de véhicule de service", "Planning des astreintes", "Note de frais — déplacement Yaoundé",
        "Demande d'attestation de salaire", "Circulaire — sécurité des locaux",
    ],
}
REPLY_SUBJECTS = [
    "Réponse à votre courrier {ref}", "Suite à votre demande {ref}",
    "Accusé de réception et réponse — {ref}", "Réponse — {subject}",
]
COMMENTS_FORWARD = [
    "Pièces vérifiées, RAS.", "Transmis pour suite à donner.", "Validé.",
    "Conforme aux procédures.", "OK pour moi.", "À traiter en priorité.",
    "Dossier complet.", "Vu, transmis.", "",
]
COMMENTS_BACKWARD = [
    "Pièce jointe illisible, merci de renumériser.", "Service destinataire erroné.",
    "Montant incohérent avec le bon de commande.", "Signature manquante sur l'original.",
    "Merci de compléter la référence du contrat.", "Priorité à revoir.",
]
COMMENTS_REJECT = [
    "Demande hors périmètre.", "Doublon d'un courrier déjà traité.",
    "Tiers non référencé, courrier retourné.", "Facture non conforme, rejetée.",
]

# ECM
CONTRACT_OBJECTS = [
    "Maintenance préventive et curative des groupes électrogènes",
    "Prestations de gardiennage du siège", "Nettoyage des locaux",
    "Fourniture de consommables informatiques", "Bail commercial — agence",
    "Location longue durée de véhicules", "Abonnement Internet fibre",
    "Assistance juridique", "Hébergement et infogérance", "Impression et reprographie",
    "Assurance flotte automobile", "Formation continue du personnel",
]
PROCEDURES = [
    "Procédure d'achat et de sélection des fournisseurs", "Procédure de gestion des congés",
    "Instruction de sauvegarde des données", "Procédure d'accueil des visiteurs",
    "Procédure de traitement des réclamations", "Procédure de notes de frais",
    "Instruction de classement et d'archivage", "Procédure d'onboarding",
    "Plan de continuité d'activité", "Procédure de gestion des incidents SI",
]
PV_INSTANCES = ["Conseil d'administration", "Comité de direction", "Comité d'hygiène et sécurité",
                "Assemblée générale", "Comité achats", "Revue de direction qualité",
                "Comité de pilotage ERP"]
RH_NATURES = ["cni", "diplome", "contrat", "medical", "autre"]
TAGS = ["Urgent", "2025", "2026", "À renouveler", "Confidentiel RH", "Appel d'offres",
        "Contentieux", "Original papier", "Signé", "En attente", "Archivage 10 ans",
        "Fiscal", "Assurance", "Immobilier", "Qualité"]
SUBFOLDERS = [
    ("folder_juridique", "Contrats fournisseurs", None),
    ("folder_juridique", "Baux et immobilier", None),
    ("folder_juridique", "Contentieux", "manager"),
    ("folder_finance", "Factures fournisseurs 2025", None),
    ("folder_finance", "Factures fournisseurs 2026", None),
    ("folder_finance", "Banques et assurances", "compta"),
    ("folder_rh", "Notes de service RH", None),
    ("folder_rh", "Recrutements", "manager"),
    ("folder_achats", "Agréments fournisseurs", None),
    ("folder_achats", "Appels d'offres", None),
    ("folder_qualite", "Procédures en vigueur", None),
    ("folder_direction", "Procès-verbaux", None),
]
SHARE_TEXTS = ["Diffusion contrôlée — AITE ECM", "Confidentiel — ne pas diffuser",
               "Copie de travail", "Document transmis à titre d'information"]
LOREM = (
    "Le présent document est produit à des fins de test et de démonstration de la "
    "plateforme AITE ECM. Il ne comporte aucune information réelle. Son contenu "
    "est indexé en texte intégral afin d'illustrer la recherche sur le contenu "
    "des pièces, la détection de doublons par empreinte et le filigrane des "
    "partages externes."
)
