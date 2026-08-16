---
document_type: runbook
service: payment-service
failure_type: payment_latency
---
# Payment latency runbook

Suspect payment-path latency when checkout emits `UpstreamPaymentTimeout` near its one-second
budget and matching payment request IDs show charge durations above 1,000 ms. Confirm the delay
is in payment rather than checkout by comparing correlated durations.

Immediate actions: inspect provider latency, preserve request samples, and avoid increasing the
checkout timeout before identifying the slow dependency. If authorization succeeds after the
caller timed out, assess duplicate-charge/idempotency risk. Restore the normal provider path or
temporarily shed checkout traffic before changing timeouts.

