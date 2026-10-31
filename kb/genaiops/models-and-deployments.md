# Foundry models and deployments

Choosing a model, deployment types, performance, and safe upgrades. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

## Choosing a foundation model

From practice question [Q68](../../practice/genaiops/q068-foundation-model-selection.md).

Match a **property to a workload need**: conversational reasoning ↔
assistant; multimodal input ↔ text + image; enterprise governance ↔
regulated data; then cost/latency. "Largest" or "smallest" model *by size
alone* is always the distractor. Compare candidates with the **model
leaderboard** and your own evaluation.

## Foundry deployment types

From practice question [Q19](../../practice/genaiops/q019-foundry-deployment-types.md).

The name = **where data may be processed** + **how you pay**:
- **Where:** *Global* = any Azure region; *Data Zone* = within a geography
  (US/EU); regional = one region.
- **How you pay:** *Standard* = pay-per-token; *Provisioned* = reserved
  throughput units (PTUs); *Batch* = async, discounted.

| Workload | Pick |
|---|---|
| Variable or bursty, cost-sensitive (the default) | **Global Standard** |
| Steady, high-volume, latency-sensitive | **Global Provisioned** |
| Must stay in the EU/US | **Data Zone** Standard/Provisioned |
| Large offline jobs, results within 24h | **Global Batch** |

## Provisioned throughput and spillover

From practice question [Q167](../../practice/genaiops/q167-provisioned-spillover.md).

- Predictable, sustained volume with strict latency SLAs → **Provisioned
  (PTU)** deployment: reserved capacity, stable latency.
- Peaks above the PTU → **spillover** to a Standard deployment instead of
  throttling (429).
- Search side: semantic ranking needs a `SemanticConfiguration` with
  `SemanticField` entries in `prioritized_fields` ([Q166](../../practice/genaiops/q166-semantic-configuration-code.md)).

## Performance metrics: latency, throughput, response time

From practice question [Q67](../../practice/genaiops/q067-latency-throughput-response-time.md).

| Metric | Answers | Cue |
|---|---|---|
| **Latency** | How long before output comes back (time to first token for streaming) | "slow to return output" |
| **Throughput** | Requests or tokens per minute the deployment sustains | "can't sustain request volume" |
| **Response time** | End-to-end duration of one request | "duration of handling a request" |
| **Concurrency** | Calls in flight at once | describes load, not a symptom |

Provisioned (PTU) deployments trade cost for predictable latency and
throughput; Standard can throttle (429) at peaks.

## Safe model-version upgrades

From practice question [Q8](../../practice/genaiops/q008-foundry-safe-model-upgrade.md). 🟡 The
Foundry-specific steps aren't verified yet.

Pattern: **deploy alongside → validate → shift traffic** (keep the old
version for rollback). Never edit the live production route in place.

It's the same idea as Azure ML managed online endpoints:
1. Deploy `green` with 0% traffic.
2. Test it directly.
3. Optionally mirror or canary a small percentage.
4. Shift 100%.
5. Keep `blue` for rollback.

My production project implements this with `deploy.yml`
(`route_traffic=no`) + `shift-traffic.yml`.
