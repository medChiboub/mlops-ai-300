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

### 2.5 Plan how to extend the script for several environments (design)

```bash
ENVIRONMENT=${1:-dev}                    # ./setup.sh prod → prod; no argument → dev
if [ "$ENVIRONMENT" = "prod" ]; then
  RESOURCE_GROUP=$PROD_RESOURCE_GROUP; WORKSPACE_NAME=$PROD_WORKSPACE_NAME
else
  RESOURCE_GROUP=$DEV_RESOURCE_GROUP;  WORKSPACE_NAME=$DEV_WORKSPACE_NAME
fi
```
- **Shared, created once:** the registry. **Isolated per environment:**
  workspace, compute and data assets (so each gets its own access controls).
- **In CI:** GitHub Actions calls it with `dev` to validate PRs and `prod`
  for approved deployments; locally, `dev` rebuilds the experimentation
  environment.
- My project's version: **one Bicep template + one `.bicepparam` per
  environment**, the same idea, declarative.

### 2.6 Clean up (the lab's last step): skipped on purpose

The lab says to delete the extra resource groups. **I chose to keep all
three** (`rg-ai300-dev-…`, `rg-ai300-prod-…`, `rg-ai300-reg-…`). Ongoing cost:
mainly the registry's Premium ACR, **$1.67/day**. The dev compute instance is
stopped. They're on the final cleanup list after lab 07, together with the
lab 01 group and the service principal.

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

Domain 1: *Create and manage a workspace*, *Share assets across workspaces by
using registries*, *Deploy Machine Learning workspaces and resources by using
Bicep and Azure CLI*, *Create and manage data assets*; also the design side
of *Configure identity and access management*.

- **Why several workspaces:** security and compliance isolation, separate
  subscriptions for billing, and regions. Train in dev, deploy in test and
  prod. Keep **prod data out of dev** (separate data assets per workspace).
- **Registry:** shares **models, environments, components and data assets**
  across workspaces, regions and subscriptions in the same tenant. **Assets**
  are workspace-agnostic; **resources** (compute, jobs, endpoints) aren't.
- **Promotion:** publish a good model to the registry and deploy it from
  there (pattern A), or register components and environments and retrain in
  each workspace (pattern B, when prod data can't leave prod).
- **Create a registry:** YAML (`name`, `location`, `replication_locations`,
  where the primary appears in both) → `az ml registry create --file …
  --resource-group …`. Also possible from Studio, the portal, or REST. It
  provisions a **managed resource group** with storage per region and one
  **Premium ACR** with geo-replication. **The name** (unique in the tenant,
  32 characters max) and **the primary region can't be changed**; extra
  regions can be added.
- **Registry RBAC:** use assets → **Reader** (or `registries/read` +
  `registries/assets/read`); publish assets → add
  `registries/assets/write`/`delete` (a custom role); create or delete the
  registry → **Contributor/Owner**.
- **Scripted provisioning with the CLI:** a random suffix for unique names,
  `az provider register --namespace Microsoft.MachineLearningServices`,
  `az configure --defaults` (global, which is a trap with multiple
  environments), and rendering YAML with `sed` placeholders because the CLI
  reads YAML literally. "Repeatable, version-controlled" provisioning still
  points to **Bicep/ARM**.

## 5. Lab way vs. my production project

Tags (legend in [README](README.md#tags)): 🧪 lab shortcut · 📘 Microsoft docs
recommendation (**the exam answer**) · 🛠 my project's own choice.

| | Lab | My project | Microsoft's recommended answer |
|---|---|---|---|
| Environments | Dev + prod workspaces, one subscription and region | Dev, staging and prod resource groups, each from the same Bicep template with its own `.bicepparam` | 📘 Separate workspaces (and often subscriptions) per environment |
| Provisioning | 🧪 Imperative bash + `az`: no `set -e`, random region, a registry name that always fails, global defaults left on prod | Bicep (`infra/main.bicep`, `registry.bicep`): declarative, idempotent, fails loudly | 📘 **IaC (Bicep/ARM)** for repeatable environments; the CLI for one-off tasks |
| Registry | 🧪 Created, **never used** by labs 06–07 | `mlreg-diabetes`: `az ml model share` dev → registry, staging and prod deploy `azureml://registries/…/versions/N` | 📘 Publish approved assets to a registry and deploy them from there |
| Promotion pattern | Retrain in prod (lab 07) | Train once in dev, promote the same model (pattern A) | 📘 Both are documented; pattern B needs the components and environment in the registry, and a prod evaluation gate |
| Data separation | `diabetes-dev-folder` vs. `diabetes-prod-folder` (byte-identical files) | One data asset, used only by dev training | 📘 Separate data assets per environment; prod data stays in prod |
| Identity per environment | (Lab 07: one service principal for both) | OIDC, one app, federated per GitHub Environment | 📘 Least privilege, **separate identities** per environment |

## 6. In my words

<!-- Mine to write. -->

## 7. Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> You train a model in a dev workspace and must deploy exactly that model to a prod workspace in another subscription. What do you use?<br><br>A) Copy the model file to prod's datastore<br>B) Publish it to an Azure ML <strong>registry</strong> and deploy from the registry in prod<br>C) Retrain it in prod<br>D) Share the dev workspace with prod users</summary>

> **✅ Answer: B.** Registries decouple assets from workspaces, across subscriptions and regions, and keep lineage back to the training job.
</details>

---

<details>
<summary><strong>2.</strong> Production data can't leave the prod environment. How do you still reuse dev's validated training pipeline?<br><br>A) Copy prod data to dev<br>B) Register the pipeline's <strong>components and environment</strong> in a registry and run the pipeline in the prod workspace with prod data and compute<br>C) Deploy dev's model<br>D) Use one shared workspace</summary>

> **✅ Answer: B.** Pattern B. The docs: the compute and training data, unique to each workspace, determine where it runs.
</details>

---

<details>
<summary><strong>3.</strong> Which can a registry hold?<br><br>A) Compute clusters and endpoints<br>B) Models, environments, components and data assets<br>C) Jobs and their logs<br>D) Workspaces</summary>

> **✅ Answer: B.** Those are <em>assets</em> (workspace-agnostic). Compute, jobs and endpoints are <em>resources</em> (workspace-specific).
</details>

---

<details>
<summary><strong>4.</strong> <code>az ml registry create</code> fails with <em>"Names must be between 3 and 33 in length"</em>. The name was <code>mlr-ai300-shared-5ae342744a834c9880</code>. What happened, and what can you change later?<br><br>A) A region problem; rename later<br>B) The name is 35 characters, over the limit. Neither the name nor the primary region can be changed after creation, so pick both carefully<br>C) The name has a hyphen<br>D) The name is fine; retry</summary>

> **✅ Answer: B.** Lab 05's reference script always builds a 35-character name. We shortened the suffix to get 32 characters. Extra replication regions <em>can</em> be added later.
</details>

---

<details>
<summary><strong>5.</strong> A team should publish models to the shared registry but must not be able to delete the registry itself. Which role?<br><br>A) Owner<br>B) Contributor<br>C) A custom role with <code>registries/read</code>, <code>registries/assets/read</code>, <code>registries/assets/write</code> (and <code>delete</code> if needed), without <code>registries/write</code>/<code>delete</code><br>D) Reader</summary>

> **✅ Answer: C.** Contributor and Owner can also create, update and delete registries. Reader can only use assets.
</details>

---

<details>
<summary><strong>6.</strong> After running the multi-environment script, you run <code>az ml job create -f job.yml</code> without <code>-g</code>/<code>-w</code>. Where does the job go?<br><br>A) The first workspace created<br>B) Whatever <code>az configure --defaults</code> last set: here, <strong>prod</strong><br>C) An error<br>D) Dev, because it's the default environment</summary>

> **✅ Answer: B.** Defaults are global. The script left them on prod; we restored them. With several environments, pass <code>-g</code>/<code>-w</code> explicitly (or use per-environment config).
</details>

---

<details>
<summary><strong>7.</strong> What does creating a registry provision besides the registry resource?<br><br>A) Nothing<br>B) A compute cluster<br>C) An Azure-managed resource group with a storage account per region and a Premium Azure Container Registry (geo-replicated)<br>D) A new workspace</summary>

> **✅ Answer: C.** Ours: <code>azureml-rg-mlr-ai300-shared-…_&lt;guid&gt;</code> with a Premium ACR ($1.67/day) and Standard_LRS storage.
</details>

---

<details>
<summary><strong>8.</strong> A provisioning script's registry step fails, yet the script prints "Provisioning complete" and exits 0. Why, and what's the better approach?<br><br>A) Azure retried it<br>B) The bash script has no <code>set -e</code>, so it keeps going after errors. Read the logs; better, use declarative IaC (Bicep) that fails the deployment<br>C) The error was only a warning<br>D) Exit code 0 means it succeeded</summary>

> **✅ Answer: B.** Exactly what lab 05's reference script did.
</details>
