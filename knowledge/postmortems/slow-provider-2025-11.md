---
document_type: postmortem
service: payment-service
failure_type: payment_latency
---
# Slow provider authorization, November 2025

Checkout errors increased when provider authorization latency rose above the caller's one-second
budget. Payment requests completed in 1.4–2.1 seconds while checkout returned 504. The key evidence
was identical request IDs across both services and the asymmetric duration. Service health stayed
green because health did not perform an authorization.

The incident was mitigated by routing away from the degraded provider. Follow-up work added a
provider latency alert and clarified that health is not evidence of charge-path performance.

