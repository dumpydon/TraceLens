# Evaluation

The dataset contains one reproducible case per V1 lab scenario. Scenario ground truth stays in
this evaluation boundary and is never placed in investigation state or prompts.

Start both lab services, then run `make eval`. The harness activates each scenario, generates real
checkout traffic, runs the same durable investigation graph used by the API, and stores a local
summary plus structured per-case results for the frontend. The same runner can be launched
explicitly from the Evaluations page through `POST /api/evaluations/run`. The evaluator functions
accept `outputs` and `reference_outputs`, which matches the callable shape used by LangSmith
offline evaluators.

Root-cause category and affected service are exact deterministic comparisons. Retrieval relevance
checks whether retrieved metadata includes the expected failure type. Evidence groundedness checks
that every report citation resolves to collected evidence. An LLM judge is intentionally not
required for these V1 metrics.

Expected labels are compared only after an investigation has produced its report and retrieved
evidence. They are never placed in normal investigation state or model prompts.
