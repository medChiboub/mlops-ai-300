# Lab 06: Automate model training with GitHub Actions

Source: [docs/06-automate-model-training.md](../docs/06-automate-model-training.md)

Microsoft Learn module: [Automate model training with GitHub Actions](https://learn.microsoft.com/en-us/training/modules/trigger-azure-machine-learn-jobs-github-actions/)
(module 6 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/), dated 2026-08-27).
Its exercise unit links to this lab. Theory units 2–6 and the 5-question
assessment were read before starting.

Mechanics: [GitHub Actions ↔ Azure ML](mechanics/github-actions-azureml.md) · [interfaces](mechanics/interfaces.md) · [command jobs](mechanics/command-jobs.md)

## 1. What this lab does

Connects the GitHub repo to the Azure ML workspace so a **workflow** can
submit training jobs:
1. a **service principal** (Contributor on the lab resource group) whose
   JSON credentials go into the repo secret `AZURE_CREDENTIALS`, plus repo
   variables for the resource group and workspace
2. a read-only look at the workspace's **network access** settings
3. the `manual-trigger-job.yml` workflow, extended with an `az ml job create`
   step for `src/job.yml`, run by hand
4. a `pull_request` trigger, **branch protection** on `main`, and a feature
   branch + PR that runs training automatically

## 2. Steps I actually ran

Reusing lab 01's workspace (`rg-ai300-l0533925c724d4c839e` /
`mlw-ai300-l0533925c724d4c839e`) and this repo (`medChiboub/mlops-ai-300`,
created from the template and **made public** so branch protection works on
the free plan). The lab's "provision" and "create your repository from the
template" sections are skipped.

### 2.1 Configure GitHub integration with Azure ML (Claude, CLI)

```bash
SUB=$(az account show --query id -o tsv)
az ad sp create-for-rbac --name "sp-mslearn-mlops-github" --role contributor \
    --scopes "/subscriptions/$SUB/resourceGroups/rg-ai300-l0533925c724d4c839e" \
    --json-auth \
  | gh secret set AZURE_CREDENTIALS -R medChiboub/mlops-ai-300     # JSON goes straight into GitHub; never printed or saved
gh variable set AZURE_RESOURCE_GROUP -R medChiboub/mlops-ai-300 --body "rg-ai300-l0533925c724d4c839e"
gh variable set AZURE_WORKSPACE_NAME -R medChiboub/mlops-ai-300 --body "mlw-ai300-l0533925c724d4c839e"
```

The lab does this by copying the JSON by hand from Cloud Shell into
*Settings → Secrets and variables → Actions*. Same result; piping avoids the
secret ever sitting in a terminal or clipboard.

Verified:
- **Secret** `AZURE_CREDENTIALS` (repository-level); **variables**
  `AZURE_RESOURCE_GROUP`, `AZURE_WORKSPACE_NAME`.
- **App registration** `sp-mslearn-mlops-github` (appId `a9bd6f2c-…`), one
  client secret valid **2026-09-30 → 2027-09-30** (the default 1 year).
- **Role:** Contributor on `rg-ai300-l0533925c724d4c839e` **only** (nothing at
  subscription scope). It can't reach the lab 05 resource groups.
- The CLI warned: *"Option '--sdk-auth' has been deprecated"*. `--json-auth` is
  its alias, and the JSON-secret login style is on its way out in favour of
  OIDC.
- Two older app registrations from earlier work (`sp-ai300-prod`,
  `sp-ai300-github-actions`) exist in the tenant and were left untouched.
- What the command created underneath (app registration vs. service
  principal vs. client secret vs. role assignment, and how `azure/login`
  uses them):
  [mechanics/github-actions-azureml.md](mechanics/github-actions-azureml.md#what-az-ad-sp-create-for-rbac-actually-created-verified-lab-06).

### 2.2 Review workspace network access (portal, me; read only)

Portal → workspace → **Settings → Networking**: **Public access: Enabled
from all networks**, no private endpoints. Nothing changed. Claude confirmed
from the CLI: `public_network_access: Enabled`, `default_action: ALLOW`, no
IP rules, managed network `disabled`, `az network private-endpoint list` → 0.

The lab's point: GitHub-hosted runners come from the public internet, so
public access has to stay on here. In production you'd use **private
endpoints + a virtual network + self-hosted runners** inside that network,
plus RBAC, to control who can submit jobs and from where. That's the
exam's *Restrict network access to Machine Learning workspaces*, and this
read-only review is the only place these labs touch it.

### 2.3 Train with a manually triggered workflow (VS Code + GitHub, me)

1. `src/job.yml`: filled the two placeholders → `type: uri_file`,
   `path: azureml:diabetes-data@latest`.
2. `.github/workflows/manual-trigger-job.yml`: appended, with **spaces** (the
   lab's snippet uses tabs):
   ```yaml
       - name: Run Azure Machine Learning training job
         run: az ml job create -f src/job.yml --stream --resource-group ${{vars.AZURE_RESOURCE_GROUP}} --workspace-name ${{vars.AZURE_WORKSPACE_NAME}}
   ```
   Claude checked both edits (diff, no tabs, valid YAML) before the push.
3. Committed and pushed to `main` (`443a39b`). Pushing doesn't run it: this
   workflow only has `workflow_dispatch`.
4. **Actions → "Manually trigger an Azure Machine Learning job" → Run
   workflow** → run `36669089137` (04:29:44 UTC).

| Step | Result |
|---|---|
| Set up job, Check out repo, Install az ml extension | ✅ |
| **Azure login** (`AZURE_CREDENTIALS`) | ✅ the service principal works |
| Run Azure Machine Learning training job | ❌ the job **Completed**, but the step failed (see section 3) |

The Azure ML job **`plucky_yogurt_9rv71w234s`** (`diabetes-train-command`,
experiment `diabetes-training`) ran 04:33:17 → 04:35:37 UTC on `aml-cluster`:
input `diabetes-data:1` (`@latest` resolved), `Regularization rate 0.01`,
Accuracy **0.774**, AUC **0.8483**, `ROC-Curve.png`. Its
**`created_by` = `a9bd6f2c-…`, the service principal's appId**: Azure
recorded GitHub, not me, as the submitter.

## 3. What broke and how we fixed it

- **The workflow failed even though training succeeded: an Azure CLI bug in
  `--stream`.** The step uploaded `src/` and submitted the job, then at
  04:35:33 (4 s before the job finished) crashed with
  `ERROR: Met error <class 'binascii.Error'>:Invalid base64-encoded string:
  number of data characters (97) cannot be 1 more than a multiple of 4`,
  exit code 1, having streamed none of the job's log lines. The runner
  installs **the latest `ml` extension, 2.45.0** (`az extension add -n ml -y`,
  unpinned). Checks:
  - `az ml job stream` on the **finished** job works with both **2.44.1** (my
    Mac) and **2.45.0** (installed into an isolated `AZURE_EXTENSION_DIR`).
  - So the bug is in **live** streaming of a running job, likely new in
    2.45.0 or intermittent. Not yet reproduced on demand.
  - Lesson: **an unpinned tool version in CI can break a workflow overnight.**
    A workflow that fails after the Azure job succeeds is a *false* failure;
    read the log before rerunning training.

## 4. Exam mapping

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

**Do these workflows launch Azure ML pipelines? No, command jobs.**
`manual-trigger-job.yml` (lab 06) and `train-dev.yml`/`train-prod.yml` (lab 07)
all run `az ml job create -f src/job.yml`, and `src/job.yml` is a **command
job** (`commandJob.schema.json`) running one script,
`train-model-parameters.py`. `deploy-prod.yml` runs an SDK deploy script,
not a job. Lab 04's pipeline only exists as notebook-generated files on the
Studio clone, not in this repo. The same `az ml job create -f <file>`
would submit a **pipeline** if the YAML were `type: pipeline`; the workflow
doesn't change.

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| What the workflow submits | 🧪 One **command job** (`src/job.yml`) | A **pipeline job** (`ml/pipelines/train_pipeline.yml`: prep → train → evaluate, registered components) | 📘 Command job for a single script; **pipeline job** for multi-step, reusable, versioned steps. Both via `az ml job create -f` |
| Quality gate | None; accuracy only printed (lab 07 posts it to the PR) | `evaluate` fails the pipeline below AUC 0.95, so nothing is registered | 📘 Required status checks on PRs; a gate before registering is 🛠 my addition |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check
