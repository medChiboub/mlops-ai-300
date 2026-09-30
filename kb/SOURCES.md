# Sources and pre-flight notes, per lab

Read the lab's block **before** starting it. For each lab it lists what the
lab doc, the repo and the Azure checks already told us, plus where my
production project (`../MLOps_Project_Azure_ML`, "prod project" below)
already covers the same ground.

Checked on **2026-09-29** against this repo (the template copy of upstream
`mslearn-mlops`) and subscription *Cheboss Azure subscription 1*
(Pay-As-You-Go, canadaeast).

## Applies to every lab

- **Every lab doc starts with "provision + clone".** We skip both: the
  workspace from lab 01 (`mlw-ai300-l0533925c724d4c839e`) and the clone on its
  file share are reused. Each lab really starts at its own exercise section.
  Also skip every "Delete Azure resources" section until after lab 07.
- **The notebooks are saved with the *Python 3.8 - AzureML* kernel.** Always
  switch to **Python 3.10 - AzureML** (the lab says to "verify" it; in
  practice you have to change it).
- **The real quota is Azure ML's, not the VM quota.** Check it with
  `az ml compute list-usage -l canadaeast`, not `az vm list-usage` (which
  showed 0 used while the compute instance was running). canadaeast:

  | Pool | Limit | Used by |
  |---|---|---|
  | `standardDSv2Family` | **6** | compute instance (2) + `aml-cluster` up to 2×2 = **exactly 6** |
  | `standardDASv4Family` | 10 | lab 07's endpoint (`Standard_D2as_v4`, 2 cores) |
  | `standardESv3Family` | 20 | lab 07's monitoring (Spark runs only on ESv3 sizes) |
  | Low-priority cores | **0** | none possible: no spot/low-priority clusters |
  | Total dedicated | 20 | |

- **The curated environment `AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest`**
  is used by labs 02, 03, 06 and 07. It's listed in the workspace but **not in
  the `azureml` registry any more**, and `az ml environment show/list` on it
  fails with `System.Net.Http.HttpConnectionResponseContent`. That's the same
  error the prod project recorded for `@latest` label resolution in sweep jobs
  (`docs/AI-300.md`, "Other real gotchas"). **Risk: the first command job
  (lab 02) tells us whether it still resolves.** If it doesn't, a fix means
  changing lab code (the environment line), which is my call, not Claude's.
- **Your earlier notes on the same Microsoft Learn modules:**
  `../MLOps_Project_Azure_ML/docs/AI300_PREP/CERT_NOTES.md` has notes unit by
  unit, from a first pass on a Titanic dataset in another workspace. The
  module ↔ lab map is below. **Your debugging history:** `docs/SCENARIOS.md`
  (IAM/RBAC, quota, deployment/traffic, versioning, infra lifecycle, SDK
  quirks).

| Lab | Microsoft Learn module (CERT_NOTES section) |
|---|---|
| 01 | Module 1: Experiment with Azure ML (Units 1–8) |
| 02 | none directly; notebook → script → command job (Module 4 Unit 4 covers `job.yml`) |
| 03 | Module 2: Hyperparameter tuning (Units 1–6) |
| 04 | Module 3: Run pipelines (Units 1–5) |
| 05 | Module 6: Environments in GitHub Actions ("Real Production build … `05-plan-and-prepare`") |
| 06 | Module 4: Trigger jobs with GitHub Actions, and Module 5: trunk-based development |
| 07 | Module 7: Deploy a model with GitHub Actions ("Challenge 7 …", the full earlier run) |

---

## Lab 01: Experiment and evaluate models ✅ done

Cross-check against CERT_NOTES Module 1, after the fact:
- **AutoML dropped Titanic's `PassengerId` but kept our `PatientID`.**
  Hypothesis: `PassengerId` is 100% unique (891/891); `PatientID` has 41
  duplicates (9,959/10,000). So AutoML's ID detection may need *every* value
  to be unique. Not verified.
- The same `JobNotSupported` error when reading AutoML internals and bare
  MLflow runs through the jobs API.
- **The RAI dashboard shows up on a *registered* model** (Unit 7). Our
  AutoML's automatic `_RAI` run failed; the prod project's own RAI pipeline
  also got stuck (`docs/AI-300.md`).
- Unit 5 quirk: the module text shows `mlflow.set_tracking_uri = "..."`,
  which assigns instead of calling the function. Irrelevant on a compute
  instance, where the URI is preset.
- If you ever log MLflow runs **locally**: MLflow 3.x's logged-models API
  isn't supported by Azure ML's tracking server (404), so pin `mlflow<3`.

## Lab 02: Optimize model training

- **Doc/file name mismatch:** the doc says `Run script as command job.ipynb`;
  the file is **`Run script as a command job.ipynb`**.
- I already ran `Train classification model.ipynb` by mistake during lab 01
  (accuracy 0.774). Lab 02 runs it again, then **Export as → Python (.py)**.
- The doc warns about a possible `ImportError` for `libstdc++6` when running
  the exported script. It gives the fix (a PPA plus `apt-get upgrade`).
- `src/train-model-parameters.py` needs `--training_data`. Running it without
  that argument is *meant* to fail, as a teaching point.
- The command job uses the curated environment above, so this is the **first
  real test** of whether it still resolves.
- The job appears as `diabetes-train-script` in experiment `diabetes-training`.
  Look at the **Code** tab (the snapshot of `src/`) and `std_log.txt`.
- **Prod project:** `ml/components/{prep,train,evaluate}` + YAML, the same
  idea split into three components.

## Lab 03: Hyperparameter tuning

- **The sweep optimizes `training_accuracy_score`**, an autolog *training*
  metric (which lab 01 showed is optimistic: 0.7916 train vs. 0.7737 test).
  That's a lab shortcut 🧪. The docs-recommended answer is a metric measured
  on held-out data.
- `sampling_algorithm="grid"`, `max_total_trials=4`, `max_concurrent_trials=2`
  → **2 nodes**, the first job to use the whole cluster. The quota fits
  exactly (2 + 4 = 6), but only while nothing else uses DSv2.
- Environment `…@latest` + data `diabetes-data:1`. The prod project hit an SDK
  bug in **sweep jobs specifically** resolving `@latest`
  (`System.Net.Http.HttpConnectionResponseContent`) and fixed it by pinning
  versions. That's a real risk here.
- **Prod project:** `ml/experiments/sweep/` (grid over `max_depth`, optimizes
  AUC, best 0.9765). CERT_NOTES Module 2 covers search spaces, sampling and
  early termination in depth.

## Lab 04: Run pipelines

- The notebook writes `prep-data.py`, `train-model.py` and two component
  YAMLs, then `load_component(...)` → pipeline job, experiment
  `pipeline_diabetes`, data `diabetes-data:1` (exists).
- **After lab 04: stop the compute instance.** Labs 05–07 don't need it.
- **Prod project:** `ml/pipelines/train_pipeline.yml` (3 components, CLI YAML
  instead of the SDK) and `train_schedule.yml` (a weekly recurrence).
  CERT_NOTES Module 3.

## Lab 05: Plan and prepare (design)

- Mostly reading and planning, plus an **optional** script (ask first) that
  creates `rg-ai300-dev-*`, `rg-ai300-prod-*`, `rg-ai300-reg-*` and a registry.
  Those names don't match `rg-ai300-l*`, so the lab 06/07 workflows would
  still find only our workspace.
- Lab 05 points `diabetes-dev-folder` at `data/diabetes-data`; **lab 07 points
  it at `experimentation/data`.** We follow lab 07 (all these files are
  byte-identical anyway).
- `code setup.sh` needs Classic Cloud Shell. We're local, so any editor works.
- **Prod project:** `infra/main.bicep` + `infra/parameters/*.bicepparam`,
  `infra/registry.bicep`. `docs/AI300_PREP/MLOPS_CICD_CT.md` covers the two
  promotion patterns (retrain in prod vs. promote the artifact) and when a
  registry is really needed.

## Lab 06: Automate model training with GitHub Actions

- **We already have the repo** (`medChiboub/mlops-ai-300`, from the template).
  Skip "Create your GitHub repository from the template".
- **⚠ The YAML snippets in the doc are indented with TAB characters**
  (`on:`/`workflow_dispatch:`/`pull_request:` and the new
  `- name: Run Azure Machine Learning training job` step). YAML forbids tabs.
  Re-type the indentation with spaces. The existing `manual-trigger-job.yml`
  puts steps at **4 spaces** (`    - name:`), so the new step must match.
- `src/job.yml` still has placeholders: `type: <uri_file_or_uri_folder>`,
  `path: <azureml:data-asset-name@latest>`. Lab 06 sets `uri_file` +
  `azureml:diabetes-data@latest`.
- Secret: **repository**-level `AZURE_CREDENTIALS` (the service principal's
  JSON, Contributor on our RG). Variables: `AZURE_RESOURCE_GROUP`,
  `AZURE_WORKSPACE_NAME`.
- **Branch protection on a private repo** may need a paid plan. Try it; if
  GitHub shows an upgrade prompt, skip it and just learn what it does.
- The networking review (public access vs. private endpoints) is read-only.
  It's the lab's only coverage of the "restrict network access" skill (a gap
  in the prod project too).
- **Prod project:** OIDC instead of a secret (`docs/concepts/02-iam.md`,
  `docs/concepts/07-cicd-github-actions.md`), and
  `train-and-register.yml`. There's no PR-triggered training and no branch
  protection there, which is exactly what this lab adds.

## Lab 07: Deploy and monitor

Most of the known issues are in this lab. Read CERT_NOTES "Challenge 7" first.

- **Data assets:** add `diabetes-dev-folder` → `../experimentation/data` and
  `diabetes-prod-folder` → `../production/data` (both `uri_folder`) to the
  existing workspace.
- **`src/job.yml` must switch to `type: uri_folder`.** `train-dev.yml` and
  `train-prod.yml` only override the *path* (`--set inputs.training_data.path=…`),
  not the type. If lab 06's `uri_file` stays, a folder asset gets passed as a
  file.
- **GitHub environments `dev` and `prod`**, each with an `AZURE_CREDENTIALS`
  *environment* secret. The lab reuses **one service principal for both**
  (a lab shortcut: the environment name differs, the access doesn't).
- `train-dev.yml`'s `pull_request` trigger has a `paths:` filter. A PR only
  triggers it if it changes `src/train-model-parameters.py` or `src/job.yml`.
- **`/train-prod` and `/deploy-prod` match anywhere in the comment**
  (`contains(...)`), and the workflows check out `refs/pull/<N>/head` with prod
  credentials: the "pwn request" pattern (`MSLEARN-MLOPS.md`). It's OK on a
  private repo where only I can comment. Know it for the exam.
- **What gets deployed is the committed `model/` folder** (2023, Python 3.8,
  MLflow 1.30, sklearn 0.24.1), never the model the workflows trained.
  Retraining changes the PR comments, not the endpoint. Expect a slow image
  build. Its `conda.yaml` **already includes** `azureml-ai-monitoring` and
  `azureml-contrib-services`, the two missing packages that broke the
  earlier run.
- **Endpoint name:** the workflow creates `diabetes-endpoint-<first 8 chars
  of the suffix>` = `diabetes-endpoint-0533925c`. The rollback section says
  `diabetes-endpoint`; use the real name.
- **`sample-request.json` doesn't exist** in the repo. Use the JSON payload
  in the doc (8 features, no `PatientID`, which matches `model/MLmodel`'s
  signature).
- **If the deployment fails** with a generic `Liveness probe failed … 502`:
  run `az ml online-deployment get-logs` first. The real error is only in the
  container logs.
- **Rollback:** `Model(path="./model")` registers the model *implicitly*,
  under a name derived from a content hash, so "Models → previous version"
  won't look like the doc. You **can't delete a deployment that still has
  traffic**: set it to 0% first.
- **Monitoring:** needs a successful request *after* deployment (collection
  isn't retroactive). It runs on serverless Spark (ESv3, quota 20 here, not the
  earlier subscription's 0). There's a **1-day minimum lookback**, so the first
  run can only succeed about a day after traffic starts. The lab's no-code
  MLflow deployment auto-collects data; the prod project needed explicit
  `Collector` calls because it has a `score.py` (`docs/MONITORING.md`, "How
  the official MS Learn lab does this differently").
- **Out-of-box vs. advanced monitoring:** out-of-box compares production
  against *older production*, not against training data. Only advanced
  signals use training data as the reference (CERT_NOTES Challenge 7,
  section 7).
- **Prod project:** `deploy.yml`, `shift-traffic.yml`, `chatops.yml`,
  `ml/score/score.py`, `endpoints/monitor.dev.yml`, `docs/MONITORING.md`,
  `docs/CHATOPS.md`.

## Cleanup (after lab 07)

- Delete `rg-ai300-l0533925c724d4c839e` (plus any lab 05 extras).
- Delete the lab's **service principal and app registration** (it has a
  long-lived client secret).
- Stop or delete the monitor schedule if it outlives the resource group
  (it doesn't: it's inside the workspace).
- Keep this repo.
