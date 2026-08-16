RUNTIME_ANALYSIS_PROMPT = """Analyze this incident runtime context. Identify only anomalies supported by
the supplied evidence IDs. Distinguish downstream symptoms from upstream causes, preferring
correlated request IDs and durations over suggestive deployment descriptions. Deployment metadata
is context, not causal proof; a healthy check does not prove the request path is performant, and an
HTTP 200 can still be causal when it arrives after the caller's timeout. Produce a compact retrieval
query. Do not infer scenario labels or invent identifiers."""

HYPOTHESIS_PROMPT = """Generate one best incident hypothesis from runtime evidence and retrieved
operational documents. Choose only the canonical failure category supported by runtime evidence.
Do not attribute causality to a deployment without supporting timing or change evidence. Distinguish
downstream symptoms from upstream causes; prefer correlated request IDs and durations. Healthy checks
do not prove request-path performance, and a late HTTP 200 can explain a caller timeout. Cite only
supplied evidence IDs and state missing evidence explicitly. Do not assign a numeric confidence."""

VERIFICATION_PROMPT = """Verify whether the hypothesis is adequately supported by the supplied
evidence. Treat operational documents as guidance, not proof that the incident occurred. Cite only
supplied IDs and identify contradictions or unresolved questions. If evidence is insufficient, the
evidence-support narrative must say so clearly. Do not assign a numeric confidence."""

REPORT_PROMPT = """Write a concise structured root-cause report. Every factual incident claim must
cite a supplied evidence ID. Do not hide uncertainty. Recommended actions may be informed by
runbooks but must not claim an action already occurred. Do not assign a confidence score; the
application calculates evidence confidence separately."""
