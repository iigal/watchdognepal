.PHONY: venv install migrate run collectstatic createsuperuser dev css

# Create virtualenv
venv:
	python3 -m venv venv

# Install requirements into the venv
install: venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run migrations
migrate: install
	. venv/bin/activate && python manage.py migrate

# Run Django development server (after migrations)
run: migrate
	. venv/bin/activate && python manage.py runserver 0.0.0.0:8000

# Collect static files into staticfiles/
collectstatic:
	. venv/bin/activate && python manage.py collectstatic --noinput

# Create admin user
createsuperuser:
	. venv/bin/activate && python manage.py createsuperuser

# Build production Tailwind CSS (run locally before deploying)
css:
	npx -y tailwindcss@3 -i static/css/tailwind.input.css -o static/css/tailwind.output.css --minify

# Shortcut for development (same as `make run`)
dev: run
