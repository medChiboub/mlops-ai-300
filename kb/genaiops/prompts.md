# Prompts and prompt flow

Prompt design, governance, versioning, and prompt flow tools. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

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

## Prompt governance: prompts are code

From practice question [Q51](../../practice/genaiops/q051-prompt-governance.md).

| Need | Mechanism |
|---|---|
| History and audit | Prompts in a **Git repository** |
| Review before production | **Gated pull requests** (required reviewers / checks, for example the evaluation gate from Q48) |
| Roll back | Redeploy a **prior agent/prompt version** (or revert and redeploy) |

Never edit prompts directly in production; that bypasses all three.

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
