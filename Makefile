SHELL := /bin/bash

export PATH := ./venv/bin:$(PATH)

SHA  := $(shell git rev-parse --short HEAD )
REPO := quay.io/quay/quay
TAG  := $(REPO):$(SHA)

MODIFIED_FILES_COUNT = $(shell git diff --name-only origin/master | grep -E .+\.py$ | wc -l)
GIT_MERGE_BASED = $(shell git merge-base origin/master HEAD)
MODIFIED_FILES = $(shell git diff --name-only $(GIT_MERGE_BASED) | grep -E .+\.py$ | paste -sd ' ')

show-modified:
	echo $(MODIFIED_FILES)

.PHONY: all unit-test registry-test registry-test-old buildman-test test build run clean

all: clean test build

unit-test:
	TEST=true PYTHONPATH="." py.test \
	--cov="." --cov-report=html --cov-report=term-missing \
	--timeout=3600 --verbose -x \
	./

registry-test:
	TEST=true PYTHONPATH="." py.test  \
	--cov="." --cov-report=html --cov-report=term-missing \
	--timeout=3600 --verbose --show-count -x \
	test/registry/registry_tests.py


buildman-test:
	TEST=true PYTHONPATH="." py.test \
	--cov="." --cov-report=html --cov-report=term-missing \
	--timeout=3600 --verbose --show-count -x \
	./buildman/

certs-test:
	./test/test_certs_install.sh

full-db-test: ensure-test-db
	TEST=true PYTHONPATH=. QUAY_OVERRIDE_CONFIG='{"DATABASE_SECRET_KEY": "anothercrazykey!"}' \
	alembic upgrade head
	TEST=true PYTHONPATH=. \
	SKIP_DB_SCHEMA=true py.test --timeout=7200 \
	--verbose --show-count -x --ignore=endpoints/appr/test/ \
	./

clients-test:
	cd test/clients; python clients_test.py

types-test:
	mypy .

test: unit-test registry-test registry-test-old certs-test

ensure-test-db:
	@if [ -z $(TEST_DATABASE_URI) ]; then \
	  echo "TEST_DATABASE_URI is undefined"; \
	  exit 1; \
	fi

PG_PASSWORD := quay
PG_USER := quay
PG_PORT := 5433
PG_VERSION := 12.1
PG_HOST := postgresql://$(PG_USER):$(PG_PASSWORD)@localhost:$(PG_PORT)/quay

test_postgres : TEST_ENV := SKIP_DB_SCHEMA=true TEST=true \
	TEST_DATABASE_URI=$(PG_HOST) PYTHONPATH=.

test_postgres:
	docker rm -f postgres-testrunner-postgres || true
	docker run --name postgres-testrunner-postgres \
		-e POSTGRES_PASSWORD=$(PG_PASSWORD) -e POSTGRES_USER=${PG_USER} \
		-p ${PG_PORT}:5432 -d postgres:${PG_VERSION}
	docker exec -it postgres-testrunner-postgres bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	docker exec -it postgres-testrunner-postgres bash -c "psql -U ${PG_USER} -d $(PG_PASSWORD) -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'"
	$(TEST_ENV) alembic upgrade head
	@echo '------------------------------------------------------------------------------------------------------------------------'
	@echo "postgres is ready to accept connections!"
	@echo "now run pytest with the necessary env vars, i.e:"
	@echo "'$(TEST_ENV) pytest <your-test-file.py>'"
	@echo "attaching to postgres container, use Ctrl+C detach and stop the container"
	@echo '------------------------------------------------------------------------------------------------------------------------'
	docker attach postgres-testrunner-postgres

docker-build:
	docker build -t $(TAG) .
	@echo $(TAG)

app-sre-docker-build:
	$(BUILD_CMD) -t ${IMG} -f Dockerfile .

clean:
	find . -name "*.pyc" -exec rm -rf {} \;
	rm -rf node_modules 2> /dev/null
	rm -rf grunt/node_modules 2> /dev/null
	rm -rf dest 2> /dev/null
	rm -rf dist 2> /dev/null
	rm -rf .cache 2> /dev/null
	rm -rf static/js/build
	rm -rf static/build
	rm -rf static/dist
	rm -rf build
	rm -rf conf/stack
	rm -rf screenshots

generate-proto-py:
	python -m grpc_tools.protoc -Ibuildman/buildman_pb --python_out=buildman/buildman_pb --grpc_python_out=buildman/buildman_pb buildman.proto


black:
	black --line-length=100 --target-version=py38 --exclude "/(\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.venv|_build|buck-out|build|dist)/" .

#################################
# Local Development Environment #
#################################

.PHONY: local-dev-clean
local-dev-clean:
	./local-dev/scripts/clean.sh

.PHONY: local-dev-build-frontend
local-dev-build-frontend:
	make local-dev-clean
	npm install --quiet --no-progress --ignore-engines --no-save
	npm run --quiet build

.PHONY: local-dev-build
local-dev-build:
	make local-dev-clean
	make local-dev-build-frontend
	docker-compose build

.PHONY: local-dev-up
local-dev-up:
	make local-dev-clean
	make local-dev-build-frontend
	docker-compose up -d redis
	docker-compose up -d quay-db
	docker exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	docker-compose up -d quay

local-docker-rebuild:
	docker-compose up -d redis --build
	docker-compose up -d quay-db --build
	docker exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	docker-compose up -d quay --build
	docker-compose restart quay

ifeq ($(CLAIR),true)
	docker-compose up -d clair-db --build
	docker exec -it clair-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	docker-compose up -d clair --build
	docker-compose restart clair
else
	@echo "Skipping Clair"
endif


.PHONY: local-dev-up-with-clair
local-dev-up-with-clair:
	make local-dev-clean
	make local-dev-build-frontend
	docker-compose up -d redis
	docker-compose up -d quay-db
	docker exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	docker-compose up -d quay
	docker-compose up -d clair-db
	docker exec -it clair-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	docker-compose up -d clair

.PHONY: local-dev-up
local-dev-down:
	docker-compose down
	make local-dev-clean
