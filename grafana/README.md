# Quay Grafana Dashboards

The following dashboards are given:
- Quay API
- Quay AWS Resources
- Quay Garbage Collection
- Quay Resources

## Required Recording Rules

Due to the high cardinality of reported metrics, the following [Prometheus recording rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/) are expected. Before modifying/creating any metrics read the [Quay documenation on Prometheus.](/docs/prometheus.md)

```yaml
rules:
  - record: aggregation:quay_request_duration_seconds_bucket:rate5m:sum
    expr: sum(rate(quay_request_duration_seconds_bucket[5m])) by (le, route, method, status)
  - record: aggregation:quay_request_duration_seconds_count:rate1m:sum
    expr: sum(rate(quay_request_duration_seconds_count[1m])) by (route, status, method)
```
