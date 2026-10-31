# GenAIOps concepts (from practice questions)

The labs and my production project are classic MLOps, so they never touched
GenAIOps (exam domains 3–5). This note collects the GenAIOps concepts that
practice questions surfaced, verified where possible, until the separate
Foundry project covers them hands-on. Sections are added as questions come
in.

## Evaluation metrics

From practice question [Q2](../../practice/genaiops/q002-genai-quality-metrics.md).

Pick the evaluator by the **requirement's wording**:

| Requirement says… | Evaluator | Needs a reference answer? |
|---|---|---|
| "supported by the sources", "no fabrication", "grounded" | **Groundedness** | No (needs the context) |
| "addresses the user's question", "on-topic" | **Relevance** | No |
| "readable", "natural", **"grammatically correct"** ([Q45](../../practice/genaiops/q045-fluency-evaluator.md)) | **Fluency** | No |
| "logically consistent", "ideas connect" (not grammar!) | Coherence | No |
| "matches the expected answer" | Similarity, F1 | **Yes** (ground truth) |
| "unsafe or harmful content" | Safety evaluators (violence, self-harm, hate, sexual) | No |

- For RAG, "accurate and source-backed" → **groundedness**. "Answers the
  prompt" → **relevance**.
- Fairness, harmfulness and tone aren't *quality* metrics for "dependable
  and meaningful" answers.

## Identity: key-less access and least privilege

From practice question [Q3](../../practice/genaiops/q003-foundry-keyless-identity-rbac.md).

| Need | Mechanism |
|---|---|
| A service or workload signs in **without stored secrets** | **Managed identity** (Entra ID; Azure manages the credential) |
| Decide **what** a person or identity may do, and **where** | **Azure RBAC role assignment**, scoped to the project, Foundry resource, resource group or subscription |

- A managed identity has **no permissions by itself**. Pair it with role
  assignments (for example a Storage Blob Data role, or a Search index data
  role).
- API keys and secret-based service principals violate a "no stored
  credentials" policy.
- It's the same pattern as my production project's OIDC + scoped
  Contributor, and the lab's service-principal secret is the counterexample.

## RAG retrieval quality

From practice question [Q5](../../practice/genaiops/q005-rag-retrieval-accuracy.md).

When answers are incomplete because the **right content isn't retrieved
consistently**, fix retrieval, not generation:

| Lever | Fixes | Cost |
|---|---|---|
| **Chunk size + overlap** tuned to the content's structure | Context cut across chunk boundaries; chunks too broad or narrow | One-time re-index |
| **Re-ranking** (semantic ranker / cross-encoder) | Relevant chunks retrieved but ranked too low | Modest, per query |
| **Hybrid search** (keyword + vector) | Exact names, codes and IDs that vectors miss | Low |
| New embedding model or dimensions | Representation quality | Re-embed everything |
| Bigger token limits | Nothing retrieval-related | Higher cost on every call |

- "Without changing the embedding model" rules out changing vector
  dimensions, which is a property of the model.
- More context tokens can't fix a passage that was never retrieved.

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

## RAG evaluation: completeness vs. utilization

From practice question [Q13](../../practice/genaiops/q013-rag-completeness-utilization.md).
📘 Microsoft's *RAG: LLM end-to-end evaluation phase* guide.

- **Completeness:** does the response answer every part of the query?
- **Utilization:** how much of the response comes from the provided
  chunks? Low = the retrieved chunks were mostly irrelevant.

| | High utilization | Low utilization |
|---|---|---|
| **High completeness** | No action | Irrelevant chunks come along → **reduce top-k** |
| **Low completeness** | Chunks used but not enough → **increase top-k**, **find relevant chunks that weren't returned and why**, richer chunks | Chunks insufficient *and* unused → **increase chunk size**, tune the prompt |

For low completeness in general, the guide's order is:
1. Check the embedding model's vocabulary fit.
2. Then check the chunking strategy (bigger fixed-size chunks).
3. Then check whether the data even contains the answer.

## Evaluation datasets

From practice question [Q15](../../practice/genaiops/q015-synthetic-eval-data.md).

An evaluation = **dataset** (inputs, optionally expected outputs) +
**target** (app, prompt variant, model) + **evaluators**. To compare
variants fairly, the **dataset must be fixed**.

| Source | When |
|---|---|
| Curated real examples | You have them, and they're representative |
| **Synthetic data generation** | No live traffic yet (dev). Foundry can generate queries from your content |
| Logged production traffic | After launch, for regression sets |

### Synthetic data: for evaluation *and* fine-tuning

From practice question [Q27](../../practice/genaiops/q027-synthetic-finetuning-data.md).
Foundry's **simulator** generates task-matched conversations
(prompt → response) without production data:
- **Evaluation:** a fixed test set (Q15).
- **Fine-tuning:** training examples when compliance blocks real
  conversations (Q27).

Telemetry and traces describe *how* the app ran; they aren't training
examples.

## Prompt design

From practice question [Q16](../../practice/genaiops/q016-prompt-design-reusable.md).

| Technique | Use for |
|---|---|
| **System message** | Persistent role, tone, style, rules |
| **Separate/delimit system instructions from user input** | Robustness, reuse, prompt-injection resistance |
| Few-shot examples | Showing the format or style |
| Repeat key instructions at the end | Compliance on long prompts (recency bias) |
| Lower temperature | Consistency (higher = more variety) |
| Fine-tuning | Only when prompting can't get there. It *is* retraining |

Exam cue: "dependable, reusable, **without retraining**" → system message +
clear system/user separation. Never fine-tuning or a higher temperature.

## Observability for a model deployment

From practice question [Q14](../../practice/genaiops/q014-foundry-latency-observability.md). 🟡 Exact
Foundry step order not verified.

1. **Deploy** (the endpoint must exist).
2. **Metrics:** Azure Monitor time series for latency, requests, tokens and
   errors. They're on by default; you build charts and alerts.
3. **Logs:** per-request telemetry. Turn it on with a **diagnostic
   setting** that sends it to Log Analytics.

It's the same metrics-vs-logs split as Azure ML online endpoints (see
[monitoring-ms-learn.md](monitoring-ms-learn.md)). Blocklists (content safety)
and embeddings (retrieval) aren't observability.

## Safety evaluators vs. content filters

From practice question [Q18](../../practice/genaiops/q018-hate-content-evaluator.md).

| Risk | Evaluator (measure, pre-release) |
|---|---|
| Hate/unfairness, violence, sexual, self-harm | **Content safety** evaluators |
| Copyrighted text or code reproduced | Protected material |
| Instructions injected via documents/data (XPIA) | Indirect attack |
| Jailbreak in the user prompt | Direct attack |
| Unsupported claims | Groundedness (*quality*, not safety) |

- **Evaluators** measure, on a dataset, before release, repeatably.
- **Content filters** and **blocklists** *block* at runtime.
- Production uses both.

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

## Search modes in Azure AI Search

From practice question [Q25](../../practice/genaiops/q025-search-keyword-vs-semantic.md).

| Mode | Good at | Weak at |
|---|---|---|
| **Keyword / full-text (BM25)** | **Exact terms**: IDs, codes, names | Paraphrases and synonyms |
| **Vector** | Meaning: paraphrased natural-language questions | Exact IDs and rare tokens |
| **Hybrid** (keyword + vector, merged with RRF) | Both at once | — |
| **Semantic ranker** (on top) | Re-ranking the top results by meaning | Doesn't retrieve, only re-orders |

Exam cue: "exact identifiers must match" → keyword. "Natural-language
relevance" → vector + semantic ranking. Usually configured together as
**hybrid + semantic ranker**.

## Reading evaluation results: before vs. after

From practice question [Q31](../../practice/genaiops/q031-finetune-eval-comparison.md).

- Compare runs on the **same dataset**, metric by metric, and check each
  metric's **direction**:

| Metric | Better is |
|---|---|
| Groundedness, relevance, coherence, fluency | **Higher** |
| Hallucination rate, safety defect rate | **Lower** |
| Latency, cost per call | **Lower** |

- A **regression** = a metric moved the wrong way. A small latency change
  (420 → 430 ms) is a trade-off to note, not a functional failure.

## Fine-tuning data: SFT vs. DPO, and file format

From practice questions [Q32 + Q34](../../practice/genaiops/q032-dpo-preference-records.md).

| Method | Learns from | One JSONL line |
|---|---|---|
| **SFT** (supervised) | Correct examples | `{"messages":[{system},{user},{assistant}]}` |
| **DPO** (direct preference optimization) | **Comparisons** | `{"input":[...], "preferred_output":[{assistant}], "non_preferred_output":[{assistant}]}` |

- DPO needs **contrast**: identical preferred and non-preferred outputs give
  no signal.
- Each output must be an `assistant`-role message.
- Files are **JSONL** (one object per line), **UTF-8** encoded. Upload
  training (and optionally validation) files, then fine-tune.

**Vision fine-tuning** ([Q55](../../practice/genaiops/q055-vision-finetuning-model.md)): to fine-tune
on **text + images**, pick a base model whose fine-tuning supports vision.
At the time of the question that's **`gpt-4o`**; `gpt-35-turbo` and
`davinci-002` are text-only. Model lineups change, so check the current
table.

## Foundry resource vs. project

From practice question [Q42](../../practice/genaiops/q042-foundry-resource-vs-project.md).

| Level | Holds | Use for |
|---|---|---|
| **Foundry resource** | Governance, security, networking, model deployments, **shared connections** | One shared resource = central control |
| **Project** (under the resource) | A team's files, agents, evaluations, access | **One project per team** = isolation |

It's the same shape as Azure ML **hub + projects**.

## Evaluation in the release workflow

From practice questions [Q43, Q46, Q48](../../practice/genaiops/q048-eval-github-action-gate.md).

| Question | Mechanism |
|---|---|
| "Is it healthy *now*?" (timeouts, latency, errors) | **Observability metrics** + diagnostic logs (production) |
| "Is the *new version* good and safe?" | **Evaluation workflow** on a dataset, **before release** |
| "Check **every PR** and **fail the build**" | A **GitHub Actions** workflow running Foundry evaluations with thresholds |

Cloud safety evaluation with the SDK, using an **already registered**
dataset:
1. Install/create the Foundry **project client**.
2. **Configure safety evaluators** (violence, sexual, self-harm, hate).
3. **Submit the evaluation to the project in the cloud.**

Don't re-upload a dataset that's already registered. A local test run is
optional.

## Promoting a fine-tuned model

From practice question [Q44](../../practice/genaiops/q044-promote-finetuned-model.md). 🟡

Generic order: **version/register → evaluate and validate → production
deployment** (for example Global Standard).
- Foundry's **Developer tier** deployment exists to *evaluate* fine-tuned
  models cheaply: no hosting fee, no SLA, not for production.
- So "Developer tier → evaluate → Global Standard" is also defensible. Read
  the stem carefully.

## Prompt governance: prompts are code

From practice question [Q51](../../practice/genaiops/q051-prompt-governance.md).

| Need | Mechanism |
|---|---|
| History and audit | Prompts in a **Git repository** |
| Review before production | **Gated pull requests** (required reviewers / checks, for example the evaluation gate from Q48) |
| Roll back | Redeploy a **prior agent/prompt version** (or revert and redeploy) |

Never edit prompts directly in production; that bypasses all three.

## Building a RAG flow from files

From practice question [Q61](../../practice/genaiops/q061-rag-flow-from-local-files.md), [Q76](../../practice/genaiops/q076-fabrikam-rag-serving-retrieval.md).

| Step | What it produces |
|---|---|
| 1. **Data asset** (upload local files) | The source content, versioned in the project |
| 2. **Vector index** | Chunks + embeddings, stored in Azure AI Search (or a FAISS file) |
| 3. **Connection** | Credentials/endpoint for the model (and search) the flow calls |
| 4. **Flow** | lookup (index) → prompt (context + question) → LLM |

To serve it: deploy the flow to a **managed online endpoint**. If curated
documents already live in **Azure AI Search**, reuse that index as the
retriever instead of building a new one.

## Chunk size, overlap and similarity threshold

From practice question [Q66](../../practice/genaiops/q066-chunk-overlap-threshold.md).

| Knob | Too high | Too low |
|---|---|---|
| **Chunk size** | *Semantic dilution*: one chunk mixes topics → blurry embedding → loose, off-topic matches | Fragments lose context; answers incomplete |
| **Overlap** | Neighbouring chunks repeat each other → **duplicate** results in top-k (e.g., 400 of 1,200 tokens) | Sentences split at boundaries lose context (10–15% is a common start) |
| **Similarity threshold** | Strict filter drops relevant but lower-scoring chunks | Admits weak matches (noise) |
| **Top-k** | Irrelevant chunks dilute the prompt | Misses needed chunks |

Fix dilution with **smaller chunks**, not a lower threshold. Keyword-only
search removes semantic matching altogether.

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

## Choosing a foundation model

From practice question [Q68](../../practice/genaiops/q068-foundation-model-selection.md).

Match a **property to a workload need**: conversational reasoning ↔
assistant; multimodal input ↔ text + image; enterprise governance ↔
regulated data; then cost/latency. "Largest" or "smallest" model *by size
alone* is always the distractor. Compare candidates with the **model
leaderboard** and your own evaluation.

## Optimization order: evaluate, prompt, RAG, fine-tune

From practice questions [Q72](../../practice/genaiops/q072-finetuning-first-step-jsonl.md), [Q78](../../practice/genaiops/q078-fabrikam-optimization-strategy.md), [Q79](../../practice/genaiops/q079-fabrikam-evaluate-first.md).

1. **Evaluate** against an evaluation set → a baseline (use real pairs if you
   have them; synthetic only if you don't).
2. **Prompt engineering** (system message, examples, structure): cheapest,
   first fix, including for poor RAG answers.
3. **RAG** when the model lacks knowledge (facts, private data).
4. **Fine-tuning** when it lacks *behaviour*: domain/task specialization or
   format (SFT); alignment with ranked preferences (DPO). Starts with a JSONL
   training file, then a job, then a Developer-tier deployment to evaluate.

Temperature and `max_tokens` change randomness and length, not accuracy or
grounding.

## Prompt versioning: Git plus published agent versions

From practice questions [Q84](../../practice/genaiops/q084-prompts-in-git.md), [Q90](../../practice/genaiops/q090-prompt-versions-without-redeploy.md).

- **Track and reuse** prompt templates across projects → versioned files in
  a **Git** repo (not blob, datasets or app config).
- **Ship a prompt change without redeploying the app** → publish a new
  **agent version**; the consuming app calls a stable agent application
  endpoint that serves the latest published version.
- **Roll back** → republish/point to the prior agent version.

## Prompt flow: tools, variants, tracing

From practice questions [Q91–Q94](../../practice/genaiops/q091-pf-variants-evaluation.md), [Q96](../../practice/genaiops/q096-prompt-flow-llm-python-tools.md).

| Need | Use |
|---|---|
| Try alternative prompts / parameters | **Variants**: only on the **LLM tool** node |
| Call a custom API or run custom code | **Python tool** (+ custom connection for secrets) |
| Make embeddings | Embedding tool |
| Compare variants on a dataset | **Batch run** per variant → evaluation results view (outputs, tokens, duration) |
| Per-run inputs, outputs, latency, tokens | **Tracing** (portal toggle or `start_trace()` in the SDK) |
| Production health of a deployed flow | Azure Monitor / App Insights (not for prompt comparison) |

Prompt flow is the *classic* Foundry experience; the same ideas carry over
to agents (versions, tracing, evaluations).
