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

### 2.4 Feature-based development: PR trigger, branch protection, PR (me + Claude)

1. **PR trigger** (Claude, at my request): `on:` in `manual-trigger-job.yml`
   became
   ```yaml
   on:
     workflow_dispatch:
     pull_request:
       branches:
         - main
   ```
   Committed and pushed to `main` (`db64fbf`); no run (a push isn't a trigger).
2. **Branch protection** (me, GitHub UI): Settings → Branches → **Add classic
   branch protection rule** → pattern `main` → **Require a pull request before
   merging** with **Require approvals unticked** (the classic dropdown only
   offers 1–6; unticking the box is how you get 0) → Create. Claude read it back
   through the API: require PR ✅, approvals **0**, required status checks
   **none**, admins **not** enforced (so admin can bypass), force pushes and
   deletion **blocked**. On this now-public repo the API went from `403
   Upgrade to GitHub Pro` (private) to working.
3. **Feature branch** (Claude): `feature/update-parameters`, `src/job.yml`
   `reg_rate: 0.01 → 0.1` (`f281c9e`), pushed the branch only.
4. **PR #1** (me): `feature/update-parameters → main` → the **`pull_request`
   trigger started run `36671001563` automatically**. Job
   `ashy_holiday_qxk8djl5xk` Completed (reg 0.1 → Accuracy 0.774, AUC 0.8483),
   but the step failed with the **same `--stream` error** → check `train` =
   FAILURE, PR state **UNSTABLE** but still **mergeable** (the check isn't
   required).
5. **Fix on the same branch** (my decision, option B): pinned the CLI
   extension, `az extension add -n ml --version 2.44.1 -y` (`99c37b8`). The
   push re-ran the PR check (`36681715090`): **✅ green**, and the log now
   shows the job's output (`Reading data...`, `Accuracy: 0.774`,
   `AUC: 0.8483…`, `Execution Summary`). PR state **CLEAN**.
6. **Merged** PR #1 at 07:18:32 UTC (merge commit `7afe772`; Claude on my "ok
   go"), deleted the branch. `main` now has `reg_rate: 0.1` + the pinned CLI.

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
  - **Reproduced on the PR run** (identical error, same 97 characters), so
    it's deterministic with 2.45.0, not a fluke.
  - **Fixed** by pinning `az extension add -n ml --version 2.44.1 -y`. The
    PR re-run went green, and the stream then **printed the training log**
    (with 2.45.0 it had printed nothing before crashing). ⚠ Lab 07's
    workflows (`train-dev.yml`, `train-prod.yml`, `deploy-prod.yml`) install
    the same unpinned extension, and `train-dev.yml` parses Accuracy/AUC
    **from the streamed log**, so they need the same pin.
- **Branch protection vs. my own kb pushes:** admins aren't enforced, so
  Claude's direct kb pushes to `main` show as *bypassing* the PR rule. That's
  allowed by the rule as set, and fine for a solo notes folder; code changes
  go through PRs.

## 4. Exam mapping

Domain 1: *Configure GitHub integration with Machine Learning to enable
secure access*, *Configure identity and access management*, *Manage source
control for ML projects by using Git*, *Restrict network access* (review
only). Domain 2: *Run model training scripts* (from CI).

- **What goes in Git:** scripts, job and component YAML, environment files,
  config. **Not in Git:** data (data assets / ADLS), trained models (the model
  registry), run outputs and logs (the job), **secrets** (GitHub secrets / Key
  Vault). Module assessment: a model binary in the repo is misplaced.
- **Trunk-based development:** short-lived feature branches → PR → `main`.
  **Branch protection or rulesets** (repo settings, not Actions): restrict
  direct pushes, require approvals, **require status checks** (named by the
  workflow's **job name**). Module assessment: a direct push broke `main` →
  **branch protection + PRs**; lint on every PR and block on failure → **a
  `pull_request` workflow + a required status check**.
- **Secrets vs. variables:** secrets are encrypted and masked
  (`AZURE_CREDENTIALS`); variables are plain config (`AZURE_RESOURCE_GROUP`).
  Environment secrets are narrower than repo secrets (lab 07).
- **Identity:** a service principal with a **least-privilege role at the
  narrowest scope** (RG or workspace). `az ad sp create-for-rbac --role
  contributor --scopes … --json-auth` → `azure/login` with `creds:`.
  **Prefer OIDC / workload identity federation**: a short-lived token per run,
  no stored secret to leak or rotate (module assessment). `create-for-rbac`
  creates an **app registration** (holds the secret) + a **service principal**
  (holds the roles) + a **role assignment**.
- **Triggers:** `pull_request` (validate), `push` (after merge),
  `workflow_dispatch` (manual), `schedule`, **`repository_dispatch`** (an
  external system; Azure Event Grid → Logic Apps/Functions → GitHub API,
  because Actions can't subscribe to Event Grid; module assessment).
- **Submitting from CI:** `az ml job create -f <yaml> --stream` (command or
  pipeline job; the YAML decides). If the job fails, the step fails, and a
  required check blocks the merge.
- **Network:** GitHub-hosted runners need a public workspace. Private
  endpoints + VNet → **self-hosted runners**.

**What the Microsoft Learn module says, checked against our run**

| Module says | Our run | Take-away |
|---|---|---|
| Prefer **OIDC** over service-principal client secrets (unit 5) | The lab uses a client secret; the CLI even warns `--sdk-auth` is deprecated | 🧪 the lab's shortcut; 📘 OIDC is the answer |
| Validate PRs with **linting and unit tests** as required checks (unit 4) | The lab validates by *running training*; no lint or tests, no required check | Tests are in `archive/` (the old lab); the gate here is a training run |
| A workflow step waits for the job; job fails → workflow fails → the merge is blocked if required (unit 6) | The job **succeeded** but the workflow **failed** (CLI bug) | False failures exist; pin tool versions |
| Git tracking: Azure ML records repo, branch and commit when you submit from a Git repo (unit 5) | Jobs submitted from the runner's checkout | ▢ check a job's Git properties in lab 07 |

*All module units read (1–6 theory, exercise → this lab, assessment,
summary), dated 2026-08-27.*

**Module assessment**, five questions:
1. Misplaced in the repo → **the trained model binary**.
2. A direct push broke `main` → **a branch protection rule blocking direct pushes + a PR process**.
3. Lint on every PR, block the merge on failure → **a `pull_request` workflow + branch protection requiring that status check**.
4. Main benefit of OIDC over client secrets → **short-lived tokens at runtime instead of a stored long-lived credential**.
5. Why an intermediary for Event Grid → **Actions can't subscribe to Event Grid; the intermediary sends `repository_dispatch`**.

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

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Azure login | 🧪 A service-principal **client secret** in `AZURE_CREDENTIALS` (valid 1 year) | **OIDC** federated credentials, no stored secret | 📘 **Workload identity federation (OIDC)** |
| Identity scope | Contributor on one resource group ✅ | One app, federated per GitHub Environment, RBAC per RG | 📘 Least privilege, narrowest scope, ideally one identity per environment |
| When training runs | `pull_request` to `main` + manual | Push to `main` (after merge) + manual | 📘 `pull_request` to validate, `push` to train/register after merge; both are standard |
| Branch protection | Require PR, 0 approvals, no required checks (solo repo) | None (the gap `MSLEARN-MLOPS.md` flags) | 📘 Require PR + reviews + **required status checks** |
| Tool versions in CI | 🧪 `az extension add -n ml` unpinned (broke on 2.45.0); pinned to 2.44.1 by us | Pinned | 📘 Pin versions for reproducible CI |
| Validation | A full training run on every PR | Pipeline + AUC gate | 📘 Fast lint/unit tests as required checks; heavier training as its own gate |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> <code>az ad sp create-for-rbac --role contributor --scopes &lt;RG&gt; --json-auth</code> creates what?<br><br>A) Only a GitHub secret<br>B) An app registration (holding a client secret), its service principal, and a Contributor role assignment on the resource group<br>C) A managed identity on the workspace<br>D) An OIDC federated credential</summary>

> **✅ Answer: B.** Deleting the resource group doesn't delete the app registration or its secret, so clean it up separately.
</details>

---

<details>
<summary><strong>2.</strong> What's the main security advantage of OIDC (workload identity federation) over <code>AZURE_CREDENTIALS</code>?<br><br>A) It picks the minimum role automatically<br>B) GitHub gets a short-lived token per run; there's no long-lived secret stored that could leak<br>C) Secrets move to Key Vault<br>D) It removes the need for role assignments</summary>

> **✅ Answer: B.** The module assessment's question. Roles are still needed.
</details>

---

<details>
<summary><strong>3.</strong> You want training to run on every PR into <code>main</code> and the merge blocked if it fails. What two things do you need?<br><br>A) A <code>push</code> trigger and a required reviewer<br>B) A workflow with <code>on: pull_request: branches: [main]</code> and a branch protection rule that <strong>requires that workflow's status check</strong><br>C) A schedule and an environment<br>D) <code>workflow_dispatch</code> and CODEOWNERS</summary>

> **✅ Answer: B.** We set the trigger and "require PR", but not the required check (the CLI bug would have blocked the merge). The check is named by the workflow's <strong>job name</strong> (<code>train</code>).
</details>

---

<details>
<summary><strong>4.</strong> The Azure ML job shows <em>Completed</em>, but the GitHub step fails with <code>binascii.Error: Invalid base64-encoded string</code> right as the job ends. What's going on?<br><br>A) Training failed<br>B) Wrong credentials<br>C) A client-side tool failure (here: <code>--stream</code> in the unpinned <code>ml</code> extension 2.45.0), a false failure. Read the log; pin the version<br>D) The data asset is missing</summary>

> **✅ Answer: C.** It reproduced twice; pinning 2.44.1 turned it green and the stream printed the training log.
</details>

---

<details>
<summary><strong>5.</strong> Which belongs in GitHub <strong>variables</strong> rather than secrets?<br><br>A) The service-principal JSON<br>B) The resource group and workspace names<br>C) A storage account key<br>D) A client secret</summary>

> **✅ Answer: B.** Identifiers are config; credentials are secrets.
</details>

---

<details>
<summary><strong>6.</strong> Your workspace has public network access disabled and uses private endpoints. GitHub-hosted runners can't reach it. What do you use?<br><br>A) A bigger runner<br>B) Self-hosted runners inside the virtual network (or one peered to it)<br>C) OIDC<br>D) A repository_dispatch trigger</summary>

> **✅ Answer: B.** GitHub-hosted runners come from the public internet. Ours works because public access is enabled.
</details>

---

<details>
<summary><strong>7.</strong> New data landing in storage should start the retraining workflow. How?<br><br>A) A <code>pull_request</code> trigger<br>B) Event Grid → an intermediary (Logic App / Function) → GitHub REST API → <code>repository_dispatch</code><br>C) GitHub subscribes to Event Grid directly<br>D) A branch protection rule</summary>

> **✅ Answer: B.** Actions can't subscribe to Event Grid.
</details>

---

<details>
<summary><strong>8.</strong> In lab 06, which of these submitted the Azure ML job for PR #1?<br><br>A) Me, from the Studio notebook<br>B) The compute instance<br>C) The service principal <code>sp-mslearn-mlops-github</code>, from the GitHub-hosted runner (the job's <code>created_by</code> is its appId)<br>D) The workspace's managed identity</summary>

> **✅ Answer: C.** The same appId (<code>a9bd6f2c-…</code>) showed as <code>created_by</code> on every workflow-submitted job.
</details>
