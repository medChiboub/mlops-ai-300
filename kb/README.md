# AI-300 knowledge base: MLOps half

My own notes for the AI-300 exam. This repo holds the **MLOps half**
(exam domains 1–2, about 45%):

- [mlops/](mlops/README.md): the 7 Microsoft Learn labs redone from scratch, a timeline, and
  [mechanics/](mlops/mechanics/README.md): what Azure ML actually does underneath (workspace,
  compute, data, AutoML, MLflow, jobs, sweeps, pipelines, registries, endpoints, monitoring,
  network isolation, Responsible AI, Bicep/CLI, GitHub Actions).
- **[SDK v2 + MLflow cheat sheet](mlops/mechanics/sdk-v2-cheatsheet.md)**: the code side of the exam on one page; review it the night before.

The **GenAIOps half** (domains 3–5, about 55%) lives in
[medChiboub/genaiops-ai-300](https://github.com/medChiboub/genaiops-ai-300/blob/main/kb/README.md):
the Foundry labs, plus the concepts from practice questions in
[kb/from-practice/](https://github.com/medChiboub/genaiops-ai-300/blob/main/kb/from-practice/README.md).

**[../practice/](../practice/README.md)** (local, git-ignored): the 100 MLOps practice
questions, each linked to the kb section it fed. The 70 GenAIOps ones are in the GenAIOps
repo's `practice/`.

Shared ground: network isolation ([Foundry section](mlops/mechanics/network-isolation.md#foundry-the-same-model)),
Bicep for a Foundry account ([bicep-and-cli-deployments.md](mlops/mechanics/bicep-and-cli-deployments.md)),
GitHub Actions gates ([github-actions-azureml.md](mlops/mechanics/github-actions-azureml.md),
[evaluation in CI](https://github.com/medChiboub/genaiops-ai-300/blob/main/kb/from-practice/evaluation.md#evaluation-in-the-release-workflow)).
