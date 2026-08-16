---
document_type: architecture
service: all
failure_type: topology
---
# Checkout and payment boundaries

The checkout service owns order confirmation and calls `payment-service` synchronously over
HTTP. It forwards the incoming `X-Request-ID`, so a checkout failure and its corresponding
payment operation can be joined by request ID. Checkout has a one-second payment timeout.

Payment owns provider authorization. Normal authorization takes less than 100 ms. A payment
duration above 1,000 ms can cause checkout to return `UpstreamPaymentTimeout` even if payment
eventually records a successful provider response. Investigators should compare both services'
logs before treating a checkout timeout as a checkout defect.

