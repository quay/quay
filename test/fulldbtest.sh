set -e

up_mysql() {
  # Run a SQL database on port 3306 inside of Docker.
  docker run --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password -d mysql:5.7

  # Sleep for 10s to get MySQL get started.
  echo 'Sleeping for 10...'
  sleep 10

  # Add the database to mysql.
  docker run --rm --link mysql:mysql mysql:5.7 sh -c 'echo "create database genschema;" | mysql -h"$MYSQL_PORT_3306_TCP_ADDR" -P"$MYSQL_PORT_3306_TCP_PORT" -uroot -ppassword'
}

down_mysql() {
  docker kill mysql || true
  docker rm -v mysql || true
}

up_postgres() {
  # Run a SQL database on port 5432 inside of Docker.
  docker run --name postgres -p 5432:5432 -d postgres

  # Sleep for 10s to get SQL get started.
  echo 'Sleeping for 10...'
  sleep 10

  # Add the database to postgres.
  docker run --rm --link postgres:postgres postgres sh -c 'echo "create database genschema" | psql -h "$POSTGRES_PORT_5432_TCP_ADDR" -p "$POSTGRES_PORT_5432_TCP_PORT" -U postgres'
  docker run --rm --link postgres:postgres postgres sh -c 'echo "CREATE EXTENSION IF NOT EXISTS pg_trgm;" | psql -h "$POSTGRES_PORT_5432_TCP_ADDR" -p "$POSTGRES_PORT_5432_TCP_PORT" -U postgres -d genschema'
}

down_postgres() {
  docker kill postgres || true
  docker rm -v postgres || true
}

run_tests() {
  # Initialize the database with schema.
  PYTHONPATH=. TEST_DATABASE_URI=$1 TEST=true alembic upgrade head

  # Run the full test suite.
  PYTHONPATH=. SKIP_DB_SCHEMA=true TEST_DATABASE_URI=$1 TEST=true py.test ${2:-.} --ignore=endpoints/appr/test/
}

CIP=${CONTAINERIP-'127.0.0.1'}
echo "> Using container IP address $CIP"

# NOTE: MySQL is currently broken on setup.
# Test (and generate, if requested) via MySQL.
echo '> Starting MySQL'
down_mysql
up_mysql

echo '> Running Full Test Suite (mysql)'
set +e
run_tests "mysql+pymysql://root:password@$CIP/genschema" $1
set -e
down_mysql

# Test via Postgres.
echo '> Starting Postgres'
down_postgres
up_postgres

echo '> Running Full Test Suite (postgres)'
set +e
run_tests "postgresql://postgres@$CIP/genschema" $1
set -e
down_postgres
