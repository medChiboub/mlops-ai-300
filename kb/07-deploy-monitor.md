# Lab 07: Deploy and monitor a model

Source: [docs/07-deploy-monitor.md](../docs/07-deploy-monitor.md)

Microsoft Learn module: [Deploy and monitor a model in Azure Machine Learning](https://learn.microsoft.com/en-us/training/modules/deploy-model-github-actions/)
(module 7 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/), dated 2026-08-27).
Its exercise (`go.microsoft.com/fwlink/?LinkId=2378100`) links to this lab.
Units 2–5 and the 5-question assessment were read before starting.

Mechanics: [GitHub Actions ↔ Azure ML](mechanics/github-actions-azureml.md) · [registries and environments](mechanics/registries-and-environments.md) · [job types](mechanics/job-types.md)

## 1. What this lab does

The full dev → prod loop, driven from a pull request:
1. dev and prod **data assets** + GitHub **environments** `dev`/`prod`
   (each with its own `AZURE_CREDENTIALS`, prod optionally gated by a
   reviewer)
2. **PR-triggered dev training** (`train-dev.yml`) that comments Accuracy/AUC
   on the PR
3. **`/train-prod`** comment → retrain on prod data (`train-prod.yml`)
4. **`/deploy-prod`** comment → deploy to a **managed online endpoint** with
   data collection (`deploy-prod.yml` → `src/deploy_to_online_endpoint.py`)
5. test the endpoint, set up **model monitoring** (data drift) in Studio
6. simulate drift → retrain through the same PR flow; optional **rollback**
   and **archive**

## 2. Steps I actually ran

Same workspace and repo as before (`rg-ai300-l…` / `mlw-ai300-l…`,
`medChiboub/mlops-ai-300`). "Provision" and "create repo from template" are
skipped; lab 05's separate dev/prod workspaces are **not** used (the lab
simulates dev/prod inside one workspace).

### 2.1 Data assets (Claude, CLI)

```bash
cd infra
az ml data create --type uri_folder --name diabetes-dev-folder  --path ../experimentation/data -g rg-ai300-l0533925c724d4c839e -w mlw-ai300-l0533925c724d4c839e
az ml data create --type uri_folder --name diabetes-prod-folder --path ../production/data      -g rg-ai300-l0533925c724d4c839e -w mlw-ai300-l0533925c724d4c839e
```
Both are version 1, in separate `LocalUpload/<hash>/data/` folders. The
three CSVs (`experimentation/data/diabetes-dev.csv`,
`production/data/diabetes-prod.csv`, `data/diabetes-data/diabetes.csv`) have
the **same MD5** (`d8b14b5e…`): dev and prod data are byte-identical. The
upload folders still differ, because the hash covers the file name.

### 2.2 GitHub environments and secrets (Claude, API)

- `dev` and `prod` environments created (`gh api -X PUT
  repos/…/environments/<name>`).
- **`prod`: required reviewer = me** (`prevent_self_review: false`), so any
  job with `environment: prod` pauses until I approve it. The lab marks this
  *optional*; we did it because the repo is **public** and the two
  comment-triggered workflows are about to be re-enabled.
- **`AZURE_CREDENTIALS` as an environment secret in both.** Like the lab,
  **one identity for dev and prod** (the same service principal). New
  client secret `gh-environments-lab07` (`az ad app credential reset
  --append`), assembled into the JSON and piped into both environment secrets,
  never printed. The lab 06 repo secret (`rbac`) still works. Environment
  secrets take precedence for jobs that declare `environment:`.

### How dev and prod share one job definition

Both workflows submit **the same `src/job.yml`**; only submit-time settings
differ:

| | `train-dev.yml` | `train-prod.yml` |
|---|---|---|
| Job definition, script, environment, compute, `reg_rate` | `src/job.yml` | **the same** |
| Training data (`--set inputs.training_data.path=…`) | `azureml:diabetes-dev-folder@latest` | `azureml:diabetes-prod-folder@latest` |
| GitHub environment → secret and gate | `dev`: no approval | `prod`: **my approval** |
| Workspace | lab 01 (found by the `rg-ai300-l` prefix) | **the same** |
| Job name | `diabetes-train-dev-<run id>` | `diabetes-train-prod-<run id>` |

"Same definition, different configuration": what was reviewed in dev is
exactly what runs in prod. ⚠ `--set` overrides the **path**, not the
**type**, so `job.yml` must say `type: uri_folder` (the lab's first edit).
Lab 06 left it at `uri_file`.

**What `train-prod.yml` does on `/train-prod`:** an `issue_comment` on a PR
containing `/train-prod` → the job waits for **my approval** (`environment:
prod`) → checks out **the PR's code** (`refs/pull/<N>/head`) → logs in with
prod's `AZURE_CREDENTIALS` → submits `src/job.yml` with the prod data →
`az ml job stream` → downloads `metrics.json` (the `metrics_output` output) →
posts Accuracy and AUC as a PR comment. Caveats: the prod data is
byte-identical to dev, so the metrics will match; the model it trains is
**not** what `/deploy-prod` deploys (that's the committed `model/`);
`contains()` matches anywhere in the comment; and it runs PR code with prod
credentials (the pwn-request risk, mitigated here by the interaction limits
+ the reviewer gate).

## 3. What broke and how we fixed it

## 4. Exam mapping

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check
