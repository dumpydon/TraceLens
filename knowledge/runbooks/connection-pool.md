---
document_type: runbook
service: payment-service
failure_type: connection_exhaustion
---
# Provider connection exhaustion

Payment 503 responses with `ConnectionPoolExhausted` and health reporting zero available
connections indicate local provider connection exhaustion. Checkout commonly surfaces the same
requests as `UpstreamPaymentHTTP503` or a generic upstream payment failure.

Inspect pool limits and connection release behavior. Reduce concurrency if necessary and recycle
the affected service only through an approved operational action. Do not classify generic network
connection failures as pool exhaustion without the explicit runtime or health signal.

