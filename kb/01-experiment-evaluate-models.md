# Lab 01: Find the best classification model

Source: [docs/01-experiment-evaluate-models.md](../docs/01-experiment-evaluate-models.md)

Mechanics: [workspace and storage](mechanics/workspace-and-storage.md) ·
[compute](mechanics/compute.md) · [data assets](mechanics/data-assets.md) ·
[AutoML](mechanics/automl.md) · [MLflow tracking](mechanics/mlflow-tracking.md)

## 1. What this lab does

Provisions the Azure ML workspace, a compute instance and a compute cluster
with one Azure CLI script from Cloud Shell, plus two data assets. Then it
explores models two ways: an AutoML classification job submitted from a
notebook (algorithm and featurization search, run in parallel on the
cluster), and hand-written scikit-learn training in a notebook, tracked with
MLflow (autologging vs. custom logging).

## 2. Steps I actually ran

### 2.1 Provision the workspace (local Mac instead of Cloud Shell)

The lab runs `infra/setup.sh` in Azure Cloud Shell. We ran it from my Mac's
terminal instead (az CLI 2.89.1, `ml` extension 2.44.1, already logged in).
The script as written can't run on macOS, so we ran a copy with two lines
changed and left the repo's `setup.sh` untouched:

```bash
cd infra
sed -e 's#cat /proc/sys/kernel/random/uuid#uuidgen | tr "[:upper:]" "[:lower:]"#' \
    -e 's/^REGIONS=.*/REGIONS=("canadaeast")/' setup.sh > setup-local.sh
bash setup-local.sh        # run from infra/: the data paths are ../data/...
```

What the script does, in order (all `az` CLI):

```bash
az provider register --namespace Microsoft.MachineLearningServices
az group create --name rg-ai300-l<suffix> --location canadaeast
az configure --defaults group=rg-ai300-l<suffix>
az ml workspace create --name mlw-ai300-l<suffix>      # also creates storage, key vault, App Insights
az configure --defaults workspace=mlw-ai300-l<suffix>
az ml compute create --name ci<suffix> --size STANDARD_DS11_V2 --type ComputeInstance
az ml compute create --name aml-cluster --size STANDARD_DS11_V2 --max-instances 2 --type AmlCompute
az ml data create --type mltable  --name diabetes-training --path ../data/diabetes-data
az ml data create --type uri_file --name diabetes-data     --path ../data/diabetes-data/diabetes.csv
```

My resources:

| Resource | Name |
|---|---|
| Resource group | `rg-ai300-l0533925c724d4c839e` (canadaeast) |
| Workspace | `mlw-ai300-l0533925c724d4c839e` |
| Compute instance | `ci0533925c724d4c839e` (Standard_DS11_v2) |
| Compute cluster | `aml-cluster` (Standard_DS11_v2, 0–2 nodes) |
| Data assets | `diabetes-training` (MLTable), `diabetes-data` (uri_file) |

Before running we checked:
- Quota: `az vm list-usage -l canadaeast` showed 10 DSv2-family vCPUs. The compute instance takes 2 and the cluster up to 4.
- Name clashes: `az group list` showed no other `rg-ai300-*` group.

It finished in about 6 minutes with exit code 0 and no errors. We verified it with:

```bash
az ml workspace show                # location canadaeast, plus storage, key vault and App Insights
az ml compute list -o table         # CI Running; aml-cluster min 0 / max 2
az ml data list -o table            # diabetes-training:1, diabetes-data:1
```

The workspace's dependent resources were created automatically:
`mlwai300storage…` (storage), `mlwai300keyvault…` (key vault),
`mlwai300insights…` (App Insights), plus a Log Analytics workspace behind App
Insights. No container registry exists yet; Azure creates one on the first
environment image build or deployment.

### 2.2 Clone the lab materials into the workspace (Studio, me)

1. Portal → `mlw-ai300-l0533925c724d4c839e` → **Launch studio** → **Compute**:
   the compute instance was Running and `aml-cluster` was at 0 nodes.
2. **Compute instances** tab → my instance → **Terminal**:
   ```bash
   pip uninstall azure-ai-ml
   pip install azure-ai-ml
   git clone https://github.com/MicrosoftLearning/mslearn-mlops.git mslearn-mlops
   ```
3. **Files** pane → ↻ → `Users/mohamedd.chiboubb/mslearn-mlops` appeared.

Verified from the CLI: the files are on the workspace's Azure Files share
(`code-391ff5ac…` in the workspace storage account). The compute instance
mounts that share at `~/cloudfiles/code/`. Studio adds `.amlignore` files
automatically; they control what gets uploaded when you submit a job from
that folder.

### 2.3 AutoML classification (Studio, me)

1. Opened `experimentation/Classification with Automated Machine Learning.ipynb`
   (after first running the wrong notebook by mistake; see section 3).
2. Switched the kernel from the saved *Python 3.8 - AzureML* to
   **Python 3.10 - AzureML**.
3. Ran all cells, which submitted **`coral_drawer_c6770sv3k6`** to experiment
   `auto-ml-class-dev` on `aml-cluster`.
4. Claude watched it from the CLI. It took about 11 minutes on 1 node.
   The best model was **VotingEnsemble at 0.953 accuracy** (5-fold CV), vs.
   0.774 for my hand-trained LogisticRegression. Full leaderboard in
   [mechanics/automl.md](mechanics/automl.md#the-actual-run-coral_drawer_c6770sv3k6).

Commands Claude used to follow the job:

```bash
az ml job list --parent-job-name coral_drawer_c6770sv3k6 -o table      # all child jobs
az ml job show -n coral_drawer_c6770sv3k6 --query limits               # max_concurrent_trials: 1
az ml job download -n coral_drawer_c6770sv3k6_setup --all --download-path …   # featurization logs
# trial metrics:  MLflow REST  …/api/2.0/mlflow/runs/get?run_id=<parent>_N
# trial algorithm: run-history REST …/experiments/auto-ml-class-dev/runs/<parent>_N → properties.run_algorithm
```

### 2.4 Track model training with MLflow (Studio, me)

1. Opened `experimentation/Track model training with MLflow.ipynb`, switched
   the kernel to **Python 3.10 - AzureML**, and ran all cells.
2. Five runs appeared in experiment **`mlflow-experiment-diabetes`**. Run 1 is
   autolog; runs 2–5 use custom logging. Results are in
   [mechanics/mlflow-tracking.md](mechanics/mlflow-tracking.md#the-actual-runs-verified).
3. Claude read them through the workspace's MLflow REST API
   (`experiments/get-by-name`, `runs/search`, `runs/get`) and the run-history
   artifacts endpoint. It confirmed that the cluster ran none of them.

## 3. What broke and how we fixed it

- **Ran the wrong notebook, and no AutoML job appeared.** I ran
  `Train classification model.ipynb` (plain sklearn, lab 02's starting
  point) instead of `Classification with Automated Machine Learning.ipynb`.
  How we found it: `az ml job list` was empty. Claude downloaded both
  notebooks from the workspace file share (`az storage file download`) and
  compared execution counts and last-modified times. Lesson: **a notebook
  that trains in-kernel creates no job.** Only `ml_client.jobs.create_or_update`
  (or `mlflow.start_run`) leaves a trace in the workspace. Side benefit: a
  baseline of LogisticRegression **accuracy 0.774 / AUC 0.848** to compare
  AutoML against.
- **`az ml job show` can't read AutoML trials.** On `<parent>_0` it fails
  with `UserError … JobNotSupported`. AutoML trials are an internal, older job
  type that the v2 jobs API doesn't expose; only the parent and the
  `_setup`/`_featurize` jobs are readable. Workaround: every job is also an
  **MLflow run**, so metrics come from the workspace's MLflow REST API
  (`https://<region>.api.azureml.ms/mlflow/v2.0<workspace-id>/api/2.0/mlflow/runs/get?run_id=…`),
  and the algorithm name comes from the run-history API (`properties.run_algorithm`).
  In Studio, just use the **Models + child jobs** tab.
- **"Why is the cluster still running?"** 6 minutes after the AutoML parent
  showed Completed, `aml-cluster` still had 1 node, and `az ml job list`
  showed nothing active. `az ml compute list-nodes -n aml-cluster` named the
  job on the node: `coral_drawer_c6770sv3k6_rai`. It turned out to be
  `_RAI` (run type `automl.rai`), a Responsible AI dashboard run that AutoML
  creates automatically under the best model. Lesson: **`list-nodes` is the
  fastest way to find out what's using (and billing) a cluster.**
- **MLflow `runs/search` returned no metrics for the autolog run.** `runs/get`
  on the same ID returned all 7. Read single runs directly when numbers look
  missing.
- **Kernel mismatch in the saved notebook:** the AutoML notebook's metadata
  says *Python 3.8 - AzureML*. The lab's "verify it uses Python 3.10 -
  AzureML" step is there to catch exactly this.

- **`setup.sh` doesn't run on macOS.** Its shebang is `#! /usr/bin/sh`, which
  doesn't exist on macOS. It also reads `/proc/sys/kernel/random/uuid`, which
  is Linux-only. Fix: we ran a copy with `bash` and generated the suffix with
  `uuidgen`. In Cloud Shell (Linux) it runs as written.
- **Random region.** The script picks one of 5 US/EU regions at random. We
  pinned `canadaeast` with `sed`. The workspace takes the resource group's
  location because `az ml workspace create` has no `--location`.

## 4. Exam mapping

**Provisioning (2.1)**, Domain 1: *Design and implement an MLOps infrastructure*

- *Create and manage a workspace*: `az ml workspace create` creates the
  storage account, key vault and App Insights along with it. The container
  registry only appears later, when it's first needed.
- *Create and manage compute targets*: a **compute instance** (one VM per
  user, for notebooks, billed while running) vs. a **compute cluster**
  (`AmlCompute`, scales from `min_instances` to `max_instances` for jobs, no
  cost at 0 nodes).
- *Create and manage data assets*: `uri_file` (one file, e.g. a CSV) vs.
  `mltable` (a folder containing an `MLTable` file that defines a tabular
  schema). AutoML requires MLTable.
- *Deploy workspaces and resources by using Bicep and Azure CLI*: this is the
  CLI half of that skill.

**Clone into the workspace (2.2)**, Domain 2: *Orchestrate model training*

- *Use notebooks for experimentation and exploration*: a compute instance is a
  single-user dev VM (set idle shutdown to save cost). It mounts the
  workspace file share and gets workspace access and MLflow tracking with no
  setup. If a question mentions sensitive data, collaboration or GPU needs
  during exploration, the answer is a compute instance. If it mentions
  repeatable or production runs, the answer is jobs or pipelines on a
  cluster.

**AutoML (2.3)**, Domain 2: *Orchestrate model training*

- *Use automated machine learning to explore optimal models*: an AutoML job
  is a parent job with child jobs (`_setup`, `_featurize`, `_worker_0`,
  trials `_0`…`_N`, ensembles, `_ModelExplain`). Know the settings: task
  type, `primary_metric`, `n_cross_validations`, limits (`max_trials`,
  `max_concurrent_trials`, `timeout_minutes`, `trial_timeout_minutes`,
  `enable_early_termination`), and `blocked_training_algorithms`.
- **Training data must be MLTable.** Featurization `auto` runs the **data
  guardrails** (statuses Passed / Done / Alerted).
- **Ensembles** (Voting, Stack) count toward `max_trials` and often win.
- **Output:** the best model in MLflow format plus ONNX, generated training
  code, and an explanation. **Nothing is registered automatically.**
- *Compare model performance across jobs*: the leaderboard, and each trial's
  logged metrics.
- **Trap seen here:** all guardrails passed while an ID column was used as a
  feature. Guardrails check data quality, not whether a feature makes sense.

**MLflow tracking (2.4)**, Domain 2: *Orchestrate model training*

- *Configure experiment tracking with MLflow*: on a compute instance the
  tracking URI is preset; elsewhere, set it to the workspace's
  `mlflow_tracking_uri`. `set_experiment` → `start_run` →
  `log_param` / `log_metric` / `log_artifact`.
- **Autolog** logs params, **training** metrics and the model, and it applies
  globally once enabled. **Custom logging** logs only what you ask for.
  Saving a file isn't logging it.
- **Tracking ≠ submitting:** these runs executed in the notebook kernel. Azure
  ML only stored the logged values. No compute, environment or code snapshot.
- *Compare model performance across jobs*: select runs in Studio →
  **Compare**, or `mlflow.search_runs()`. Set seeds; otherwise the same
  params can give different scores (runs 4 vs. 5).

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice (sound,
but not a specific Microsoft recommendation).

**Provisioning (2.1)**

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Style | 🧪 Imperative `az` script run once. Re-running it creates a *new* RG with a new suffix | Declarative Bicep (`infra/main.bicep`) with one `.bicepparam` per environment. Re-running changes nothing | 📘 **Infrastructure as code (Bicep/ARM)** for repeatable, reviewable provisioning. My project matches; the CLI is fine for one-off or scripted tasks |
| Region | 🧪 Random from 5 (we pinned canadaeast) | Fixed per environment in its parameter file | 📘 Choose it deliberately: data residency, quota, feature availability, latency to data |
| Compute | Compute instance + cluster | 🛠 Cluster only; notebooks run locally | 📘 **Compute instance** is the documented dev environment; **cluster** for jobs. The lab matches; local notebooks are my own choice |
| Naming | 🧪 Random suffix; workflows find the workspace by prefix | 🛠 Names set explicitly per GitHub Environment | No specific rule; explicit configuration avoids targeting the wrong workspace |
| Identity/RBAC | 🧪 Whatever the signed-in user has (a secret-based service principal comes in lab 06) | OIDC, RBAC and managed-identity grants set up by bootstrap scripts | 📘 **Managed identities + OIDC federated credentials + least-privilege RBAC.** My project matches |

Why it matters: an imperative script is quick for a lab, but you can't
review a change to it or rebuild the same thing twice. Bicep gives the same
result every time and shows a diff before applying. On the exam, "repeatable,
version-controlled provisioning" points to Bicep or ARM templates, not a
shell script.

**Notebooks on a compute instance (2.2)**

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Where the notebook runs | Compute instance (Azure VM, billed while running) | 🛠 My Mac. Nothing executes in Azure | 📘 **Compute instance** for exploration, especially with sensitive data, a team, or GPU needs. The lab matches |
| How code reaches Azure | `git clone` onto the workspace file share (`~/cloudfiles/code/Users/<me>/`) | `code: .` in the job YAML; `az ml job create` uploads a snapshot per job | 📘 Both, at different stages: clone Git repos into the instance for notebook work; a **code snapshot per job** for anything run as a job |
| Connecting to the workspace | `MLClient.from_config()`, which the instance already has | `MLClient(AzureCliCredential(), sub, rg, ws)` from env vars | 📘 Both are documented: `from_config()` on a compute instance, explicit IDs elsewhere |
| MLflow tracking | Already points at the workspace | `mlflow.set_tracking_uri(workspace.mlflow_tracking_uri)`, set by hand | 📘 Both are documented: built in on Azure compute, set the tracking URI when running remotely |
| Packages | 🧪 Image defaults plus a manual `pip install` | Pinned custom conda environment, the same one for training and scoring | 📘 **A registered environment (curated or custom), versioned** for reproducible jobs. My project matches |
| Compute instance cost | 🧪 No idle shutdown set (`idle: null`) | No compute instance | 📘 **Idle shutdown and/or a schedule** on every compute instance |

Why it matters: a compute instance is the Microsoft answer to *experimenting*,
but its hand-installed packages drift just like a laptop's. Operationalizing
means moving the logic into jobs or components that run in a pinned
environment on a cluster, with the code snapshotted per run. My project's
README records that the clean-container run caught bugs the notebook's local
packages had hidden.

**AutoML (3), so far**

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Primary metric | 🧪 `accuracy` | AUC (`AUC_weighted` in its AutoML script) | 📘 **`AUC_weighted`** when classes are imbalanced; accuracy is threshold-dependent and misleading under skew |
| ID column | 🧪 `PatientID` left in the MLTable, and AutoML kept it as Numeric | Its data has no ID column | 📘 **Drop identifiers** before training, or set featurization to `custom` and mark the column *Ignore*. Automatic featurization isn't guaranteed to catch them |
| Training data | Registered MLTable asset `diabetes-training:1` | 🛠 Local, unregistered MLTable folder | 📘 **A registered, versioned data asset**, so the job's lineage points at fixed data. The lab matches |

**MLflow tracking (2.4)**

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Where tracked training runs | Notebook kernel on the compute instance; the runs are log-only | Local notebook (optional tracking cell) **and** pipeline jobs on the cluster | 📘 Notebooks for exploration; **jobs for anything you need to reproduce**. A tracked notebook run has no code snapshot or environment |
| Autolog vs. custom | Both, as a demo | `mlflow.sklearn.autolog()` in `train.py` + custom metrics (AUC, recall) in `evaluate.py` | 📘 **Autolog plus custom metrics on held-out data.** Autolog's metrics are training metrics |
| Artifacts | 🧪 ROC plot saved but never logged (a lab bug) | Metrics written to `metrics.json` as a pipeline output | 📘 `mlflow.log_artifact` / `log_figure` for anything you want kept with the run |
| Seeds | 🧪 None on the decision trees; the same code gave 0.892 and 0.8883 | `random_state` set | 📘 Set seeds and log them. Reproducibility is part of tracking |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> You submit an AutoML classification job from a notebook with <code>training_data=Input(type=AssetTypes.URI_FILE, path="azureml:diabetes-data:1")</code>. What happens?<br><br>A) It runs normally; AutoML accepts any data asset<br>B) It fails: AutoML (SDK/CLI v2) needs an <strong>MLTable</strong> input<br>C) It runs, but featurization is disabled<br>D) It converts the CSV to parquet first</summary>

> **✅ Answer: B.** AutoML needs tabular semantics, which a <code>mltable</code> asset provides (a folder with an <code>MLTable</code> file that describes how to read it). That's why <code>setup.sh</code> registered <code>diabetes-training</code> as MLTable alongside the plain <code>uri_file</code>.
</details>

---

<details>
<summary><strong>2.</strong> Every AutoML data guardrail shows <em>Passed</em>, yet the best model's <code>MLmodel</code> signature requires <code>PatientID</code>. Why wasn't the ID caught?<br><br>A) Guardrails only run when featurization is <code>off</code><br>B) The ID was typed <em>Numeric</em>, and the high-cardinality check only looks at categorical/text columns. Guardrails check data quality, not whether a feature makes sense<br>C) PatientID had missing values<br>D) The class-balancing check removes IDs</summary>

> **✅ Answer: B.** In our run: 9,959 unique values, typed Numeric, 0 columns ignored, and all guardrails green. The fix is yours to make: drop it in the MLTable, or use <code>custom</code> featurization and mark it *Ignore*. Leaving it in turns into an API contract problem at deployment.
</details>

---

<details>
<summary><strong>3.</strong> The lab's AutoML job sets <code>max_trials=5</code> and doesn't set <code>max_concurrent_trials</code>. <code>aml-cluster</code> has <code>max_instances=2</code>. What did we observe?<br><br>A) 5 trials in parallel on 2 nodes<br>B) 1 node; a <code>_worker_0</code> job ran the trials one after another, and the default <code>max_concurrent_trials=1</code> applied<br>C) 2 nodes, 2 trials at a time<br>D) The job waited in the queue for a second node</summary>

> **✅ Answer: B.** <code>limits</code> showed <code>max_concurrent_trials: 1, max_nodes: 1</code>. The cluster's maximum is an upper bound, not a target. Concurrency comes from the job's limits.
</details>

---

<details>
<summary><strong>4.</strong> With <code>max_trials=5</code>, how many distinct algorithms did AutoML actually try?<br><br>A) 5<br>B) 3: the last two trials were the VotingEnsemble and StackEnsemble, which count toward <code>max_trials</code><br>C) 4<br>D) 6, because ensembles are free</summary>

> **✅ Answer: B.** LightGBM, XGBoost and ExtremeRandomTrees, then VotingEnsemble (LightGBM 0.8 + XGBoost 0.2, the winner at 0.953) and StackEnsemble (0.9529).
</details>

---

<details>
<summary><strong>5.</strong> The AutoML parent job shows <em>Completed</em>, but <code>aml-cluster</code> still has a running node 6 minutes later. What's the fastest way to see what's on it?<br><br>A) <code>az ml job list</code><br>B) <code>az ml compute list-nodes -n aml-cluster</code>, which shows <code>current_job_name</code> per node<br>C) Restart the cluster<br>D) Check the Data guardrails tab</summary>

> **✅ Answer: B.** It showed <code>coral_drawer_c6770sv3k6_rai</code>: a Responsible AI dashboard run AutoML created under the best model. <code>az ml job list</code> showed nothing active, because these follow-up runs aren't top-level v2 jobs.
</details>

---

<details>
<summary><strong>6.</strong> Run 1 (autolog) reports <code>training_accuracy_score 0.7916</code>; run 2 (same model, same settings, custom logging) reports <code>Accuracy 0.7737</code>. Why the gap?<br><br>A) Autolog uses a different solver<br>B) Autolog measures on the <strong>training</strong> data it was fit on; run 2 measured on the held-out test set<br>C) Custom logging rounds values<br>D) Autolog uses cross-validation</summary>

> **✅ Answer: B.** Autolog doesn't know about your <code>X_test</code>. Compare like with like: log your own held-out metrics next to autolog's.
</details>

---

<details>
<summary><strong>7.</strong> Run 5 calls <code>plt.savefig("ROC-Curve.png")</code> inside <code>with mlflow.start_run():</code>. Where is the image in Studio?<br><br>A) Outputs + logs<br>B) The Images tab<br>C) Nowhere: saving a file isn't logging it. It needs <code>mlflow.log_artifact("ROC-Curve.png")</code> (or <code>mlflow.log_figure(fig, ...)</code>)<br>D) Attached to the registered model</summary>

> **✅ Answer: C.** Run 5's artifact list was empty. The PNG only exists in the notebook's folder on the workspace file share.
</details>

---

<details>
<summary><strong>8.</strong> What's the key mechanical difference between the MLflow notebook's runs and the AutoML job?<br><br>A) None, both run on the cluster<br>B) MLflow runs are <strong>tracked</strong>: the code ran in the notebook kernel and Azure ML only stored the logs. AutoML was <strong>submitted</strong>: Azure ML executed it on <code>aml-cluster</code> with its own environment and snapshot<br>C) MLflow runs can't be compared<br>D) AutoML doesn't use MLflow</summary>

> **✅ Answer: B.** The cluster stayed idle for the MLflow notebook. Tracking gives you a record; submitting gives you a reproducible execution. AutoML trials *are* MLflow runs too, which is how we read their metrics.
</details>
