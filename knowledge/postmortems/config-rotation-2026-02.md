---
document_type: postmortem
service: payment-service
failure_type: bad_deployment
---
# Provider configuration rotation regression, February 2026

A payment release changed the provider endpoint mapping. Immediately afterward, all charge calls
returned `ProviderConfigurationError`; health reported degraded and identified invalid provider
configuration. Checkout returned upstream 502 errors for the same request IDs.

The team rolled back the release after comparing deployment metadata and error onset. A validation
step was added to deployment checks. The postmortem cautions that deployment timing alone is not
root-cause evidence without a compatible runtime failure signal.

