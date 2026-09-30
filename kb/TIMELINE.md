# Timeline: every step, in order

One running log across all labs, top to bottom, like a waterfall. Each entry
records **when**, **who** did it (**me** or **Claude**), **what**, and **why /
context**. The per-lab files (`01-…md` to `07-…md`) hold the organized notes;
this file is the raw sequence of what happened.

Times are local (EDT).

---

## Lab 01: Find the best classification model

### 2026-09-29

**19:44 · me · Repo created**
Created `medChiboub/mlops-ai-300` (private) from the MicrosoftLearning/mslearn-mlops
template.
*Context:* a clean copy to redo labs 01→07 the Microsoft Learn way, with this
`kb/` as my notes.

**19:50 · Claude · Pre-flight checks** (read-only)
- `az group list`: no existing `rg-ai300-*` group, so the lab 06/07 workflows'
  prefix lookup will find exactly one workspace.
- `az vm list-usage -l canadaeast`: 10 DSv2-family vCPUs. The compute instance
  needs 2 and the cluster at most 4.
- `az provider show -n Microsoft.MachineLearningServices`: already Registered.
- `~/.azure/config`: no `az` defaults set, so `setup.sh`'s `az configure
  --defaults` overwrites nothing.

*Context:* catch quota and naming problems before spending 10 minutes on
provisioning.

**19:52 · me → Claude · Decision: run the provisioning locally, not in Cloud Shell**
*Context:* the exam tests the `az ml` commands, not the Cloud Shell window.
`setup.sh` can't run on macOS as written (`#! /usr/bin/sh`,
`/proc/sys/kernel/random/uuid`), so Claude ran a scratchpad copy with two
changes: the suffix comes from `uuidgen`, and the region is `canadaeast`. The
repo's `setup.sh` is untouched.

**19:55 → 20:01 · Claude · Section 1: provision the workspace** (about 6 min, exit 0)
```bash
cd infra && bash setup-local.sh
```
Created `rg-ai300-l0533925c724d4c839e` (canadaeast):
- the workspace `mlw-ai300-l0533925c724d4c839e`, with its storage, key vault,
  App Insights and Log Analytics
- the compute instance `ci0533925c724d4c839e` (DS11_v2, **running and billing
  from here**)
- `aml-cluster` (DS11_v2, 0–2 nodes)
- the data assets `diabetes-training:1` (MLTable) and `diabetes-data:1` (uri_file)

The script also set the local `az` defaults to this group and workspace.
*Context:* one workspace, reused for every lab until cleanup after lab 07.

**20:02 · Claude · Verified section 1**
`az ml workspace show`, `az ml compute list`, `az ml data list`: all present.

**~20:08 · me · Section 2: clone the lab materials into the workspace** (Studio)
1. Portal → workspace → **Launch studio** → **Compute**: checked that the
   compute instance was Running and the cluster was at 0 nodes.
2. On the compute instance, opened **Terminal**:
   ```bash
   pip uninstall azure-ai-ml
   pip install azure-ai-ml
   git clone https://github.com/MicrosoftLearning/mslearn-mlops.git mslearn-mlops
   ```
3. **Files** pane → ↻ → `Users/mohamedd.chiboubb/mslearn-mlops` appeared.

*Context:* Studio notebooks run on the compute instance and can only see the
workspace file share, so the repo has to be there. The relative data paths
need the whole repo next to the notebooks. Reinstalling the SDK replaces the
image's older `azure-ai-ml`.

**20:10 · Claude · Verified section 2**
Listed the file share `code-391ff5ac…` with `az storage file list`: the repo
is at `Users/mohamedd.chiboubb/mslearn-mlops/`, with all 7 notebooks in
`experimentation/`. Studio also added `.amlignore` files (like `.gitignore`,
but for job code snapshots).

**20:15 · Claude · Wrote `kb/mechanics/`**
Explained what happens underneath, using the real workspace: the workspace
and its 4 datastores, compute instance vs. cluster, data assets and MLTable,
and AutoML from submission to best model.
Findings from inspecting the real resources:
- The compute instance has **no idle shutdown** (`idle: null`), so it bills
  until stopped.
- The compute instance has **no managed identity**, which is why notebooks
  ask to *Authenticate* (the SDK runs as me).
- The cluster releases nodes after 120 s idle.
- `PatientID` is 99.6% unique: a question for AutoML's featurization.

*Context:* I asked to understand the mechanics, not just run notebooks.

**20:12 · me · Ran `Train classification model.ipynb`** (not the lab 01 notebook)
Ran every cell of the plain scikit-learn notebook on the compute instance:
- read the CSV
- split 70/30 on the 8 feature columns (it drops `PatientID`)
- trained `LogisticRegression`
- **Accuracy 0.7737, AUC 0.8484**
- plotted the ROC curve

It created no Azure ML job and no MLflow run; it all ran inside the compute
instance's kernel.
*Context:* I opened the wrong notebook. It's harmless: it only cost compute
instance time, and it gives a **hand-made baseline to compare against
AutoML**. This notebook is the starting point of lab 02 (notebook → script).

**20:17 · Claude · Diagnosed "no job"**
`az ml job list` and the REST `jobs` list returned nothing. I downloaded both
notebooks from the file share: the AutoML notebook had no executed cells and
still had the **Python 3.8 - AzureML** kernel saved in its metadata. The lab
says to switch it to 3.10.

**20:18 · me · Section 3: submitted the AutoML job** (Studio notebook)
Opened `Classification with Automated Machine Learning.ipynb`, switched the
kernel to **Python 3.10 - AzureML**, and ran all cells. The job was created as
**`coral_drawer_c6770sv3k6`** in experiment `auto-ml-class-dev`.
*Context:* the notebook only *submits*; the search itself runs on
`aml-cluster`. Settings: accuracy, 5-fold CV, at most 5 trials,
LogisticRegression blocked.

**20:19 · Claude · Watching the job**
Polling every 60 s: parent status, child jobs (`az ml job list
--parent-job-name`), and cluster node states (REST `nodeStateCounts`).

**20:23 · Claude · Read the AutoML setup job's logs**
`az ml job download -n coral_drawer_c6770sv3k6_setup --all` → `azureml_automl.log`.
Findings:
- The first phase is **two** child jobs, `_setup` then `_featurize`.
- Class sizes are 3344 / 6656.
- **`PatientID` was kept as a Numeric feature** (0 ignored).
- `Pregnancies` (15 values) was typed Categorical.

*Context:* this answers the ▢ verify question in `mechanics/automl.md`.
Automatic featurization didn't drop the ID column.

**20:25 · me → Claude · Decision: tag every lab-vs-project difference**
Each comparison table in section 5 now has a **Microsoft's recommended answer**
column, tagged 🧪 lab shortcut / 📘 docs recommendation (the exam answer) /
🛠 my project's own choice. The legend is in `README.md#tags`.
*Context:* "Microsoft's way" has two layers, what the lab does and what the
docs recommend, and the exam follows the docs.

**20:27 · Claude · Trials started: one at a time, on one node**
`_featurize` Completed. `_worker_0` and trial `_0` are Running; `_1` and `_2`
are NotStarted. Cluster: 1 node running. Parent limits:
`max_concurrent_trials: 1, max_nodes: 1`.
*Context:* confirms the ▢ verify item. The notebook didn't set concurrency,
so the second node allowed by `max_instances: 2` is never used.

**20:28 · Claude · First 3 trials done**

| Trial | Pipeline | Accuracy | AUC_weighted |
|---|---|---|---|
| `_0` | MaxAbsScaler + LightGBM | 0.9518 | 0.9905 |
| `_1` | MaxAbsScaler + XGBoostClassifier | 0.9518 | 0.9904 |
| `_2` | MaxAbsScaler + ExtremeRandomTrees | 0.8313 | 0.9432 |

vs. my hand-trained LogisticRegression: accuracy 0.774 / AUC 0.848.
*Snag:* `az ml job show` on a trial fails with `JobNotSupported`. Metrics come
from the workspace **MLflow REST API**; algorithm names come from the
**run-history API**.

**20:29 · Claude · Ensembles**
The worker finished after 3 base trials. `_3` **VotingEnsemble** Completed:
**0.953**, made of LightGBM 0.8 + XGBoost 0.2, with ExtremeRandomTrees left
out. `_4` **StackEnsemble** is Running.
*Context:* ensembles count toward `max_trials=5` (3 algorithms + 2 ensembles).

**20:30 · Claude · AutoML job Completed**
`coral_drawer_c6770sv3k6`: 00:18:40 → 00:29:55 UTC (about 11 min, 1 node).
`_4` StackEnsemble 0.9529. **Best: `_3` VotingEnsemble, 0.953.**
The explanation run `_ModelExplain` is a child of `_3` and started *after* the
parent reported Completed.
*Context:* the Studio "Completed" status comes before the Explanations tab is
ready. Nothing has been registered.

**20:32 · Claude · Explanation finished; opened up the best model**
Downloaded `_3`'s artifacts through the run-history API. Findings:
- Raw-feature importance puts **PatientID last** (0.019 vs. 1.543 for
  Pregnancies, the top feature).
- `MLmodel` **requires PatientID in its input signature**.
- `generated_code/script.py` rebuilds the exact VotingEnsemble
  (`weights=[0.2, 0.8]`).
- An ONNX copy and scoring scripts sit next to it.

*Context:* the featurization choice carries into the model's API contract.
The generated code is how you would take AutoML's winner and fix it.

**20:33 · me · Reviewed the AutoML job in Studio** (screenshots)
- **Data guardrails:** class balancing **Passed**, missing values **Passed**,
  high cardinality **Passed**.
- **Models + child jobs:** VotingEnsemble 0.9530 > StackEnsemble 0.9529 >
  XGBoost 0.9518 = LightGBM 0.9518 > ExtremeRandomTrees 0.8313. Sampling
  100%, 34–49 s per trial.

*Context:* every ▢ verify item in `mechanics/automl.md` is now confirmed.
PatientID passed the high-cardinality check because it's Numeric: green
guardrails, but the ID still went into the model.

**20:34 · Claude · Wrote `mechanics/mlflow-tracking.md`** (before section 4)
*Context:* read it before running. It covers tracking vs. submitting (these
runs execute in the kernel, not on the cluster), autolog = *training*
metrics, and why run 5 probably never logs its ROC image.

**20:35 · me · Section 4: ran the MLflow tracking notebook** (Studio)
Kernel → Python 3.10 - AzureML, then Run all. 5 runs in
`mlflow-experiment-diabetes`:
- **LR autolog:** training_accuracy 0.7916
- **LR 0.1:** 0.7737
- **LR 0.01:** 0.7740
- **Tree:** 0.892
- **Tree + ROC:** 0.8883

*Context:* experiment tracking. The runs executed in the notebook kernel;
Azure ML only stored the logs.

**20:37 · Claude · Verified the MLflow runs**
Read them through the MLflow REST API.
- **Confirmed:** autolog metrics are `training_*` (0.7916 train vs. 0.7737
  test for the same model).
- **Confirmed:** run 5 logged **no artifacts**; the ROC PNG was never logged.
- The decision trees differ between identical runs because there's no seed.
- **Snag:** `runs/search` omitted run 1's metrics; `runs/get` returned them.

**20:38 · Claude · Explained the "busy" cluster**
`aml-cluster` still had 1 node. `az ml compute list-nodes` →
`current_job_name: coral_drawer_c6770sv3k6_rai` → run `_RAI`
(`automl.rai`), created automatically by AutoML at 00:29:57 UTC under the best
model, running since 00:31:22.
*Context:* AutoML's follow-up work (explanation + Responsible AI dashboard)
keeps the cluster busy after the parent shows Completed. The MLflow
notebook itself used no cluster.

**20:41 · Claude · `_RAI` failed; lab 01 closed**
The automatic Responsible AI run failed at 00:38:39 UTC (the Python process
exited with code 1; the reachable logs don't show a root cause). We didn't
investigate further, because the lab doesn't use it. Filled in the README
line for lab 01, then committed `kb/`.
*Context:* all lab 01 steps are done: provisioning, clone, AutoML, MLflow.
"Delete resources" is skipped on purpose, since the workspace is reused
through lab 07. "In my words" is left for me.

**20:47 · me → Claude · "What about the lab docs themselves and my production project's docs?"**
Claude read all 7 lab docs, the workflows, `src/job.yml`, the deploy script,
the `model/` folder and the lab 02–04 notebooks. It also read the prod
project's `AI300_PREP/CERT_NOTES.md` (Module 1 plus the "Challenge 7" lab 07
record), `MSLEARN-MLOPS.md`, `AI-300.md` and the SCENARIOS/MONITORING
headings. Then it checked Azure: Azure ML quota, the curated environment, and
the subscription's offer.
Wrote **`kb/SOURCES.md`**, a per-lab pre-flight list. Biggest findings:
- The real DSv2 quota is **6**, not 10 (the wrong pool was checked on day
  one). The instance plus the full cluster is exactly 6.
- The curated environment `AzureML-sklearn-1.0-ubuntu20.04-py38-cpu` is gone
  from the `azureml` registry, and the CLI can't read it. Risk for labs
  02/03/06/07.
- Lab 03's sweep optimizes a *training* metric.
- Lab 06's YAML snippets use tab indentation, which breaks YAML.
- Lab 07: `job.yml` type must become `uri_folder`; `sample-request.json` is
  missing; the endpoint name isn't `diabetes-endpoint`; the model's
  `conda.yaml` already has the packages that broke the earlier deployment;
  ESv3 Spark quota is 20 (it was 0 on the earlier subscription).
- AutoML dropped Titanic's `PassengerId` but kept `PatientID`. Hypothesis:
  it needs 100% unique values to treat a column as an ID.

*Context:* so every upcoming lab starts with known issues already listed,
instead of finding them mid-lab.

**20:51 · me → Claude · Dropped `kb/SOURCES.md`**
Removed the per-lab pre-flight file and its README link.
*Context:* a separate list of predicted problems blurs the reasoning. Pitfalls
get briefed at the start of each lab section instead, and only real findings
are recorded (lab file, `mechanics/`, this timeline). The quota correction
stays, because it fixes a wrong statement in `compute.md` and the lab 01 file.
Checks run just before, for the record:
- **Branch protection** on this private repo returned `403 Upgrade to GitHub
  Pro or make this repository public`, so it isn't available (lab 06).
- **The curated environment** couldn't be read through the workspace REST API
  either. The older `AzureML-sklearn-0.24-…` gave the same error, so this may
  be how the API handles curated environments rather than proof that one
  environment is gone. Lab 02's first command job will settle it.

**20:56 · me · Made the repo public**
*Context:* on a private repo on the free plan, branch protection returns a
403 "Upgrade to GitHub Pro" error, and environment required reviewers aren't
available either. On a public repo both are free, so labs 06/07 can do them
properly.

**20:57 · Claude · Hardening the public repo**
- **Interaction limits:** `gh api -X PUT repos/medChiboub/mlops-ai-300/interaction-limits
  -f limit=contributors_only -f expiry=six_months` → only prior contributors
  (me) can comment or open issues and PRs, until **2027-03-30**.
- **Disabling `train-prod.yml` / `deploy-prod.yml`:** Claude's permission
  system blocked this (it counts as bypassing CI), so I did it myself
  (typing `! gh …` in the VS Code chat didn't run anything; I used the
  Actions UI/terminal). Claude verified it with `gh workflow list`: both are
  **`disabled_manually`**, and `manual-trigger-job.yml` and `train-dev.yml`
  stay active.
- **Current exposure: none.** No secrets and no environments exist yet
  (`gh secret list` and `…/environments` are both empty).

*Context:* the two comment-triggered workflows check out a PR's code and run
it with `AZURE_CREDENTIALS`, and they don't check who commented. Once lab 06
adds a repo-level secret, that's the "pwn request" hole on a public repo.
Plan: keep them disabled until lab 07, where `prod` gets me as required
reviewer *before* they're re-enabled.

**21:00 · me → Claude · Read the Microsoft Learn module behind lab 01**
Claude fetched the live learning path. It was restructured on 2026-08-27 as
*Operationalize machine learning models (MLOps)*, with 7 modules. Lab 01 is
unit 8 of the module **Experiment with Azure Machine Learning**. Claude read
units 2–7 and the unit 9 assessment, then compared them with our run:
- **Featurization:** the module says it drops "record IDs". Our run kept
  `PatientID`.
- **Parallel trials:** the module suggests they follow node count. Ours
  defaulted to `max_concurrent_trials` = 1.
- **Algorithm choice:** the module says AutoML "randomly selects" algorithms.
- **RAI dashboard:** the module describes it as a pipeline on a registered
  model, and never mentions AutoML's automatic `_RAI` run.
- **Assessment answers:** `primary_metric='AUC_weighted'`, featurization
  `off`, autologging.

Added to section 4 of the lab file, and corrected `mechanics/automl.md`.
*Context:* the exam uses the module's wording, so know both what the module
says and what actually happened.

**21:02 · me → Claude · "Is my doc up to date for lab 01?"**
Claude reviewed the lab 01 file and the mechanics files end to end:
- **Section 1:** said the trials ran "in parallel"; now says one at a time
  (`max_concurrent_trials` default 1).
- **Section 3:** put in the order we hit the problems. The `_RAI` bullet now
  records that the run failed.
- **Section 5:** removed the "so far" label from the AutoML table and added a
  *parallel trials* row (lab default 1 vs. `max_concurrent_trials=2` in my
  project).
- **`mechanics/automl.md`:** the intro no longer claims AutoML "uses what it
  learned" to pick trials; it uses the module's "randomly selects" wording.

*Context:* the file was written as we went, so early statements had fallen
behind later findings.

**21:05 · me → Claude · Added the AI-300 coverage table**
`kb/README.md` now maps every Domain 1 and Domain 2 skill (31 in all) to the
labs that cover it, my status so far, and my production project's status.
After lab 01: 8 skills ✅ plus the CLI half of Bicep/CLI.
Not covered by any lab or by my project: distributed training, feature
retrieval specifications, restricting network access, and automated
retraining or alert triggers. Domains 3–5 (GenAIOps) aren't in these labs.
*Context:* one place to see exam coverage across all labs, updated at the end
of each lab.

---

## Lab 02: Optimize model training

### 2026-09-29

**21:07 · Claude · Prepared lab 02**
Read the lab doc, `Run script as a command job.ipynb` and
`src/train-model-parameters.py`, and the live Microsoft Learn module *Run
training scripts and track models with MLflow* (units 2–6 plus the
assessment). Checked the compute instance is Running and the cluster is at 0.
Created `kb/02-optimize-model-training.md`.
*Context:* the lab's provision and clone sections are skipped (lab 01's
workspace and clone are reused). Three sections remain: convert a notebook to
a script, test in the terminal, run as a command job.

**21:10 · me · Section 1: converted a notebook to a script** (Studio)
Ran `Train classification model.ipynb`, then **Export as → Python** →
`train-classification-model.py`, then **▷▷** ran it in the terminal:
Accuracy 0.7737, AUC 0.8484. `which python` →
`/anaconda/envs/azureml_py38/bin/python`, **Python 3.10.0**.
*Context:* the first step from notebook toward a production script.

**21:12 · Claude · Checked the export**
Downloaded the `.py` from the share. It's a straight paste of the cells
(`# In[n]:` markers, hardcoded path and `C`, no functions). `df.head()` and
the ROC plot run but show nothing. The share's `ROC-Curve.png` (00:35:48 UTC)
is lab 01 run 5's saved-but-unlogged image.
*Context:* an export alone doesn't make production code. Section 2's script
shows the refactored version.

**21:20 · me → Claude · "How did the exported script turn into src/ with .py and .yml files?"**
It didn't. `src/` was written by Microsoft and has been in the repo all
along. The lab uses my export (`experimentation/train-classification-model.py`,
a raw copy of the cells) and `src/train-model-parameters.py` (the same logic
refactored: functions, `argparse`, MLflow logging) as a before and after.
`job.yml` belongs to labs 06–07. Documented at the start of section 2.2 of the
lab 02 file.
*Context:* the lab jumps from "export" to "test the refactored script"
without saying where that script came from.

**21:21 · me · Section 2: tested the script in the terminal** (Studio)
**▷▷** with no arguments → `TypeError: stat: path should be string… not
NoneType` (intended). The lab's `cd mslearn-mlops/src/` → no such directory
(already in `src/`). Then `python train-model-parameters.py --training_data
../data/diabetes-data/diabetes.csv` → Accuracy 0.774, AUC 0.8485.
*Context:* testing the parameterised script before running it as a job.

**21:24 · Claude · Checked what the terminal run left behind**
MLflow API: the run `epic_floor_prhg1jbc` landed in experiment **`Default`**
(param `Regularization rate=0.01`, Accuracy/AUC, artifact `ROC-Curve.png`).
MLflow started the run automatically on the first `log_*` call. File share:
a new `src/ROC-Curve.png`, which will go into the next job's code snapshot.
*Context:* even a terminal test on a compute instance is tracked in the
workspace.

**21:24 · me · Section 3: ran the command-job notebook** (all cells)
`Run script as a command job.ipynb` submitted two jobs to `aml-cluster`,
experiment `diabetes-training`:
- **`musing_reggae_mnbbwkylvf`** (`diabetes-train-script`)
- **`lime_train_h5fzjbwn0n`** (`diabetes-train-mlflow`, the optional autolog
  run)

Both passed submission with the curated environment
`AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest`.
*Context:* the same script as section 2, now run by Azure ML.
**Note:** the optional step says to add `mlflow.autolog()` to the script
first. The script on the share has no `autolog` line, so the second job
runs identical code under a different name.

**21:30 · Claude · Both command jobs Completed**
Queued 01:24 → nodes up about 3 min later (**2 nodes**, one per job, 6/6
quota cores) → finished 01:29:14 / 01:29:38 UTC. Both logged Accuracy 0.774,
AUC 0.84828, param `Regularization rate 0.01`, `ROC-Curve.png`.
- **Code snapshot:** the whole `src/` folder, including the terminal test's
  PNG, `job.yml` and the deploy script. One code asset shared by both jobs.
- **Input:** reused lab 01's `LocalUpload/03f6bb5b…` upload.
- **Environment:** the curated environment ran fine
  (`/azureml-envs/sklearn-1.0`).
- **AUC:** differs from the terminal (0.84849), most likely the scikit-learn
  version.

Wrote `mechanics/command-jobs.md`.
*Context:* the jobs keep code, data, environment and logs together, which
the terminal run didn't.

**21:35 · me · Optional autolog step, done properly**
Added `mlflow.autolog()` as the first line of `main()` in
`src/train-model-parameters.py`, saved, and reran only the last cell → job
**`epic_king_fhy758f6cn`** (queued 01:35:46 → started 01:37:52 → done
01:40:14 UTC; another cold start, since the nodes had scaled to 0).
*Context:* see what autolog adds on top of custom logging.

**21:43 · Claude · Compared the two jobs; closed lab 02**
- **Autolog job:** 16 params vs. 1, 9 metrics vs. 2 (7 `training_*`:
  training accuracy 0.7914 vs. test 0.774), plus a `model/` folder,
  `estimator.html` and 3 charts. A new code snapshot (`504b4a23…`) because
  the script changed.
- **AUC difference explained:** autolog logged `multi_class: auto` in the job
  (scikit-learn 1.0) vs. `deprecated` on the compute instance in lab 01, so
  the library versions really differ.

Wrote exam mapping (with the Microsoft Learn module comparison and its
4-question assessment), the comparison table, and the 8-question quiz.
Updated the README line and coverage table: *Run model training scripts* ✅,
MLflow ✅, compare ✅, environments 👀.
*Context:* all lab 02 sections done. "Delete resources" skipped (the
workspace is reused).

**21:47 · me → Claude · "Is the Microsoft Learn documentation for these labs up to date with what we have?"**
Pushed lab 02, then checked three things:
- **Lab repo:** our copy is byte-identical to upstream `87482bc`
  (2026-06-30, still the latest commit). Diffed against a fresh download.
- **Microsoft Learn exercise units** (module *Experiment…* unit 8, module *Run
  training scripts…* unit 7, both updated 2026-08-27) link through
  `go.microsoft.com` to `microsoftlearning.github.io/mslearn-mlops/docs/01-…`
  and `02-….html`. The published pages match our `docs/` (spot-checked,
  including the `Run script as command job` filename typo).
- **Theory:** the module units read live today (2026-08-27 versions) are what
  sections 4 of the lab 01 and 02 files compare against.

Added a "Versions checked" line to the kb README.
*Context:* confirms the labs and theory we're following are the current ones.
My production project's `CERT_NOTES.md` predates the 2026-08-27
restructure, so its module numbering differs.

---

## Lab 03: Hyperparameter tuning

### 2026-09-29

**21:49 · Claude · Prepared lab 03**
Read `Hyperparameter tuning.ipynb` and the live module *Perform
hyperparameter tuning with Azure Machine Learning* (units 2–5 plus the
2-question assessment, dated 2026-08-27). Created
`kb/03-hyperparameter-tuning.md` and `mechanics/sweep-jobs.md`.
**Correction:** earlier I said lab 03's sweep optimizes an autolog *training*
metric. The notebook's own `train.py` logs `training_accuracy_score`
computed on **`X_test`**, so it's held-out accuracy with a misleading name.
Also found: the notebook writes a **new** `experimentation/src/train.py`
(not the root `src/`); the grid has 3 values but `max_total_trials=4`; the
notebook's text says the test job uses `reg_rate` 0.1 but the code uses 0.01.
*Context:* one lab section: run the notebook (a command job test, then the
sweep).

**21:51 · me · Ran the whole sweep notebook** (Studio, kernel Python 3.10 - AzureML)
Submitted two jobs:
- **`jovial_insect_nygrdp1wqj`**: the test command job, experiment
  `diabetes-training`, `reg_rate` 0.01, input `diabetes-data:1`
- **`quiet_parcel_r5zv90jjw2`**: the **sweep job**, experiment
  `sweep-diabetes`, grid over `reg_rate` ∈ {0.01, 0.1, 1}, 2 concurrent. It
  inherited the display name `diabetes-train-mlflow` from the base job.

*Context:* test the script once, then tune. With "Run all", the sweep was
submitted without waiting for the test job to finish.

**22:02 · Claude · Sweep Completed; wrote up lab 03**
- **Trials:** `_0` (0.01) 0.774, `_1` (0.1) 0.774, `_2` (1.0) 0.7727. Best
  = `_0` (a tie, decided by trial order). Parent ran 01:50:36 → 01:57:10 UTC.
- **Nodes:** the test job and trial `_1` took the 2 nodes first. The warm-node
  trials took **16–17 s** vs. **2 min 14 s** cold.
- **Readable:** trials open with `az ml job show` (unlike AutoML).
- **Input:** registered `diabetes-data:1`.
- **Snapshot:** only `src/train.py`.
- **Anomaly:** the job reads back `sampling_algorithm: Random`, but the
  notebook ran `grid`. Rebuilt the sweep locally with SDK 1.35.0 (scratch
  venv) and 1.34.1 → both serialize `Grid`. Behaviour was grid-like, so most
  likely a service read-back quirk.

Wrote the exam mapping (module comparison plus its 2-question assessment),
the comparison with `ml/experiments/sweep/`, and an 8-question quiz. Coverage:
*Automate hyperparameter tuning* ✅.
*Context:* the lab's one exercise section is done. The Trials tab in Studio
is left for me to look at.

**22:05 · me · Checked the sweep in Studio**
Trials tab: the 3 trials. **Overview shows sampling = Grid.**
Claude then queried the jobs REST API with 6 versions (2023-10-01 →
2025-09-01): all return `Random`.
*Context:* settles the anomaly. The sweep ran as a grid; the API/CLI read-back
of `sampling_algorithm` is wrong. Lab 03 closed ("Delete resources" skipped).

**22:06 · me → Claude · Checked the Microsoft Learn theory for lab 03 before moving on**
Read the remaining units (1 introduction, 6 exercise, 8 summary). The
exercise links through `go.microsoft.com/fwlink/?LinkId=2377900` to the
published `03-hyperparameter-tuning.html`, which matches our `docs/`. The only
gap in the kb was the **parameter vs. hyperparameter** definition (unit 1),
now added to section 4 of the lab 03 file.
*Context:* confirm the kb covers the whole module before starting lab 04.

---

## Lab 04: Run pipelines

### 2026-09-29

**22:07 · Claude · Prepared lab 04**
Read `Run a pipeline job.ipynb` and all 7 units of the live module *Run
pipelines in Azure Machine Learning* (2026-08-27). Its exercise links to the
published `04-run-pipelines.html`, which matches our `docs/`. Created
`kb/04-run-pipelines.md` and `mechanics/components-and-pipelines.md`.
Findings:
- **The module's exercise unit says "build, run, and schedule a pipeline",
  but the lab never schedules** (no "schedul" in the doc or notebook).
  Scheduling (`JobSchedule` + `RecurrenceTrigger`) is in the theory and the
  assessment.
- The components are loaded, not registered.
- The notebook writes into lab 03's `experimentation/src/`.
- The prep step scales 7 of 8 features on all the data before the split.

*Context:* the last lab that needs the compute instance. Stop it right
after.

**22:09 · me · Ran the pipeline notebook** (Studio, Python 3.10 - AzureML, Run all)
Wrote `src/prep-data.py`, `src/train-model.py`, `prep-data.yml` and
`train-model.yml`, loaded both components, built `diabetes_classification`
with `@pipeline()`, and submitted **pipeline job `calm_ticket_wcbhgt8w7n`**
(experiment `pipeline_diabetes`, input `diabetes-data:1`). The first child,
**`clean_data`** (named after the pipeline variable, with a GUID job ID), was
Queued.
*Context:* two steps as one job; prep's output feeds train's input.

**22:11 · me → Claude · "It's either Python, SDK, Azure ML or YAML. Why?"**
Explained the four layers: the script does the ML; the SDK, CLI + YAML and
Studio are ways to tell Azure ML to run it, all over one REST API. Wrote
`mechanics/interfaces.md` with an SDK ↔ CLI/YAML table.
*Context:* lab 04 mixes all of them (YAML components, SDK wiring, Python
scripts).

**22:17 · Claude · Pipeline Completed; wrote up lab 04**
- **`clean_data`:** 02:11:02 → 02:13:11 (cold), 10,000 rows, 7 features
  scaled, `Age` not scaled.
- **`train_model`:** 02:13:36 → 02:13:59 (warm), created only after
  `clean_data` finished. Accuracy 0.774 / AUC 0.84849, printed only.
- **Components:** anonymous (`az ml component list` empty).
- **Code snapshot:** one, shared by both steps.
- **Outputs:** in `workspaceblobstore/azureml/<run>/…`. The `MLmodel` says
  scikit-learn 1.0.2, which settles lab 02's version question.
- **CLI bug:** `az ml job download` of the `mlflow_model` output crashes
  (`BatchGetResolvedUrisDto … 'values'`); read the blobs directly instead.

Wrote the exam mapping (module comparison plus its 2-question assessment),
the comparison with my project, and an 8-question quiz. Coverage: pipelines
✅, components ⚠ (loaded, not registered).
*Context:* the lab's one section is done. Left: my Studio look at the
graph, the optional schedule step, then stopping the compute instance.

**22:19 · me → Claude · "The schedule should be pipeline know-how, well documented; no need to run it"**
Wrote a full **Scheduling** section in `mechanics/components-and-pipelines.md`,
from verified sources: the SDK signatures (`RecurrenceTrigger`, `CronTrigger`,
`RecurrencePattern`, `JobSchedule`, inspected locally), the `az ml schedule`
CLI help (create/list/show/update/trigger/disable/enable/delete; a delete keeps
past jobs), the module, and my production project's live
`train_schedule.yml` (weekly, Sundays 04:00 UTC).
*Context:* the module's exercise says "schedule"; the lab doesn't do it.
Documented rather than run.

**22:19 · Claude · Lab 04 closed; stopped the compute instance**
`az ml compute stop -n ci0533925c724d4c839e` → **Stopping**. The cluster's
last node is releasing after its idle time.
*Context:* labs 05–07 don't need the compute instance. Stopping it ends its
per-minute billing (its disk and the file share are kept).

---

## Lab 05: Plan and prepare an MLOps solution

### 2026-09-29

**22:30 · me → Claude · "Run lab 05 fully"** (including the optional script)
Claude looked for lab 05's theory: **no module in the current learning
path** (modules 6 and 7 link to labs 06 and 07), so it read the product docs
*Machine Learning registries* and *Create and manage registries* instead.
Read the reference `infra/setup-mlops-envs.sh`: dev RG + workspace + **a
running compute instance** + cluster + 3 data assets; prod RG + workspace +
1 data asset; registry RG + registry.
Quota check: DSv2 **2/6** with the lab 01 compute instance *Stopped*, so a
stopped instance still counts.

**22:24 · Claude · Built `infra/setup-prod-design.sh` the lab's way, then diffed it**
Following the lab literally (copy `setup.sh`, add the variables, append the
commands) produces a script that **still creates `rg-ai300-l<suffix>`** and
**never creates the dev RG or workspace**. It would fail halfway and leave a
second `rg-ai300-l*` group, breaking the lab 06/07 workflows. Following the
lab's "diff against the reference, then update" step, the final
`setup-prod-design.sh` = the reference. Ran a scratchpad copy (`uuidgen`,
`canadaeast`) from `infra/`.
*Context:* the lab's optional run. It creates 3 resource groups, 2
workspaces, a compute instance, a cluster, 4 data assets and a registry.

**22:35 · Claude · Design script run: dev ✅, prod ✅, registry ❌ → fixed**
Suffix `5ae342744a834c9880`, canadaeast.
- **Dev:** RG + workspace + compute instance + cluster + 3 data assets.
- **Prod:** RG + workspace + `diabetes-prod-folder`.
- **Registry:** failed: `Registry Name … is invalid. Names must be between 3
  and 33 in length`. The reference script's `mlr-ai300-shared-<18 chars>` is
  35 characters. The script still exited 0 and printed "Provisioning
  complete" (no `set -e`).

Then:
- Stopped the dev compute instance.
- **Restored the `az` defaults** (the script left them on prod).
- Recreated only the registry as `mlr-ai300-shared-5ae342744a834c9`
  (32 characters, 45 s). It built the managed RG
  `azureml-rg-mlr-ai300-shared-…` with a **Premium ACR** + Standard_LRS
  storage.
- Fixed `REGISTRY_NAME` in my `setup-prod-design.sh`
  (`${suffix:0:15}`).
- Wrote `mechanics/registries-and-environments.md`.

*Context:* lab 05's optional run done. Left: the "extend the script" design
question, then cleanup of the 3 extra RGs.

**22:37 · me · Decision: keep all lab 05 resource groups**
Kept `rg-ai300-dev-…`, `rg-ai300-prod-…` and `rg-ai300-reg-…` (skipping the
lab's cleanup). They're added to the final cleanup list after lab 07.
Claude finished the lab 05 write-up: the "extend the script" design (2.5),
the exam mapping, the comparison with my project, an 8-question quiz, and
the coverage (workspace ✅, data assets ✅, registries ⚠: created but
nothing shared).
*Context:* ongoing cost is about $1.67/day (the registry's Premium ACR); the
dev compute instance is stopped.

---

## Lab 06: Automate model training with GitHub Actions

### 2026-09-29

**22:40 · Claude · Prepared lab 06**
Read the live module *Automate model training with GitHub Actions*: units
2–6 (what goes in Git; trunk-based development; required status checks;
secrets vs. variables; **OIDC preferred over service-principal secrets**;
trigger types incl. `repository_dispatch` via Logic Apps/Functions) and the
5-question assessment. Upstream lab repo still `87482bc`.
Checks: I'm **Owner** on the subscription. GitHub has no secrets, variables
or environments; `main` returns "Branch not protected" (404, not the old
403), so protection is available now the repo is public. Two old app
registrations (`sp-ai300-prod`, `sp-ai300-github-actions`) exist from
earlier work and are left untouched.

**22:41 · Claude · Section: configure GitHub integration**
Created the service principal `sp-mslearn-mlops-github` (appId `a9bd6f2c-…`),
**Contributor on the lab 01 RG only**, with `--json-auth` piped straight into
`gh secret set AZURE_CREDENTIALS` (never printed). Set the repo variables
`AZURE_RESOURCE_GROUP` and `AZURE_WORKSPACE_NAME`. Verified: client secret
valid until 2027-09-30, no subscription-level role. The CLI warned that
`--sdk-auth`/`--json-auth` is deprecated.
*Context:* this is what lets GitHub-hosted runners sign in to Azure. The two
comment-triggered workflows stay disabled, so the new secret can't be reached
through a PR comment.

### 2026-09-30

**00:18 · me · Section: reviewed workspace network access** (portal, read only)
Public access enabled from all networks, no private endpoints. Claude
confirmed from the CLI (`public_network_access: Enabled`, default Allow, no
IP rules, 0 private endpoints). Wrote `mechanics/github-actions-azureml.md`.
*Context:* GitHub-hosted runners need public access; private workspaces need
self-hosted runners.

**00:28 · me → Claude · "Why didn't you add the service principal to the mechanics?"**
Added a section to `mechanics/github-actions-azureml.md`, verified against
Entra ID: one command created an **app registration** (appId `a9bd6f2c-…`,
objectId `f9c702e5-…`, 1 client secret until 2027-09-30, 0 federated
credentials), a **service principal** (objectId `15b1f7f7-…`), and a
**Contributor role assignment** on the lab RG. Also covers how `azure/login`
uses the JSON, and why cleanup must delete the app registration.
*Context:* section 1 of lab 06 was done by me while I was away; this makes
the mechanics explicit.

**00:29 · me → Claude · "What about dev and prod?"**
Clarified: lab 05's dev/prod are real separate workspaces that **no workflow
uses**. Lab 07's dev/prod are GitHub Environments + data assets **inside the
lab 01 workspace** (the lab says so). Lab 06 has no dev/prod. Added a
"Careful: labs 06–07 don't use this design" section to the lab 05 file.

**00:33 · me → Claude · "Which code is original vs. what we edited?"**
Mapped it: two independent copies. **The GitHub repo** differs from the
template only in `src/job.yml` and `manual-trigger-job.yml` (mine, lab 06),
plus `infra/setup-prod-design.sh` and `kb/` (Claude). **The workspace file
share clone** has the notebook-generated files and the lab 02 `autolog` edit,
which isn't in GitHub. Added the map to the kb README.

**04:30–04:35 UTC · me · Ran the workflow by hand** (run `36669089137`)
Login ✅. The job **`plucky_yogurt_9rv71w234s`** Completed (Accuracy 0.774,
AUC 0.8483, **`created_by` = the service principal**). But the **step
failed**: `--stream` crashed with `binascii.Error: Invalid base64-encoded
string` 4 s before the job ended.

**00:38 · Claude · Diagnosed the false failure**
The runner installs the unpinned **ml 2.45.0**. Streaming the finished job
works with both 2.44.1 and 2.45.0 (isolated `AZURE_EXTENSION_DIR`), so it's
the **live** streaming path. The next PR-triggered run will show whether it
repeats.
*Context:* the training is fine; the GitHub check is red only because of
the CLI.

**00:39 · me → Claude · "Do these workflows launch Azure ML pipelines?"**
No: every lab workflow submits the **command job** `src/job.yml` (one
script); `deploy-prod.yml` runs an SDK deploy script. Lab 04's pipeline files
exist only on the Studio clone. The same `az ml job create -f` would submit
a pipeline YAML unchanged. My project's workflow does submit a pipeline
(prep → train → evaluate with an AUC gate). Added to section 5 of the lab
06 file.

**00:42 · me → Claude · "So we submit either a command job or a pipeline job? A pipeline is a set of commands?"**
Nuanced and documented: **5 job types** (command, sweep, automl, pipeline,
spark), all submitted with `az ml job create -f`, where the YAML's `type:`
decides. A pipeline is a **graph of component steps** (usually commands, but
steps can also be sweep/AutoML/Spark/parallel/sub-pipelines) whose
output → input wiring gives ordering, data passing, reuse and per-step child
jobs. Plus the non-job `az ml` actions a workflow may run (register,
deploy, schedule). New `mechanics/job-types.md`, and a nuance section in
`components-and-pipelines.md`.

**04:40–04:50 UTC · me + Claude · Section: PR trigger + branch protection**
Claude (on my "do it for me") added `pull_request: branches: [main]` to
`manual-trigger-job.yml` (`db64fbf`). I created a **classic branch protection
rule** on `main` in the UI: require PR, **approvals unticked** (the dropdown only
goes 1–6). The API read-back: approvals 0, no required checks, admins not
enforced, force push and deletion blocked.
*Context:* the PR becomes the only way into `main`.

**04:54–05:00 UTC · Claude + me · Feature branch → PR #1**
Claude: branch `feature/update-parameters`, `reg_rate 0.01 → 0.1` (`f281c9e`).
I opened **PR #1** → the `pull_request` trigger ran automatically (run
`36671001563`). Job `ashy_holiday_qxk8djl5xk` Completed (acc 0.774, AUC
0.8483), but the **same `--stream` binascii error** → check FAILURE, PR
"unstable" but mergeable.

**07:05–07:18 UTC · me → Claude · Option B: pin the CLI, re-test, merge**
Pinned `az extension add -n ml --version 2.44.1 -y` on the PR branch
(`99c37b8`). The PR re-ran (`36681715090`): **✅ green**, and the stream printed
`Accuracy: 0.774` / `AUC: 0.8483`. PR state CLEAN. Claude merged PR #1 on my
"ok go" (07:18:32, `7afe772`) and deleted the branch; local switched back to
`main`.
*Context:* confirms the 2.45.0 streaming bug and the fix. Lab 07's workflows
need the same pin (`train-dev.yml` parses metrics from the streamed log).

**03:20 · Claude · Lab 06 closed**
Wrote the exam mapping (module comparison plus the 5-question assessment),
the comparison table (client secret vs. OIDC, unpinned tools…), and an 8-question
quiz. Coverage: IAM ✅, GitHub integration ✅, Git ✅, network 👀, training
scripts from CI ✅.

---

## Lab 07: Deploy and monitor

### 2026-09-30

**03:25 · Claude · Prepared lab 07; data assets; environments**
Read the live module *Deploy and monitor a model in Azure ML* (units 2–5 +
the 5-question assessment); its exercise links to this lab. The module's way
differs from the lab: register the model, blue/green at 0% → 10%, OIDC, a
protected `production` environment. The lab deploys an unregistered folder
at 100%, with a client secret and an optional reviewer.
- Added `diabetes-dev-folder` and `diabetes-prod-folder` (uri_folder, v1)
  to the **lab 01 workspace**. All three CSVs have the same MD5.
- Created GitHub environments `dev` and **`prod` with me as required
  reviewer**.
- Put `AZURE_CREDENTIALS` into both from a **new client secret**
  (`gh-environments-lab07`) on the same service principal, never printed.

*Context:* the setup lab 07's workflows need. The reviewer gate matters
because the repo is public.

**03:38 · me → Claude · "What does train-prod do? One job.yml for dev and prod?"**
Documented, in the lab 07 file ("How dev and prod share one job
definition") and in `mechanics/github-actions-azureml.md` (sections "One job
definition, several environments (--set)" and "issue_comment workflows").
Both workflows submit the same `src/job.yml`; `--set` swaps only the data
path at submit time, and the GitHub environment supplies the credentials and
the gate. `/train-prod` runs the workflow from `main` against the PR's
code, after my approval.
