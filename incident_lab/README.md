# Incident Lab

The lab is an executable evidence source, not a fixture. `checkout-service` calls
`payment-service` over HTTP and both append structured JSON logs under
`data/runtime`. The scenario controller changes payment behavior through a small
shared runtime state file.

Run the services in separate terminals from the repository root:

```bash
make lab-payment
make lab-checkout
```

Then activate and exercise a scenario:

```bash
.venv/bin/python -m incident_lab.scenarios activate payment_latency
.venv/bin/python -m incident_lab.scenarios traffic --count 12
.venv/bin/python -m incident_lab.scenarios reset
```

The scenario state is ground truth. The investigation backend reads only service
logs, deployments, and health endpoints; it never reads the active scenario file
while forming a diagnosis.
