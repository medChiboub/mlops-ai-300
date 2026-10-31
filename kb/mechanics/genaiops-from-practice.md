# GenAIOps concepts (from practice questions)

The labs and my production project are classic MLOps, so they never touched
GenAIOps (exam domains 3–5). This note collects the GenAIOps concepts that
practice questions surfaced, verified where possible, until the separate
Foundry project covers them hands-on. Sections are added as questions come
in.

## Evaluation metrics

From practice question [Q2](../../practice/q002-genai-quality-metrics.md).

Pick the evaluator by the **requirement's wording**:

| Requirement says… | Evaluator | Needs a reference answer? |
|---|---|---|
| "supported by the sources", "no fabrication", "grounded" | **Groundedness** | No (needs the context) |
| "addresses the user's question", "on-topic" | **Relevance** | No |
| "readable", "natural" | Fluency | No |
| "logically consistent" | Coherence | No |
| "matches the expected answer" | Similarity, F1 | **Yes** (ground truth) |
| "unsafe or harmful content" | Safety evaluators (violence, self-harm, hate, sexual) | No |

- For RAG, "accurate and source-backed" → **groundedness**. "Answers the
  prompt" → **relevance**.
- Fairness, harmfulness and tone aren't *quality* metrics for "dependable
  and meaningful" answers.

## Identity: key-less access and least privilege

From practice question [Q3](../../practice/q003-foundry-keyless-identity-rbac.md).

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

From practice question [Q5](../../practice/q005-rag-retrieval-accuracy.md).

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

From practice question [Q8](../../practice/q008-foundry-safe-model-upgrade.md). 🟡 The
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
