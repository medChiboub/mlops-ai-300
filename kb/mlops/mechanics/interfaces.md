# Script, SDK, CLI + YAML, Studio: four layers, one service

They aren't alternatives to the ML code. Your **script** does the ML work;
the **SDK**, the **CLI + YAML** and **Studio** are different ways of telling
Azure ML to run it. All three call the same **Azure ML REST API**.

```
                    ┌──────────── ways to TELL Azure ML what to run ────────────┐
                    │  Studio (UI)  │  Python SDK   │  CLI  az ml … + YAML files │ → Azure ML REST API
                    └───────────────────────────────┬───────────────────────────┘
                                                    ▼
                                    Azure ML runs a job on aml-cluster
                                                    ▼
                               ┌─ your Python script (train.py, prep-data.py) ─┐
                               │   the actual ML work: pandas, sklearn, MLflow │
                               └───────────────────────────────────────────────┘
```

| Layer | What it is | Where these labs use it |
|---|---|---|
| **Python script** | The ML code. It doesn't know about Azure ML (except MLflow logging) and runs the same in a terminal or on the cluster | Lab 02 terminal test; inside every job |
| **Python SDK** (`azure-ai-ml`) | A library to **define and submit** jobs and assets: `MLClient`, `command()`, `automl.classification()`, `.sweep()`, `@pipeline`, `load_component` | Every lab notebook (01–04) |
| **YAML** | A **declarative file** describing a job, component, environment, data asset, endpoint or schedule | Lab 04 component files, `src/job.yml`, `infra/registry.yml` |
| **CLI v2** (`az ml …`) | Command-line tool; submits and manages YAML-defined things | `setup.sh` (lab 01), Claude's monitoring, labs 06–07 GitHub workflows |
| **Studio** | Web UI over the same objects | Notebooks, the Trials tab, guardrails, lab 07 monitoring and rollback |
| **REST API** | What all of the above call | Claude, when the CLI couldn't show something (AutoML trials, MLflow runs) |

## The same thing, both ways

| | SDK (Python) | CLI + YAML |
|---|---|---|
| Command job | `command(code=…, command=…, environment=…, compute=…)` → `ml_client.jobs.create_or_update(job)` | `type: command` in `job.yml` → `az ml job create -f job.yml` |
| Override an input | `job(reg_rate=0.1)` | `az ml job create -f job.yml --set inputs.reg_rate=0.1` |
| Component | `load_component("prep.yml")` → `ml_client.components.create_or_update(c)` | `az ml component create -f prep.yml` |
| Pipeline | `@pipeline()` function | `type: pipeline` YAML with `jobs:` → `az ml job create -f pipeline.yml` |
| Data asset | `ml_client.data.create_or_update(Data(...))` | `az ml data create -f data.yml` (or flags, as `setup.sh` does) |
| Look at a job | `ml_client.jobs.get(name)` | `az ml job show -n name` |

The SDK and YAML are **interchangeable representations**: `print(pipeline_job)`
prints YAML, and `load_component` / `load_job` read YAML into SDK objects.

## Why several ways exist

- **SDK:** notebooks and data scientists. Stays in Python, can loop and
  branch.
- **CLI + YAML:** automation and CI/CD. The files live in Git, are reviewed
  in PRs, and run from GitHub Actions without writing Python. Labs 06–07 and
  all of my production project use this.
- **Studio:** exploring, reviewing results, and a few UI-first tasks
  (monitoring setup, traffic updates).

**The CLI isn't "for GitHub Actions", and GitHub Actions isn't CLI-only.**
The CLI runs anywhere: my terminal, Cloud Shell, scripts like `setup.sh`,
any CI/CD. A workflow can run SDK code too: lab 07's `deploy-prod.yml`
installs `azure-ai-ml` and runs `python src/deploy_to_online_endpoint.py`.
CLI + YAML is simply the **usual** choice in CI (a reviewable YAML in Git, a
one-line step, no Python to maintain).

**Exam:** expect code snippets in both forms, and know how they correspond.
