# Lab 07: Deploy and monitor a model

Source: [docs/07-deploy-monitor.md](../docs/07-deploy-monitor.md)

Microsoft Learn module: [Deploy and monitor a model in Azure Machine Learning](https://learn.microsoft.com/en-us/training/modules/deploy-model-github-actions/)
(module 7 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/), dated 2026-08-27).
Its exercise (`go.microsoft.com/fwlink/?LinkId=2378100`) links to this lab.
Units 2–5 and the 5-question assessment were read before starting.

Mechanics: **[end-to-end flow: architecture, flowchart, sequence diagrams](mechanics/end-to-end-flow.md)** · [GitHub Actions ↔ Azure ML](mechanics/github-actions-azureml.md) · [registries and environments](mechanics/registries-and-environments.md) · [job types](mechanics/job-types.md)

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

### 2.3 Pin the CLI in the lab 07 workflows (PR #2), re-enable the comment workflows (Claude)

- PR #2 (`fix/pin-azure-ml-cli`): `az extension add -n ml --version 2.44.1 -y` in
  `train-dev.yml`, `train-prod.yml`, `deploy-prod.yml` (the same 2.45.0
  `--stream` bug as lab 06). It had to be **merged before** using
  `/train-prod` and `/deploy-prod`, because `issue_comment` workflows run from
  `main`. Its check (the lab 06 workflow runs on every PR) was green: Accuracy
  0.774, AUC 0.8483 in the streamed log. Merged at 07:41:50 UTC (`7adbdf0`) on
  my "merge it".
- `gh workflow enable train-prod.yml` / `deploy-prod.yml`: both **active**
  again (disabled since the repo went public). Now safe: interaction limits
  (only I can comment) + the `prod` reviewer gate.

### 2.4 PR #3: dev training from the PR (Claude, on "do all of that for me")

On branch `feature/lab07-dev-training`:
- `src/job.yml` → `type: uri_folder`, `path: azureml:diabetes-dev-folder@latest`
- `train-dev.yml` → `pull_request` on `main` with `paths:
  ['src/train-model-parameters.py', 'src/job.yml']`
- `src/train-model-parameters.py` → default `--reg_rate` **0.01 → 0.05** (the
  lab's suggestion). ⚠ **It has no effect on these runs:** `job.yml` passes
  `--reg_rate ${{inputs.reg_rate}}` = **0.1** explicitly, and an argparse
  default only applies when no value is passed.

Opened **PR #3** → two runs started automatically: **"Train model in dev"**
(the `paths` filter matched) and lab 06's workflow (it runs on every PR).
Both green. The bot commented: **Dev evaluation metrics: Accuracy 0.774, AUC
0.8483**. The metrics came from the streamed log, which only works because
of PR #2's pin.

### 2.5 `/train-prod` (Claude, on "do it for me for prod")

1. `gh pr comment 3 --body "/train-prod"` → run `36686100623`
   ("Train model in prod (PR comment)", workflow file from `main`).
2. The run stopped at **`waiting`**: the `prod` environment's required
   reviewer. `…/pending_deployments` → env `prod`, reviewers `[medChiboub]`,
   `current_user_can_approve: true`.
3. **Approved** through the API (`POST …/actions/runs/<id>/pending_deployments`
   with `state: approved`, with a comment citing the dev metrics). GitHub
   records the approval as me. *In real life the point of this gate is a
   person reviewing the evidence; here I delegated it.*
4. Job **`diabetes-train-prod-36686100623`**: input
   **`diabetes-prod-folder:1`**, `created_by` = the service principal, ran
   07:56:16 → 07:58:39 UTC. Every step green (stream, `job download
   --output-name metrics_output`, parse `metrics.json`, comment).
5. The bot commented: **Prod evaluation metrics: Accuracy 0.774, AUC 0.8483**
   plus the job name and Studio link. **Identical to dev**, as expected: the
   two CSVs are byte-identical.

### Which model does `/deploy-prod` deploy? (verified)

**The committed `model/` folder**, untouched since the template's initial
commit: an MLflow model created **2023-02-15** (run `calm_garden_gzd94mfzcr`,
in a Microsoft workspace), scikit-learn **0.24.1** (cloudpickle), MLflow
**1.30**, Python **3.8**, signature 8 inputs → a boolean.

- `deploy_to_online_endpoint.py` passes an **unregistered**
  `Model(path="./model", type=mlflow_model)`, so Azure **registers it
  implicitly** while deploying, under a **content-hash name**:
  `c68e03c630c5…fc8f96:1` (`created_by` = the service principal, 08:08:29 UTC,
  description "MLflow diabetes classification model"). Deployment `blue` →
  `…/models/c68e03c6…/versions/1`.
- **None of our trained models could be deployed anyway:** the repo's
  `train-model-parameters.py` saves no model (no `autolog`/`log_model`; the lab
  02 `autolog` edit only exists on the Studio copy). `train-dev`/`train-prod`
  produce only metrics.
- **The workspace's model list** also shows **auto-generated entries from
  earlier jobs' MLflow outputs**: `azureml_coral_drawer_c6770sv3k6_<n>_output_mlflow_log_model_…`
  (AutoML, lab 01), `azureml_a84deb22…` (lab 01 autolog),
  `azureml_epic_king_…` (lab 02 autolog), `azureml_aa0f7853…_output_model_output`
  (lab 04 pipeline). None were deliberately registered with a real name.
- Why it matters: the lab's rollback ("Models → previous version → deploy")
  meets hash and auto names, not `diabetes-model:1/:2`. The 📘 answer (module
  unit 2): **register the MLflow model explicitly** from the job output,
  with a name and version, and deploy by `name:version`.

### 2.6 Change of plan: deploy our own model (my decision, 08:15 UTC)

The lab's `/deploy-prod` deploys the committed 2023 `model/`, and the
training jobs save no model, so retraining never changes what's served. I
chose to **deploy my own prod-trained model** instead ("our way": it's what
the module teaches and what makes the loop real). This goes beyond the lab.

1. **Stopped the lab's deployment:** cancelled run `36687608547`
   (`gh run cancel`, ended `cancelled`), then `az ml online-deployment delete -n
   blue` (it had been `Creating`; deletion waits for the half-built deployment
   to stop). **Endpoint kept** (`auth: key`); its traffic map still showed
   `"blue": 0` afterwards, a stale key.
2. **Merged PR #3** (`6802809`): its lab steps (dev training + `/train-prod`)
   were done.
3. **PR #4 `feature/deploy-own-model`** (6 files):
   - `train-model-parameters.py`: `--model_output` → `mlflow.sklearn.save_model`
     with a **signature from the original columns** + `input_example`, plus
     `azureml-ai-monitoring==1.0.0` and `azureml-contrib-services` (as in the
     committed model, for the data collector).
   - `job.yml`: output `model_output: {type: mlflow_model}`.
   - `train-prod.yml`: a **Register prod model** step: `az ml model create
     --name diabetes-model --type mlflow_model --path
     azureml://jobs/<job>/outputs/model_output`, tagged `training_job`, `pr`,
     `data`, `accuracy`, `auc`. The comment reports `diabetes-model:<N>`.
   - `deploy_to_online_endpoint.py` + `deploy-prod.yml`: deploy
     `diabetes-model:<latest>` (`models.get(label="latest")`) as deployment
     **`v<N>`**, **smoke-test it by invoking that deployment directly**, then
     traffic **100% to it, 0% to the deployments that actually exist**
     (built from `online_deployments.list`, not the traffic map, because of
     stale keys). The comment reports model, deployment, traffic and the smoke
     result.
   - `sample-request.json`: the lab's payload (the lab references it; it
     didn't exist).
4. **Tested locally before pushing:** trained on `data/diabetes-data`, loaded
   the saved model with `mlflow.pyfunc`, and predicted on the lab payload.
   **First try failed:** the signature inferred from `X_train` (a float array)
   typed every column `double`, and the lab's integer payload was rejected:
   `Incompatible input types for column Pregnancies. Can not safely convert
   int64 to float64`. Fixed by inferring from `df[FEATURES]`: integers →
   `long`, `BMI`/`DiabetesPedigree` → `double`, the same as the committed
   model. Retest predicted **`[1]`**.

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

### Dev vs. prod in this lab: logical, not physical

| | Dev | Prod | Really separate? |
|---|---|---|---|
| Azure workspace | `mlw-ai300-l…` | **the same** | ❌ |
| Compute | `aml-cluster` | **the same** | ❌ |
| Training data | `diabetes-dev-folder` | `diabetes-prod-folder` | ✅ a different asset (a byte-identical file) |
| GitHub environment | `dev` | `prod` | ✅ |
| `AZURE_CREDENTIALS` | `dev` env copy | `prod` env copy | ⚠ **the same service principal** |
| Approval | none | **me** (required reviewer) | ✅ the one real control |
| Workflows | `train-dev.yml` (auto on PRs) | `train-prod.yml`, `deploy-prod.yml` (comment + approval) | ✅ |
| Endpoint | none | `diabetes-endpoint-0533925c` | prod only |

The separation lives on the **GitHub side** (who triggers what, plus the
approval). On Azure, dev and prod share everything but a data asset's name,
so a dev run *could* read prod data or touch the endpoint. The 📘 fix is
**physical separation**: separate workspaces/subscriptions, **one identity
per environment** scoped to its own workspace, and a registry to promote
between them. That's lab 05's design (documented in the lab 05 file and
`infra/setup-prod-design.sh`) and what my production project runs.

### Why "prod" isn't lab 05's prod workspace

Three reasons, all by design:
- **Discovery:** every workflow takes the first `rg-ai300-l*` group and its
  `mlw-ai300-l*` workspace. Lab 05's `rg-ai300-prod-…`/`mlw-ai300-prod-…`
  doesn't match.
- **Access:** the service principal is Contributor on the lab 01 RG only.
- **The lab's words:** *"a single workspace and separate data assets to
  represent development and production"*. Lab 05's prod workspace also has no
  cluster, so `compute: azureml:aml-cluster` would fail there.

Using it for real (📘, and what my project does) takes: per-environment
`AZURE_RESOURCE_GROUP`/`AZURE_WORKSPACE_NAME` **environment variables**
instead of prefix discovery, **a separate prod identity** (OIDC) with a role
on the prod RG only, **compute in the prod workspace**, and **the registry**
to promote models or components. A possible optional extra after lab 07.

### What PR-triggered dev training does, and doesn't, prove

- **Runs only when a PR changes the training code** (`paths:` =
  `src/train-model-parameters.py`, `src/job.yml`). Lab 06's workflow has no
  filter and runs on every PR.
- **Proves:** the changed code runs **end to end** on real compute, with the
  real environment and data (the check fails if the job fails), and **shows**
  the new Accuracy/AUC on the PR.
- **Doesn't prove it improved:** there's no baseline and no threshold. The
  comment has only the new numbers, and the check is green even if accuracy
  drops. Proper versions:
  - an **absolute gate**: fail below a bar (my project: AUC < 0.95 fails the pipeline)
  - **champion vs. challenger**: promote only if it beats the current best
    (`MLOPS_CICD_CT.md` pattern B)
  - a **required status check**, so a failing PR can't merge
- Exam: PR training on dev data = **validation before merge**; "only merge if
  the model is at least as good" = **an evaluation gate + a required status
  check**.

## 3. What broke and how we fixed it

## 4. Exam mapping

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check
