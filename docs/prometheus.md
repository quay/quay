# Prometheus

[Prometheus] is a time series database used for the short-term storage of metrics.
Quay exposes numerous metrics that can be used to ensure the performance and reliability while the application is running.

Because Quay is actually a collection of processes inside the container, [PushGateway] is used to consolidate, but not aggregate, all of the metrics into one endpoint.
A grouping key of `(pid, host, process_name)` is added to every metric in ordered to keep every metric unique per process.
This grouping key does cause high cardinality for sufficiently large deployments and aggregation using a federated deployment of Prometheus is then recommended.
The metrics endpoint can be found on the [PushGateway port]: `9091`.

[Prometheus]: https://prometheus.io
[PushGateway]: https://github.com/prometheus/pushgateway
[PushGateway port]: https://github.com/prometheus/prometheus/wiki/Default-port-allocations#core-components-starting-at-9090


## Adding a metric

### Caveats - Please read and understand

[Brian's post] on cardinality is required reading before defining your first metric.
The cardinality of the set of labels on a metric can destroy querying performance to the degree where the metric is unusable.
In newer versions of Prometheus, expensive queries will timeout, but in older versions it can make the whole Prometheus process hang.

[Brian's post]: https://www.robustperception.io/cardinality-is-key

### Code Details

Abstractions useful for instrumenting new code with metrics can be found in [`/util/metrics`].
This module also contains a [flask extension] that pushes metrics on a regular interval from the default [registry] in the Prometheus client library to the PushGateway.
Adding a new metric should roughly follow the process described by the Prometheus [client library README]: define a new metric in the module being instrumented, and call the respective functions to record the metric.

[`/util/metrics`]: https://github.com/quay/quay/tree/master/util/metrics
[flask extension]: https://flask.palletsprojects.com/en/1.1.x/extensions/
[registry]: https://github.com/prometheus/client_python/blob/master/prometheus_client/registry.py
[client library]: https://github.com/prometheus/client_python
[client library README]: https://github.com/prometheus/client_python/blob/master/README.md
