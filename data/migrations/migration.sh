set -e

PARSED_DOCKER_HOST=`echo $DOCKER_HOST | sed 's/tcp:\/\///' | sed 's/:.*//'`
DOCKER_IP="${PARSED_DOCKER_HOST:-127.0.0.1}"
MYSQL_CONFIG_OVERRIDE="{\"DB_URI\":\"mysql+pymysql://root:password@$DOCKER_IP/genschema\"}"
PERCONA_CONFIG_OVERRIDE="{\"DB_URI\":\"mysql+pymysql://root:password@$DOCKER_IP/genschema\"}"
PGSQL_CONFIG_OVERRIDE="{\"DB_URI\":\"postgresql://postgres@$DOCKER_IP/genschema\"}"

up_mysql() {
  # Run a SQL database on port 3306 inside of Docker.
  docker run --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password -d mysql:5.7

  echo 'Sleeping for 25...'
  sleep 25

  # Add the database to mysql.
  docker run --rm --link mysql:mysql mysql:5.7 sh -c 'echo "create database genschema" | mysql -h"$MYSQL_PORT_3306_TCP_ADDR" -P"$MYSQL_PORT_3306_TCP_PORT" -uroot -ppassword'
}

down_mysql() {
  docker kill mysql || true
  docker rm -v mysql || true
}

up_mariadb() {
  # Run a SQL database on port 3306 inside of Docker.
  docker run --name mariadb -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password -d mariadb

  echo 'Sleeping for 25...'
  sleep 25

  # Add the database to mysql.
  docker run --rm --link mariadb:mariadb mariadb sh -c 'echo "create database genschema" | mysql -h"$MARIADB_PORT_3306_TCP_ADDR" -P"$MARIADB_PORT_3306_TCP_PORT" -uroot -ppassword'
}

down_mariadb() {
  docker kill mariadb || true
  docker rm -v mariadb || true
}

up_percona() {
  # Run a SQL database on port 3306 inside of Docker.
  docker run --name percona -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password -d percona

  echo 'Sleeping for 25...'
  sleep 25

  # Add the daabase to mysql.
  docker run --rm --link percona:percona percona sh -c 'echo "create database genschema" | mysql -h $PERCONA_PORT_3306_TCP_ADDR -uroot -ppassword'
}

down_percona() {
  docker kill percona || true
  docker rm -v percona || true
}

up_postgres() {
  # Run a SQL database on port 5432 inside of Docker.
  docker run --name postgres -p 5432:5432 -d postgres

  # Sleep for 5s to get SQL get started.
  echo 'Sleeping for 5...'
  sleep 5

  # Add the database to postgres.
  docker run --rm --link postgres:postgres postgres sh -c 'echo "create database genschema" | psql -h "$POSTGRES_PORT_5432_TCP_ADDR" -p "$POSTGRES_PORT_5432_TCP_PORT" -U postgres'
  docker run --rm --link postgres:postgres postgres sh -c 'echo "CREATE EXTENSION IF NOT EXISTS pg_trgm;" | psql -h "$POSTGRES_PORT_5432_TCP_ADDR" -p "$POSTGRES_PORT_5432_TCP_PORT" -U postgres -d genschema'

}

down_postgres() {
  docker kill postgres || true
  docker rm -v postgres || true
}

gen_migrate() {
  # Generate a database with the schema as defined by the existing alembic model.
  QUAY_OVERRIDE_CONFIG=$1 PYTHONPATH=. alembic -x generatedbaopmigrations=true upgrade head


  # Generate the migration to the current model.
  QUAY_OVERRIDE_CONFIG=$1 PYTHONPATH=. alembic revision --autogenerate -m "$2"
}

test_migrate() {
  # Generate a database with the schema as defined by the existing alembic model.
  echo '> Running upgrade'
  TEST_MIGRATE=true QUAY_OVERRIDE_CONFIG=$1 PYTHONPATH=. alembic upgrade head

  # Downgrade to verify it works in both directions.
  echo '> Running downgrade'
  COUNT=`ls data/migrations/versions/*.py | wc -l | tr -d ' '`
  TEST_MIGRATE=true QUAY_OVERRIDE_CONFIG=$1 PYTHONPATH=. alembic downgrade "-$COUNT"
}

down_mysql
down_postgres
down_mariadb
down_percona

# Test (and generate, if requested) via MySQL.
echo '> Starting MySQL'
up_mysql

if [ ! -z "$@" ]
  then
    set +e
    echo '> Generating Migration'
    gen_migrate $MYSQL_CONFIG_OVERRIDE "$@"
    set -e
  fi

echo '> Testing Migration (mysql)'
set +e
test_migrate $MYSQL_CONFIG_OVERRIDE
set -e
down_mysql

# Test via Postgres.
echo '> Starting Postgres'
up_postgres

echo '> Testing Migration (postgres)'
set +e
test_migrate $PGSQL_CONFIG_OVERRIDE
set -e
down_postgres

# Test via MariaDB.
echo '> Starting MariaDB'
up_mariadb

echo '> Testing Migration (mariadb)'
set +e
test_migrate $MYSQL_CONFIG_OVERRIDE
set -e
down_mariadb

# Test via Percona.
echo '> Starting Percona'
up_percona

echo '> Testing Migration (percona)'
set +e
test_migrate $PERCONA_CONFIG_OVERRIDE
set -e
down_percona
