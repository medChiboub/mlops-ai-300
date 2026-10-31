# AI-300 knowledge base

My own notes for the AI-300 exam, split by the exam's two halves.

| Track | What's in it | Exam domains |
|---|---|---|
| [mlops/](mlops/README.md) | The 7 Microsoft Learn labs redone from scratch, a timeline, and [mechanics/](mlops/mechanics/README.md): what Azure ML actually does underneath (workspace, compute, data, AutoML, MLflow, jobs, sweeps, pipelines, registries, endpoints, monitoring, network isolation, Responsible AI, Bicep/CLI, GitHub Actions) | 1–2 (about 45%) |
| [genaiops/](genaiops/README.md) | Microsoft Foundry concepts from practice questions: evaluation, RAG and search, models and deployments, fine-tuning, prompts and prompt flow, Foundry setup and identity, observability | 3–5 (about 55%) |

**[../practice/](../practice/README.md)** (local, git-ignored): 170 practice
questions, split the same way (`practice/mlops/`, `practice/genaiops/`), each
linked to the kb section it fed.

Shared ground between the tracks: network isolation
([Foundry section](mlops/mechanics/network-isolation.md#foundry-the-same-model)),
Bicep deployments of a Foundry account
([bicep-and-cli-deployments.md](mlops/mechanics/bicep-and-cli-deployments.md)),
and GitHub Actions gates ([github-actions-azureml.md](mlops/mechanics/github-actions-azureml.md),
[evaluation in CI](genaiops/evaluation.md#evaluation-in-the-release-workflow)).
