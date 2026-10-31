# GenAI observability

Monitoring a deployed model or app: metrics, logs, traces. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

## Observability for a model deployment

From practice question [Q14](../../practice/genaiops/q014-foundry-latency-observability.md). 🟡 Exact
Foundry step order not verified.

1. **Deploy** (the endpoint must exist).
2. **Metrics:** Azure Monitor time series for latency, requests, tokens and
   errors. They're on by default; you build charts and alerts.
3. **Logs:** per-request telemetry. Turn it on with a **diagnostic
   setting** that sends it to Log Analytics.

It's the same metrics-vs-logs split as Azure ML online endpoints (see
[monitoring-ms-learn.md](../mlops/mechanics/monitoring-ms-learn.md)). Blocklists (content safety)
and embeddings (retrieval) aren't observability.

## Traces, metrics, logs: which answers what

From practice questions [Q129](../../practice/genaiops/q129-traces-vs-metrics.md), [Q132](../../practice/genaiops/q132-tracing-early-termination.md), [Q133](../../practice/genaiops/q133-tracing-vs-aggregated-metrics.md).

| Question | Look at |
|---|---|
| What happened inside **one** request: which step, inputs/outputs, tokens per node, latency, errors, `finish_reason` | **Traces** (spans per flow node / agent step) |
| Trends over **many** requests: error rates, latency regressions, recurring failures | **Aggregated metrics** (dashboards, alerts) |
| A quality score (accuracy, groundedness) from an evaluation | **Evaluation metrics** |
| Raw text output for debugging | Logs |

Production-only, intermittent bugs ("ends early, can't reproduce") → enable
**tracing** first.
