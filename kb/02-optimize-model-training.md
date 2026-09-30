# Lab 02: Optimize model training

Source: [docs/02-optimize-model-training.md](../docs/02-optimize-model-training.md)

Microsoft Learn module: [Run training scripts and track models with MLflow in Azure Machine Learning](https://learn.microsoft.com/en-us/training/modules/run-training-scripts-track-models-mlflow/)
(module 3 of [Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/)).
The lab is its unit 7.

Mechanics: [command jobs](mechanics/command-jobs.md) · [MLflow tracking](mechanics/mlflow-tracking.md) · [compute](mechanics/compute.md)

## 1. What this lab does

Takes the notebook code from lab 01 toward production: export a notebook to
a `.py` script, run a parameterised version of it (`src/train-model-parameters.py`)
in the compute instance's terminal, then submit that same script as a
**command job** on `aml-cluster`. The job logs a parameter, two metrics and a
ROC plot with MLflow, and Azure ML records its code snapshot, environment,
inputs and logs.

## 2. Steps I actually ran

Reusing lab 01's workspace and the clone on its file share, so the lab's
"provision" and "clone" sections are skipped.

### 2.1 Convert a notebook to a script (Studio, me)

1. Opened `experimentation/Train classification model.ipynb` (kernel
   **Python 3.10 - AzureML**) and ran all cells.
2. **☰** → **Export as** → **Python (.py)** → `train-classification-model`,
   which created `experimentation/train-classification-model.py` on the file share.
3. **▷▷** (save and run script in terminal), which ran
   `python train-classification-model.py` in the compute instance terminal:

   ```
   Reading data...
   Splitting data...
   Training model...
   Accuracy: 0.7736666666666666
   AUC: 0.8483830041295587
   ```
4. `which python && python --version` → `/anaconda/envs/azureml_py38/bin/python`,
   **Python 3.10.0**.

What the export actually produced (Claude downloaded it from the share):
- **Every cell pasted into one file, nothing more.** Markdown cells became
  comments, and each cell is marked `# In[1]:` … `# In[7]:`. There are no
  functions and no arguments, and the data path
  (`'../data/diabetes-data/diabetes.csv'`) and `C=1/0.1` are hardcoded. So it
  only works when run from `experimentation/`.
- **Code left over from exploring still runs, but shows nothing:**
  `df.head()` (only a notebook displays a cell's last value) and the whole
  ROC plotting block (no `plt.show()` or `savefig`). That's the module's
  "remove nonessential code" rule in action.
- **The same numbers as in lab 01** (0.7737 / 0.8484), because the split uses
  `random_state=0`.

### 2.2 Test a script with the terminal (Studio, me)

**Where `src/` comes from (it isn't generated from my export).** The files in
`src/` were written by Microsoft and have been in the repo since the clone.
The lab uses the two scripts as a before and after:

| | My export: `experimentation/train-classification-model.py` | Microsoft's: `src/train-model-parameters.py` |
|---|---|---|
| Who made it | Me, with Studio **Export as .py** (section 2.1) | Already in the repo |
| What it is | Every notebook cell pasted into one file | The same code, cleaned up by hand |
| Data path | Hardcoded `'../data/diabetes-data/diabetes.csv'` | Argument `--training_data <path>` |
| Regularization | Hardcoded `C=1/0.1` | Argument `--reg_rate` (default 0.01) |
| Structure | One block, top to bottom | `main()` + 4 functions: `get_data`, `split_data`, `train_model`, `eval_model`; `parse_args()` reads the arguments |
| Leftovers | `df.head()`, plot code that shows nothing | Removed |
| Tracking | None | MLflow: `log_param("Regularization rate")`, `log_metric("Accuracy")`, `log_metric("AUC")`, `log_artifact("ROC-Curve.png")` |

The logic is the same (read `diabetes.csv`, split 70/30, LogisticRegression,
accuracy + AUC). `src/` is what the export becomes after the module's three
rules: remove nonessential code, refactor into functions, add parameters. The
lab hands it over ready-made instead of making me rewrite it.

The other files in `src/` belong to later labs: `job.yml` (labs 06–07, used by
the GitHub workflows), `deploy_to_online_endpoint.py` and `model/` (lab 07).

How lab 02 uses it: **this section** runs `train-model-parameters.py` in the
terminal with `--training_data`; **the next section** runs the *same file* as
a command job on the cluster, passing the path the same way.

Steps I ran:
1. Opened `src/train-model-parameters.py` → **▷▷**. Studio opened a second
   terminal already in `src/` and ran `python train-model-parameters.py` with
   no arguments → failed as intended:
   ```
   Reading data...
   File ".../src/train-model-parameters.py", line 35, in get_data
       if os.path.isdir(path):
   TypeError: stat: path should be string, bytes, os.PathLike or integer, not NoneType
   ```
   `--training_data` has no default, so `path` was `None`.
2. Typed the lab's `cd mslearn-mlops/src/` → `No such file or directory` (the
   terminal was already in `src/`), then
   `python train-model-parameters.py --training_data ../data/diabetes-data/diabetes.csv`:
   ```
   Reading data...
   Splitting data...
   Training model...
   Accuracy: 0.774
   AUC: 0.8484934573859395
   🏃 View run epic_floor_prhg1jbc at: https://canadaeast.api.azureml.ms/mlflow/...
   🧪 View experiment at: ...
   ```

What happened underneath (Claude checked through the MLflow API and the file share):
- **The terminal run was logged to the workspace, into an experiment called
  `Default`.** Run `epic_floor_prhg1jbc`: param `Regularization rate = 0.01`,
  metrics `Accuracy 0.774`, `AUC 0.8485`, artifact `ROC-Curve.png`. The script
  never calls `mlflow.start_run()` or `set_experiment()`. MLflow **starts a
  run automatically** on the first `log_*` call, and on a compute instance
  the tracking URI already points at the workspace. With no experiment set,
  it uses `Default`. So even a quick terminal test leaves a record. That's
  useful, but it clutters `Default` if you forget.
- **The numbers differ from section 2.1** (0.7737 → 0.774) because the
  default `reg_rate` here is **0.01** vs. the hardcoded 0.1 in the export. It
  matches lab 01's MLflow run 3 (reg 0.01 → 0.7740).
- **`src/ROC-Curve.png` now exists** (written by `savefig` before
  `log_artifact`). `src/` is the `code` folder of the next section's command
  job, so this PNG will be uploaded with the job's code snapshot too.
  Studio's `.amlignore` in `src/` decides what's left out.
- **The real path of `~/cloudfiles/code`** shows in the traceback:
  `/mnt/batch/tasks/shared/LS_root/mounts/clusters/<compute-instance>/code/Users/…`,
  the workspace file share mounted on the VM.
- **▷▷ saves the file before running it**: the script's last-modified time
  changed to 01:20:55 UTC even though its content didn't.

### 2.3 Run a script as a command job (Studio, me)

1. Opened `experimentation/Run script as a command job.ipynb` (kernel
   **Python 3.10 - AzureML**) and ran **all** cells, including the optional
   autolog cell, but **without** first adding `mlflow.autolog()` to the script.
2. Two jobs in experiment `diabetes-training`, both on `aml-cluster`:

| Job | Display name | Queued → started → finished (UTC) | Accuracy | AUC |
|---|---|---|---|---|
| `musing_reggae_mnbbwkylvf` | diabetes-train-script | 01:24:13 → 01:27:04 → 01:29:14 | 0.774 | 0.84828 |
| `lime_train_h5fzjbwn0n` | diabetes-train-mlflow | 01:24:14 → 01:27:28 → 01:29:38 | 0.774 | 0.84828 |

   Both logged the same things: param `Regularization rate = 0.01`, metrics
   `Accuracy`, `AUC`, artifact `ROC-Curve.png`, plus `user_logs/std_log.txt`
   and `system_logs/`. They're identical because the autolog edit was skipped.
3. **Optional autolog, done properly:** added `mlflow.autolog()` as the
   first line of `main()` in `src/train-model-parameters.py`, saved, and
   reran only the last cell → job **`epic_king_fhy758f6cn`** (01:35:46 →
   01:40:14 UTC). It logged 16 params (vs. 1), 9 metrics (vs. 2) and a
   **`model/`** folder, `estimator.html` and 3 training charts. Full
   comparison in [mechanics/command-jobs.md](mechanics/command-jobs.md#custom-logging-vs-autolog-in-a-job-verified).
4. Claude followed them from the CLI (`az ml job show`, cluster
   `nodeStateCounts`) and inspected them afterwards through the MLflow and
   run-history APIs and the code asset's blob container. Details in
   [mechanics/command-jobs.md](mechanics/command-jobs.md).

What the jobs showed:
- **Cold start about 3 min**, then about 2 min per job. The cluster scaled to
  **2 nodes** for the first time (one job each), so with the compute instance
  that's **6/6** DSv2 quota cores.
- **The code snapshot is the whole `src/` folder**, including the leftover
  `ROC-Curve.png` from the terminal test and later labs' `job.yml` and
  `deploy_to_online_endpoint.py`. Only `*.amltmp` and checkpoints were
  excluded by `.amlignore`. **Both jobs share one code asset** (same contents →
  one snapshot).
- **Input upload reused:** `../data/diabetes-data` resolved to the same
  `LocalUpload/03f6bb5b…` folder `setup.sh` uploaded in lab 01.
- **The curated environment works for jobs.** It ran in
  `/azureml-envs/sklearn-1.0/`, even though the CLI and REST API couldn't read
  it. The risk I'd flagged didn't happen.
- **AUC 0.84828 in the job vs. 0.84849 in the terminal**, with the same code,
  data and seed. The cause is the library version: autolog logged
  `multi_class: auto` in the job (scikit-learn 1.0) vs. `multi_class:
  deprecated` on the compute instance in lab 01 (a newer scikit-learn).
  That's why jobs pin an environment.

## 3. What broke and how we fixed it

- **Nothing broke in 2.1.** The `libstdc++6` ImportError the lab warns about
  didn't happen.
- **Surprise: the terminal's environment is `azureml_py38`, but its Python is
  3.10.0.** The conda environment names on the compute instance image are old
  labels, so trust `python --version`, not the name. The Studio kernel name
  *Python 3.10 - AzureML* and this terminal both run 3.10 here.
- **The optional autolog job was submitted without the edit.** The notebook
  says to add `mlflow.autolog()` to `main()` *before* rerunning. I ran all
  cells straight through, so `diabetes-train-mlflow` ran identical code. The
  fix: add the line, save, rerun only that cell (done: `epic_king_fhy758f6cn`).
- **Harmless warning** at the top of `std_log.txt`:
  `/bin/bash: /azureml-envs/sklearn-1.0/lib/libtinfo.so.6: no version information available`
  (bash picking up the environment's own library). The job still succeeded.
- **The lab's `cd mslearn-mlops/src/` fails** (`No such file or directory`)
  unless the terminal is in the home folder (`~/cloudfiles/code/Users/<me>`).
  ▷▷ had already opened the terminal in `src/`, so the next command worked
  anyway.
- **The stray `experimentation/ROC-Curve.png` explained:** last modified at
  00:35:48 UTC, the minute of lab 01's MLflow run 5, and `Track model training
  with MLflow.ipynb` is the only notebook that calls `savefig`. It's the image
  run 5 saved to disk but never logged (its MLflow artifact list was empty).

## 4. Exam mapping

**Notebook → script (2.1)**, Domain 2: *Run model training scripts* (the
preparation step) and *Use notebooks for experimentation*.
- The Microsoft Learn module's three rules for a production-ready script:
  **remove nonessential code**, **refactor into functions**, **test in a
  terminal**. Module assessment: code to retrain weekly → **several small
  functions** in a script, not one big function and not a copy-paste of the
  cells (a copy-paste is exactly what the Studio export gives you).
- Testing a script: Studio's **Save and run script in terminal**, or
  `python train.py` in the compute instance terminal. Prints and errors show
  up there.

**Test with the terminal (2.2)**, Domain 2: *Run model training scripts*
- Parameters come in through **`argparse`**; the command line passes them
  (`--training_data …`). Missing required input fails fast. Module assessment:
  to vary batch size and learning rate per run → **add arguments to the
  script and set them in the job's command**, not separate scripts or job
  properties.
- MLflow in a script **starts a run automatically** on the first `log_*`
  call. On a compute instance without `set_experiment`, it lands in
  **`Default`**.

**Run as a command job (2.3)**, Domain 2: *Run model training scripts*,
*Configure experiment tracking with MLflow*, *Compare model performance*;
Domain 1: *Create and manage environments* (used, not created)
- `command(code, command, inputs, environment, compute, display_name,
  experiment_name)` → `ml_client.create_or_update(job)`. `${{inputs.x}}` is
  replaced with the mounted path on the node.
- **The job records** its code snapshot (the whole `code` folder minus
  `.amlignore`), inputs, environment, command and logs (`user_logs/std_log.txt`).
- **MLflow in a job:** the environment needs `mlflow` + `azureml-mlflow`. No
  `start_run()`: the job is the run. Use `log_metric` for numbers such as
  RMSE (module assessment), `log_param` for inputs, `log_figure`/`log_image`
  for plots without saving them first.
- **Autolog** adds every estimator param, `training_*` metrics, charts and the
  **`model/` folder under Outputs + logs** (module assessment).
- Studio: Params on **Overview**, the **Metrics** tab, plots under
  **Images**, files under **Outputs + logs**, code snapshot on the **Code** tab.
- Querying runs from a notebook: `mlflow.search_experiments()`,
  `mlflow.get_experiment_by_name()`,
  `mlflow.search_runs(exp_id, order_by=["start_time DESC"], filter_string="params.x='1'", max_results=2)`;
  `search_all_experiments=True` searches across all experiments.

**Microsoft Learn module vs. our run**

| Module says | Our run | Take-away |
|---|---|---|
| Examples use environment `AzureML-sklearn-0.24-ubuntu18.04-py37-cpu@latest` | The lab uses `AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest` | Curated environment names change. Know the *pattern* (`AzureML-<framework>-<version>-<os>-<python>-<cpu/gpu>@latest`), not a specific name |
| Scripts need `mlflow` + `azureml-mlflow` in the environment (unit 5) | The curated sklearn environment already had both (logging worked) | For a custom environment, add both packages |
| The module doesn't say where terminal runs go | Terminal runs landed in `Default` | Set an experiment name even when testing |

**Module assessment (unit 8)**, four questions:
1. Different batch size / learning rate per run → **arguments in the script, set in the command**.
2. Retrain weekly, make the code production-ready → **several functions** in a script.
3. Log RMSE → **`mlflow.log_metric()`**.
4. With autologging, the model assets are in → **the `model` folder under Outputs + logs**.

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

**Notebook → script (2.1)**

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| From notebook to code | 🧪 Studio **Export as .py**: every cell pasted into one file, with a hardcoded path | Rewritten by hand into three scripts (`ml/components/{prep,train,evaluate}`), each with typed inputs and outputs | 📘 **Refactor into functions and parameters, then test**. The export is only a starting point |
| Where it's tested | Compute instance terminal | Locally, then as a real pipeline run in a clean container, which caught bugs the local packages had hidden | 📘 Terminal first, then **a job** (section 3) so it runs in a defined environment |

**Command job (2.2–2.3)**

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Unit of work | One command job running one script | A 3-step pipeline (prep → train → evaluate) of registered components | 📘 A command job to run a script; a **pipeline of components** for multi-step training (lab 04) |
| How it's defined | Python SDK `command()` in a notebook | CLI v2 YAML (`az ml job create -f …`) | 📘 Both are first-class. YAML is easier to version and review |
| Environment | 🧪 Curated `…@latest`: the version can change under you, and the CLI can't read it | Custom conda environment, pinned version | 📘 **A registered, versioned environment**, pinned (`name:version`) for reproducibility. `@latest` is fine for labs |
| Input data | 🧪 A local folder, uploaded anonymously | A registered data asset (`diabetes-raw`) | 📘 **A registered, versioned data asset** (`azureml:name:version`) for lineage |
| Code snapshot | 🧪 The whole `src/` folder, including unrelated files and a stray PNG | Each component has its own small `code: .` folder | 📘 Keep the `code` folder minimal; use `.amlignore` |
| Logging | Custom `log_param`/`log_metric` (+ autolog optional) | `mlflow.sklearn.autolog()` in `train.py` + held-out metrics in `evaluate.py` written to `metrics.json` | 📘 **Autolog + custom held-out metrics** |
| Quality gate | None; you read the numbers | Pipeline fails below AUC 0.95 | 🛠 A gate is my own addition. The exam's closest topic is comparing runs |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> You run <code>python train-model-parameters.py</code> in the compute instance terminal with no arguments. It prints <code>Reading data...</code>, then fails with <code>TypeError: stat: path should be string… not NoneType</code>. Why?<br><br>A) The CSV file is missing<br>B) <code>--training_data</code> has no default, so the script received <code>None</code> as the path<br>C) The terminal isn't connected to the workspace<br>D) pandas isn't installed</summary>

> **✅ Answer: B.** <code>argparse</code> only fills in what you pass (or a default). The job's <code>command</code> passes it as <code>--training_data ${{inputs.training_data}}</code>.
</details>

---

<details>
<summary><strong>2.</strong> A script calls <code>mlflow.log_metric("Accuracy", acc)</code> but never calls <code>start_run()</code> or <code>set_experiment()</code>. You run it in a compute instance terminal. What happens?<br><br>A) An error: no active run<br>B) Nothing is logged<br>C) MLflow starts a run automatically and logs it to the workspace, in the experiment <code>Default</code><br>D) It's logged to a local <code>mlruns/</code> folder</summary>

> **✅ Answer: C.** On a compute instance the tracking URI already points at the workspace. We saw run <code>epic_floor_prhg1jbc</code> land in <code>Default</code>.
</details>

---

<details>
<summary><strong>3.</strong> A command job uses <code>code="../src"</code>. Which files are uploaded?<br><br>A) Only the file named in <code>command</code><br>B) Everything in <code>src/</code> except what <code>.amlignore</code> excludes, including unrelated files left in the folder<br>C) Only <code>.py</code> files<br>D) Nothing; the node reads the file share directly</summary>

> **✅ Answer: B.** Our snapshot included <code>job.yml</code>, <code>deploy_to_online_endpoint.py</code> and a stray <code>ROC-Curve.png</code>. Keep the code folder small; large files there are uploaded with every job.
</details>

---

<details>
<summary><strong>4.</strong> The same script, the same data and the same <code>random_state</code> give AUC 0.84849 in the compute instance terminal and 0.84828 as a command job. Most likely reason?<br><br>A) Randomness in the data split<br>B) The job ran on a different VM size<br>C) Different library versions: the job's pinned environment (scikit-learn 1.0) vs. the compute instance's own packages<br>D) The job used a different data file</summary>

> **✅ Answer: C.** Autolog even showed it: <code>multi_class: auto</code> in the job vs. <code>deprecated</code> on the compute instance. A result belongs to code + data + <strong>environment</strong>.
</details>

---

<details>
<summary><strong>5.</strong> You want each run to use a different learning rate and batch size. What's the recommended approach?<br><br>A) One script per combination<br>B) Set learning-rate and batch-size properties on the command job<br>C) Add them as script arguments and set their values in the job's <code>command</code><br>D) Change the environment for each run</summary>

> **✅ Answer: C.** The same pattern as <code>--reg_rate</code>. Sweep jobs (lab 03) build on exactly this.
</details>

---

<details>
<summary><strong>6.</strong> You add <code>mlflow.autolog()</code> to a scikit-learn training script run as a job. Where do you find the model files?<br><br>A) In the Metrics tab<br>B) In the <code>model</code> folder under <strong>Outputs + logs</strong><br>C) Under Models, automatically registered<br>D) In the Code tab</summary>

> **✅ Answer: B.** Job <code>epic_king_fhy758f6cn</code> had <code>model/MLmodel</code>, <code>model.pkl</code> and <code>conda.yaml</code>. It's logged, not registered: registering is a separate step.
</details>

---

<details>
<summary><strong>7.</strong> Which one belongs in <code>mlflow.log_param</code>, not <code>mlflow.log_metric</code>?<br><br>A) RMSE<br>B) The regularization rate you chose<br>C) AUC<br>D) Training time</summary>

> **✅ Answer: B.** Params are inputs you chose (logged once); metrics are numbers you measured (can be logged repeatedly and charted).
</details>

---

<details>
<summary><strong>8.</strong> Two jobs submitted a few seconds apart use the same unchanged <code>src/</code> folder. A third job runs after one line of the script was edited. How many code snapshots exist?<br><br>A) 3<br>B) 1<br>C) 2: identical contents share one snapshot; the edit created a new one<br>D) 0: code isn't stored</summary>

> **✅ Answer: C.** <code>codes/04f04747…</code> was shared by the first two jobs, <code>codes/504b4a23…</code> came from the edited script.
</details>
