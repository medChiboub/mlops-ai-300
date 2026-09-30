# Lab 03: Hyperparameter tuning with a sweep job

Source: [docs/03-hyperparameter-tuning.md](../docs/03-hyperparameter-tuning.md)

Microsoft Learn module: [Perform hyperparameter tuning with Azure Machine Learning](https://learn.microsoft.com/en-us/training/modules/perform-hyperparameter-tuning-azure-machine-learning-pipelines/)
(module 4 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/), dated 2026-08-27).
The lab is its unit 6.

Mechanics: [sweep jobs](mechanics/sweep-jobs.md) · [command jobs](mechanics/command-jobs.md)

## 1. What this lab does

One notebook, `experimentation/Hyperparameter tuning.ipynb`. It writes a new
training script (`experimentation/src/train.py`) with a `--reg_rate`
argument, tests it once as a command job, then turns that command job into
a **sweep job**. The sweep is a grid search over `reg_rate` ∈ {0.01, 0.1, 1},
running each value as its own trial on `aml-cluster`, two at a time, and
picks the best by the logged metric `training_accuracy_score`.

## 2. Steps I actually ran

Reusing lab 01's workspace and the clone on its file share, so the lab's
"provision" and "clone" sections are skipped.

### 2.1 Tune hyperparameters with a sweep job (Studio, me)

1. Opened `experimentation/Hyperparameter tuning.ipynb`, set the kernel to
   **Python 3.10 - AzureML** (the notebook shows `azure-ai-ml 1.35.0` installed
   in `/anaconda/envs/azureml_py38`), and ran all cells.
2. The notebook:
   - `%%writefile $script_folder/train.py` → created
     **`experimentation/src/train.py`** (a new folder; not the root `src/`)
   - submitted a **test command job** `jovial_insect_nygrdp1wqj`
     (`diabetes-training`, `reg_rate` 0.01, input `azureml:diabetes-data:1`)
     → Completed, accuracy 0.774
   - `job(reg_rate=Choice(values=[0.01, 0.1, 1]))` →
     `.sweep(sampling_algorithm="grid", primary_metric="training_accuracy_score", goal="Maximize")`
     → `set_limits(max_total_trials=4, max_concurrent_trials=2, timeout=7200)`
     → submitted **sweep `quiet_parcel_r5zv90jjw2`** (experiment `sweep-diabetes`)
3. Claude watched it from the CLI (`az ml job list --parent-job-name`, cluster
   `nodeStateCounts`) and read the results through `az ml job show` and the
   MLflow API:

| Trial | `reg_rate` | `training_accuracy_score` | AUC |
|---|---|---|---|
| **`_0`** (best) | 0.01 | 0.774 | 0.8483 |
| `_1` | 0.1 | 0.774 | 0.8483 |
| `_2` | 1.0 | 0.7727 | 0.8480 |

   Full timings and details in [mechanics/sweep-jobs.md](mechanics/sweep-jobs.md#what-actually-happened-sweep-quiet_parcel_r5zv90jjw2).

## 3. What broke and how we fixed it

Nothing failed. Things that surprised us:
- **A wrong statement of mine, corrected before the run.** I'd said the sweep
  optimizes an autolog *training* metric. The notebook's `train.py` logs
  `training_accuracy_score` computed on **`X_test`**, so it's held-out
  accuracy with a misleading name. Read the script, not the metric name.
- **Stored sampling algorithm `Random` vs. `grid` in the notebook.** The SDK
  (1.35.0 and 1.34.1, rebuilt locally in a scratch venv without submitting)
  sends `Grid`, and the run behaved like a grid (3 unique trials, stopped at 3
  of 4). **Settled: Studio's Overview shows *Grid*,** while every REST API version
  (2023-10 → 2025-09) and `az ml job show` return `Random`. The sweep ran as a
  grid; the jobs API reads the field back wrongly. Lesson: for a sweep's
  sampling method, trust Studio, not the CLI. Details in the mechanics file.
- **The test job and the sweep competed for nodes.** "Run all" submitted
  both at once; the notebook's text says to wait for the test job first.
  Harmless here (it only delayed trial `_0`), but the notebook's own advice
  is sound: test before sweeping.
- **The notebook's text doesn't match its code:** it says the test job uses
  `reg_rate` 0.1, but the code passes 0.01.
- **The metric is tied** (0.774 for both 0.01 and 0.1). Here the order of the
  trials picked the winner; AUC would have picked 0.1.

## 4. Exam mapping

Domain 2: *Automate hyperparameter tuning*; also *Run model training
scripts* and *Compare model performance across jobs*.

- **Parameter vs. hyperparameter** (module unit 1): *parameters* are values
  the model **learns from the training data** (LogisticRegression's
  coefficients); *hyperparameters* **configure how training runs** and aren't
  learned from the data (regularization rate; learning rate and batch size
  for neural networks). Tuning = training the same algorithm on the same
  data with different hyperparameter values, then picking the best by one
  metric. A **sweep job** runs one **trial** per combination.
- **The script must** take each hyperparameter as an argument and **log the
  target metric with `mlflow.log_metric`** under the exact `primary_metric`
  name (module assessment: not `print`, not `logging.info`).
- **Build:** base `command()` → `job(param=Choice(...))` (the search space) →
  `.sweep(compute, sampling_algorithm, primary_metric, goal)` →
  `set_limits(max_total_trials, max_concurrent_trials, timeout)` →
  optional `early_termination` → `ml_client.create_or_update`.
- **Search space:** discrete = `Choice` (a list / `range` / tuple) or
  `QUniform`/`QLogUniform`/`QNormal`/`QLogNormal`; continuous = `Uniform`,
  `LogUniform`, `Normal`, `LogNormal`.
- **Sampling:** **grid** = every combination, discrete only (module
  assessment); **random** = mixed spaces, **Sobol** =
  `RandomSamplingAlgorithm(seed=…, rule="sobol")` for reproducibility;
  **Bayesian** = learns from earlier trials, only `choice`/`uniform`/`quniform`.
- **Early termination** (per trial, not the whole sweep): **Bandit**
  (`slack_factor`/`slack_amount`), **Median stopping**, **Truncation
  selection** (`truncation_percentage`); all use `evaluation_interval` +
  `delay_evaluation`. Only useful when the metric is logged repeatedly, and
  not needed for a small grid.
- **Review:** the parent job's **Trials** tab and charts; each trial is a
  normal job and MLflow run.

**What the Microsoft Learn module says, checked against our run**

| Module says | Our run | Take-away |
|---|---|---|
| The example's base job uses environment `AzureML-sklearn-1.5@latest` (unit 5) | The lab uses `AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest` | Curated names changed; know the pattern, not a specific name |
| The example logs `Accuracy` and sweeps on `primary_metric="Accuracy"` | The lab logs **test** accuracy under the name `training_accuracy_score` | The name must *match*; it doesn't have to *describe* the metric. Check what's actually computed |
| Early termination is unnecessary for a small grid (the example: 6 trials) | 3-trial grid, no policy | Matches |
| Grid tries every combination | 3 trials for 3 values, even with `max_total_trials=4`. Studio shows *Grid*; the CLI/REST read-back says `Random` | Behaviour matches the module; the API field is wrong |

*All 8 module units read (1–5 theory, 6 exercise → links to the same
published `03-hyperparameter-tuning.html` our `docs/` builds, 7 assessment,
8 summary), versions dated 2026-08-27.*

**Module assessment (unit 7)**, two questions:
1. Try every combination of specified discrete values → **grid sampling**.
2. Tune on a target metric named "AUC" → **`mlflow.log_metric()`** in the script.

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

| | Lab | My project (`ml/experiments/sweep/`) | Microsoft's recommended answer |
|---|---|---|---|
| Hyperparameter | `reg_rate` ∈ {0.01, 0.1, 1} for LogisticRegression | `max_depth` ∈ {5, 10, 20, 50} for RandomForest | 📘 Tune what actually affects the model; a small discrete set → grid |
| Primary metric | 🧪 test accuracy, logged under a *training*-sounding name | **AUC**, the same metric as the pipeline's promotion gate | 📘 **The metric you'll actually judge the model by**, measured on held-out data. `AUC_weighted`/AUC for imbalanced classes |
| Result | A tie at 0.774 (0.01 vs. 0.1); the order of the trials picked the winner | Best `max_depth=10`, AUC 0.9765 vs. 0.9674 for the unbounded default | A tie is a sign the metric or search space isn't discriminating |
| Environment and data refs | `…@latest` environment, `diabetes-data:1` | Pinned `diabetes-train-env:1`, `diabetes-raw:1`: pinning avoided an SDK bug resolving `@latest` in sweep jobs | 📘 **Pin versions** for reproducibility (`@latest` worked fine for us here) |
| What happens to the best trial | Nothing; you read the Trials tab | Nothing either; applying `max_depth=10` to `train.py` is a deliberate manual decision | 📘 A sweep finds values; **registering and deploying are separate steps** |
| Test before sweeping | The notebook says to, but "Run all" sends both at once | Components tested in the pipeline first | 📘 Run the base command job once, then sweep |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> A sweep uses <code>primary_metric="AUC"</code>. The script computes AUC and <code>print()</code>s it but never logs it. What happens?<br><br>A) The sweep reads AUC from the logs<br>B) Trials run, but the sweep has no metric to compare, so it can't pick a best trial<br>C) The sweep uses accuracy instead<br>D) Azure ML logs it automatically</summary>

> **✅ Answer: B.** The metric must be logged with <code>mlflow.log_metric("AUC", …)</code> under exactly the <code>primary_metric</code> name (module assessment).
</details>

---

<details>
<summary><strong>2.</strong> Search space <code>Choice(values=[0.01, 0.1, 1])</code>, grid sampling, <code>max_total_trials=4</code>. How many trials run?<br><br>A) 4<br>B) 3: the grid has only 3 combinations, and the limit is a ceiling<br>C) 1<br>D) 12</summary>

> **✅ Answer: B.** Our sweep created exactly <code>_0</code>, <code>_1</code>, <code>_2</code>.
</details>

---

<details>
<summary><strong>3.</strong> You want to tune a learning rate drawn from <code>Normal(mu=10, sigma=3)</code>. Which sampling can't you use?<br><br>A) Random<br>B) Random with Sobol<br>C) Grid, and also Bayesian (which only supports <code>choice</code>, <code>uniform</code>, <code>quniform</code>)<br>D) None, all work</summary>

> **✅ Answer: C.** Grid needs discrete values only; Bayesian is limited to choice/uniform/quniform. Random handles mixed and continuous spaces.
</details>

---

<details>
<summary><strong>4.</strong> You need to be able to reproduce a random-sampling sweep exactly. What do you use?<br><br>A) Grid<br>B) <code>RandomSamplingAlgorithm(seed=123, rule="sobol")</code><br>C) Bayesian with a seed<br>D) <code>max_concurrent_trials=1</code></summary>

> **✅ Answer: B.** Sobol is seeded random sampling that also spreads the values more evenly.
</details>

---

<details>
<summary><strong>5.</strong> A Bandit policy with <code>slack_amount=0.2</code> is active. At an evaluation interval the best trial has accuracy 0.9. A trial reports 0.65. What happens?<br><br>A) The whole sweep stops<br>B) Only that trial is stopped, because it's below 0.9 − 0.2 = 0.7<br>C) Nothing until all trials finish<br>D) The best trial is stopped</summary>

> **✅ Answer: B.** Early-termination policies stop individual trials, never the sweep. They need the metric logged repeatedly to have anything to compare.
</details>

---

<details>
<summary><strong>6.</strong> In our sweep, <code>reg_rate</code> 0.01 and 0.1 both scored accuracy 0.774, and <code>_0</code> (0.01) was reported as best. What would have changed the winner?<br><br>A) Nothing, 0.01 is always better<br>B) Using <code>primary_metric="AUC"</code>: 0.1 had a marginally higher AUC<br>C) Adding more nodes<br>D) Switching to Bayesian sampling</summary>

> **✅ Answer: B.** The primary metric defines "best". A tie means the order of the trials decided it.
</details>

---

<details>
<summary><strong>7.</strong> Trial <code>_1</code> took about 2 minutes, while <code>_0</code> and <code>_2</code> took about 17 seconds. Why?<br><br>A) Higher <code>reg_rate</code> trains faster<br>B) <code>_1</code> ran on a fresh node that had to pull the environment image; the others reused warm nodes that already had it<br>C) <code>_1</code> used more data<br>D) Early termination stopped the others</summary>

> **✅ Answer: B.** Environment setup, not training, dominates small jobs. It's the same reason the cluster's idle time before scale-down (120 s) matters.
</details>

---

<details>
<summary><strong>8.</strong> Where is the sweep's winning model registered?<br><br>A) Automatically in Models<br>B) In the shared registry<br>C) Nowhere: a sweep only finds the best values; registering is a separate step<br>D) In the compute instance</summary>

> **✅ Answer: C.** Same as AutoML: finding ≠ registering. Our script doesn't even log a model (no autolog, no <code>log_model</code>).
</details>
