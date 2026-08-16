---
document_type: runbook
service: payment-service
failure_type: payment_failure
---
# Payment HTTP failure runbook

A broad series of payment 502 responses with `ProviderDeclinedError`, paired with checkout
`UpstreamPaymentHTTP502`, indicates provider-side charge rejection or an upstream payment
dependency failure. Group by request ID and deployment version; confirm health and configuration
before attributing the problem to a deployment.

Preserve response counts and representative correlated requests. Check provider availability and
error contracts, then apply the provider failover procedure if the failure is not isolated to
invalid customer inputs.

