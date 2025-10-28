# Watchdog Nepal — Running locally

This project is a Django application. The sections below provide detailed, copy-paste examples you can use after cloning the repo.

## Prerequisites

- Python 3.10+ (or a compatible 3.x supported by your environment)
- pip
- A virtual environment tool (venv) is recommended
- MySQL available if you want to run against the production-style database (the project uses PyMySQL)

## Files added to help development

- `.env.example` — example environment variables you can copy to `.env` and edit.
- `scripts/dev.sh` — helper script that creates the venv (if needed), installs deps, loads `.env`, runs migrations and starts the dev server.
- `Makefile` — convenient targets: `make venv`, `make install`, `make migrate`, `make run`, `make dev`.
- `.gitignore` — ignores `.env`, `venv/`, `db.sqlite3`, and other common artifacts.

## Quick start (recommended for local testing)

1. Clone the repo and change into it:

	git clone <repo-url>
	cd watchdognepal.com

2. Create a local environment file from the example and edit it:

	cp .env.example .env
	# Edit .env and set SECRET_KEY and DB_ values (or choose SQLite below)

	Example `.env` (SQLite quick-run):

	SECRET_KEY=a-local-secret-key
	DEBUG=True
	DB_ENGINE=django.db.backends.sqlite3
	DB_NAME=db.sqlite3
	ALLOWED_HOSTS=localhost,127.0.0.1

	Example `.env` (MySQL):

	SECRET_KEY=a-production-secret
	DEBUG=False
	DB_ENGINE=django.db.backends.mysql
	DB_NAME=your_db_name
	DB_USER=your_db_user
	DB_PASSWORD=your_db_password
	DB_HOST=localhost
	DB_PORT=3306
	ALLOWED_HOSTS=watchdognepal.com,www.watchdognepal.com

	Important: do NOT commit your `.env` to version control. The repo includes `.gitignore` with `.env` excluded.

3. (Optional) Create and activate a virtual environment manually, or use the Makefile/script below.

	Manual:

	python3 -m venv venv
	source venv/bin/activate
	pip install --upgrade pip
	pip install -r requirements.txt

4. Using the Makefile (recommended):

	# create venv and install deps
	make install

	# apply migrations
	make migrate

	# run dev server
	make run

	Or run the combined dev target:

	make dev

5. Using the helper script `scripts/dev.sh` (alternative to Makefile)

	The script will create a venv (if missing), install requirements, load `.env` (if present), run migrations, and start the server.

	If the script is not executable yet, make it executable and run it:

	chmod +x scripts/dev.sh
	./scripts/dev.sh

	Or run it with bash without changing permissions:

	bash scripts/dev.sh

6. If you prefer to export environment variables manually (example):

	# SQLite quick-run
	export SECRET_KEY='a-local-secret-key'
	export DB_ENGINE=django.db.backends.sqlite3
	export DB_NAME=db.sqlite3
	export DEBUG=True

	# Then run migrations and server
	python manage.py migrate
	python manage.py runserver

7. Create an admin user (interactive):

	python manage.py createsuperuser

8. Collect static files for a production-like setup:

	python manage.py collectstatic --noinput

## Notes and tips

- `watchdog/settings.py` reads DB and SECRET_KEY values from environment variables. The `.env` file is a convenient way to store them locally; the `scripts/dev.sh` loader exports those variables during the script run.
- The repo uses PyMySQL in production settings; by default `DATABASES` uses environment variables and `DB_ENGINE` defaults to MySQL. Use SQLite for quick tests by setting `DB_ENGINE=django.db.backends.sqlite3`.
- If you use the Makefile, the commands source the venv for each target so you don't need to activate it manually in your shell.
- To avoid accidentally committing secrets, the repository already contains a `.gitignore` entry for `.env`.

## Troubleshooting

- Database connection errors: confirm `DB_*` environment variables and that the DB server is reachable. For MySQL, ensure the database exists and the user has permissions.
- Static files: run `make collectstatic` and configure your webserver to serve the `staticfiles/` folder in production.
- If you see a templating or import error, ensure you installed the versions in `requirements.txt` and are running the correct Python interpreter from the `venv`.

If you'd like, I can:

- Make `scripts/dev.sh` executable in the repository (set executable bit). Note: changing the executable bit requires a git index change — I can prepare a patch but your environment may need to run `git add` to pick it up.
- Add a `README` section with commands for deploying with Passenger or Gunicorn.
- Add a `docker-compose.yml` for a reproducible local stack with MySQL.

Tell me which of the above you'd like next and I'll implement it.
