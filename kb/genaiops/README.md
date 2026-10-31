# GenAIOps track: Microsoft Foundry

Part of the [knowledge base](../README.md). The labs and my production
project are classic MLOps ([../mlops/](../mlops/README.md)), so they never
touched exam domains 3–5. These notes come from the practice questions in
[../../practice/genaiops/](../../practice/README.md), verified against
Microsoft Learn where possible, until a hands-on Foundry project covers them.

| Note | Covers |
|---|---|
| [foundry-setup.md](foundry-setup.md) | Foundry resource vs. project; managed identity, RBAC roles, key-less access |
| [models-and-deployments.md](models-and-deployments.md) | Choosing a model; Global / Data Zone / regional Standard, Provisioned, Batch, Developer; PTU + spillover; latency vs. throughput vs. response time; safe version upgrades |
| [prompts.md](prompts.md) | System-prompt design; prompts as code (Git, gated PRs, branches); published agent versions; prompt flow tools, variants, tracing |
| [rag-and-search.md](rag-and-search.md) | Retrieval levers, chunk size / overlap / threshold, keyword vs. vector vs. hybrid vs. semantic ranking, building a RAG flow |
| [evaluation.md](evaluation.md) | Which evaluator for which requirement; completeness × utilization; datasets (real, synthetic); safety evaluators vs. filters; reading before/after results; CI evaluation gates; manual evaluation; benchmarks by model type |
| [fine-tuning.md](fine-tuning.md) | Evaluate → prompt → RAG → fine-tune; SFT vs. DPO JSONL (UTF-8, `messages` with `role`/`content`); vision fine-tuning; promoting a fine-tuned model |
| [observability.md](observability.md) | Deployment metrics vs. diagnostic logs; traces vs. aggregated metrics vs. evaluation metrics |

Related MLOps notes: [network isolation for Foundry](../mlops/mechanics/network-isolation.md#foundry-the-same-model),
[Bicep for a Foundry account](../mlops/mechanics/bicep-and-cli-deployments.md).
