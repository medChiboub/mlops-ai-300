# Lab 05: Plan and prepare an MLOps solution

Source: [docs/05-plan-and-prepare.md](../docs/05-plan-and-prepare.md)

**No Microsoft Learn module:** the learning path *Operationalize machine
learning models (MLOps)* has no module whose exercise is this lab. The
path's description mentions "plan an MLOps solution", but modules 6 and 7
link to labs 06 and 07. The theory comes from the product docs instead:
[Machine Learning registries](https://learn.microsoft.com/en-us/azure/machine-learning/concept-machine-learning-registries-mlops?view=azureml-api-2)
(updated 2026-07-07) and
[Create and manage registries](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-registries?view=azureml-api-2)
(2026-01-28).

Mechanics: [registries and environments](mechanics/registries-and-environments.md) · [workspace and storage](mechanics/workspace-and-storage.md)

## 1. What this lab does

Moves from one workspace to an **environment strategy**: separate **dev**
and **prod** workspaces (each with its own data), plus one **shared Azure ML
registry** for promoting models and environments between them. You review
`infra/setup.sh`, design the target architecture, write the Azure CLI
commands for it into your own `setup-prod-design.sh`, check it against the
reference `infra/setup-mlops-envs.sh`, and (optionally, which we did) run it.

## 2. Steps I actually ran

### 2.1 Review the existing dev script (`infra/setup.sh`)

Already ran in lab 01. It creates: a resource group with a random suffix
(`rg-ai300-l…`), a workspace (`mlw-ai300-l…`), a compute instance, a compute
cluster, and data assets from `data/diabetes-data`. Patterns the lab
points out: **a random suffix** to avoid name collisions, **registering the
`Microsoft.MachineLearningServices` provider**, and **`az configure
--defaults`** so later `az ml` commands don't need `-g`/`-w`.

### 2.2 Design dev and prod environments (the target architecture)

| | Dev | Prod | Shared |
|---|---|---|---|
| Resource group | `rg-ai300-dev-<suffix>` | `rg-ai300-prod-<suffix>` | `rg-ai300-reg-<suffix>` |
| What's in it | Workspace `mlw-ai300-dev-<suffix>` + compute + data asset `diabetes-dev-folder` | Workspace `mlw-ai300-prod-<suffix>` + data asset `diabetes-prod-folder` | Registry `mlr-ai300-shared-<suffix>` |
| Purpose | Experiment and train | Production training and deployment | Store and **promote** models and environments across workspaces |

The principles: **separate workspaces** isolate experiments from production
(access, network, data); **a shared registry** carries approved assets
between them; **separate data assets** keep production data out of dev.

### 2.3 Plan the CLI commands (`infra/setup-prod-design.sh`)

Following the lab literally (`cp setup.sh setup-prod-design.sh`, add the
dev/prod/registry variables at the top, append the planned registry,
prod-workspace and data-asset commands), then diffing against
`setup-mlops-envs.sh` as the lab says:

- ⚠ **The literal result is broken.** It **still creates `rg-ai300-l<suffix>`**
  with its workspace, compute instance and cluster (the whole of
  `setup.sh`), and it **never creates the dev resource group or dev
  workspace**, yet its dev data-asset command targets them. Run as is, it
  would fail halfway **and** leave a second `rg-ai300-l*` group, which breaks
  labs 06–07 (their workflows take the *first* `rg-ai300-l*` group they
  find).
- The lab's "diff, then update your script" step is what fixes it. The
  final `infra/setup-prod-design.sh` = the reference script.
- `infra/registry.yml` already has the placeholders the lab asks for
  (`REGISTRY_NAME_PLACEHOLDER`, `PRIMARY_REGION_PLACEHOLDER`). Upstream
  already applied that change.

### 2.4 Run the design script (the lab's optional step, done)

Ran a scratchpad copy of `infra/setup-prod-design.sh` from `infra/`: suffix
from `uuidgen`, region pinned to `canadaeast` (same macOS fix as lab 01).
Suffix `5ae342744a834c9880`.

| Created | Result |
|---|---|
| `rg-ai300-dev-…` → `mlw-ai300-dev-…` + compute instance `ci5ae342744a834c9880` + `aml-cluster` + `diabetes-training`, `diabetes-data`, `diabetes-dev-folder` | ✅ |
| `rg-ai300-prod-…` → `mlw-ai300-prod-…` + `diabetes-prod-folder` (no compute) | ✅ |
| `rg-ai300-reg-…` → registry `mlr-ai300-shared-5ae342744a834c9880` | ❌ `Registry Name … is invalid. Names must be between 3 and 33 in length` |

The script still exited **0** and printed "Provisioning complete", because it
has no `set -e`.

Fix: I kept the naming pattern, shortened the suffix to fit, and
re-rendered and created only the registry:

```bash
N="mlr-ai300-shared-5ae342744a834c9"          # 32 characters
sed -e "s|REGISTRY_NAME_PLACEHOLDER|$N|g" -e "s|PRIMARY_REGION_PLACEHOLDER|canadaeast|g" \
    registry.yml > registry.generated.yml
az ml registry create --file registry.generated.yml --resource-group rg-ai300-reg-5ae342744a834c9880
```

It was created in 45 s. That also created the managed resource group
`azureml-rg-mlr-ai300-shared-5ae342744a834c9_<guid>` (Premium ACR + Standard_LRS
storage). Details in [mechanics/registries-and-environments.md](mechanics/registries-and-environments.md).

Afterwards Claude:
- **stopped the dev compute instance** (lab 05 doesn't use it)
- **restored the `az` defaults** to the lab 01 workspace (the script had left
  them on *prod*)
- confirmed **no new `rg-ai300-l*` group**, so labs 06–07's workspace
  discovery is unaffected

### Why a registry, if prod retrains anyway?

The labs create the registry but never use it: lab 07 retrains in prod and
deploys the committed `model/` folder. But there are two promotion patterns,
and a registry serves both:

| | **A. Promote the model** | **B. Promote the pipeline, retrain in prod** |
|---|---|---|
| What moves dev → prod | The trained **model** | The **components + environment** |
| What prod does | Deploys that exact model | Runs the same pipeline on **prod data** and compute |
| The registry holds | `model:N` | `prep:3`, `train:5`, `train-env:2` (+ prod's model, if reused elsewhere) |
| Use when | Dev data represents prod; you want the exact reviewed artifact in prod | **Prod data can't leave prod** (privacy, compliance) |
| Example | My production project (`az ml model share` → `mlreg-diabetes`) | The lab's design, but nothing gets registered |

Even with B, the registry makes prod run **the exact reviewed versions**
of the code and environment, not whatever is in a branch. From the docs:
*"register the components and environments that form the building blocks of
the pipeline… the compute and the training data, which are unique to each
workspace, determine the workspace to run in."* Deeper comparison:
`../MLOps_Project_Azure_ML/docs/AI300_PREP/MLOPS_CICD_CT.md`.

Exam cues: *share across workspaces* → registry; *train in dev, deploy the
same model in prod* → publish the model to a registry; *prod data can't leave
prod* → register components and environments, retrain in prod.

## 3. What broke and how we fixed it

- **The lab's literal design script would have broken labs 06–07** (see
  2.3). Caught by the lab's own diff step before running.
- **The reference script's registry name is too long, every time:**
  `mlr-ai300-shared-` (17) + an 18-character suffix = 35 characters, over
  the limit. Microsoft's own script can't create its registry. Fixed by
  shortening the suffix (see 2.4).
- **No `set -e`:** after the registry failed, the script kept going and
  printed "Provisioning complete" with exit code 0. Always read the log;
  don't trust "complete".
- **The script leaves `az` defaults on the *prod* workspace**
  (`az configure --defaults` is global). Anything run afterwards without
  `-g/-w` would have hit prod. Restored.
- **A stopped compute instance still uses quota.** `az ml compute list-usage`
  showed DSv2 **2/6** with the lab 01 compute instance *Stopped* and the
  cluster at 0 nodes. Stopping saves money, not quota.

## 4. Exam mapping

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check
