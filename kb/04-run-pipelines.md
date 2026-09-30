# Lab 04: Run pipelines

Source: [docs/04-run-pipelines.md](../docs/04-run-pipelines.md)

Microsoft Learn module: [Run pipelines in Azure Machine Learning](https://learn.microsoft.com/en-us/training/modules/run-pipelines-azure-machine-learning/)
(module 5 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/), dated 2026-08-27).
The lab is its unit 5. All 7 units read.

Mechanics: [components and pipelines](mechanics/components-and-pipelines.md) · [command jobs](mechanics/command-jobs.md)

## 1. What this lab does

One notebook, `experimentation/Run a pipeline job.ipynb`. It writes two
scripts (`prep-data.py`: drop missing rows and MinMax-scale; `train-model.py`:
LogisticRegression, saved as an MLflow model) plus one **component YAML**
each. It loads them with `load_component`, chains them with the `@pipeline()`
decorator (prep's output → train's input), and submits the result as a
**pipeline job** whose two steps run as child jobs on `aml-cluster`.

## 2. Steps I actually ran

Reusing lab 01's workspace and the clone on its file share, so the lab's
"provision" and "clone" sections are skipped.

### 2.1 Run scripts as a pipeline job (Studio, me)

1. Opened `experimentation/Run a pipeline job.ipynb`, set the kernel to
   **Python 3.10 - AzureML**, and ran all cells.
2. The notebook:
   - `%%writefile` → `experimentation/src/prep-data.py` and `src/train-model.py`
     (into the same `src/` as lab 03's `train.py`)
   - `%%writefile` → `experimentation/prep-data.yml` and `train-model.yml`
     (the component definitions)
   - `load_component(...)` for both (**loaded, not registered**)
   - `@pipeline() def diabetes_classification(pipeline_job_input)`: prep's
     `outputs.output_data` → train's `training_data`
   - set both outputs to `mode = "upload"`, `settings.default_compute = "aml-cluster"`,
     `settings.default_datastore = "workspaceblobstore"`
   - `ml_client.jobs.create_or_update(pipeline_job, experiment_name="pipeline_diabetes")`
     → **`calm_ticket_wcbhgt8w7n`**, input `azureml:diabetes-data:1`
3. Claude watched it (`az ml job list --parent-job-name`, cluster node
   states) and inspected it afterwards (run history, MLflow, blob storage):

| Step | Ran (UTC) | Output |
|---|---|---|
| `clean_data` | 02:11:02 → 02:13:11 (cold node) | `azureml/8ba7c1f5…/output_data/diabetes.csv`: 10,000 rows, 7 features scaled 0–1, `Age` unscaled |
| `train_model` | 02:13:36 → 02:13:59 (warm node) | `azureml/aa0f7853…/model_output/` (MLflow model); printed Accuracy 0.774, AUC 0.84849 |

   Details in [mechanics/components-and-pipelines.md](mechanics/components-and-pipelines.md#what-actually-happened-pipeline-job-calm_ticket_wcbhgt8w7n).

## 3. What broke and how we fixed it

The pipeline itself ran cleanly. Things to know:
- **`az ml job download --output-name pipeline_job_trained_model` crashed**
  with `TypeError: BatchGetResolvedUrisDto.__init__() got an unexpected
  keyword argument 'values'` (CLI `ml` extension 2.44.1). The data output
  downloaded fine; the `mlflow_model` output didn't. Workaround: list the
  blobs directly in `workspaceblobstore` under
  `azureml/<child-run-id>/model_output/`.
- **`az ml job show` on pipeline steps shows almost nothing**
  (`code`, `component`, times and outputs all `null`). The step details
  (module name and version, snapshot ID, times) are in the **run-history
  API**, and in Studio's pipeline graph.
- **The test metrics are printed, not logged.** `train-model.py`'s
  `eval_model` only `print`s Accuracy and AUC, so Studio shows only autolog's
  `training_*` metrics. Lab code, left as is.
- **My prediction was wrong:** I expected scaling to change accuracy. It
  stayed 0.774; only AUC moved in the 4th decimal.
- **The module's exercise mentions scheduling, the lab doesn't:** the
  exercise unit says "build, run, and **schedule** a pipeline", but neither
  the lab doc nor the notebook creates a schedule. **Decision:** not run
  (my call). Documented instead, in full, in
  [mechanics/components-and-pipelines.md → Scheduling](mechanics/components-and-pipelines.md#scheduling-automatic-retraining):
  real SDK signatures, CLI commands, and my production project's live
  `train_schedule.yml`.

## 4. Exam mapping

Domain 1: *Create and manage components*. Domain 2: *Implement training
pipelines*; also *Run model training scripts*.

- **Component** = metadata (name, version, display name, type) + interface
  (typed inputs/outputs) + command, code and environment. Two files: the
  **script** and the **YAML** (or the `@command_component` decorator). Why
  use them: **to build pipelines** and **to share ready-to-go code**.
- **Loaded vs. registered:** `load_component("x.yml")` is enough to use it in
  your own pipeline; `ml_client.components.create_or_update(c)` (or
  `az ml component create -f x.yml`) registers it so others can reuse it.
- **Pipeline** = components wired output → input with `@pipeline()` (or
  pipeline YAML). The return dict defines the pipeline outputs.
  `print(pipeline_job)` shows the generated YAML (`${{parent.inputs…}}`,
  `${{parent.outputs…}}`). Module assessment: step 2's input is
  **`prep_data.outputs.output_data`**.
- **Pipeline job:** each component runs as a **child job**. Configure
  `outputs.<name>.mode`, `settings.default_compute`,
  `settings.default_datastore` before submitting.
- **Troubleshooting:** the pipeline config fails → the pipeline job's logs;
  a component fails → **that child job's** logs.
- **Scheduling (module only):** `JobSchedule(name, trigger, create_job=pipeline_job)`
  with **`RecurrenceTrigger(frequency, interval)`** (minute/hour/day/week/month)
  or `CronTrigger`; `ml_client.schedules.begin_create_or_update`. To delete:
  **disable first**, then delete. Module assessment: the simple weekly
  schedule → **`RecurrenceTrigger`**.
- "Pipeline" in Azure ML = ML training steps. A GitHub or Azure DevOps
  pipeline builds and releases software; a Synapse or Data Factory pipeline
  ingests data. They can call each other (module intro).

**What the Microsoft Learn module says, checked against our run**

| Module says | Our run | Take-away |
|---|---|---|
| The example component uses `AzureML-sklearn-0.24-ubuntu18.04-py37-cpu@latest` | The lab uses `…sklearn-1.0-ubuntu20.04-py38…` (really scikit-learn 1.0.2) | Know the pattern, not a specific environment name |
| "To make the component accessible to other users, register it" (unit 2) | Loaded only; `az ml component list` empty | Loaded = private to your pipeline; registered = shareable |
| Each component runs as a child job (unit 3) | `clean_data`, `train_model` child jobs, named after the pipeline variables | Matches |
| The exercise: "build, run, **and schedule**" (unit 5) | No schedule in the lab | Covered by the theory and the assessment; optional extra |
| Troubleshoot through the child job's logs (unit 4) | Step details were readable only through run history / Studio, not `az ml job show` | Studio's pipeline graph is the practical way in |

*All 7 module units read (1–4 theory, 5 exercise → links to the published
`04-run-pipelines.html` our `docs/` builds, 6 assessment, 7 summary), dated
2026-08-27.*

**Module assessment (unit 6)**, two questions:
1. Input to step 2 (training) → **`prep_data.outputs.output_data`**.
2. The simplest class to run a pipeline weekly → **`RecurrenceTrigger`**.

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

| | Lab | My project (`ml/components/`, `ml/pipelines/train_pipeline.yml`) | Microsoft's recommended answer |
|---|---|---|---|
| Steps | 2: prep → train | 3: prep → train → **evaluate** (AUC gate) | 📘 Split into steps that change or get reused independently |
| Component definition | YAML written by the notebook, **loaded only** (anonymous) | YAML in Git, **registered and versioned** (`diabetes_prep:3`, …) | 📘 **Register** components meant for reuse |
| Pipeline definition | Python `@pipeline()` in a notebook | Pipeline YAML, submitted with `az ml job create` from CI | 📘 Both; YAML suits CI/CD and review |
| Code folder | 🧪 One shared `src/` holding both scripts **plus lab 03's `train.py`** | One small folder per component | 📘 A minimal code folder per component |
| Scaling | 🧪 MinMax fit on **all** data before the split; `Age` left out | One-hot encoding inside a sklearn `Pipeline`, fit on training data | 📘 Fit preprocessing on **training data only** (no leakage); keep it inside the model so inference applies it too |
| Test metrics | 🧪 Printed, not logged | `evaluate.py` logs them and writes `metrics.json`, and **fails the pipeline below AUC 0.95** | 📘 Log held-out metrics; a quality gate is 🛠 my addition |
| Model output | An MLflow model in the pipeline output, **not registered** | Registered, then shared to `mlreg-diabetes` | 📘 Register the MLflow model (lab 07, Domain 2) |
| Schedule | None | `train_schedule.yml`, weekly, Sundays 04:00 UTC | 📘 **`JobSchedule` + `RecurrenceTrigger`/`CronTrigger`** for retraining |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> What are the three parts of a component definition?<br><br>A) Script, data, model<br>B) Metadata (name, version…), interface (typed inputs/outputs), and command + code + environment<br>C) Compute, datastore, schedule<br>D) Pipeline, job, experiment</summary>

> **✅ Answer: B.** Our <code>prep-data.yml</code> has all three: <code>name/version/type</code>, <code>inputs/outputs</code>, and <code>command/code/environment</code>.
</details>

---

<details>
<summary><strong>2.</strong> A two-step pipeline: step 1 prepares data, step 2 trains. What do you pass as step 2's <code>training_data</code>?<br><br>A) <code>pipeline_job_input</code><br>B) <code>prep_data.outputs.output_data</code><br>C) <code>train_model.outputs.model_output</code><br>D) The raw data asset again</summary>

> **✅ Answer: B.** The module assessment's question. That wiring is also what makes step 2 wait for step 1.
</details>

---

<details>
<summary><strong>3.</strong> The lab's notebook loads both components with <code>load_component</code> and runs the pipeline. Afterwards, <code>az ml component list</code> shows…<br><br>A) <code>prep_data:1</code> and <code>train_model:1</code><br>B) Nothing: loaded components are used anonymously; registering needs <code>ml_client.components.create_or_update</code><br>C) Only <code>train_model</code><br>D) An error</summary>

> **✅ Answer: B.** Our list was empty, even though each step recorded a <code>moduleid</code> and <code>moduleName</code>.
</details>

---

<details>
<summary><strong>4.</strong> In our run, when did the <code>train_model</code> child job appear?<br><br>A) At submission, alongside <code>clean_data</code><br>B) Only after <code>clean_data</code> completed, because its input didn't exist before<br>C) After the parent completed<br>D) Never; it ran inside <code>clean_data</code></summary>

> **✅ Answer: B.** Order comes from the data dependency. Independent steps could run in parallel.
</details>

---

<details>
<summary><strong>5.</strong> The <code>train_model</code> step fails but <code>clean_data</code> succeeded. Where do you look first?<br><br>A) The pipeline job's own logs<br>B) The <code>train_model</code> child job's outputs and logs (<code>user_logs/std_log.txt</code>)<br>C) The compute instance terminal<br>D) The data asset</summary>

> **✅ Answer: B.** Pipeline config errors show on the parent; component errors show on that component's child job (module unit 4).
</details>

---

<details>
<summary><strong>6.</strong> You want the pipeline to retrain every Sunday. Which classes do you use?<br><br>A) <code>RecurrencePattern</code> only<br>B) <code>RecurrenceTrigger(frequency="week", interval=1)</code> wrapped in a <code>JobSchedule(create_job=pipeline_job)</code>, then <code>ml_client.schedules.begin_create_or_update</code><br>C) A sweep job<br>D) <code>pipeline_job.settings.schedule</code></summary>

> **✅ Answer: B.** (A <code>CronTrigger</code> also works.) To delete a schedule: <code>begin_disable</code> first, then <code>begin_delete</code>.
</details>

---

<details>
<summary><strong>7.</strong> <code>pipeline_job.settings.default_compute = "aml-cluster"</code> means…<br><br>A) Every step must run on <code>aml-cluster</code><br>B) Steps that don't set their own compute run on <code>aml-cluster</code><br>C) The pipeline's parent job runs there<br>D) Outputs are stored there</summary>

> **✅ Answer: B.** Outputs follow <code>default_datastore</code> (<code>workspaceblobstore</code>): ours landed under <code>azureml/&lt;child-run-id&gt;/&lt;output-name&gt;/</code>.
</details>

---

<details>
<summary><strong>8.</strong> The prep step fits <code>MinMaxScaler</code> on the whole dataset, and the train step then splits train/test. What's the problem?<br><br>A) None<br>B) Data leakage: the scaler's min/max values include test rows, so the test set isn't truly unseen. Fit preprocessing on training data only<br>C) MinMax can't handle integers<br>D) The pipeline will fail</summary>

> **✅ Answer: B.** Small here (accuracy unchanged), but it's the classic pipeline-design mistake. My project keeps the encoding inside a sklearn <code>Pipeline</code> fit on training data.
</details>
