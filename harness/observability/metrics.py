
from prometheus_client import Counter, Histogram, Gauge

tasks_total = Counter("harness_tasks_total", "Total tasks", ["status"])
task_latency = Histogram("harness_task_latency_seconds", "Task latency")
token_usage = Counter("harness_token_usage_total", "Total tokens used", ["agent"])
retries_total = Counter("harness_retries_total", "Total retries")
active_tasks = Gauge("harness_active_tasks", "Active tasks")
