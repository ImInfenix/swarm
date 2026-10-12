# Swarm

Swarm est un espace communautaire de suivi de problèmes. Les visiteurs lisent les projets et les tickets ; les membres créent des projets, signalent des problèmes et commentent ; le responsable d'un projet gère l'état et la priorité de ses tickets. Voir [Architecture.md](Architecture.md) pour les choix techniques et le périmètre.

## Développement local

Python 3.10 ou plus récent est nécessaire. Depuis la racine du dépôt :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG = '1'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Ouvrir <http://127.0.0.1:8000/>. Les comptes se créent depuis l'interface. Pour accéder à l'administration :

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Les tests s'exécutent avec `python manage.py test`. La base locale `db.sqlite3` reste hors de Git.

## API JSON

L'API est accessible sous `/api/v1/`. Un appel `GET /api/v1/` renvoie sa documentation JSON : routes, méthodes, champs, filtres, droits et authentification. Les listes publiques sont paginées et renvoient `count`, `next`, `previous` et `results`. Les paramètres `page` et `page_size` sont acceptés, avec 100 résultats maximum par page.

| Méthode | Route | Fonction | Accès |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/signup/` | Créer un compte et recevoir un jeton | Public |
| `POST` | `/api/v1/auth/token/` | Se connecter et recevoir un jeton | Public |
| `DELETE` | `/api/v1/auth/token/` | Révoquer le jeton courant | Jeton |
| `GET` | `/api/v1/auth/me/` | Lire son compte | Jeton |
| `GET`, `POST` | `/api/v1/projects/` | Lister ou créer des projets | Lecture publique, création avec jeton |
| `GET`, `PATCH` | `/api/v1/projects/<slug>/` | Lire ou modifier un projet | Modification par son responsable |
| `GET`, `POST` | `/api/v1/projects/<slug>/tickets/` | Lister ou créer ses tickets | Lecture publique, création avec jeton |
| `GET` | `/api/v1/tickets/` | Lister les tickets | Public |
| `GET`, `PATCH` | `/api/v1/tickets/<id>/` | Lire ou corriger un ticket | Modification par son auteur |
| `PATCH` | `/api/v1/tickets/<id>/triage/` | Changer état ou priorité | Responsable du projet |
| `GET`, `POST` | `/api/v1/tickets/<id>/comments/` | Lire ou ajouter des commentaires | Lecture publique, ajout avec jeton |

La création de compte attend `username`, `email`, `password1` et `password2`. La connexion attend `username` et `password`. Le jeton reçu s'envoie ensuite dans l'en-tête `Authorization: Bearer <token>`. Un nouveau jeton est créé à chaque connexion et expire après 30 jours. Le nom du projet suffit à sa création : son identifiant d'adresse est généré automatiquement. Les listes acceptent `q` pour la recherche ; les tickets acceptent aussi `status`, `priority` et `project` selon la route.

```sh
curl -X POST https://swarm.example.org/api/v1/auth/token/ -H 'Content-Type: application/json' -d '{"username":"member","password":"password"}'
curl -X POST https://swarm.example.org/api/v1/projects/ -H 'Content-Type: application/json' -H 'Authorization: Bearer YOUR_TOKEN' -d '{"name":"Example Project","description":"Example"}'
```

Les jetons et mots de passe doivent transiter par HTTPS. Le serveur local lancé en HTTP sert uniquement à la prévisualisation : y utiliser des identifiants de test. L'API ne permet pas les appels directs depuis une page hébergée sur un autre domaine tant que CORS n'est pas configuré.

## Auto-hébergement sur un serveur Linux

Installer Python 3.10 ou plus récent, puis depuis le dossier de l'application :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-production.txt
export DJANGO_SECRET_KEY='replace-with-a-long-random-secret'
export DJANGO_ALLOWED_HOSTS='swarm.example.org'
export DJANGO_CSRF_TRUSTED_ORIGINS='https://swarm.example.org'
export SWARM_DB_PATH='/var/lib/swarm/db.sqlite3'
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/gunicorn --bind 127.0.0.1:8000 config.wsgi:application
```

Créer le dossier de la base avant les migrations et donner l'accès en écriture à l'utilisateur qui exécute Swarm. Conserver `DJANGO_DEBUG` absent, ou différent de `1`, en production. Faire tourner Gunicorn comme un service et placer un serveur HTTPS devant lui. Ce serveur doit rediriger HTTP vers HTTPS, transmettre les requêtes à `127.0.0.1:8000` et servir `/static/` depuis `collected_static/`. Remplacer le domaine d'exemple dans `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS`.

Exécuter `migrate` et `collectstatic` après chaque mise à jour. Sauvegarder régulièrement le fichier SQLite par l'API de sauvegarde SQLite ou avec un outil qui garantit une copie cohérente pendant l'utilisation. Tester la restauration. Ne pas placer la base sur un partage réseau.

Les variables `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` et `SWARM_DB_PATH` sont lues au démarrage.
