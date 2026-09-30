# AutoML: what happens from "Run all" to "best model"

## The one idea

AutoML is a **search loop run as a job**. It repeatedly picks a
*pipeline*: a preprocessing step (scaler or encoder) plus an algorithm plus
hyperparameters. It trains and scores that pipeline, records the score, and
uses what it has learned so far to pick the next one. It stops when it hits
a limit. The result is a ranked leaderboard and a best model. It doesn't
register or deploy anything.

## The lab's configuration, line by line

```python
automl.classification(
    compute="aml-cluster",          # trials run as child jobs on the cluster, not on my compute instance
    experiment_name="auto-ml-class-dev",
    training_data=Input(type=MLTABLE, path="azureml:diabetes-training:1"),   # must be MLTable
    target_column_name="Diabetic",  # the label; every other column is a candidate feature
    primary_metric="accuracy",      # what the leaderboard ranks by
    n_cross_validations=5,          # each trial is scored by 5-fold CV (see below)
    enable_model_explainability=True,   # explain the best model after the search
)
.set_limits(timeout_minutes=60,          # whole search stops after 60 min
            trial_timeout_minutes=20,    # a single trial is killed after 20 min
            max_trials=5,                # at most 5 pipelines tried
            enable_early_termination=True)   # stop the search early if scores stop improving
.set_training(blocked_training_algorithms=["LogisticRegression"],
              enable_onnx_compatible_models=True)   # only ONNX-convertible models; also saves an ONNX copy
```

The notebook cell only **submits**. `ml_client.jobs.create_or_update(...)`
returns within seconds with a job ID and Studio URL. Everything else happens
in Azure while the notebook sits idle. Stopping the compute instance now
wouldn't stop the AutoML job.

## Timeline of the job

```
my notebook (compute instance)          workspace                      aml-cluster
──────────────────────────────          ─────────                      ───────────
create_or_update(job) ─────────────────▶ parent AutoML job: Queued
                                          │                           scale 0 → 1 node (cold start, minutes)
                                          ├─ <parent>_setup ─────────▶ load MLTable, detect column types,
                                          │                             run data guardrails, choose featurizers
                                          ├─ <parent>_featurize ─────▶ fit those featurizers on the data
                                          ├─ <parent>_worker_0 ──────▶ long-lived worker on the node; runs trials in turn:
                                          ├─ <parent>_0 (trial) ─────▶   pipeline A, trained 5× (CV)
                                          ├─ <parent>_1 (trial) ─────▶   pipeline B  (chosen using trial 0's score)
                                          ├─ …                          …
                                          ├─ ensemble trial(s) ───────▶ VotingEnsemble / StackEnsemble of the best
                                          ├─ explain child job ───────▶ feature importance for the best model
                                          └─ parent: Completed          nodes idle 120 s → back to 0
```

### 1. Setup and featurization (`featurization="auto"` by default)

AutoML reads the MLTable into a table and **detects a type for each column**:
numeric, categorical, datetime, text, or *ignore*. It then builds the
preprocessing steps that go *inside* every model:
- missing-value imputation (for example, the mean for numeric columns)
- encoding for categorical columns
- dropping useless columns: constant, all-unique IDs, hashes

Because these steps are part of the saved model, the same transformations
run at inference time automatically. That's the key difference from
preprocessing by hand in a notebook, where training and scoring can drift
apart.

✅ **Verified in run `coral_drawer_c6770sv3k6`.** Two separate child jobs:
`_setup` detects types and chooses featurizers, then `_featurize` fits them.
The setup log (`logs/azureml/azureml_automl.log`, from `az ml job download -n
<parent>_setup --all`) showed:

| Col | Column | Unique values | Detected as | Featurizer |
|---|---|---|---|---|
| 0 | `PatientID` | 9,959 | **Numeric** | SimpleImputer |
| 1 | `Pregnancies` | 15 | **Categorical** | StringCast + CountVectorizer (one-hot) |
| 2–8 | the other 7 clinical columns | 56–10,000 | Numeric | SimpleImputer |

The summary line was `Number of Ignore features: 0`. So **AutoML kept
`PatientID` as a numeric feature.** Its ID detection didn't fire on an integer
column, and every model gets an ID as an input. That's noise at best, and a
leakage risk if IDs correlate with the label (for example, if they were
assigned by clinic). The MLflow notebook drops it by hand; AutoML doesn't.
**The fix is on me, not AutoML:** drop ID columns from the MLTable, for
example with a `drop_columns` transformation, or set featurization to
`custom` and mark it *Ignore*. Exam lesson: **automatic featurization isn't a
substitute for knowing your columns.**

The logs refer to columns by index only. AutoML's logs deliberately leave out
column names, so the mapping above comes from the CSV's column order.

### 2. Data guardrails

These are automatic checks run during featurization. Each one reports
**Passed** (no issue), **Done** (issue found *and* AutoML fixed it), or
**Alerted** (issue found, fix it yourself). For classification:
- **Class balancing**: is the minority class too rare?
  ✅ the setup log reports `Minority class size: 3344, Majority class size: 6656`
  (33.4%). ✅ Studio: **Passed**, *"all classes are balanced in your training
  data."* A 1:2 ratio isn't imbalanced by AutoML's definition. That's why the
  guardrail passing doesn't settle the metric question below.
- **Missing feature values**: ✅ **Passed**, *"No feature missing values were
  detected."* Every numeric column still got a `MeanImputer`, which does
  nothing here, but it's part of the model, so it will fill gaps in future
  scoring data.
- **High-cardinality features**: ✅ **Passed**, *"no high cardinality features
  were detected."* As predicted, `PatientID` (9,959 unique values) was **not
  flagged**, because it was typed *Numeric* and this check only looks at
  categorical and text columns. **All green guardrails doesn't mean the
  features are sensible.**

### 3. Trials

Each trial is a child job that trains one pipeline, named like
`MaxAbsScaler, LightGBM` or `StandardScalerWrapper, XGBoostClassifier`. The
next pipeline is chosen by AutoML's recommender, using the scores so far. It
isn't a fixed list.

**How one trial is scored with 5-fold CV:** the data is split into 5 equal
parts. The pipeline is trained 5 times, each time on 4 parts and scored on
the 1 part held out. The trial's `accuracy` is the **average of the 5
scores**. This gives a steadier estimate than one train/test split, at 5×
the compute. Without `n_cross_validations`, AutoML picks a strategy by data
size. For under 20,000 rows it uses cross-validation anyway.

`max_trials=5` is **tiny**. Real searches use dozens. The lab keeps it cheap.

✅ **Verified, parallelism:** `az ml job show` on the parent reports
`limits: max_concurrent_trials: 1, max_nodes: 1`. The defaults applied, so
the cluster **never scaled past 1 node** even though `max_instances` is 2.
Trials run one after another.

✅ **Verified, how trials actually run:** AutoML started a long-lived
**`<parent>_worker_0`** child job on the node. The trials (`<parent>_0`,
`_1`, `_2`, …) are created ahead of time as `NotStarted`, and the worker
runs them in turn. So the "Running" count in Studio shows 2 (the worker plus
the current trial), but only one pipeline is training at a time. One worker
per node means the setup and image-pull cost is paid once, not per trial.

To use both nodes: `set_limits(max_concurrent_trials=2)`. The cluster would
then scale to 2 nodes (2 × 2 vCPU, within quota) and the search would take
about half the time at the same total cost.

### 4. Ensembles

AutoML can add ensemble trials at the end, which combine the best
individual models:
- **VotingEnsemble**: a weighted average of the models' predicted probabilities.
- **StackEnsemble**: a meta-model (logistic regression by default) trained on
  the models' outputs.

They're on by default and often win the leaderboard.

✅ **Verified in run `coral_drawer_c6770sv3k6`:** the ensembles **count toward
`max_trials`**. With `max_trials=5` we got 3 individual algorithms (`_0`–`_2`,
run by the worker) plus **`_3` VotingEnsemble** and **`_4` StackEnsemble**.
The ensembles ran as their own child jobs after the worker finished.

The VotingEnsemble's run properties show how it was built:
`ensembled_iterations [1, 0]`, `ensembled_algorithms ['XGBoostClassifier',
'LightGBM']`, `ensemble_weights [0.2, 0.8]`. So it **left out ExtremeRandomTrees**
(0.831, too weak), and weighted LightGBM 4× more than XGBoost. The weights come
from greedy Caruana selection: models are added (with repeats allowed) as long
as the ensemble's score improves, which gives 4 × LightGBM and 1 × XGBoost.
It scored **0.953**, beating both of its members (0.9518). That's the usual
pattern: combining two strong, slightly different models smooths out their
individual errors.

### 5. Early termination

`enable_early_termination=True` ends the *whole search* early if scores
stop improving. This isn't the Bandit or median-stopping policy of sweep
jobs (lab 03), which kills individual *trials* early.

### 6. Explanation of the best model

✅ **Verified:** the explanation is a separate run,
**`<parent>_ModelExplain`**, and it's a child of the **best trial**
(`_3`, VotingEnsemble), not of the AutoML parent. It **started 26 s after the
parent reported Completed** (00:29:55 → 00:30:21 UTC). So "Completed" in
Studio doesn't mean the Explanations tab is ready yet. The parent's
`ModelExplainRunId` property points to it. Like the trials, `az ml job show`
can't read it (`JobNotSupported`).

With `enable_model_explainability=True`, a final child job computes
**feature importance** for the best model. It appears on the best model's
**Explanations** tab.

✅ **Verified: what the explanation contains.** It's saved as artifacts on the
best trial's run (`_3/explanation/<id>/…`), **twice**:
- **Engineered-feature explanation:** importance per *post-featurization*
  column (`Age_MeanImputer`, `Pregnancies_CharGramCountVectorizer_0` … `_14`).
- **Raw-feature explanation:** the same, rolled up to the original 9 columns.
  `Pregnancies` = the sum of its 15 one-hot columns.

Global importance, raw features (`_3`, VotingEnsemble):

| Feature | Importance |
|---|---|
| Pregnancies | 1.543 (the sum of 15 one-hot columns) |
| Age | 1.069 |
| BMI | 0.701 |
| SerumInsulin | 0.602 |
| PlasmaGlucose | 0.526 |
| TricepsThickness | 0.379 |
| DiastolicBloodPressure | 0.249 |
| DiabetesPedigree | 0.174 |
| **PatientID** | **0.019**, last by a wide margin |

- **PatientID:** the models learned to almost ignore it (about 1% of the total
  importance). It wasn't dropped, but it had little effect. That's luck, not
  a safeguard: an ID that correlated with the label would have been used.
- **My guess was wrong:** I expected `PlasmaGlucose` near the top. It's 5th.
  Always look at the explanation instead of assuming.
- **Pregnancies ranks 1st partly because of how it was encoded:** as a
  Categorical column it became 15 columns, and the raw roll-up adds them
  together.

## The actual run: `coral_drawer_c6770sv3k6`

| Child | Pipeline | Accuracy (5-fold CV) | AUC_weighted |
|---|---|---|---|
| `_0` | MaxAbsScaler + LightGBM | 0.9518 | 0.9905 |
| `_1` | MaxAbsScaler + XGBoostClassifier | 0.9518 | 0.9904 |
| `_2` | MaxAbsScaler + ExtremeRandomTrees | 0.8313 | 0.9432 |
| **`_3`** | **VotingEnsemble** (LightGBM 0.8 + XGBoost 0.2) | **0.9530** ← best | |
| `_4` | StackEnsemble (XGBoost + LightGBM) | 0.9529 | |
| *baseline* | my hand-trained LogisticRegression, 70/30 split (not AutoML) | 0.774 | 0.848 (plain AUC) |

- **Timing:** submitted at 00:18:26 UTC; the parent ran 00:18:40 → 00:29:55,
  so **about 11 minutes**, faster than the 20–40 I estimated. The data is
  small, and early termination wasn't needed because it hit `max_trials`.
- **Nodes:** at most 1, the whole time.
- **Studio leaderboard** (Models + child jobs tab) matched the API exactly.
  Other columns: *Sampling 100%* (each trial trained on all the data; lower
  values would mean subsampling), *Duration* 34–49 s per trial, and a
  *Hyperparameter* summary (for example `min_data_in_leaf: 20`). The
  *Responsible AI* column is empty because no RAI dashboard was generated.
  The toolbar actions (**Deploy**, **Download**, **Explain model**, **View
  generated code**) are greyed out until you select a model row.
- **Every child job in order:** `_setup` → `_featurize` → `_worker_0`
  (running `_0`, `_1`, `_2`) → `_3` → `_4` → `_ModelExplain` (under `_3`).
- **A second automatic follow-up, `_RAI`** (run type `automl.rai`), was
  created alongside `_ModelExplain` (both at 00:29:57 UTC, as children of
  `_3`, under my identity). It builds a **Responsible AI dashboard** for the
  best model and ran on `aml-cluster` from 00:31:22. That's why the cluster
  still had 1 node minutes after the AutoML parent reported Completed. Its
  ID is uppercase `_RAI`; `az ml compute list-nodes` showed it as
  `current_job_name`. **Lesson: "parent Completed" ≠ "cluster idle."**
  **It failed** at 00:38:39 UTC: `User process 'python' exited with status
  code 1`, and `execution-wrapper.log` reports a failed user process. The
  logs we could reach don't name a root cause (they mostly repeat `_3`'s
  training log). We didn't investigate further, because the lab doesn't use
  it: the Explanations tab comes from `_ModelExplain`, which succeeded. So
  the *Responsible AI* column stays empty for this run.
- **Registered model: none.** The best model's files sit in `_3`'s outputs
  until someone registers it.

## Reading trials from outside Studio (verified)

- `az ml job list --parent-job-name <parent>` lists every child: `_setup`,
  `_featurize`, `_worker_0`, `_0` … `_N`.
- `az ml job show -n <parent>_0` **fails** (`JobNotSupported`). Trials aren't
  v2 jobs.
- **Metrics:** use MLflow. Each trial is an MLflow run with the same ID, and
  AutoML logs dozens of metrics (`accuracy`, `AUC_weighted`, `f1_score_*`,
  `precision_*`, …) no matter which primary metric you chose.
- **Pipeline details:** the run-history properties `run_preprocessor`,
  `run_algorithm`, `score`, `iteration`, `model_output_path`,
  `onnx_model_resource`.

## Where things end up

| Thing | Where |
|---|---|
| Leaderboard | Parent job → **Models + child jobs** tab |
| Each trial's metrics (accuracy, AUC, precision, recall, …) | Child job → Metrics. AutoML logs *many* metrics, not only the primary one |
| Each trial's model files (MLflow format, plus ONNX here) | Child job outputs → `workspaceartifactstore` (`azureml` container) |
| Everything on the best trial (`_3`), verified | `outputs/mlflow-model/` (MLmodel, `model.pkl`, `conda.yaml`); `outputs/model.onnx`; `outputs/featurization_summary.json`; `outputs/scoring_file_v_2_0_0.py`; **`outputs/generated_code/script.py`**; `explanation/…` |
| Guardrails + featurization summary | Parent job → **Data guardrails** tab |
| Registered model | **Nowhere yet.** Registering the best model is a separate, deliberate action |

## The best model, opened up (verified)

**`outputs/mlflow-model/MLmodel`**:
- `flavors: python_function + sklearn` (sklearn 1.5.1, Python 3.10.19,
  MLflow 2.15.1)
- `metadata: azureml.engine: automl`,
  `azureml.base_image: mcr.microsoft.com/azureml/curated/ai-ml-automl:41`
- **`signature.inputs` lists all 9 columns, including `PatientID` (`required:
  true`)**
- output: `bool`

**The PatientID mistake carries into deployment.** If this model is
deployed, every caller has to send a `PatientID`, a field the model barely
uses, and requests without it fail schema validation. A featurization mistake
at training time turns into an API contract problem later.

**`conda.yaml`** pins about 200 packages, including `azureml-train-automl
1.61`, `lightgbm 4.6.0` and `xgboost 1.5.2`. That's the environment the model
needs to be served in, and why AutoML models use a large curated AutoML base
image.

**`outputs/generated_code/script.py`** (544 lines) is **AutoML's code
generation**: a standalone training script that rebuilds this exact
pipeline:
- the column groups, with `PatientID` in the numeric group
- `XGBClassifier(...)` and `LGBMClassifier(...)` with their tuned
  hyperparameters
- `PreFittedSoftVotingClassifier(weights=[0.2, 0.8])`

It lets you take AutoML's winner, edit it (for example, drop `PatientID`),
and run it as a normal command job. Exam angle: *"view/generate the training
code of the best AutoML model"* is a real Studio feature (Model → **View
generated code**).

## Why `accuracy` is a questionable primary metric here

With 33.4% positives, a model that always predicts "not diabetic" scores
66.6% accuracy. Accuracy depends on a threshold and is sensitive to class
balance. Microsoft's own guidance suggests **`AUC_weighted`** for imbalanced
classification. My production project uses AUC for exactly this reason: its
data is far more skewed, where always-negative gets about 91.5%. The lab's
data is mild enough that accuracy still ranks models sensibly, but on the
exam, "imbalanced classes" + "which primary metric" → `AUC_weighted`.

## Exam cheat-sheet

- AutoML needs **MLTable** training data (SDK/CLI v2).
- Task types: classification, regression, forecasting, plus CV and NLP tasks.
- **Limits:** `timeout_minutes`, `trial_timeout_minutes`, `max_trials`,
  `max_concurrent_trials`, `enable_early_termination`.
- **Block or allow** algorithms: `blocked_training_algorithms` /
  `allowed_training_algorithms`.
- **Validation:** `n_cross_validations`, or `validation_data`, or a
  size-based automatic choice.
- **Featurization:** `auto` (default), `off`, or custom per column.
- **Guardrail statuses:** Passed / Done / Alerted.
- **Output:** a best model in MLflow format, ready to register and deploy.
  AutoML doesn't register or deploy for you.
