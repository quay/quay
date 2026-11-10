set -e

PARSED_DOCKER_HOST=`echo $DOCKER_HOST | sed 's/tcp:\/\///' | sed 's/:.*//'`
DOCKER_IP="${PARSED_DOCKER_HOST:-127.0.0.1}"
# The data-backfill migrations encrypt values and need a database secret key (fixture value only).
SECRET_KEY_OVERRIDE="\"DATABASE_SECRET_KEY\":\"QUAY_FIXTURE_ONLY-anothercrazykey!\""
MYSQL_CONFIG_OVERRIDE="{\"DB_URI\":\"mysql+pymysql://root:password@$DOCKER_IP:3307/genschema\",$SECRET_KEY_OVERRIDE}"
PERCONA_CONFIG_OVERRIDE="{\"DB_URI\":\"mysql+pymysql://root:password@$DOCKER_IP:3307/genschema\",$SECRET_KEY_OVERRIDE}"
PGSQL_CONFIG_OVERRIDE="{\"DB_URI\":\"postgresql://postgres:password@$DOCKER_IP:5433/genschema\",$SECRET_KEY_OVERRIDE}"

# Quay's schema needs latin1: e.g. image.ancestors is VARCHAR(60535), which only fits MySQL's
# 65535-byte row limit at one byte per character. MySQL 8+/MariaDB/Percona default to utf8mb4.
MYSQL_CHARSET_ARGS="--character-set-server=latin1 --collation-server=latin1_swedish_ci"

# Wait until a container answers a readiness command (instead of a fixed sleep). Probes use TCP
# (-h 127.0.0.1): the official images start a temporary init server that only listens on a
# socket, so a TCP success means the real server is up.
wait_for() {
  name=$1; shift
  for _ in $(seq 1 60); do
    if docker exec "$name" "$@" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  echo "Timed out waiting for $name" >&2
  return 1
}

up_mysql() {
  # Run a SQL database on port 3307 inside of Docker.
  docker run --name mysql -p 3307:3306 \
    -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=genschema -d mysql:8.0 $MYSQL_CHARSET_ARGS
  wait_for mysql mysqladmin ping -h 127.0.0.1 -uroot -ppassword
}

down_mysql() {
  docker kill mysql || true
  docker rm -v mysql || true
}

up_mariadb() {
  # Run a SQL database on port 3307 inside of Docker.
  docker run --name mariadb -p 3307:3306 \
    -e MARIADB_ROOT_PASSWORD=password -e MARIADB_DATABASE=genschema -d mariadb:11.4-ubi $MYSQL_CHARSET_ARGS
  wait_for mariadb mariadb-admin ping -h 127.0.0.1 -uroot -ppassword
}

down_mariadb() {
  docker kill mariadb || true
  docker rm -v mariadb || true
}

up_percona() {
  # Run a SQL database on port 3307 inside of Docker.
  docker run --name percona -p 3307:3306 \
    -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=genschema -d percona:8.0 $MYSQL_CHARSET_ARGS
  wait_for percona mysqladmin ping -h 127.0.0.1 -uroot -ppassword
}

down_percona() {
  docker kill percona || true
  docker rm -v percona || true
}

up_postgres() {
  # Run a SQL database on port 5433 inside of Docker.
  docker run --name postgres -p 5433:5432 \
    -e POSTGRES_PASSWORD=password -e POSTGRES_DB=genschema -d postgres:18
  wait_for postgres pg_isready -h 127.0.0.1 -U postgres -d genschema
  docker exec postgres psql -U postgres -d genschema -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
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
  TEST_MIGRATE=true QUAY_OVERRIDE_CONFIG=$1 PYTHONPATH=. alembic upgrade head || return 1

  # Downgrade to verify it works in both directions.
  echo '> Running downgrade'
  TEST_MIGRATE=true QUAY_OVERRIDE_CONFIG=$1 PYTHONPATH=. alembic downgrade base || return 1
}

# Run one database's test without aborting the remaining ones, but remember any failure.
FAILED=0
run_test() {
  set +e
  test_migrate "$1"
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    echo "> FAILED: $2" >&2
    FAILED=1
  fi
}

# Always remove the containers on exit, including when set -e aborts the script (for example when
# a database never becomes ready). Set KEEP_CONTAINERS=1 to keep them for inspection.
cleanup() {
  if [ "${KEEP_CONTAINERS:-}" != "1" ]; then
    down_mysql
    down_postgres
    down_mariadb
    down_percona
  fi
}
trap cleanup EXIT

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
run_test "$MYSQL_CONFIG_OVERRIDE" mysql
down_mysql

# Test via Postgres.
echo '> Starting Postgres'
up_postgres

echo '> Testing Migration (postgres)'
run_test "$PGSQL_CONFIG_OVERRIDE" postgres
down_postgres

# Test via MariaDB.
echo '> Starting MariaDB'
up_mariadb

echo '> Testing Migration (mariadb)'
run_test "$MYSQL_CONFIG_OVERRIDE" mariadb
down_mariadb

# Test via Percona.
echo '> Starting Percona'
up_percona

echo '> Testing Migration (percona)'
run_test "$PERCONA_CONFIG_OVERRIDE" percona
down_percona

exit $FAILED
