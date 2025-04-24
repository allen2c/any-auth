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
	codepress . \
		--output dist/codebase.txt \
		--ignore poetry.lock \
		--ignore requirements.txt \
		--ignore requirements-all.txt \
		--ignore tests \
		--inspect

# Services
svc-run:
	fastapi run any_auth/app.py --host 0.0.0.0 --port 8000

svc-dev:
	fastapi dev any_auth/app.py --host 0.0.0.0 --port 8000

# Docs
mkdocs:
	mkdocs serve

# Generate RSA keys
gen-rsa-keys:
	openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048
	openssl rsa -pubout -in private_key.pem -out public_key.pem

# Tests
pytest:
	python -m pytest
