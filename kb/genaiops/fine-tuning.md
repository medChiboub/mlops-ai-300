# Fine-tuning and optimization

When to fine-tune, data formats, and promoting a fine-tuned model. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

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

## Promoting a fine-tuned model

From practice question [Q44](../../practice/genaiops/q044-promote-finetuned-model.md). 🟡

Generic order: **version/register → evaluate and validate → production
deployment** (for example Global Standard).
- Foundry's **Developer tier** deployment exists to *evaluate* fine-tuned
  models cheaply: no hosting fee, no SLA, not for production.
- So "Developer tier → evaluate → Global Standard" is also defensible. Read
  the stem carefully.
