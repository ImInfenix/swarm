# Self-hosted deployment

Swarm can run on a Linux server with Python 3.10 or newer. The example below uses Gunicorn behind an HTTPS reverse proxy and stores the SQLite database in a persistent directory.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-production.txt
export DJANGO_DEBUG='0'
export DJANGO_SECRET_KEY='replace-with-a-long-random-secret'
export DJANGO_ALLOWED_HOSTS='swarm.example.org'
export DJANGO_CSRF_TRUSTED_ORIGINS='https://swarm.example.org'
export SWARM_TRUSTED_PROXY_IPS='127.0.0.1'
export SWARM_DB_PATH='/var/lib/swarm/db.sqlite3'
export SWARM_MEDIA_ROOT='/var/lib/swarm/media'
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
.venv/bin/gunicorn --bind 127.0.0.1:8000 config.wsgi:application
```

Create the database and media directories before running migrations and give the Swarm process write access to them. In production, leave `DJANGO_DEBUG` unset or set it to a value other than `1`. Never expose `runserver` to the Internet. Run Gunicorn as a service bound to `127.0.0.1`, with an HTTPS reverse proxy in front of it. The proxy must redirect HTTP to HTTPS, forward requests to `127.0.0.1:8000`, serve `/static/` from `collected_static/`, and send an HSTS header once HTTPS has been verified. Address the HTTPS warnings from `check --deploy` through the reverse proxy or appropriate Django settings. Verify the HTTP redirect, HSTS header, and absence of debug pages before public access. Replace the example domain in `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Optional parallel demonstration instance

Run a second service from the same checkout and virtual environment. Give it its own hostname, port, secret, and SQLite file. In the demo service environment:

```sh
export DJANGO_DEBUG='0'
export DJANGO_SECRET_KEY='use-a-different-random-secret'
export DJANGO_ALLOWED_HOSTS='demo.example.org'
export DJANGO_CSRF_TRUSTED_ORIGINS='https://demo.example.org'
export SWARM_TRUSTED_PROXY_IPS='127.0.0.1'
export SWARM_DB_PATH='/var/lib/swarm-demo/db.sqlite3'
export SWARM_MEDIA_ROOT='/var/lib/swarm-demo/media'
mkdir -p /var/lib/swarm-demo/media
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/gunicorn --bind 127.0.0.1:8001 config.wsgi:application
```

Give the demo process write access to its database and media directories. Configure the HTTPS proxy to forward the demo hostname to port `8001`. Clear the demo database with `.venv/bin/python manage.py reset_demo`; this removes its accounts, content, and stored attachments after confirmation.

Limit login attempts and abusive requests at the reverse proxy. Swarm also limits registrations and logins by IP address, and contributions by account. The proxy must forward the real client address in `X-Forwarded-For` and be the only service able to reach Gunicorn. Set `SWARM_TRUSTED_PROXY_IPS` only to trusted proxy addresses; leave it unset if direct connections are possible. The local cache used for these limits is suitable for a single process. Multiple processes or servers require a shared cache or limits enforced by the reverse proxy.

Run `migrate` and `collectstatic` after each update. Back up the SQLite file regularly using the SQLite backup API or another tool that guarantees a consistent copy while the application is running. Back up `SWARM_MEDIA_ROOT` as well; it contains bug screenshots. Keep that directory private because downloads are served through Django after checking ticket visibility. Test restoration. Do not put the database on a network share.

API tokens and passwords must travel over HTTPS. The local HTTP server is only for previews with test credentials. Direct API calls from a page hosted on another domain require additional CORS configuration.
