# Testing quay

## Unit tests (run in CI automatically)

Basic unit tests for testing all the functionality of Quay:

```sh
make unit-test
```

## Registry tests (run in CI automatically)

Quay has two sets of registry tests (current and legacy), which simulate Docker clients by executing
REST operations against a spanwed Quay.

```sh
make registry-test
make registry-test-old
```

## Certs tests (run in CI automatically)

Ensures that custom TLS certificates are correctly loaded into the Quay container on startup.

```sh
make certs-test
```

## Full database tests (run in CI automatically)

The full database tests runs the entire suite of Quay unit tests against a real running database
instance.

NOTE: The database *must be running* on the local machine before this test can be run.

```sh
TEST_DATABASE_URI=database-connection-string make full-db-test
```

## Clients tests (must be manually run)

The clients test spawns CoreOS virtual machines via Vagrant and VirtualBox and runs real Docker/podman
commands against a *running Quay*.

NOTE: A Quay *must be running* on the local machine before this test can be run.

```sh
make clients-test 10.0.2.2:5000 # IP+Port of the Quay on the host machine.
```
