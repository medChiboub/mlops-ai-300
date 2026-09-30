# Command jobs

## The one idea

A **command job** is "run this command, on that compute, in this
environment, with these files", with Azure ML keeping a full record of
all four. It's the basic unit that sweeps (lab 03), pipelines (lab 04) and
the GitHub workflows (labs 06–07) are built from.

## The pieces, as used in lab 02

```python
job = command(
    code="../src",                                   # folder → uploaded as the job's code snapshot
    command="python train-model-parameters.py --training_data ${{inputs.training_data}}",
    inputs={"training_data": Input(type="uri_folder", path="../data/diabetes-data")},
    environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest",   # Docker image + conda env
    compute="aml-cluster",
    display_name="diabetes-train-script",            # the job's label in Studio
    experiment_name="diabetes-training",             # the group it's filed under
)
ml_client.create_or_update(job)                       # submit
```

`${{inputs.training_data}}` is a placeholder. Azure ML replaces it with the
path where the input is mounted **on the node**, so the script receives a real
filesystem path, the same as `../data/diabetes-data/diabetes.csv` in the
terminal.

## What actually happened (verified, jobs `musing_reggae_mnbbwkylvf` and `lime_train_h5fzjbwn0n`)

**Code snapshot.** `code="../src"` uploaded the **whole `src/` folder** as a
*code asset* (`codes/04f04747…/versions/1`), stored in its own blob
container. Its contents:

```
src/.amlignore
src/ROC-Curve.png                 ← left over from the section 2 terminal test
src/deploy_to_online_endpoint.py  ← lab 07's file, uploaded anyway
src/job.yml                       ← labs 06–07's file, uploaded anyway
src/model/train.py
src/train-model-parameters.py
```

- Everything in the folder goes, not just the script. Only `.amlignore`
  patterns are left out. Studio's default `.amlignore` excludes just
  `.ipynb_aml_checkpoints/`, `*.amltmp` and `*.amltemp` (so
  `train-model-parameters.py.amltmp` was left out; the PNG wasn't).
  Keep the `code` folder small and clean: large data or model files in it are
  uploaded with every job (there's a size limit on snapshots).
- **Both jobs reused the same code asset.** Same folder contents → same
  snapshot, uploaded once. The Studio **Code** tab of a job shows this snapshot.

**Input data.** The local `../data/diabetes-data` folder resolved to
`azureml://datastores/workspaceblobstore/paths/LocalUpload/03f6bb5b…/diabetes-data/`,
the **same hash folder `setup.sh` uploaded in lab 01** for the
`diabetes-training` asset. Uploads are identified by their content, so
nothing was uploaded twice. It isn't registered as a data asset; it's an
anonymous upload the job points to.

**Environment.** The job ran in `/azureml-envs/sklearn-1.0/` (from the
curated image). The first log line is a harmless
`libtinfo.so.6: no version information available` warning from bash inside
that image. So the environment I'd flagged as a risk (unreadable through the
CLI and REST) **resolved and ran fine** for jobs.

**Timing.**

| | Time (UTC) |
|---|---|
| Submitted | 01:24:13 / 01:24:14 |
| Started (node ready) | 01:27:04 / 01:27:28, **about 3 min of cold start** |
| Finished | 01:29:14 / 01:29:38, about 2 min including environment setup; the script itself takes seconds |

Two jobs queued at once → the cluster scaled to **2 nodes**, one job each,
in parallel (the first use of `max_instances: 2`). With the compute instance,
that's **6 of 6** DSv2 quota cores.

**Logs and results.** Job → **Outputs + logs**:
- `user_logs/std_log.txt` has the script's `print` output (the same lines as
  the terminal)
- `system_logs/…` holds Azure ML's own logs: data mounting (`data_capability`),
  snapshot download, lifecycle, metrics
- `ROC-Curve.png` is the MLflow artifact

The MLflow values (param `Regularization rate`, metrics `Accuracy`, `AUC`) are
attached to the job itself. **Inside a job, the job *is* the MLflow run**, so
the script needs no `start_run()`, and its values don't go to `Default` as in
the terminal test.

## Same code, same data, different number

| Where | Accuracy | AUC |
|---|---|---|
| Compute instance terminal (section 2) | 0.774 | 0.84849 |
| Command job, curated `sklearn-1.0` environment | 0.774 | **0.84828** |

The split has a fixed seed and the data is identical, so the likeliest
difference is the **library versions** (the job's environment is pinned to
scikit-learn 1.0; the compute instance has its own, probably newer, version).
✅ **Verified indirectly:** the autolog job (`epic_king_fhy758f6cn`) logged
the estimator param `multi_class: auto`, while autolog on the compute
instance in lab 01 logged `multi_class: deprecated`. scikit-learn changed that
default in a newer release, so the two really do run different versions.
This is the concrete reason jobs pin an **environment**: the result belongs
to *code + data + environment*, not just code + data.

## Custom logging vs. autolog in a job (verified)

After adding `mlflow.autolog()` as the first line of `main()` and rerunning
the cell (job `epic_king_fhy758f6cn`):

| | Custom only (`musing_reggae_mnbbwkylvf`) | + `mlflow.autolog()` (`epic_king_fhy758f6cn`) |
|---|---|---|
| Params | 1: `Regularization rate` | **16**: + every `LogisticRegression` argument (`C=100.0`, `solver=liblinear`, `penalty=l2`, …) |
| Metrics | 2: `Accuracy 0.774`, `AUC 0.8483` (test set) | **9**: + `training_accuracy_score 0.7914`, `training_roc_auc 0.862`, `training_f1_score`, `training_precision_score`, `training_recall_score`, `training_log_loss`, `training_score` |
| Artifacts | `ROC-Curve.png` | + **`model/`** (`MLmodel`, `model.pkl`, `conda.yaml`, `python_env.yaml`, `requirements.txt`), `estimator.html`, `training_confusion_matrix.png`, `training_precision_recall_curve.png`, `training_roc_curve.png` |
| Tags | none | `estimator_name`, `estimator_class` |
| Code asset | `codes/04f04747…` | **new** `codes/504b4a23…`, because the script changed |

- **Autolog and custom logging work together.** Both sets of values land on
  the same run.
- **Autolog metrics are training metrics again:** 0.7914 train vs. 0.774
  test, the same pattern as lab 01.
- **`model/` under Outputs + logs** is the MLflow model, ready to register.
  That's the module assessment's answer to *"where are the model assets
  with autologging?"*
- **Changing one line of code produced a new code snapshot**, while the two
  earlier jobs with identical code shared one.
- Timing: queued 01:35:46 → started 01:37:52 → done 01:40:14. The nodes had
  already scaled back to 0 (120 s idle), so another cold start of about 2 min.

## Job vs. terminal run

| | Terminal (section 2) | Command job (section 3) |
|---|---|---|
| Runs on | Compute instance | `aml-cluster` node(s) |
| Code recorded | ❌ | ✅ snapshot (Code tab) |
| Environment recorded | ❌ (whatever the VM has) | ✅ named environment |
| Inputs recorded | ❌ | ✅ exact data path |
| Output logs kept | ❌ (only on screen) | ✅ `std_log.txt` |
| MLflow run | Auto-created in `Default` | The job itself, in `diabetes-training` |
| Rerunnable by someone else | No | Yes: same code, data and environment |

## Exam cheat-sheet

- `command()` parameters: `code`, `command`, `inputs`/`outputs`,
  `environment`, `compute`, `display_name`, `experiment_name`. Submit with
  `ml_client.create_or_update(job)` (or `ml_client.jobs.create_or_update`).
- **Hyperparameters go in as script arguments** set in `command` (module
  assessment: add `--batch_size`/`--learning_rate` arguments to the script and
  set them in the command, not separate scripts or job properties).
- **MLflow in a job:** the environment needs `mlflow` + `azureml-mlflow`.
  `mlflow.autolog()` or `mlflow.log_*`, no `start_run()`. `log_metric` for
  numbers like RMSE; `log_param` for inputs.
- **Where things are in Studio:** Params on **Overview**; **Metrics** tab;
  plots in **Images**; all files, including autolog's `model/` folder, under
  **Outputs + logs**.
- CLI equivalent: the same job as YAML (`src/job.yml`) →
  `az ml job create -f job.yml`, which is what labs 06–07's workflows use.
