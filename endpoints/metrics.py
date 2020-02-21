from prometheus_client import Counter

image_pulls = Counter(
    "quay_registry_image_pulls_total",
    "number of images that have been downloaded via the registry",
    labelnames=["protocol", "ref", "status"],
)

image_pushes = Counter(
    "quay_registry_image_pushes_total",
    "number of images that have been uploaded via the registry",
    labelnames=["protocol", "status", "media_type"],
)

image_pulled_bytes = Counter(
    "quay_registry_image_pulled_estimated_bytes_total",
    "number of bytes that have been downloaded via the registry",
    labelnames=["protocol"],
)
