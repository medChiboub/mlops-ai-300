# GenAI evaluation

Evaluators, datasets, reading results, and evaluation in CI/CD. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

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

## Manual and human evaluation

From practice question [Q137](../../practice/genaiops/q137-manual-evaluation-steps.md), [Q134](../../practice/genaiops/q134-evaluation-inputs.md).

- Manual evaluation in the portal: import a CSV (or type rows) → run → rate
  each response 👍/👎 → **save** to review later.
- Automated evaluation inputs: a fixed **test dataset** (reuse it for
  comparable runs), **ground truth** where metrics need it, and **column
  mapping** from dataset/app fields to evaluator inputs (`query`, `response`,
  `context`, `ground_truth`).

## Comparing prompt variants: cost and quality

From practice question [Q104](../../practice/genaiops/q104-token-usage-llm-judge.md).

- **Cost** = tokens (input + output) on pay-per-token deployments → monitor
  **token usage**; longer responses cost more.
- **Quality** = AI-assisted evaluators (**LLM-as-a-judge**: coherence,
  relevance, groundedness, fluency) on the same dataset for both variants.
- Latency and run-to-run consistency are secondary signals.

## Benchmark metrics by model type

From practice questions [Q88](../../practice/genaiops/q088-benchmark-coherence-f1.md), [Q161](../../practice/genaiops/q161-benchmark-vmeasure-gptsimilarity.md).

| Model / task | Benchmark cue |
|---|---|
| Embeddings for **clustering / categorising** | **V measure** |
| Embeddings for **retrieval** (find relevant, avoid irrelevant) | NDCG, MAP, **F1** (precision + recall) |
| Generation compared with a reference answer | **GPTSimilarity** (semantic similarity to ground truth) |
| Generation readability | Coherence, fluency |
