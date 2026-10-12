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
