---
document_type: architecture
service: all
failure_type: observability
---
# Runtime evidence contract

Each request log carries `service`, `request_id`, `event`, `duration_ms`, `status_code`,
`error_type`, and `deployment_version`. The same request ID is used on checkout and payment.
Deployment records describe version, time, commit, and change summary but never contain an
incident's ground truth.

Health is point-in-time evidence. A healthy endpoint does not disprove a latency incident:
health checks deliberately avoid exercising the provider charge path. Prefer correlated request
logs for path-specific conclusions and cite deployment evidence only when timing and symptoms
support a change-related hypothesis.

