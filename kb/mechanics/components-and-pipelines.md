# Components and pipelines

## The one idea

A **component** is a reusable step *definition*: a script plus a YAML that
declares its **metadata** (name, version), its **interface** (typed inputs
and outputs), and **how to run it** (command, code folder, environment). A
**pipeline** wires components together by connecting one step's output to
the next step's input. A **pipeline job** is one run of that pipeline; each
step runs as a **child job**.

| | Component | Pipeline | Pipeline job |
|---|---|---|---|
| What | A step template | Steps + how data flows between them | A run of the pipeline |
| Analogy | A function | A program calling functions | An execution of the program |
| Made with | YAML (or `@command_component`) + script | `@pipeline()` function (or pipeline YAML) | `ml_client.jobs.create_or_update(pipeline_job)` |
| Stored as | `name:version` if **registered**; otherwise anonymous | Only inside the job definition | Job history: parent + child jobs |

## The lab's two components

```yaml
# prep-data.yml                          # train-model.yml
name: prep_data                          name: train_model
version: 1                               version: 1
type: command                            type: command
inputs:                                  inputs:
  input_data: {type: uri_file}             training_data: {type: uri_folder}
outputs:                                   reg_rate: {type: number, default: 0.01}
  output_data: {type: uri_folder}        outputs:
code: ./src                                model_output: {type: mlflow_model}
environment: azureml:AzureML-sklearn-…   code: ./src
command: python prep-data.py             environment: azureml:AzureML-sklearn-…
  --input_data ${{inputs.input_data}}    command: python train-model.py
  --output_data ${{outputs.output_data}}   --training_data ${{inputs.training_data}} …
```

- `${{outputs.output_data}}` is a folder path **Azure ML creates on the
  node**. The script writes `diabetes.csv` into it, and Azure ML then uploads
  it to the datastore.
- The output type `mlflow_model` tells Azure ML the folder is an MLflow model
  (`train-model.py` calls `mlflow.sklearn.save_model(model, args.model_output)`).

## The pipeline

```python
@pipeline()
def diabetes_classification(pipeline_job_input):
    clean_data  = prep_data(input_data=pipeline_job_input)
    train_model = train_logistic_regression(training_data=clean_data.outputs.output_data)   # ← the wiring
    return {"pipeline_job_transformed_data": clean_data.outputs.output_data,
            "pipeline_job_trained_model":    train_model.outputs.model_output}

pipeline_job = diabetes_classification(Input(type=URI_FILE, path="azureml:diabetes-data:1"))
pipeline_job.outputs.pipeline_job_transformed_data.mode = "upload"
pipeline_job.settings.default_compute   = "aml-cluster"        # used by steps that don't set their own
pipeline_job.settings.default_datastore = "workspaceblobstore" # where outputs land
ml_client.jobs.create_or_update(pipeline_job, experiment_name="pipeline_diabetes")
```

Because train's input *is* prep's output, Azure ML knows train must wait for
prep, so the **order comes from the data dependency**, not from the order
of the lines. Steps with no dependency between them could run in parallel.

## Loaded vs. registered components

The notebook only **loads** the YAMLs (`load_component`). The Microsoft
Learn module adds the second option:

```python
prep = ml_client.components.create_or_update(loaded_component_prep)   # register → prep_data:1 in the Components page
```

- **Loaded (the lab):** usable in a pipeline you submit from this notebook.
  At submission Azure ML still stores the component, but as an
  **anonymous** version not listed for reuse.
- **Registered:** named and versioned in the workspace, so other people and
  pipelines can reuse it (and it can be shared to a registry).

## Scheduling (in the module, not in the lab notebook)

```python
from azure.ai.ml.entities import RecurrenceTrigger, JobSchedule
trigger  = RecurrenceTrigger(frequency="week", interval=1)          # minute | hour | day | week | month
schedule = JobSchedule(name="weekly_retrain", trigger=trigger, create_job=pipeline_job)
ml_client.schedules.begin_create_or_update(schedule=schedule).result()
# delete = disable first, then delete
ml_client.schedules.begin_disable(name="weekly_retrain").result()
ml_client.schedules.begin_delete(name="weekly_retrain").result()
```

Jobs started by a schedule get the schedule name as a display-name prefix.
`CronTrigger` is the cron-expression alternative. Module assessment: the
simple weekly schedule uses **`RecurrenceTrigger`** (with `JobSchedule` to
attach it).

## Troubleshooting (module unit 4)

- The **pipeline configuration** fails → read the **pipeline job's** outputs
  and logs.
- **A component** fails → read **that step's child job's** outputs and logs.

## What actually happened (pipeline job `calm_ticket_wcbhgt8w7n`)

| Step (child job) | Run ID | Ran (UTC) | Result |
|---|---|---|---|
| `clean_data` (component `prep_data:1`) | `8ba7c1f5…` | 02:11:02 → 02:13:11 (**cold node**, about 2 min) | `Preparing 10000 rows of data`, so `dropna` removed nothing |
| `train_model` (component `train_model:1`) | `aa0f7853…` | 02:13:36 → 02:13:59 (**warm node, 23 s**) | Accuracy **0.774**, AUC **0.84849** (printed only) |

The parent was submitted at 02:08:53. About 2 min in the queue plus the
cold start, then the two steps ran one after the other on **one node**.

- ✅ **Steps run one after the other because of the data dependency.**
  `train_model` didn't even *exist* until `clean_data` completed; then it
  was created and queued.
- ✅ **Child jobs are named after the pipeline function's variables**
  (`clean_data`, `train_model`), not after the components, and their job IDs
  are GUIDs. Run history shows the link: `azureml.moduleName = prep_data`,
  `azureml.moduleVersion = 1`, `StepType = PythonScriptStep`.
- ✅ **The components are anonymous.** `az ml component list` is **empty**,
  though each step has a `moduleid`. Loading a YAML and using it in a
  pipeline doesn't register anything for reuse.
- ✅ **One shared code snapshot:** both steps have `ContentSnapshotId
  1d405e6d…`, the whole `experimentation/src/` (including lab 03's
  `train.py`), because both YAMLs say `code: ./src`.
- ✅ **Outputs land where the settings say.** `default_datastore`
  `workspaceblobstore`, under `azureml/<child-run-id>/<output-name>/`:
  - `azureml/8ba7c1f5…/output_data/diabetes.csv`: **scaled** to 0–1 for the
    7 listed features; **`Age` unscaled** (21, 23…); `PatientID` untouched.
  - `azureml/aa0f7853…/model_output/`: `MLmodel`, `model.pkl`, `conda.yaml`,
    `python_env.yaml`, `requirements.txt`. The `MLmodel` file says
    **scikit-learn 1.0.2, Python 3.8.16, MLflow 2.4.1** (the curated
    environment's real versions, which settles lab 02's AUC question).
- ✅ **The model is stored twice:** autolog's `model/` artifact on the train
  run, *and* the `model_output` pipeline output written by
  `mlflow.sklearn.save_model`. Neither is registered.
- ⚠ **The test metrics aren't logged.** The train run has 16 params and 7
  autolog `training_*` metrics (training accuracy 0.7911), but the script's
  `eval_model` only **prints** test Accuracy and AUC. They're only in
  `std_log.txt`, not comparable in Studio.
- ✗ **My prediction was wrong: scaling didn't change accuracy** (0.774, the
  same as every earlier run). AUC moved slightly (0.84828 unscaled vs. 0.84849
  scaled, in the same scikit-learn 1.0.2 environment). With `C=100` (weak
  regularization), LogisticRegression barely cares about feature scale here.
- Harmless warnings in train's log: autolog's `Cannot log the same dataset
  with different context` (it tried to log the evaluation dataset twice).
- 🧪 **The scaler is fit on all the data before the split**, so the min/max
  values include the test rows. A mild leak; fit on training data only in a
  real pipeline.
