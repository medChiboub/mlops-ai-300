# MLflow tracking in Azure ML

## The one idea

MLflow is an open-source library for recording training runs: **parameters**
(inputs you chose), **metrics** (numbers you measured), **artifacts** (files,
including the model), and **tags**. It sends them to a **tracking server**.
An Azure ML workspace *is* an MLflow tracking server, so the same `mlflow.*`
calls that work on a laptop against a local `mlruns/` folder land in the
workspace when the tracking URI points there.

| MLflow concept | Azure ML equivalent | Where you see it in Studio |
|---|---|---|
| Tracking server | The workspace | none |
| Experiment (`mlflow.set_experiment`) | Experiment | **Jobs** → experiment name |
| Run (`mlflow.start_run`) | A job | A row under the experiment |
| `log_param` | Job parameter | Job → Overview → **Params** |
| `log_metric` | Job metric | Job → **Metrics** tab (charts if logged repeatedly) |
| `log_artifact` / logged model | Job outputs (`workspaceartifactstore`) | Job → **Outputs + logs** |
| Registered model (`mlflow.register_model`) | Workspace model | **Models** |

AutoML used the same machinery: each trial we read through the MLflow REST
API was an MLflow run.

## How the notebook connects

On a compute instance, the tracking URI is **already set** to the workspace
(`azureml://canadaeast.api.azureml.ms/mlflow/v1.0/subscriptions/…/workspaces/mlw-ai300-…`).
That's why the notebook never calls `mlflow.set_tracking_uri`. My
production project's local notebook has to set it explicitly
(`mlflow.set_tracking_uri(workspace.mlflow_tracking_uri)`).

## Where the code runs, and the key difference from AutoML

The training runs **in the notebook's kernel on the compute instance**, not
on `aml-cluster`. `mlflow.start_run()` doesn't submit anything; it only
*records*. So:

- The cluster stays at 0 nodes during this whole section.
- Studio shows the runs as jobs, but they aren't jobs Azure ML executed. It
  just received the log calls. There's no code snapshot, no environment, and
  no compute target in the usual sense.
- Contrast: `ml_client.jobs.create_or_update(...)` (AutoML, and lab 02's
  command job) *hands the work to Azure ML*. Knowing the difference between
  **tracking** a run and **submitting** a job is the core of this section.

## The notebook's five runs, and what each should log

All go to experiment **`mlflow-experiment-diabetes`**. The data is the 8
feature columns (`PatientID` is dropped by hand here, unlike AutoML) with a
70/30 split and `random_state=0`, the same split as the notebook I ran by
mistake.

| # | Code | Logging style | Expected in the run |
|---|---|---|---|
| 1 | `LogisticRegression(C=1/0.1)` | **autolog** | Every estimator param (`C`, `solver`, `max_iter`, …); **training** metrics (`training_accuracy_score`, `training_f1_score`, `training_roc_auc`, `training_log_loss`, …); the model as an MLflow artifact |
| 2 | same model, reg 0.1 | custom only | param `regularization_rate=0.1`, metric `Accuracy` (test set) |
| 3 | reg 0.01 | custom only | param `regularization_rate=0.01`, metric `Accuracy` |
| 4 | `DecisionTreeClassifier()` | custom only | param `estimator`, metric `Accuracy` |
| 5 | Decision tree + ROC plot | custom only | param `estimator`, metric `Accuracy`, and supposedly the ROC image |

### Things to notice

- **Autolog metrics are *training* metrics.** `training_accuracy_score` is
  measured on the data the model was fit on, so it's optimistic. Autolog
  doesn't know about your `X_test`. Runs 2–4 log `Accuracy` on the test set.
  Comparing run 1's number with the others compares different things.
  ✅ **Verified:** run 1 logged `training_accuracy_score 0.7916`,
  `training_roc_auc 0.862`, `training_f1_score`, `training_precision_score`,
  `training_recall_score`, `training_log_loss` and `training_score`. Run 2,
  the *same model and settings*, scored **0.7737** on the test set. The
  training score is about 2 points higher.
  Autolog also logged **15 params** (every `LogisticRegression` argument, even
  defaults) and **artifacts**: `model/` (MLflow model), `estimator.html`,
  `training_confusion_matrix.png`, `training_precision_recall_curve.png` and
  `training_roc_curve.png`.
- **`mlflow.sklearn.autolog()` is global.** It's called inside run 1, but it
  patches scikit-learn for the whole kernel. Without the `autolog(disable=True)`
  cell, runs 2–5 would *also* get autologged. That's why the notebook turns it
  off.
- **Params vs. metrics:** `regularization_rate` is a *param* (something you
  chose), `Accuracy` is a *metric* (something you measured). Params are
  logged once per run. Metrics can be logged repeatedly (for example per
  epoch) and Studio charts them.
- **Run 5 probably doesn't log the image.** The cell calls
  `plt.savefig("ROC-Curve.png")` but never `mlflow.log_artifact("ROC-Curve.png")`.
  Saving a file to disk isn't logging it. It just leaves a PNG in the notebook's
  folder on the file share. ✅ **Verified:** run 5's artifact list is
  **empty** (`[]`). (We won't fix it: we don't change the lab's code. But note
  what the fix would be.)
- **Run names are random** (`sad_leaf_…`) because the notebook never passes
  `run_name=`. Studio's *Display name* is editable.

## The actual runs (verified)

Experiment `mlflow-experiment-diabetes`, all started 20:35 local, one second
apart:

| Run | Run ID (a GUID, not a job name) | Params | Metrics | Artifacts |
|---|---|---|---|---|
| 1 autolog LR | `a84deb22…` | 15 estimator params | `training_*` (accuracy 0.7916, roc_auc 0.862, …) | model, estimator.html, 3 training charts |
| 2 LR reg 0.1 | `f07b045b…` | `regularization_rate=0.1` | `Accuracy 0.7737` | none |
| 3 LR reg 0.01 | `8679df9e…` | `regularization_rate=0.01` | `Accuracy 0.7740` | none |
| 4 Decision tree | `14823782…` | `estimator=DecisionTreeClassifier` | `Accuracy 0.8920` | none |
| 5 Decision tree + ROC | `b7d97b20…` | `estimator=DecisionTreeClassifier` | `Accuracy 0.8883` | **none**: the PNG was never logged |

- **Runs 4 and 5 are the same code but scored differently** (0.892 vs.
  0.8883). `DecisionTreeClassifier()` has no `random_state`, so ties between
  splits are broken randomly. That's one reason to log params *and* set
  seeds: without a seed, "same params" doesn't mean the same model.
- **Reg rate 0.1 vs. 0.01** barely matters (0.7737 vs. 0.7740). The
  decision tree beats both logistic regressions by about 12 points, and
  AutoML's boosted ensemble beats the tree by 6 more (0.953, on CV rather
  than a single split, so not strictly comparable).
- **The cluster wasn't used:** these runs have no compute target. See the
  note on the `_RAI` run below.
- **Snag: MLflow `runs/search` returned run 1's params but no metrics.**
  `runs/get` on the same run ID returned all 7. The search endpoint here
  doesn't always include metrics, so read a run directly when numbers look
  missing.

## Exam cheat-sheet

- `mlflow.set_experiment`, `mlflow.start_run` (a context manager, so the run
  ends when the `with` block ends), `log_param(s)`, `log_metric(s)`,
  `log_artifact(s)`, `log_figure`, `set_tag`.
- `mlflow.<flavor>.autolog()`, or `mlflow.autolog()` for all supported
  libraries. It logs params, training metrics and the model automatically.
- Inside an Azure ML **job**, you don't call `start_run`. The job *is* the
  run, and `mlflow.log_*` calls attach to it automatically. (Lab 02 shows
  this.)
- **Comparing runs:** Studio → select several jobs → **Compare**, or
  `mlflow.search_runs(experiment_names=[...])`, which returns a pandas
  DataFrame.
- **Tracking vs. registering:** a logged model is just an artifact on a run.
  It becomes a versioned workspace model only when it's registered.
