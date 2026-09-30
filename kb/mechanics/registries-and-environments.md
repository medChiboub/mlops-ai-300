# Registries and dev/prod environments

> The lab 05 resources described below were **deleted on 2026-09-30** (unused by labs 06–07; the registry cost about $1.67/day). Everything here is the verified record of what they were; `infra/setup-prod-design.sh` recreates them.

## The one idea

**Workspaces are per environment; assets can be shared.** Microsoft's docs
split Azure ML entities into two kinds:

| | Examples | Scope |
|---|---|---|
| **Assets** | models, environments, components, data assets | *Workspace-agnostic*: can live in a **registry** and be used from any workspace |
| **Resources** | compute, jobs, endpoints | *Workspace-specific*: an endpoint's URI or a job's logs belong to one workspace |

A **registry** is a central store for assets (a bit like a Git repository),
outside any workspace. Dev publishes an asset; test and prod use it.

## Why separate dev and prod workspaces

From the docs, the drivers are **security and compliance** (isolate access,
network and data), **subscriptions** (separate billing and budgets), and
**regions** (latency, redundancy). The lab's design:

```
rg-ai300-dev-<s>   mlw-ai300-dev-<s>   compute + diabetes-dev-folder      (experiment)
rg-ai300-prod-<s>  mlw-ai300-prod-<s>  diabetes-prod-folder, no compute   (production)
rg-ai300-reg-<s>   mlr-ai300-shared-…  registry                           (shared, approved assets)
```

## Two promotion patterns (and what the registry carries in each)

| | A. Promote the model | B. Promote the pipeline, retrain in prod |
|---|---|---|
| Moves dev → prod | The trained model | Components + environment |
| Prod does | Deploys that exact model | Runs the pipeline on prod data and compute |
| Use when | Dev data represents prod | Prod data can't leave prod |

The docs: *"register the components and environments that form the building
blocks of the pipeline… the compute and the training data, which are unique
to each workspace, determine the workspace to run in."* A model already in
a workspace can be **promoted** to a registry, or registered in a registry
straight from a job's output.

## What `az ml registry create` actually built (verified, lab 05)

```yaml
# registry.generated.yml (rendered from infra/registry.yml)
name: mlr-ai300-shared-5ae342744a834c9
location: canadaeast                  # primary region: can't be changed later
replication_locations:
  - location: canadaeast              # the primary appears again here; other regions can be added later
```

- **In `rg-ai300-reg-…`:** only the registry resource itself, with a
  **system-assigned managed identity**.
- **An Azure-owned managed resource group**
  `azureml-rg-<registry>_<guid>` (`managedBy` = the registry) holding a
  **Premium Azure Container Registry** (the environment images) and a
  **Standard_LRS storage account** (the model and data files). For each extra
  replication region you get another storage account, plus ACR geo-replication.
- **Its MLflow URI** is `azureml://canadaeast.api.azureml.ms/mlflow/v1.0/…/registries/<name>`.
  Assets are referenced as `azureml://registries/<name>/models/<model>/versions/<n>`.
- It took **45 s** to create.
- **Cost:** the Premium ACR is **$1.67/day** in canadaeast, whether used or not.

## Rules worth knowing (docs, confirmed by a real failure)

- **Name:** 2–32 characters (the error we got says 3–33), letters, digits,
  `-` and `_`, starting with a letter or digit, **unique in the Entra
  tenant**, and **can't be changed** (it's part of every asset ID).
  ⚠ The reference script's `mlr-ai300-shared-<18-char suffix>` is **35
  characters**, so it always fails:
  `Registry Name … is invalid. Names must be between 3 and 33 in length`.
- **Regions:** the primary is fixed at creation; others can be added later.
  Plan every region where you have or will have workspaces.
- **Who can create one:** Owner or Contributor on the resource group or
  subscription.

## Access (RBAC)

| Goal | Role |
|---|---|
| Use assets from the registry | Built-in **Reader**, or custom `registries/read` + `registries/assets/read` |
| Create and delete assets too | + `registries/assets/write`, `registries/assets/delete` (custom role) |
| Create, update or delete the registry | **Contributor** / **Owner** |

⚠ Contributor/Owner can also delete the registry. To let a team publish
assets without managing the registry, use a **custom role** with only the
asset permissions.

## Lab vs. my production project

| | Lab 05 | My project |
|---|---|---|
| Environments | Dev + prod workspaces (same subscription and region) | Dev, staging, prod resource groups (Bicep, one param file each) |
| Registry | Created, **never used** by labs 06–07 | `mlreg-diabetes`, the core of promotion: `az ml model share` dev → registry, staging/prod deploy that version |
| Provisioning | Imperative bash + `az` (no `set -e`: it continued after the registry error and printed "Provisioning complete") | Bicep: declarative; a failed resource fails the deployment |
