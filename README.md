# Swarm

Swarm est un espace communautaire de suivi de problèmes organisé par projets. Les visiteurs consultent les signalements et leurs discussions. Les membres créent des projets, ouvrent des tickets et échangent sur leur résolution. Le responsable d'un projet peut modifier sa présentation et gérer l'état et la priorité de ses tickets.

L'application réunit une interface web et une API JSON. Elle est construite avec Django et utilise SQLite. Les choix techniques et le périmètre fonctionnel sont décrits dans [Architecture.md](Architecture.md).

## Démarrage local

Python 3.10 ou plus récent est nécessaire. Sous Windows, depuis la racine du dépôt :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG = '1'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Le site est alors accessible sur <http://127.0.0.1:8000/>. Les tests s'exécutent avec `.\.venv\Scripts\python.exe manage.py test`.

## API et déploiement

L'API permet de consulter et de gérer les comptes, projets, tickets et commentaires. `GET /api/v1/` renvoie sa documentation JSON, notamment les routes, les champs et les droits d'accès.

Pour installer Swarm sur un serveur, voir [DEPLOYMENT.md](DEPLOYMENT.md).
