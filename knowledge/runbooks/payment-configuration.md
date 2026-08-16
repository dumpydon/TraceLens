---
document_type: runbook
service: payment-service
failure_type: bad_deployment
---
# Payment configuration regression

`ProviderConfigurationError` after a recent payment deployment is strong evidence of an invalid
provider endpoint or credential mapping. Correlate the first error time with the deployment time
and version. The payment health response exposes whether configuration is valid without revealing
why it changed.

Validate the deployed environment mapping, compare it with the last known-good version, and roll
back the configuration-bearing release through the normal human-controlled deployment process.
Never infer a bad deployment from temporal proximity alone when runtime errors name another cause.

