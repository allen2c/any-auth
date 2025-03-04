# Development
format-all:
	@isort . \
		--skip setup.py \
		--skip .venv \
		--skip build \
		--skip dist \
		--skip __pycache__ \
		--skip docs \
		--skip static \
		--skip .conda
	@black . \
		--exclude setup.py \
		--exclude .venv \
		--exclude build \
		--exclude dist \
		--exclude __pycache__ \
		--exclude docs \
		--exclude static \
		--exclude .conda

install-all:
	poetry install --all-extras --all-groups

update-all:
	poetry update
	poetry export --without-hashes -f requirements.txt --output requirements.txt
	poetry export --without-hashes -f requirements.txt --output requirements-all.txt --all-extras --all-groups

dump-codebase:
	mkdir -p dist
	codepress --output dist/codebase.txt --ignore poetry.lock

# Services
run-svc:
	fastapi run any_auth/app.py

run-svc-dev:
	fastapi dev any_auth/app.py

# Docs
mkdocs:
	mkdocs serve

# Tests
pytest:
	python -m pytest
