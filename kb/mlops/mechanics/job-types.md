# Job types, and what else a workflow can do

## One command, five job types

Every Azure ML job is submitted the same way (`az ml job create -f <file>.yml`,
or `ml_client.jobs.create_or_update(job)` in the SDK). **The file's `type:`
decides what kind of job it is.** A GitHub workflow doesn't care: it just
runs the command on whatever YAML is in the repo.

| `type:` | What it is | Where I ran it |
|---|---|---|
| `command` | One script, once, on one compute | Lab 02 (notebook), lab 06 (GitHub workflow, `src/job.yml`) |
| `sweep` | One script, many times: one **trial** per hyperparameter combination | Lab 03 |
| `automl` | Azure ML searches algorithms + preprocessing; trials, ensembles and an explanation as child jobs | Lab 01 |
| `pipeline` | A **graph of steps** (components) wired output → input | Lab 04 |
| `spark` | A Spark job on serverless or attached Spark compute | Lab 07, indirectly: model monitoring runs on serverless Spark |

For **training**, the everyday choice is **`command`** (one script does it
all) vs. **`pipeline`** (separate, reusable, versioned steps).

## Is a pipeline "a set of commands"? Roughly, but two nuances

1. **The steps are usually command components, but not always.** A step
   can also be a **sweep**, an **AutoML** job, a **Spark** job, a **parallel**
   step (the same script over many data chunks), or **another pipeline** (a
   sub-pipeline). Each step is a **component**: a command with a declared
   interface (typed inputs and outputs), its own environment and code, and
   optionally its own compute.
2. **The wiring is the point.** Declaring *step 1's output = step 2's input*
   lets Azure ML:
   - work out the **order**: dependent steps run in sequence, independent ones
     can run in parallel (in lab 04, `train_model` didn't even exist until
     `clean_data` produced its output)
   - **move the data** between steps (outputs land in the datastore, then are
     mounted into the next step)
   - **reuse** a step's previous result when its inputs, code and environment
     haven't changed (deterministic components), instead of rerunning it
   - run each step as a separate **child job** with its own logs, so you see
     exactly which step failed

Separate command jobs have none of this: you'd order them and pass data by
hand.

**Exam one-liner:** a pipeline is a **graph of component steps connected by
their inputs and outputs**, submitted as one pipeline job, with each step
running as a child job.

## Not everything is a job

The same `az ml` CLI (or SDK) does things a workflow may need that aren't
jobs:

| Action | Command | Lab |
|---|---|---|
| Register a model | `az ml model create` / `ml_client.models.create_or_update` | 07 (implicitly, through deployment) |
| Deploy a model | `az ml online-endpoint create`, `az ml online-deployment create`, or an SDK script (`deploy_to_online_endpoint.py`) | 07 |
| Schedule a job or a monitor | `az ml schedule create` | 04 (documented), 07 (monitoring) |
| Create data assets or environments | `az ml data create`, `az ml environment create` | 01, 05 |
| Create a component | `az ml component create` | 04 (documented; the lab only loaded them) |

**The pattern:** the **YAML in Git says *what***; the **workflow runs the
`az ml` command** on it.

## In these labs

- Labs 06–07's training workflows (`manual-trigger-job.yml`, `train-dev.yml`,
  `train-prod.yml`) submit **command jobs** (`src/job.yml`). Lab 04's pipeline
  exists only as notebook-generated files on the Studio clone.
- `deploy-prod.yml` (lab 07) runs a **deployment** (SDK script), not a job.
- My production project's `train-and-register.yml` submits a **pipeline job**
  (`ml/pipelines/train_pipeline.yml`: prep → train → evaluate with an AUC
  gate).
