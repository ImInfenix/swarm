# Déploiement auto-hébergé

Swarm peut fonctionner sur un serveur Linux avec Python 3.10 ou plus récent. L'exemple ci-dessous utilise Gunicorn derrière un serveur HTTPS et place la base SQLite dans un dossier persistant.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-production.txt
export DJANGO_DEBUG='0'
export DJANGO_SECRET_KEY='replace-with-a-long-random-secret'
export DJANGO_ALLOWED_HOSTS='swarm.example.org'
export DJANGO_CSRF_TRUSTED_ORIGINS='https://swarm.example.org'
export SWARM_DB_PATH='/var/lib/swarm/db.sqlite3'
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
.venv/bin/gunicorn --bind 127.0.0.1:8000 config.wsgi:application
```

Créer le dossier de la base avant les migrations et donner l'accès en écriture à l'utilisateur qui exécute Swarm. Conserver `DJANGO_DEBUG` absent, ou différent de `1`, en production. Ne jamais exposer `runserver` sur Internet. Faire tourner Gunicorn comme un service, lié à `127.0.0.1`, et placer un serveur HTTPS devant lui. Ce serveur doit rediriger HTTP vers HTTPS, transmettre les requêtes à `127.0.0.1:8000`, servir `/static/` depuis `collected_static/` et envoyer un en-tête HSTS après validation du fonctionnement HTTPS. Les avertissements HTTPS de `check --deploy` doivent être couverts par ce serveur frontal ou par des réglages Django adaptés. Vérifier la redirection HTTP, l'en-tête HSTS et l'absence de pages de débogage avant l'ouverture publique. Remplacer le domaine d'exemple dans `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS`.

Limiter les tentatives de connexion et les requêtes abusives sur le serveur frontal. Une protection supplémentaire par compte est nécessaire si des attaques réparties sur plusieurs adresses doivent être prises en charge ; le simple filtrage par adresse IP ne suffit pas dans ce cas.

Exécuter `migrate` et `collectstatic` après chaque mise à jour. Sauvegarder régulièrement le fichier SQLite par l'API de sauvegarde SQLite ou avec un outil qui garantit une copie cohérente pendant l'utilisation. Tester la restauration. Ne pas placer la base sur un partage réseau.

Les jetons d'API et les mots de passe doivent transiter par HTTPS. Le serveur local lancé en HTTP sert uniquement à la prévisualisation avec des identifiants de test. Les appels directs à l'API depuis une page hébergée sur un autre domaine nécessitent une configuration CORS supplémentaire.
