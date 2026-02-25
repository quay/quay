# Pyroscope profiling

Optional CPU profiling via [Grafana Pyroscope](https://grafana.com/docs/pyroscope/latest/). Off by default (no overhead). Set in config.yaml.

## Enable

1. Start Pyroscope (e.g. `docker compose up -d pyroscope` or `docker run -d -p 4040:4040 grafana/pyroscope:latest`).
2. In config.yaml add:
   ```yaml
   PROFILING_TYPE: Pyroscope
   PYROSCOPE_SERVER_ADDRESS: http://pyroscope:4040
   ```
   Use `http://localhost:4040` if Pyroscope runs on the same host.
3. Restart Quay.

UI: http://localhost:4040 — pick app `quay` to view flame graphs.

## Disable

Remove or comment out `PROFILING_TYPE` and `PYROSCOPE_SERVER_ADDRESS` in config.yaml, then restart Quay.
