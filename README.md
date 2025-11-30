# HorizonBot - Système de Gestion de Cours en Ligne

Bot Discord du serveur Horizon Ef'Réussite.

## Installation

1. **Prérequis**

- Python 3.8+
- LaTeX (texlive sur Linux)

2. **Installation**

Installer les dépendances Python:

```bash
pip install -r requirements.txt
```

3. **Configuration**

- Copier `.env.example` vers `.env` et ajouter le token du bot:

```
DISCORD_BOT_TOKEN=votre_token_ici
```

- Copier `config.example.json` vers `config.json` et configurer les IDs des rôles et canaux selon votre serveur.

- Copier `data/class_modules.example.json` vers `data/class_modules.json` et configurer les matières, avec les salons de cours associés.

4. **Lancer le bot**

```bash
python main.py
```

## Fonctionnalités

- Démarrage automatique des cours
- Notifications 30 min avant le cours
- Statistiques étudiants-profs et serveur
- Rendu LaTeX

## Structure

```
HorizonBot/
├── main.py              # Point d'entrée
├── cogs/                # Modules de commandes
│   ├── eclass.py       # Gestion des cours
│   ├── latex.py        # Rendu LaTeX
│   ├── stats.py        # Statistiques globales
│   ├── teachers.py     # Statistiques étudiants-profs
│   ├── lxp.py          # Info LXP
│   └── config.py       # Configuration
├── utils/              # Utilitaires
│   ├── data_manager.py # Base de données
│   └── helpers.py      # Fonctions helper
└── data/               # Données
    ├── bot_data.db     # Base de données SQLite
    └── class_modules.json # Configuration des matières
```

## Licence

License GPLv3. Voir le fichier LICENSE pour plus de détails.
