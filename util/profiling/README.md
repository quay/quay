# Pyroscope profiling

Optional CPU profiling via [Grafana Pyroscope](https://grafana.com/docs/pyroscope/latest/). Off by default (no overhead). Set in config.yaml.

## Enable

1. Start Pyroscope:
   ```bash
   docker run -d --name pyroscope -p 4040:4040 grafana/pyroscope:latest
   ```
2. In config.yaml set `PROFILING_TYPE: Pyroscope` and `PYROSCOPE_SERVER_ADDRESS` **for your environment**:
   - **Quay on host** (e.g. `make run`, tests): `http://localhost:4040`
   - **Quay in Docker on Mac/Windows**: `http://host.docker.internal:4040` (container reaches Pyroscope on the host)
   - **Quay and Pyroscope on same Docker network**: `http://pyroscope:4040` — when both containers are attached to one custom network (e.g. same `docker compose` project or `docker network create` + `--network`), Docker’s DNS resolves the name `pyroscope` to that container. Not the case if you start each with plain `docker run` (they end up on the default bridge and cannot use container names).
3. Restart Quay.

UI: http://localhost:4040 — pick app `quay` to view flame graphs.

## Disable

Remove or comment out `PROFILING_TYPE` and `PYROSCOPE_SERVER_ADDRESS` in config.yaml, then restart Quay.
