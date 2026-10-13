# Swarm

Swarm is a community feedback platform for game developers and other projects. Members report bugs, request features, support ideas with votes, and discuss solutions. Project owners organize this feedback and track the versions affected or targeted.

The application provides a web interface and a JSON API. It is built with Django and uses SQLite. The technology choices and feature scope are described in [Architecture.md](Architecture.md).

## Local setup

Python 3.10 or newer is required. On Windows, run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG = '1'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The site is then available at <http://127.0.0.1:8000/>. Run the tests with `.\.venv\Scripts\python.exe manage.py test`.

## Demonstration data

Fill the selected database with example accounts, projects, versions, tickets, votes, and comments:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo
```

The demonstration accounts cannot sign in. Clear the selected database, including all accounts and content, with:

```powershell
.\.venv\Scripts\python.exe manage.py reset_demo
```

The reset command asks for confirmation. Add `--yes` to skip the prompt. Set `SWARM_DB_PATH` before either command to select a separate database.

## API and deployment

The API supports viewing and managing accounts, projects, tickets, and comments. `GET /api/v1/` returns JSON documentation covering its routes, fields, and access rules.

For server installation, see [DEPLOYMENT.md](DEPLOYMENT.md).
