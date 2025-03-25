SHELL := /bin/bash
DOCKER ?= docker
DOCKER_COMPOSE ?= $(DOCKER) compose

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
	-m 'not e2e' --timeout=3600 --verbose -x --ignore=buildman/ \
	./

e2e-test:
	TEST=true PYTHONPATH="." py.test \
	--cov="." --cov-report=html --cov-report=term-missing \
	-m 'e2e' --timeout=3600 --verbose -x --ignore=buildman/ \
	./

integration-test:
	TEST=true PYTHONPATH="." py.test \
	--verbose --ignore=buildman/ \
	test/integration/*

registry-test:
	TEST=true PYTHONPATH="." py.test  \
	--cov="." --cov-report=html --cov-report=term-missing \
	-m 'not e2e' --timeout=3600 --verbose -x \
	test/registry/registry_tests.py

buildman-test:
	TEST=true PYTHONPATH="." py.test \
	--cov="." --cov-report=html --cov-report=term-missing \
	-m 'not e2e' --timeout=3600 --verbose -x \
	./buildman/

certs-test:
	./test/test_certs_install.sh

full-db-test: ensure-test-db
	TEST=true PYTHONPATH=. QUAY_OVERRIDE_CONFIG='{"DATABASE_SECRET_KEY": "anothercrazykey!"}' \
	alembic upgrade head
	TEST=true PYTHONPATH=. \
	SKIP_DB_SCHEMA=true py.test -m 'not e2e' --timeout=7200 \
	--verbose -x --ignore=endpoints/appr/test/ \
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

install-pre-commit-hook:
	pip install pre-commit==2.20.0
	pre-commit install

PG_PASSWORD := quay
PG_USER := quay
PG_PORT := 5433
PG_HOST := postgresql://$(PG_USER):$(PG_PASSWORD)@localhost:$(PG_PORT)/quay
CONTAINER := postgres-testrunner
TESTS ?= ./

test_postgres : TEST_ENV := SKIP_DB_SCHEMA=true TEST=true \
	TEST_DATABASE_URI=$(PG_HOST) PYTHONPATH=.

test_postgres:
	$(DOCKER) rm -f $(CONTAINER) || true
	$(DOCKER) run --name $(CONTAINER) \
		-e POSTGRES_PASSWORD=$(PG_PASSWORD) -e POSTGRES_USER=$(PG_USER) \
		-p $(PG_PORT):5432 -d postgres:12.1
	$(DOCKER) exec -it $(CONTAINER) bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	$(DOCKER) exec -it $(CONTAINER) bash -c "psql -U $(PG_USER) -d quay -c 'CREATE EXTENSION pg_trgm;'"
	$(TEST_ENV) alembic upgrade head
	$(TEST_ENV) py.test --timeout=7200 --verbose --ignore=endpoints/appr/test/ -x $(TESTS)
	$(DOCKER) rm -f $(CONTAINER) || true

WEBPACK := node_modules/.bin/webpack
$(WEBPACK): package.json
	npm install webpack
	npm install

BUNDLE := static/js/build/bundle.js
$(BUNDLE): $(WEBPACK) tsconfig.json webpack.config.js typings.json
	$(WEBPACK)

GRUNT := grunt/node_modules/.bin/grunt
$(GRUNT): grunt/package.json
	cd grunt && npm install

JS  := quay-frontend.js quay-frontend.min.js template-cache.js
CSS := quay-frontend.css
DIST := $(addprefix static/dist/, $(JS) $(CSS) cachebusters.json)
$(DIST): $(GRUNT)
	cd grunt && ../$(GRUNT)

build: $(WEBPACK) $(GRUNT)

docker-build: build
	ifneq (0,$(shell git status --porcelain | awk 'BEGIN {print $N}'))
	echo 'dirty build not supported - run `FORCE=true make clean` to remove'
	exit 1
	endif
	# get named head (ex: branch, tag, etc..)
	NAME = $(shell git rev-parse --abbrev-ref HEAD)
	# checkout commit so .git/HEAD points to full sha (used in Dockerfile)
	git checkout $(SHA)
	$(DOCKER) build -t $(TAG) .
	git checkout $(NAME)
	echo $(TAG)

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
	black --line-length=100 --target-version=py39 --exclude "/(\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.venv|_build|buck-out|build|dist)/" .

#################################
# Local Development Environment #
#################################

.PHONY: build-image-local-dev-frontend
build-images:: build-image-local-dev-frontend
build-image-local-dev-frontend:
# $(DOCKER)-compose run does not build images, so we need to build them if needed
	test -n "$$($(DOCKER) images localhost/quay-build:latest -q)" || $(DOCKER_COMPOSE) build local-dev-frontend

.PHONY: build-image-quay
build-images:: build-image-quay
build-image-quay: .build-image-quay-stamp
.build-image-quay-stamp: Dockerfile requirements.txt
	$(DOCKER_COMPOSE) build quay
	touch $@

node_modules: node_modules/.npm-install-stamp

node_modules/.npm-install-stamp: package.json package-lock.json | build-image-local-dev-frontend
	DOCKER_USER="$$(id -u):$$(id -g)" $(DOCKER_COMPOSE) run --rm --name quay-local-dev-frontend-install --entrypoint="" local-dev-frontend npm install --ignore-engines
# if npm install fails for some reason, it may have already created
# node_modules, so we cannot rely on the directory timestamps and should mark
# successfull runs of npm install with a stamp file.
	touch $@

.PHONY: local-dev-clean
local-dev-clean:
	rm -f ./conf/jwtproxy_conf.yaml ./conf/mitm.cert ./conf/mitm.key ./conf/quay.kid ./conf/quay.pem ./conf/supervisord.conf
	rm -rf ./conf/__pycache__ ./static/build

.PHONY: local-dev-build-frontend
local-dev-build:: local-dev-build-frontend
local-dev-build-frontend: node_modules
	DOCKER_USER="$$(id -u):$$(id -g)" $(DOCKER_COMPOSE) run --rm --name quay-local-dev-frontend-build --entrypoint="" local-dev-frontend npm run build

.PHONY: local-dev-build-images
local-dev-build:: local-dev-build-images
local-dev-build-images:
	$(DOCKER_COMPOSE) build

.PHONY: local-dev-up
local-dev-up: local-dev-clean node_modules | build-image-quay
	DOCKER_USER="$$(id -u):$$(id -g)" $(DOCKER_COMPOSE) up -d --force-recreate local-dev-frontend
	$(DOCKER_COMPOSE) up -d redis quay-db
	$(DOCKER) exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	DOCKER_USER="$$(id -u):0" $(DOCKER_COMPOSE) stop quay  # we need to restart quay after local-dev-clean
	DOCKER_USER="$$(id -u):0" $(DOCKER_COMPOSE) up -d quay
	# Waiting until the frontend is built...
	# Use '$(DOCKER_COMPOSE) logs -f local-dev-frontend' to see the progress
	while ! test -e ./static/build/main-quay-frontend.bundle.js; do sleep 2; done
	@echo "You can now access the frontend at http://localhost:8080"

.PHONY: update-testdata
update-testdata: local-dev-clean node_modules | build-image-quay
	$(DOCKER_COMPOSE) rm -fsv quay-db quay
	$(DOCKER) volume rm -f quay_quay-db-data
	$(DOCKER_COMPOSE) up -d redis quay-db
	$(DOCKER) exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	cd ./web/ && npm run quay:seed-db
	DOCKER_USER="$$(id -u):0" $(DOCKER_COMPOSE) up -d quay
	cd ./web/ && npm run quay:seed-storage
	while ! curl -fso /dev/null http://localhost:8080; do echo "waiting for quay"; sleep 2; done
	$(DOCKER) exec -it quay-db psql quay -U quay -c " \
		DELETE FROM servicekey; \
		DELETE FROM servicekeyapproval; \
		SELECT pg_catalog.setval('public.notification_id_seq', 1, false); \
		SELECT pg_catalog.setval('public.servicekey_id_seq', 1, false); \
		SELECT pg_catalog.setval('public.servicekeyapproval_id_seq', 1, false); \
	"
	cd ./web/ && npm run quay:dump
	$(DOCKER_COMPOSE) down

local-docker-rebuild:
	$(DOCKER_COMPOSE) up -d --build redis
	$(DOCKER_COMPOSE) up -d --build quay-db
	$(DOCKER) exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	DOCKER_USER="$$(id -u):0" $(DOCKER_COMPOSE) up -d --build quay
	$(DOCKER_COMPOSE) restart quay

ifeq ($(CLAIR),true)
	$(DOCKER_COMPOSE) up -d --build clair-db
	$(DOCKER) exec -it clair-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	$(DOCKER_COMPOSE) up -d --build clair
	$(DOCKER_COMPOSE) restart clair
else
	@echo "Skipping Clair"
endif

.PHONY: local-dev-up-with-clair
local-dev-up-with-clair: local-dev-up
	$(DOCKER_COMPOSE) up -d clair-db
	$(DOCKER) exec -it clair-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	DOCKER_USER="$$(id -u):0" $(DOCKER_COMPOSE) up -d clair

.PHONY: local-dev-up-static
local-dev-up-static: local-dev-clean
	$(DOCKER_COMPOSE) -f docker-compose.static up -d redis quay-db
	$(DOCKER) exec -it quay-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	DOCKER_USER="$$(id -u):0" $(DOCKER_COMPOSE) -f docker-compose.static up -d --build quay
	@echo "You can now access the frontend at http://localhost:8080"
	$(DOCKER_COMPOSE) -f docker-compose.static up -d clair-db
	$(DOCKER) exec -it clair-db bash -c 'while ! pg_isready; do echo "waiting for postgres"; sleep 2; done'
	$(DOCKER_COMPOSE) -f docker-compose.static up -d clair

.PHONY: local-dev-down
local-dev-down:
	$(DOCKER_COMPOSE) down
	$(MAKE) local-dev-clean
