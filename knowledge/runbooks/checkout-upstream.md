---
document_type: runbook
service: checkout-service
failure_type: upstream_dependency
---
# Checkout upstream dependency failures

Checkout translates payment timeouts to HTTP 504 and payment HTTP failures to checkout HTTP 502.
`PaymentServiceUnavailable` indicates a network connection failure before an HTTP response.
`UpstreamPaymentHTTP<n>` means payment answered with an error and should be investigated first.

Use request IDs to locate payment evidence. If payment has no matching log, test reachability and
service startup. If payment has a matching error or high duration, keep the affected service in
the report as payment while describing checkout as the user-visible failure surface.

