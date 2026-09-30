# AI-300 labs: knowledge base

My personal gist of the [MicrosoftLearning/mslearn-mlops](https://github.com/MicrosoftLearning/mslearn-mlops)
labs, redone from scratch in order, the Microsoft Learn way. Each file records
what I actually ran, what broke, how it maps to the AI-300 skills measured,
and how my production project (`../MLOps_Project_Azure_ML`) does the same
thing differently.

**Versions checked (2026-09-29):**
- Lab code and docs: identical to upstream `MicrosoftLearning/mslearn-mlops`
  commit [`87482bc`](https://github.com/MicrosoftLearning/mslearn-mlops/tree/87482bc76b9ffa665e6ce6b76746d31e7a164b01)
  (2026-06-30, still the latest).
- Theory: the Microsoft Learn learning path *Operationalize machine learning
  models (MLOps)*, modules dated **2026-08-27**. Each module's exercise unit
  links to the same `microsoftlearning.github.io/mslearn-mlops/docs/0N-….html`
  page these docs build. Re-check before each lab.

**Environment:** one workspace provisioned in lab 01 (canadaeast, `rg-ai300-l*` /
`mlw-ai300-l*`), reused for every lab, deleted after lab 07.

**[TIMELINE.md](TIMELINE.md):** every step across all labs, in order, with who
did it and why.

**[Diagrams: end-to-end flow](mechanics/end-to-end-flow.md):** architecture, the whole dev → prod → monitor loop, and a sequence diagram per workflow (labs 06–07).

**[mechanics/](mechanics/README.md):** what Azure actually does underneath, one
file per concept (workspace and storage, compute, data assets, AutoML, …).

| Lab | File | What I learned |
|---|---|---|
| 01 | [Experiment and evaluate models](01-experiment-evaluate-models.md) | AutoML found a VotingEnsemble at 0.953 accuracy (vs. 0.774 for hand-made LogisticRegression) in about 11 min on 1 node, but kept `PatientID` as a feature with every guardrail green. MLflow autolog reports *training* metrics, and saving a file isn't logging it |
| 02 | [Optimize model training](02-optimize-model-training.md) | A Studio export is just the cells pasted into one file; the refactored script takes arguments. A command job records code snapshot + data + environment + logs, which a terminal run doesn't (that one went to `Default`). The same code gave a different AUC in the job because the environment pins scikit-learn 1.0. Autolog adds 15 params, `training_*` metrics and the `model/` folder |
| 03 | [Hyperparameter tuning](03-hyperparameter-tuning.md) | A sweep = the same command job once per value (3 trials for 3 grid values, even with a limit of 4). The script must log the metric under the exact `primary_metric` name, and a name like `training_accuracy_score` can hide a test metric. 0.01 and 0.1 tied at 0.774, so the metric choice decides the winner. Warm nodes run trials in about 17 s vs. about 2 min cold |
| 04 | [Run pipelines](04-run-pipelines.md) | Component = metadata + interface + command/code/environment; the pipeline wires output → input, so order comes from the data dependency (train didn't exist until prep finished). Loaded components stay anonymous (`az ml component list` was empty). Outputs land in `workspaceblobstore/azureml/<run>/<output>/`. The lab never schedules, although the module does |
| 05 | [Plan and prepare](05-plan-and-prepare.md) | Dev and prod workspaces + a shared registry. The lab's literal design script would have created a second `rg-ai300-l*` group (breaking labs 06–07), and Microsoft's reference script can't create its registry (a 35-character name, over the limit) yet reports success (no `set -e`). A registry's Premium ACR costs $1.67/day. It carries models (pattern A) or components + environments (pattern B, retrain in prod) |
| 06 | [Automate model training](06-automate-model-training.md) | `create-for-rbac` = app registration + service principal + role; its JSON → `AZURE_CREDENTIALS`, and the job's `created_by` is the SP. A `pull_request` trigger + branch protection make the PR the gate. The workflow went red while training succeeded: an unpinned `ml` 2.45.0 `--stream` bug, reproduced twice, fixed by pinning 2.44.1. OIDC is the recommended answer over the lab's client secret |
| 07 | [Deploy and monitor](07-deploy-monitor.md) | _in progress_ |

## Deviations from the canonical labs

Everything not listed here follows the Microsoft Learn labs as written.

| Deviation | Why | Changes what's learned? |
|---|---|---|
| Provisioned from my Mac (a patched copy of `setup.sh`: `uuidgen`, bash), not Cloud Shell; region pinned to canadaeast | `setup.sh` is Linux-only; my region choice | No: the same `az` commands |
| One workspace reused for labs 01–07 (each lab's provision/delete skipped) | Cost and time; my decision | No |
| Lab 04: scheduling documented, not run | The module covers it; the lab doesn't | No |
| Lab 05: optional multi-environment script run; its registry name fixed (35 → 32 chars); resources deleted during lab 07 | My choice; Microsoft's script can't create its registry | Adds a real bug lesson |
| Repo made public, interaction limits on, comment workflows disabled until lab 07 | Branch protection/reviewers are paid on private repos; safety on a public repo | Enables what the labs expect |
| Lab 06 YAML snippets: tabs → spaces | The doc's snippets break YAML | No: a doc bug |
| Azure ML CLI pinned to 2.44.1 in all 4 workflows | 2.45.0 `--stream` crashes after the job succeeds | No: without it the lab's workflows fail |
| Secrets piped from the CLI (never shown); env secrets from a 2nd client secret on the same service principal | Security | No: the same result |
| `prod` required reviewer on (optional in the lab) | Public repo; it's the module's point | Adds what the module teaches |
| Lab 07: endpoint tested with `az ml online-endpoint invoke` (my Studio Test request never arrived); monitor traffic sent with `infra/send-traffic.py` (200 baseline rows, then a shifted batch sent unattended by `.github/workflows/send-monitor-traffic.yml`, a one-time schedule on Oct 1 at 18:17 UTC), not only the Test tab | A handful of Test tab calls can't give a drift score a meaningful sample | Adds a real drift result; the lab only sets the monitor up |
| Lab 07 monitor: data drift only (the 3 pre-added signals deleted), lookback 7 days | The others need days of past production traffic; 7 days keeps one batch in the window | No: the lab asks for data drift |
| Some UI steps done by Claude at my request | Speed | Only who clicked |
| PR #4 ("deploy our own registered model") built, then reverted by PR #5 | Tried the real-world design, went back to the lab | The code equals the lab's; the design is kept in [lab 07](07-deploy-monitor.md) |
| Leftovers: `diabetes-model:1`, auto-listed dev model outputs | From the PR #4 experiment | Harmless; archive in lab 07's last step |

## What's original vs. what we changed

Two independent copies of Microsoft's code (`MicrosoftLearning/mslearn-mlops`
@ `87482bc`). Nothing syncs between them.

```
Microsoft's original
  ├── Copy 1: this GitHub repo (medChiboub/mlops-ai-300)   → used by the GitHub workflows (labs 06–07)
  └── Copy 2: git clone on the workspace file share        → used by the Studio notebooks (labs 01–04)
```

**Copy 1, this repo** (`git diff 412d2d5 HEAD`, the template commit):

| File | Change | Who |
|---|---|---|
| `src/job.yml` | 2 placeholders filled: `type: uri_file`, `path: azureml:diabetes-data@latest` | me, lab 06 |
| `.github/workflows/manual-trigger-job.yml` | + the "Run Azure Machine Learning training job" step | me, lab 06 |
| `infra/setup-prod-design.sh` | **new**: the lab 05 design script (reference + registry-name fix) | Claude, lab 05 |
| `kb/` | **new**: this knowledge base | Claude |
| everything else | untouched original | |

**Copy 2, the workspace file share** (`Users/mohamedd.chiboubb/mslearn-mlops/`):

| File | Origin |
|---|---|
| `experimentation/train-classification-model.py` | lab 02, Studio *Export as .py* |
| `src/train-model-parameters.py` | lab 02, **edited**: `mlflow.autolog()` added (**only here, not in the GitHub repo**) |
| `experimentation/src/train.py` | lab 03 notebook `%%writefile` |
| `experimentation/src/prep-data.py`, `train-model.py`, `experimentation/prep-data.yml`, `train-model.yml` | lab 04 notebook |
| `experimentation/ROC-Curve.png`, `src/ROC-Curve.png` | lab 01 run 5, lab 02 terminal test |
| `*.ipynb` | code unchanged; saved outputs from running them |

So the GitHub workflows train with the **original** `train-model-parameters.py`
(no autolog).

## AI-300 coverage (MLOps domains)

Skills measured from the [AI-300 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-300)
(checked 2026-09-29). These labs only cover **Domain 1 (15–20%)** and
**Domain 2 (25–30%)**. **Domains 3–5 (GenAIOps / Microsoft Foundry, about
45–55% of the exam) aren't in any lab or in my production project.**

Updated after each lab. **Labs** = the labs whose docs cover the skill.
**Status** = what I've done so far in these labs.
**Prod** = my production project (from its `docs/AI-300.md`).

Status: ✅ done · 👀 seen but not done · ⚠ partial or failed · ⏳ planned in a later lab · ❌ no lab covers it

### Domain 1: Design and implement an MLOps infrastructure (15–20%)

| Skill | Labs | Status | Prod |
|---|---|---|---|
| Create and manage a workspace | 01 (CLI), 05 (dev/prod) | ✅ 01, 05 | ✅ |
| Create and manage datastores | none creates one | 👀 01: the 4 defaults | ✅ |
| Create and manage compute targets | 01 | ✅ 01 | ✅ |
| Configure identity and access for workspaces | 06 (service principal, RG scope), 07 (environment secrets) | ✅ 06: service principal, Contributor on the RG only | ✅ |
| Create and manage data assets | 01 (uri_file, MLTable), 05, 07 (uri_folder dev/prod) | ✅ 01, 05 | ✅ |
| Create and manage environments | 02/03 *use* a curated one; none creates one | 👀 02: used curated `sklearn-1.0` (and saw it change results) | ✅ |
| Create and manage components | 04 | ⚠ 04: defined in YAML and used in a pipeline, but only loaded, not registered | ✅ |
| Share assets across workspaces with registries | 05 (design; optional create) | ⚠ 05: registry created (after fixing its name), nothing shared through it | ✅ |
| Configure GitHub integration for secure access | 06, 07 | ✅ 06 (client secret; OIDC only as theory) | ✅ (OIDC) |
| Deploy workspaces and resources with Bicep and Azure CLI | 01, 05 (CLI); **no Bicep in any lab** | ⚠ 01, 05: CLI half | ✅ |
| Automate provisioning with GitHub Actions | ❌ (05 only mentions it) | ❌ | ✅ |
| Restrict network access to workspaces | 06 (read-only review) | 👀 06: reviewed, public access kept | ❌ |
| Manage source control with Git | 06, 07 (branches, PRs, branch protection) | ✅ 06: feature branch, PR, branch protection | ✅ |

### Domain 2: Implement ML model lifecycle and operations (25–30%)

| Skill | Labs | Status | Prod |
|---|---|---|---|
| Configure experiment tracking with MLflow | 01, 02 | ✅ 01, 02 | ✅ |
| Use AutoML to explore optimal models | 01 | ✅ 01 | ✅ |
| Use notebooks for experimentation | 01 | ✅ 01 | ✅ |
| Automate hyperparameter tuning | 03 | ✅ 03 | ✅ |
| Run model training scripts | 02, 04, 06 | ✅ 02, 04, 06 (from GitHub Actions) | ✅ |
| Manage distributed training | ❌ | ❌ | ❌ |
| Implement training pipelines | 04 | ✅ 04 (no schedule; the module covers `JobSchedule`) | ✅ |
| Compare model performance across jobs | 01, 02, 03, 07 (dev vs. prod metrics) | ✅ 01, 02, 03 | ✅ |
| Package a feature retrieval specification with the model | ❌ | ❌ | ❌ |
| Register an MLflow model | 07 (only *implicitly*, through deployment) | ⏳ | ✅ |
| Evaluate a model with responsible AI principles | 01 (module text only); optional notebook `Create Responsible AI dashboard.ipynb` | ⚠ 01: automatic `_RAI` run failed | ⚠ |
| Manage model lifecycle, including archiving | 07 (optional rollback step) | ⏳ | ✅ |
| Deploy real-time or batch endpoints | 07 (real-time only) | ⏳ | ✅ both |
| Test and troubleshoot endpoints | 07 | ⏳ | ✅ |
| Progressive rollout and safe rollback | 07 (optional) | ⏳ | ✅ |
| Detect and analyze data drift | 07 (needs about a day of traffic) | ⏳ | ⚠ |
| Monitor performance metrics in production | 07 (partly) | ⏳ | ❌ |
| Configure retraining or alert triggers | 07 (simulated by hand) | ⏳ | ❌ |

**Gaps no lab and no prod work covers:** distributed training, feature
retrieval specifications, restricting network access (beyond a read-only
review), and automated retraining or alert triggers. Study these from the
docs.

## Tags

Every "lab way vs. my project" table has a **Microsoft's recommended answer**
column, and each cell is tagged:

| Tag | Meaning | On the exam |
|---|---|---|
| 🧪 | **Lab shortcut**: done this way to keep the lab short or cheap | Usually *not* the answer when a question asks for best practice |
| 📘 | **Microsoft docs recommendation**: the documented best practice | **The answer.** When the lab and current docs disagree, the docs win |
| 🛠 | **My project's own choice**: sound, but not a specific Microsoft recommendation | Valid in real life; don't pick it over a 📘 option |
