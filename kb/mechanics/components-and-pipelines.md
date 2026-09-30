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

## Is a pipeline just "a set of commands"?

Roughly, with two nuances (full version in [job-types.md](job-types.md)):
1. **Steps are usually command components, but can also be** sweep, AutoML,
   Spark, parallel steps, or a sub-pipeline.
2. **The wiring (output → input) is the value:** it sets the order (and
   parallelism), moves the data, lets unchanged steps **reuse** earlier
   results, and gives each step its own child job and logs. Separate command
   jobs give you none of that.

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

## Scheduling: automatic retraining

The Microsoft Learn module teaches it; the lab notebook doesn't do it. Not
run here on purpose: this section is the reference. Everything below comes
from the SDK's own class signatures (azure-ai-ml, inspected locally), the
`az ml schedule` CLI help, the module (unit 4), and my production project's
working `ml/pipelines/train_schedule.yml`.

### The idea

A **schedule** is a workspace object that says *"submit this job
definition on this timetable."* Each time it fires, it creates a **new
job**, exactly as if you'd submitted it yourself. It's how pipelines become
automatic retraining. The schedule itself runs nothing on your compute; the
jobs it creates do.

```
JobSchedule(name, trigger, create_job)
             │        │         └─ WHAT to submit: a pipeline (or any) job definition,
             │        │            or the name of an existing job to copy
             │        └─ WHEN: RecurrenceTrigger (every N units) or CronTrigger (cron expression)
             └─ unique name; triggered jobs get it as their display-name prefix
```

### The four classes (real signatures)

```python
RecurrenceTrigger(frequency, interval, schedule=None, start_time=None, end_time=None, time_zone="UTC")
#   frequency: "minute" | "hour" | "day" | "week" | "month"      interval: int (every N units)
RecurrencePattern(hours, minutes, week_days=None, month_days=None)
#   the "at what time" inside a recurrence: e.g. Sundays at 04:00. NOT a trigger by itself
CronTrigger(expression, start_time=None, end_time=None, time_zone="UTC")
#   standard 5-field cron: "0 4 * * 0" = 04:00 every Sunday
JobSchedule(name, trigger, create_job, display_name=None, description=None, tags=None, properties=None)
#   create_job: a Job object (e.g. the pipeline job) or a string (an existing job's name)
```

- `start_time` / `end_time`: the window in which the schedule is active.
  Time zone defaults to **UTC**.
- **`RecurrenceTrigger` vs. `RecurrencePattern`** (the assessment's
  distractor): the *trigger* is the schedule's clock; the *pattern* only
  refines the exact hours, minutes and days inside a recurrence.

### SDK: create, check, run now, stop, delete

```python
from azure.ai.ml.entities import RecurrenceTrigger, RecurrencePattern, JobSchedule

trigger = RecurrenceTrigger(
    frequency="week", interval=1,
    schedule=RecurrencePattern(week_days=["sunday"], hours=4, minutes=0),   # Sundays 04:00 UTC
)
schedule = JobSchedule(name="diabetes_weekly", trigger=trigger, create_job=pipeline_job)  # the @pipeline() job
ml_client.schedules.begin_create_or_update(schedule=schedule).result()

ml_client.schedules.list()                          # all schedules in the workspace
ml_client.schedules.get("diabetes_weekly")          # its trigger, is_enabled, …
ml_client.schedules.trigger("diabetes_weekly")      # fire once right now (testing)
ml_client.schedules.begin_disable("diabetes_weekly").result()   # pause: stops creating jobs
ml_client.schedules.begin_enable("diabetes_weekly").result()    # resume
ml_client.schedules.begin_disable("diabetes_weekly").result()   # delete = disable FIRST…
ml_client.schedules.begin_delete("diabetes_weekly").result()    # …then delete
```

### CLI + YAML: the same thing (my production project, live)

```yaml
# ml/pipelines/train_schedule.yml  (MLOps_Project_Azure_ML)
$schema: http://azureml/sdk-2-0/Schedule.json
name: diabetes_classifier_weekly_training
display_name: Diabetes classifier weekly training
trigger:
  type: recurrence            # or: type: cron  +  expression: "0 4 * * 0"
  frequency: week
  interval: 1
  schedule:
    week_days: Sunday
    hours: 4
    minutes: 0
create_job: ./train_pipeline.yml    # the pipeline YAML to submit each time
```

```bash
az ml schedule create  -f train_schedule.yml
az ml schedule list | show -n <name> | update -f … | trigger -n <name>
az ml schedule disable -n <name>    # stop firing
az ml schedule enable  -n <name>
az ml schedule delete  -n <name>    # disable first; jobs it already triggered are NOT deleted
```

In my project this runs for real: `diabetes_classifier_weekly_training`,
`provisioning_state: Succeeded`, `is_enabled: true`, Sundays 04:00 UTC. A
scheduled run only retrains and evaluates; it **doesn't auto-promote**. A
new version still needs the human deploy step.

### Things to know

- **Jobs from a schedule are normal jobs**, with the schedule name as their
  display-name prefix. They appear under Jobs, and Studio also lists the
  schedule under **Jobs → Schedules**.
- **Deleting a schedule keeps its past jobs.** Delete is only allowed once
  it's **disabled**.
- **Inputs resolve on every run.** A `@latest` data asset in the scheduled
  pipeline picks up new data each time; a pinned `:1` retrains on the same
  data every time.
- **Retraining ≠ deploying.** A schedule makes new models; registering or
  deploying them is a separate decision (a gate, an approval).
- **The same mechanism drives monitoring.** Lab 07's model monitor is also an
  `az ml schedule`, with `create_monitor:` instead of `create_job:` (my
  project's `endpoints/monitor.dev.yml`).
- **Exam cues:** "run every week, simplest way" → **`RecurrenceTrigger`**
  (inside a `JobSchedule`); "run at a cron-style time" → **`CronTrigger`**;
  "stop and remove" → **disable, then delete**.

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
