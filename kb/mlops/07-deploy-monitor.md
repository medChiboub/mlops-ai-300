# Lab 07: Deploy and monitor a model

Source: [docs/07-deploy-monitor.md](../../docs/07-deploy-monitor.md)

Microsoft Learn module: [Deploy and monitor a model in Azure Machine Learning](https://learn.microsoft.com/en-us/training/modules/deploy-model-github-actions/)
(module 7 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/), dated 2026-08-27).
Its exercise (`go.microsoft.com/fwlink/?LinkId=2378100`) links to this lab.
Units 2–5 and the 5-question assessment were read before starting.

Mechanics: **[end-to-end flow: architecture, flowchart, sequence diagrams](mechanics/end-to-end-flow.md)** · [monitoring](mechanics/monitoring.md) · [three environments](mechanics/three-environments.md) · [GitHub Actions ↔ Azure ML](mechanics/github-actions-azureml.md) · [registries and environments](mechanics/registries-and-environments.md) · [job types](mechanics/job-types.md)

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
5. **PR #4 checks green** (train-dev + the lab 06 workflow). The dev job
   `diabetes-train-dev-36688899562` saved a full MLflow model under
   `azureml/<job>/model_output/` (`MLmodel`, `model.pkl`, `conda.yaml`,
   `input_example.json`, `python_env.yaml`, `requirements.txt`). Azure
   **auto-listed** it as `azureml_diabetes-train-dev-36688899562_output_model_output`,
   an automatic entry for an `mlflow_model` job output, **not** a
   `diabetes-model` version. Only `/train-prod` registers deliberately.
   ("Approved" here means I approved *running* prod training; there's no
   metric gate before registration yet.)
6. **Quality gate added** (my decision: "we keep a standard before
   registration"), commit `e15a2f8` on PR #4: a new `train-prod.yml` step,
   **"Quality gate before registration"** (`MIN_AUC: "0.80"`), between "Extract
   prod metrics" and "Register prod model". If prod AUC < 0.80 → `::error::…
   the model is not registered`, exit 1, so registration and the comment are
   skipped. Tested the comparison locally: 0.8483 → pass, 0.79 → fail. The PR
   comment now says "Quality gate passed: AUC ≥ 0.80".
   - Registration now means **"from a prod run I approved *and* it met the
     standard"**. A champion/challenger version would compare with the
     latest version's `auc` tag instead of a fixed bar.
   - GitHub nuance seen here: this commit only changed `train-prod.yml`, yet
     **`train-dev` re-ran**. For `pull_request` events, the `paths` filter looks
     at the **whole PR diff vs. the base**, not just the new commit.
7. **Deploy *this PR's* version, not "latest"** (my decision, after Claude's
   review of the approach), commit `14c56a9`: `deploy-prod.yml` passes
   `--pr-number ${{ github.event.issue.number }}`. The script picks the newest
   `diabetes-model` version whose tag `pr` equals that number (archived
   versions excluded), or stops with *"No diabetes-model version is registered
   for PR #N. Run /train-prod on this PR first."* An explicit `--model-version`
   still wins; no PR number falls back to `latest`. Unit-tested locally with
   a fake client (5/5 pass: PR 4 → v3 even though v4 from PR 5 is newer).
   Why: with "latest", two PRs running `/train-prod` could make one PR deploy
   the other's model.

8. **It worked end to end:** merged PR #4 (`6f4168d`), then `/train-prod` on
   PR #4 (run `36691974475`, approved) → job `diabetes-train-prod-36691974475`
   → **Quality gate passed** → **registered `diabetes-model:1`** with tags
   `pr=4`, `accuracy=0.774`, `auc=0.8483…`, `data=diabetes-prod-folder`,
   `training_job=…`.
9. **Then I reverted to the lab's original flow** ("this is getting too
   complicated; keeping the lab's original approach doesn't hurt"). **PR #5**
   reverted PR #4's merge (`429c033`); `main`'s code is identical to before PR #4
   (the lab's PR #3 changes + the CLI pins). `diabetes-model:1` stays
   registered (harmless; a candidate for the lab's final "archive" step). The
   design and its review below remain the documented "better way".

**Review of our approach (known limits, documented rather than fixed):**
- a **fixed AUC bar** (0.80) lets a regression from 0.848 to 0.81 pass;
  **champion vs. challenger** (compare with the latest version's `auc` tag)
  would be stronger
- an **instant 0 → 100% cutover** after one smoke request, which proves the
  model *answers*, not that it answers *well*; the module's pattern shifts
  10% first
- **old deployments at 0% still cost** about $2.57/day each; keep only the
  previous one
- the structural lab limits remain: one workspace, one identity, PR code with
  prod credentials, identical dev/prod data
- vs. my project: pattern A (train once in dev, promote the same artifact) vs.
  ours, pattern B (retrain in prod behind human gates). Both are valid; B
  fits when prod data can't leave prod.
- **The deepest flaw (in the lab and in ours): prod runs *unmerged* PR code.**
  `/train-prod` and `/deploy-prod` check out `refs/pull/<N>/head`, so a model can
  reach users before its code is merged or reviewed. And retraining in prod
  buys nothing here (same workspace, same file).

**How I'd build it for real (📘):** merge first → train from `main` in a
**dev** workspace with an **evaluation gate** → **register** the model (tagged
with the commit) → publish it to a **registry** → the **prod** workspace, with
its **own OIDC identity**, deploys **that same version** behind an
**environment approval** → **gradual rollout** (0% → smoke test → 10% →
monitor → 100%) → rollback = a traffic change. Never PR code with prod
credentials. This is essentially my production project's design.

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

### 2.7 `/deploy-prod` the lab's way (PR #3, 2026-09-30)

After PR #4 (our own model behind an AUC gate) was reverted by PR #5, I
commented `/deploy-prod` on PR #3 and approved the `prod` gate. Run
`36692329751` succeeded in **about 8.5 min** (08:51 → 08:59 UTC):
endpoint `diabetes-endpoint-0533925c` (key auth), deployment **`blue`**
(Standard_D2as_v4 × 1, `DataCollector(model_inputs, model_outputs)`) with
the **committed 2023 `model/` folder**, traffic **`{"blue": 100}`**. The
bot commented the endpoint and deployment names on the PR. The 2023 model
(Python 3.8, MLflow 1.30, scikit-learn 0.24.1) built fine. Azure created
its Azure ML environment from the model's `conda.yaml` and built the image
once (see [three environments](mechanics/three-environments.md)).

### 2.8 Test the endpoint and check data collection

- My **Studio Test tab** request never reached the deployment: its logs
  showed only health probes, with no `POST /score`.
- The same 8-feature payload through `az ml online-endpoint invoke`
  returned **`[1]`** (0/1, even though the signature says boolean) in
  12.9 ms.
- About 2 s later, the collector had written
  `modelDataCollector/diabetes-endpoint-0533925c/blue/{model_inputs,model_outputs}/2026/09/30/09/<id>.jsonl`:
  CloudEvents lines with the **8 feature columns** (no PatientID or
  Diabetic), an output column named `"0"`, and a shared `correlationid`.
- 200 more requests from the held-out test CSV (`infra/send-traffic.py
  baseline`): 200 × HTTP 200, appended to the same hourly file (201 lines).

### 2.9 Configure model monitoring (Studio) and why it never ran

- **Created in Studio → Monitoring → Add:** schedule `blue-fkfvn`, data
  drift only (the 3 pre-added signals deleted; the red feature-attribution
  one blocked **Next**), production `…-blue-model_inputs:1` with a
  7-day lookback, reference `diabetes-training:1` (MLTable) with target
  `Diabetic`, Top N 10, NWD/JSD at 0.1, daily at **04:00 UTC**, E4s_v3.
  Studio's "Next run" said a day later than the stored trigger (unexplained).
- **3 manual runs (`az ml schedule trigger`) all failed:** every Spark step
  sat "NotStarted" for about 4 min, then `UserError: The long operation status
  is Failed` (`commonjobprovider`), with no logs.
- **Ruled out, one test at a time:** the data and config (nothing ran far
  enough to read them), a transient issue (retry failed), `Microsoft.Synapse`
  registration (registered, still failed), size and regional quota (a
  **minimal standalone Spark job** failed too, with 14 vCPUs free), the
  region (**the same job failed in a temporary Canada Central workspace**),
  and visible quota (no Spark entry among 64 Azure ML quotas).
- **Conclusion:** serverless Spark is blocked for this **subscription**. Most
  likely a hidden serverless quota that only Azure Support can see. On Basic
  support, there's no form for it. I stopped there.
- Full trace: [monitoring mechanics](mechanics/monitoring.md#traps-why-completed-or-failed-can-mislead)
  and [TIMELINE](TIMELINE.md).

### 2.10 Stop and clean up

- **2026-10-01:** I ended monitoring: monitor deleted, traffic → 0,
  deployment `blue` deleted. The scheduled "shifted traffic" workflow then
  hit 300 × 404 (and reported green: a script bug, since fixed). The
  workflow was disabled.
- **Not done:** the lab's "simulate drift → retrain PR" and the optional
  rollback deployment. Both need the endpoint and a working monitor. The
  rollback mechanics are in the exam mapping below.
- **Resource group** `rg-ai300-l0533925c724d4c839e` deleted (by 2026-11-01).
- **2026-11-09:** app registration `sp-mslearn-mlops-github` deleted, then
  purged from Entra's 30-day recycle bin (its 2 secrets were valid until
  2027-09). GitHub: the 3 `AZURE_CREDENTIALS` copies, both variables, and the
  `dev`/`prod` environments deleted. All lab workflows disabled; the
  traffic workflow file removed. The repo stays.

## 3. What broke and how we fixed it

- **The lab deploys a model that training never produced.**
  `deploy_to_online_endpoint.py` registers the committed 2023 `model/`
  folder, so `/train-prod` changes the PR comment, not the endpoint. We
  proved our own design (register `diabetes-model:1` behind AUC ≥ 0.80,
  deploy that version) in PR #4, then reverted to the lab's flow (PR #5).
  See 2.6.
- **The Studio Test tab didn't send anything.** The deployment logs
  (`POST /score` missing) show it; the CLI request worked. **Lesson:** "I
  clicked Test" isn't evidence. The deployment log is.
- **Azure ML monitoring never ran: serverless Spark is blocked for this
  subscription** (2.9). Not fixable on Basic support. Monitoring's
  configuration was completed as the lab asks; its first-run review wasn't.
- **The local CLI can't read Studio-made monitors:** `az ml schedule
  show/list` fails on `ModelInputs` casing. `az rest` on the schedule worked,
  and `trigger`, `disable` and `delete` work despite the warning.
- **My helper reported success on total failure:** 300 × 404 → green.
  Fixed: the script now exits non-zero when no request returns 200.
- **The PR for a helper workflow triggered training:** lab 06's
  `manual-trigger-job.yml` runs on every PR into `main`.

## 4. Exam mapping

Domain 2: *Deploy real-time or batch endpoints* (real-time), *Test and
troubleshoot endpoints*, *Implement progressive rollout and safe rollback*,
*Detect and analyze data drift*, *Monitor performance metrics in
production*, *Configure retraining or alert triggers*, *Register an MLflow
model* (implicitly). Domain 1: *Configure GitHub integration* (environments,
required reviewers), *Manage source control* (PR flow).

- **Managed online endpoint = endpoint + deployments.** The endpoint holds
  the URI, auth (key or token) and the **traffic split**. Each deployment
  holds a model, environment, VM size and instance count. Quota is
  `ceil(1.2 × instances) × cores` (a 20% upgrade reserve): our 1 × D2as_v4
  reserved 4 vCPUs.
- **No-code MLflow deployment:** the MLflow model's metadata (`MLmodel`,
  `conda.yaml`, signature) lets Azure generate the scoring script and the
  environment. A custom model needs `score.py` (`init()`/`run()`) and an
  environment. Module assessment: what enables deploying without a scoring
  script → **the MLflow model's metadata**.
- **Safe rollout and rollback:** a new deployment beside the old one → a
  small traffic share (or `mirror_traffic`, a shadow copy with no responses
  returned) → shift traffic → delete the old one. **Rollback = send traffic
  back to the previous deployment first**, then investigate. Changing
  traffic is instant, with no downtime. Module assessment: a new model
  misbehaves → **route traffic back to the previous deployment, then
  investigate**.
- **Gates:** a `prod` **GitHub environment with a required reviewer**
  holds the deploy job and its secrets until someone approves. Module
  assessment: who approves production deployment → **a protected
  environment with required reviewers**.
- **Data collection** is set **on the deployment**. Automatic for a
  no-code MLflow model; a custom `score.py` needs the `Collector` SDK
  (`azureml-ai-monitoring`). Data lands as hourly JSONL in the default
  datastore. The collected inputs are what the model *receives*.
- **Model monitoring:** a **schedule** running signals on **serverless
  Spark**. **Out-of-box** (reference = recent past production; data drift,
  prediction drift, data quality; smart defaults) vs. **advanced**
  (reference = **training data** for drift and quality, validation data for
  prediction drift; feature importance needs a **target column**). Alerts
  email the monitor's creator by default. Module assessment: drift detected
  → **investigate and consider retraining** (a human decision, not
  automatic).
- **Troubleshooting a deployment:** `az ml online-deployment get-logs`
  (the container log), the provisioning state, and the Test tab vs. a
  CLI/REST call.

**Module assessment**, five questions:
1. A real-time prediction service → **a (managed) online endpoint**.
2. What lets you deploy without a scoring script → **the MLflow model's metadata (signature and environment)**.
3. A new deployment misbehaves → **route traffic back to the previous deployment, then investigate**.
4. Require approval before production → **a protected `prod` environment with a required reviewer**.
5. The monitor detects drift → **investigate, then consider retraining**.

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

| Topic | Lab 07 | 📘 Microsoft recommendation | 🛠 My production project |
|---|---|---|---|
| What gets deployed | 🧪 The committed 2023 `model/` folder, never the model training just produced | Deploy the **registered** model version that passed evaluation | The registered model version promoted through the registry |
| Promotion | Git only: the same `job.yml` reruns on "prod" data | A registry: promote the model (A) or the pipeline (B) | Pattern A: dev → `mlreg-diabetes` → staging/prod |
| Dev vs. prod | 🧪 One workspace; a data asset + a GitHub environment | Separate workspaces (and subscriptions) per stage | Separate RGs per stage (Bicep) |
| Identity | 🧪 One service principal with a client secret for repo, dev and prod | OIDC, one identity per stage, scoped to the stage | OIDC |
| Prod gate | `prod` environment with a required reviewer (on PR code, before merge) | Required reviewer **plus** deploy from `main` only (deployment branch policy) | Gates on `main` |
| Rollout | 🧪 Traffic straight to 100% | Blue/green: a small share or mirror first, then shift | Staged rollout |
| Data collection | 📘 Automatic (no-code MLflow) | Automatic for MLflow; `Collector` SDK for a custom `score.py` | `Collector` SDK in `score.py` |
| Monitor | 🧪 Studio clicks, nothing in Git; advanced reference = training data | Versioned YAML (`az ml schedule create`); training data as the drift reference | YAML in Git; out-of-box reference (a known gap) |
| Retraining | Simulated: change `--reg_rate` in a PR | A human decision on a drift signal; optionally an automated trigger | Manual |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> In lab 07, after <code>/train-prod</code> trains on prod data, which model does <code>/deploy-prod</code> deploy?<br><br>A) The model trained by <code>/train-prod</code><br>B) The latest registered version of <code>diabetes-model</code><br>C) The committed 2023 <code>model/</code> folder, registered implicitly with a hash name<br>D) The best AutoML model from lab 01</summary>

> **✅ Answer: C.** The deploy script builds <code>Model(path="./model")</code>. Training changes the PR comment, not the endpoint. 📘 Deploy the registered version that passed evaluation.
</details>

---

<details>
<summary><strong>2.</strong> What lets you deploy an MLflow model to a managed online endpoint without a scoring script or environment?<br><br>A) The <code>DataCollector</code><br>B) The MLflow model's metadata: <code>MLmodel</code>, signature and <code>conda.yaml</code><br>C) A curated environment<br>D) The endpoint's key auth</summary>

> **✅ Answer: B.** Azure generated <code>mlflow_score_script.py</code> and built an environment from <code>conda.yaml</code>, adding <code>azureml-inference-server-http</code>.
</details>

---

<details>
<summary><strong>3.</strong> A new deployment <code>green</code> starts returning bad predictions. What's the first step?<br><br>A) Delete the endpoint<br>B) Retrain immediately<br>C) Update the endpoint's traffic back to the previous deployment (<code>blue=100, green=0</code>), then investigate<br>D) Scale <code>green</code> to more instances</summary>

> **✅ Answer: C.** Traffic changes are instant and need no redeploy. Keep <code>green</code> for investigation; delete it later to stop its cost.
</details>

---

<details>
<summary><strong>4.</strong> Data collection is enabled on an MLflow no-code deployment. Where does a request's input end up?<br><br>A) Application Insights only<br>B) The workspace's default blob datastore, under <code>modelDataCollector/&lt;endpoint&gt;/&lt;deployment&gt;/model_inputs/YYYY/MM/DD/HH/*.jsonl</code><br>C) A registered data asset you must create first<br>D) Nowhere until a monitor exists</summary>

> **✅ Answer: B.** Seen 2 s after our request. Azure also auto-registered <code>…-model_inputs</code>/<code>…-model_outputs</code> data assets. Collection doesn't need a monitor.
</details>

---

<details>
<summary><strong>5.</strong> You want drift measured against what the model was trained on, with feature importance. What do you configure?<br><br>A) Out-of-box monitoring<br>B) Advanced monitoring: reference data = the training data asset, plus its target column<br>C) A prediction drift signal on model outputs<br>D) A shorter lookback window</summary>

> **✅ Answer: B.** Out-of-box compares with recent past production, so it can't see slow drift away from training.
</details>

---

<details>
<summary><strong>6.</strong> Every model monitoring step fails after about 4 minutes in "NotStarted" with <code>The long operation status is Failed</code>, and a minimal standalone Spark job fails the same way. Where's the problem?<br><br>A) The monitor's reference data<br>B) The lookback window<br>C) Serverless Spark itself (capacity or a quota for the subscription), not the monitor<br>D) The endpoint's traffic split</summary>

> **✅ Answer: C.** Monitoring runs only on serverless Spark (or an attached Synapse pool). Isolate the layer: if a trivial Spark job fails too, the monitor configuration isn't the cause.
</details>

---

<details>
<summary><strong>7.</strong> How do you make sure nobody deploys to production without approval in a GitHub Actions flow?<br><br>A) Branch protection on <code>main</code> only<br>B) A <code>prod</code> GitHub environment with required reviewers on the deploy job<br>C) A repository secret<br>D) A <code>workflow_dispatch</code> trigger</summary>

> **✅ Answer: B.** The job waits and gets no environment secrets until approved. 📘 Add a deployment branch policy (<code>main</code> only) and OIDC scoped to the environment.
</details>
