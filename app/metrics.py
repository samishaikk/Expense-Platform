from prometheus_client import Counter, Histogram

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


def record_request(method: str, route: str, status_code: int, seconds: float) -> None:
    REQUESTS.labels(method=method, route=route, status=str(status_code)).inc()
    LATENCY.labels(method=method, route=route).observe(seconds)