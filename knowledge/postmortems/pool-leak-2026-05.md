---
document_type: postmortem
service: payment-service
failure_type: connection_exhaustion
---
# Provider pool exhaustion, May 2026

A connection release regression reduced the available payment provider pool to zero. Payment
returned 503 with `ConnectionPoolExhausted`, its health response reported no available connections,
and checkout propagated upstream errors. Restarting restored capacity temporarily but did not fix
the release defect.

Evidence from both runtime logs and health was required to distinguish pool exhaustion from a
provider network outage. The permanent change fixed connection release and added pool saturation
monitoring.

