# SDK v2 + MLflow: the master cheat sheet (MLOps half)

One page for the code side of AI-300 domains 1–2. About **30 of the 100
MLOps practice questions** were code: fill a blank in SDK v2 or MLflow, or
read an exhibit. They test **exact names**, and the distractors are near
misses (`log_metric` vs. `log_metrics`, `dump` vs. `dumps`, `load` vs.
`from_delimited_files`). Review it the night before.

Sources, tagged per line where it matters:
- 📘 **Microsoft Learn / SDK reference**: the exam's answer.
- 🧪 **The labs** (this repo, `mslearn-mlops`): what the exam's hands-on material does.
- 🛠 **My project** ([mlops-diabetes-project](https://github.com/medChiboub/mlops-diabetes-project/blob/main/README.md)): real code that ran; mostly YAML + CLI, with SDK v2 in `ml/experiments/`.
- **Qn**: the practice question that tested it.

When the three disagree, answer with 📘. Sections added on 2026-10-31
(identity, interactive data, distributed training, Spark, feature store, GitHub Actions,
MLflow models, troubleshooting, registries) were checked that day against the current
Microsoft Learn pages linked in them. The deep explanations live in the
other mechanics notes; this page is the API surface.

## Contents

1. [The pattern behind every call](#1-the-pattern-behind-every-call)
2. [Connect](#2-connect)
3. [Workspace and network](#3-workspace-and-network)
4. [Identity and access](#4-identity-and-access)
5. [Datastores](#5-datastores)
6. [Data assets, paths, MLTable](#6-data-assets-paths-mltable)
7. [Compute](#7-compute)
8. [Environments](#8-environments)
9. [Command jobs](#9-command-jobs)
10. [Distributed training and Spark](#10-distributed-training-and-spark)
11. [Sweep jobs](#11-sweep-jobs)
12. [AutoML](#12-automl)
13. [Components, pipelines, schedules](#13-components-pipelines-schedules)
14. [MLflow tracking](#14-mlflow-tracking)
15. [Models: register, archive, share, package](#15-models-register-archive-share-package)
16. [Feature store and the feature retrieval spec](#16-feature-store-and-the-feature-retrieval-spec)
17. [Online endpoints](#17-online-endpoints)
18. [Batch endpoints](#18-batch-endpoints)
19. [Monitoring](#19-monitoring)
20. [Responsible AI and Fairlearn](#20-responsible-ai-and-fairlearn)
21. [Notebook and terminal bits](#21-notebook-and-terminal-bits)
22. [GitHub Actions](#22-github-actions)
23. [CLI ↔ SDK map](#23-cli--sdk-map)
24. [Near-miss traps](#24-near-miss-traps)
25. [Exam vs. lab vs. my project](#25-exam-vs-lab-vs-my-project)

## 1. The pattern behind every call

```python
entity = SomeEntity(...)                                   # describe it (azure.ai.ml.entities)
ml_client.<collection>.create_or_update(entity)            # fast operations: data, environments, models, components, jobs
ml_client.<collection>.begin_create_or_update(entity).result()  # long-running: compute, endpoints, deployments, schedules, workspaces
```

| Import from | What lives there |
|---|---|
| `azure.ai.ml` | `MLClient`, `Input`, `Output`, `command`, `automl`, `load_component`, `load_job`, … |
| `azure.ai.ml.entities` | `Data`, `Environment`, `BuildContext`, `Model`, `AmlCompute`, `ComputeInstance`, `Workspace`, `ManagedNetwork`, `AzureBlobDatastore`, `AzureDataLakeGen2Datastore`, `AccountKeyConfiguration`, `SasTokenConfiguration`, `ManagedOnlineEndpoint`, `ManagedOnlineDeployment`, `CodeConfiguration`, `BatchEndpoint`, `BatchDeployment`, `JobSchedule`, `RecurrenceTrigger`, `RecurrencePattern`, `CronTrigger` |
| `azure.ai.ml.constants` | **`AssetTypes`** (`URI_FILE`, `URI_FOLDER`, `MLTABLE`, `MLFLOW_MODEL`, `CUSTOM_MODEL`), `InputOutputModes` [Q113](../../../practice/mlops/q113-automl-image-mltable-input.md) |
| `azure.ai.ml.sweep` | `Choice`, `Uniform`, `QUniform`, `LogUniform`, `Normal`, …, `BanditPolicy`, `MedianStoppingPolicy`, `TruncationSelectionPolicy` |
| `azure.ai.ml.dsl` | `pipeline` (the decorator) |
| `mldesigner` | `command_component` (+ its own `Input`, `Output`) [Q111](../../../practice/mlops/q111-command-component-decorator.md) |
| `azure.identity` | `DefaultAzureCredential`, `InteractiveBrowserCredential` |

## 2. Connect

```python
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

ml_client = MLClient(DefaultAzureCredential(), subscription_id, resource_group, workspace_name)  # 🛠 every script
ml_client = MLClient.from_config(credential=DefaultAzureCredential())  # reads config.json (present on a compute instance) [Q159](../../../practice/mlops/q159-mlclient-command-job.md)
registry_client = MLClient(DefaultAzureCredential(), registry_name="azureml")  # a registry, not a workspace 🛠 RAI components
```

- `DefaultAzureCredential` tries env vars → managed identity → Azure CLI login → …
  On a compute instance or in CI it just works.
- Trap: `MLClient` ≠ `Workspace`. `from_config` is a **class method of `MLClient`**.

## 3. Workspace and network

```python
from azure.ai.ml.entities import Workspace, ManagedNetwork

ws = Workspace(
    name="mlw-prod", location="eastus",
    public_network_access="Disabled",                        # inbound: no public access 📘
    managed_network=ManagedNetwork(isolation_mode="allow_only_approved_outbound"),  # outbound 📘
)
ml_client.workspaces.begin_create(ws).result()
ml_client.workspaces.begin_provision_network(workspace_name="mlw-prod").result()  # build the managed VNet now
```

- Isolation modes: `disabled` · `allow_internet_outbound` · `allow_only_approved_outbound`. One-way door: you can tighten, not loosen.
- Inbound = public network access + **private endpoint** (`amlworkspace` sub-resource) [Q53](../../../practice/mlops/q053-workspace-private-endpoint.md). Outbound = managed VNet.
- 🛠 My project: Bicep (`infra/main.bicep`), public access left on. Details: [network-isolation.md](network-isolation.md).

## 4. Identity and access

📘 [Identity-based service authentication](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-identity-based-service-authentication?view=azureml-api-2),
[Manage roles](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-assign-roles?view=azureml-api-2).

```python
from azure.ai.ml.entities import AmlCompute, IdentityConfiguration, ManagedIdentityConfiguration, UserIdentityConfiguration
from azure.ai.ml.constants import ManagedServiceIdentityType

cluster = AmlCompute(name="train-cluster", size="STANDARD_DS3_v2", max_instances=4,
    identity=IdentityConfiguration(type=ManagedServiceIdentityType.SYSTEM_ASSIGNED))   # or USER_ASSIGNED +
    # user_assigned_identities=[ManagedIdentityConfiguration(resource_id="/subscriptions/.../userAssignedIdentities/uai")]

job = command(..., identity=UserIdentityConfiguration())     # run as the submitting user (YAML: identity: type: user_identity)
job = command(..., identity=ManagedIdentityConfiguration())  # run as the compute's managed identity (YAML: type: managed)
```

| Who | Needs | For |
|---|---|---|
| Compute identity | **Storage Blob Data Reader** (minimum) on the storage account | Credential-less (identity-based) datastores |
| Compute identity | **AcrPull** on the container registry | Pulling environment images 🛠 (one of my real bugs) |
| A user | Storage Blob Data Reader | Their own identity-based data access |
| Whoever assigns a user-assigned identity to compute | Managed Identity Operator | |

- A cluster has **one system-assigned *or* several user-assigned** identities, not both.
- Default job identity with identity-based datastores = the compute's managed identity. A job can't mix user and compute identity. In pipelines, set identity **per step** (on the root it does nothing).
- Workspace identity: system-assigned by default; you can go to system + user-assigned, never back.
  New workspaces (since 2024-11-19) give it **Azure AI Administrator**, not Contributor.

Built-in roles:

| Role | Can | Can't |
|---|---|---|
| **AzureML Data Scientist** | Everything in the workspace: jobs, assets, deployments, endpoint keys/tokens | Create/delete compute, change the workspace |
| **AzureML Compute Operator** | Create, manage, delete compute | |
| **AzureML Registry User** (registry scope) | Read, write, delete assets in a registry | Create/delete the registry |
| Reader | View (including datastore credentials) | Change anything |
| Contributor | All of the above + create compute, deploy | Assign roles |
| Owner | Everything, including role assignments | |

Custom role = JSON (`Actions`, `NotActions`, `AssignableScopes`) → `az role definition create --role-definition role.json`
(needs Owner; changes take 15–60 min). Details: [workspace-and-storage.md](workspace-and-storage.md), [github-actions-azureml.md](github-actions-azureml.md).

## 5. Datastores

```python
from azure.ai.ml.entities import AzureBlobDatastore, AccountKeyConfiguration, SasTokenConfiguration

store = AzureBlobDatastore(
    name="blobdatastore",
    account_name="storage1",             # from https://storage1.blob.core.windows.net/data1
    container_name="data1",              # ← the blank [Q124](../../../practice/mlops/q124-blob-datastore-account-key.md) [Q146](../../../practice/mlops/q146-blob-datastore-sas.md)
    protocol="wasbs",                    # or "https" (default)
    credentials=AccountKeyConfiguration(account_key="..."),   # never expires
    # credentials=SasTokenConfiguration(sas_token="..."),     # time-limited access [Q146](../../../practice/mlops/q146-blob-datastore-sas.md)
    # credentials omitted                                     # identity-based (no secret stored)
)
ml_client.create_or_update(store)
```

| Class | Storage | Key parameter |
|---|---|---|
| `AzureBlobDatastore` | Blob | `container_name` |
| `AzureDataLakeGen2Datastore` | ADLS Gen2 | `filesystem` |
| `AzureFileDatastore` | File share | `file_share_name` |

Credential classes: `AccountKeyConfiguration`, `SasTokenConfiguration`,
`ServicePrincipalConfiguration`, or none. The 4 built-in datastores:
`workspaceblobstore` (default), `workspaceworkingdirectory`,
`workspacefilestore`, `workspaceartifactstore`. Details: [data-assets.md](data-assets.md), [workspace-and-storage.md](workspace-and-storage.md).

## 6. Data assets, paths, MLTable

```python
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes

data = Data(name="diabetes-raw", version="1", type=AssetTypes.URI_FILE, path="./data/diabetes.csv")
ml_client.data.create_or_update(data)          # local path → uploaded to workspaceblobstore
ml_client.data.get("diabetes-raw", version="1")
ml_client.data.get("diabetes-raw", label="latest")
```

| Type | What it is | Typical use |
|---|---|---|
| `URI_FILE` | One file | A CSV for a command job 🧪 🛠 |
| `URI_FOLDER` | A folder (all files under it) | Images, many CSVs, "all blobs in the container" [Q1](../../../practice/mlops/q001-data-asset-public-blob-uri.md) [Q125](../../../practice/mlops/q125-image-files-uri-folder-wasbs.md) |
| `MLTABLE` | Folder + an `MLTable` file (schema, transforms) | **AutoML** (all tasks, including vision over JSONL) [Q113](../../../practice/mlops/q113-automl-image-mltable-input.md) [Q156](../../../practice/mlops/q156-automl-vision-jsonl.md) [Q162](../../../practice/mlops/q162-automl-parquet-compute.md) |

Paths (the **shape** decides the scheme) [Q1](../../../practice/mlops/q001-data-asset-public-blob-uri.md) [Q125](../../../practice/mlops/q125-image-files-uri-folder-wasbs.md) [Q165](../../../../GenAIOps-ai-300/practice/q165-foundry-blob-wasbs.md):

```
https://<account>.blob.core.windows.net/<container>/<path>     public blob / web
wasbs://<container>@<account>.blob.core.windows.net/<path>     Blob (container BEFORE @)
abfss://<filesystem>@<account>.dfs.core.windows.net/<path>     ADLS Gen2 (.dfs.)
azureml://datastores/<datastore>/paths/<path>                  via a datastore (recommended)
azureml:<name>:<version>                                       an existing data asset (in jobs)
```

MLTable in code [Q47](../../../practice/mlops/q047-load-mltable.md) [Q144](../../../practice/mlops/q144-mltable-from-delimited-files.md):

```python
import mltable
tbl = mltable.load("./sample_data")                    # the FOLDER that holds the MLTable file, not the file
tbl = mltable.load(f"azureml:/{data_asset.id}")        # a registered MLTable asset
tbl = mltable.from_delimited_files(paths=[{"pattern": "./folder/*.csv"}])   # CSVs, no MLTable file yet
tbl = mltable.from_parquet_files(paths=[{"file": "./x.parquet"}])           # also from_json_lines_files, from_delta_lake
tbl.save("./folder")                                   # writes the MLTable file
df = tbl.to_pandas_dataframe()                         # materialize
```

Interactive access without downloading (📘 [interactive data access](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-access-data-interactive?view=azureml-api-2); `pip install azureml-fsspec mltable`):

```python
import pandas as pd
df = pd.read_csv("azureml://subscriptions/<sub>/resourcegroups/<rg>/workspaces/<ws>/datastores/<store>/paths/<folder>/file.csv")

from azureml.fsspec import AzureMachineLearningFileSystem
fs = AzureMachineLearningFileSystem("azureml://subscriptions/<sub>/resourcegroups/<rg>/workspaces/<ws>/datastores/<store>")
fs.ls(); fs.glob("/<folder>/*.csv"); fs.exists(...); fs.upload(lpath=..., rpath=..., recursive=True); fs.download(rpath=..., lpath=...)
with fs.open("./folder1/file1.csv") as f:
    df = pd.read_csv(f)

asset = ml_client.data.get(name="titanic", version="1")
mltable.load(f"azureml:/{asset.id}")                          # an MLTable asset
mltable.from_delimited_files(paths=[{"file": asset.path}])    # a uri_file asset   ({"folder": ...} for uri_folder)
```

Pandas only for data that fits in memory; bigger → Spark (below).

Quick stats on a CSV: `pandas.read_csv(...).describe()` (count, mean, std, min, 25/50/75%, max) [Q149](../../../practice/mlops/q149-pandas-describe.md).
Reproducibility: versions are immutable, but a version points at a **path**;
write each refresh to a new folder [Q130](../../../practice/mlops/q130-versioned-data-reproducibility.md).

## 7. Compute

```python
from azure.ai.ml.entities import AmlCompute, ComputeInstance

cluster = AmlCompute(
    name="train-cluster", size="STANDARD_DS3_v2",
    min_instances=0,                     # 0 = free when idle [Q17](../../../practice/mlops/q017-compute-per-workload.md) [Q163](../../../practice/mlops/q163-cluster-cost-tier-min-instances.md)
    max_instances=4,
    idle_time_before_scale_down=120,     # seconds
    tier="low_priority",                 # or "dedicated"; cheaper, preemptible [Q83](../../../practice/mlops/q083-low-priority-compute-cluster.md) [Q163](../../../practice/mlops/q163-cluster-cost-tier-min-instances.md)
)
ml_client.compute.begin_create_or_update(cluster).result()

ci = ComputeInstance(name="ci-me", size="STANDARD_DS11_V2")    # interactive dev box
ml_client.compute.begin_create_or_update(ci).result()
```

Serverless (📘 [serverless compute](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-use-serverless-compute?view=azureml-api-2)): omit `compute`, then optionally

```python
from azure.ai.ml.entities import JobResourceConfiguration
job.resources = JobResourceConfiguration(instance_type="Standard_E4s_v3", instance_count=1)
job.queue_settings = {"job_tier": "Spot"}          # "Spot" (low priority) | "Standard" (default)
pipeline_job.settings.default_compute = "serverless"
```

Works for command (incl. distributed), sweep, AutoML (uses `ResourceConfiguration`) and parallel jobs. Identity: user
(`UserIdentityConfiguration`) or the workspace's **user-assigned** identity; system-assigned isn't supported.

Compute instance options (📘 [create a compute instance](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-create-compute-instance?view=azureml-api-2)):
`ComputeInstance(name=..., size=..., idle_time_before_shutdown_minutes=30, schedules=ComputeSchedules(compute_start_stop=[ComputeStartStopSchedule(action="stop", trigger=CronTrigger(...))]))`.
Idle shutdown 15 min–3 days; up to 4 schedules; **size and SSH can't be changed after creation**; assigning it to another user is "create on behalf of" (studio or ARM template).

- Instance = interactive (notebooks, terminal). Cluster = jobs, autoscaling. **Serverless** = omit `compute` in a job.
- Low priority: fine for training and **batch** endpoints; not for managed online endpoints.
- Cut cost without cutting capacity: change `tier` and `min_instances`, **not** `max_instances` or `size` [Q163](../../../practice/mlops/q163-cluster-cost-tier-min-instances.md).
- 🛠 My project: `compute.bicep` (`train-cluster`); 🧪 the lab creates both from the CLI.

## 8. Environments

```python
from azure.ai.ml.entities import Environment, BuildContext

Environment(name="env-a", image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04")             # image as-is [Q21](../../../practice/mlops/q021-environment-from-docker-image.md)
Environment(name="env-b", image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04",
            conda_file="conda.yml")                                                               # image + packages 🧪 🛠
Environment(name="env-c", build=BuildContext(path="docker-context/"))                             # from a Dockerfile
ml_client.environments.create_or_update(env)                                                      # new VERSION each time
```

- Versions are **immutable**: a new image tag or package = a new version via `Environment(...)` + `create_or_update` [Q40](../../../practice/mlops/q040-new-environment-version-for-image.md) [Q82](../../../practice/mlops/q082-environment-lifecycle.md).
- Reference: `"azureml:diabetes-train-env:1"` 🛠, a curated one from the `azureml` registry (`"azureml://registries/azureml/environments/<name>/labels/latest"`), or `"<name>@latest"` for the latest version of a workspace environment ([Q159](../../../practice/mlops/q159-mlclient-command-job.md) uses `aml-scikit-learn@latest`).
- "Identical dependencies in every job" → define an **environment** (not job config) [Q109](../../../practice/mlops/q109-environment-for-consistent-deps.md).

## 9. Command jobs

```python
from azure.ai.ml import command, Input, Output
from azure.ai.ml.constants import AssetTypes

job = command(
    code="./src",                                                 # uploaded as the snapshot (.amlignore applies)
    command="python train.py --training_data ${{inputs.training_data}} --reg_rate ${{inputs.reg_rate}} "
            "--model_output ${{outputs.model_output}}",
    inputs={
        "training_data": Input(type=AssetTypes.URI_FILE, path="azureml:diabetes-data:1"),
        "reg_rate": 0.01,
    },
    outputs={"model_output": Output(type=AssetTypes.URI_FOLDER)},
    environment="azureml:diabetes-train-env:1",
    compute="train-cluster",                                      # omit → serverless
    experiment_name="diabetes-training",
    display_name="train-v1",
)
returned = ml_client.jobs.create_or_update(job)                   # submit (also ml_client.create_or_update(job))
ml_client.jobs.stream(returned.name)                              # follow the logs
ml_client.jobs.download(returned.name, output_name="model_output")
```

- `${{inputs.x}}` resolves to a path at run time. The **flag must match the script's argparse name exactly**,
  and the script name must be right [Q58](../../../practice/mlops/q058-command-arg-literal-name.md) [Q59](../../../practice/mlops/q059-command-arg-wrong-flag.md) [Q60](../../../practice/mlops/q060-command-arg-positional-file.md):
  `python script.py --training_data ${{inputs.training_data}}` ✅ ·
  `--trainingdata` ❌ · a bare `training_data` ❌ · a positional `dataset1.csv` ❌.
- Input modes: `ro_mount` (default for folders), `download`, `direct`; outputs `rw_mount` (default) or `upload`.
- **`.amlignore` beats `.gitignore`**: if both exist, only `.amlignore` filters the snapshot [Q112](../../../practice/mlops/q112-amlignore-over-gitignore.md).
- 🧪 YAML twin: `src/job.yml` + `az ml job create -f job.yml`. Details: [command-jobs.md](command-jobs.md).

## 10. Distributed training and Spark

📘 [Distributed GPU training](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-train-distributed-gpu?view=azureml-api-2) (`azure-ai-ml` ≥ 1.5.0). Not done in the labs or my project: docs only.

```python
job = command(
    code="./src", command="python train.py --epochs ${{inputs.epochs}}", inputs={"epochs": 1},
    environment="azureml:AzureML-acpt-pytorch-2.8-cuda12.6@latest",
    compute="gpu-cluster",
    instance_count=2,                                                       # nodes
    distribution={"type": "PyTorch", "process_count_per_instance": 1},       # = GPUs per node
)
# MPI (Horovod, DeepSpeed):  {"type": "mpi", "process_count_per_instance": 1}
# TensorFlow:                {"type": "tensorflow", "worker_count": 2, "parameter_server_count": 1}   # PS = TF 1.x only
# Typed classes also exist: PyTorchDistribution, MpiDistribution, TensorFlowDistribution
```

| Framework | Azure ML sets | Script does |
|---|---|---|
| PyTorch | `MASTER_ADDR`, `MASTER_PORT`, `WORLD_SIZE`, `NODE_RANK` (per node); `RANK`, `LOCAL_RANK` (per process) | `torch.distributed.init_process_group(backend="nccl", init_method="env://")`; no launcher needed |
| TensorFlow | `TF_CONFIG` per worker | `tf.distribute` strategy |

- If `process_count_per_instance` is omitted, Azure ML starts **one process per node**.
- **InfiniBand** = SKUs with an **"r"** (RDMA), e.g. `Standard_NC24rs_v3`, not `Standard_NC24s_v3`; drivers preinstalled on AmlCompute.
- **DeepSpeed** runs through the PyTorch or MPI distribution; a curated ACPT environment ships it.
- AutoML classification/regression distributed: trials run one after another, `max_concurrent_trials` ignored.

Spark (📘 [Spark jobs](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-submit-spark-jobs?view=azureml-api-2)): data too big for pandas.

```python
from azure.ai.ml import spark, Input, Output
spark_job = spark(
    code="./src", entry={"file": "titanic.py"},
    driver_cores=1, driver_memory="2g", executor_cores=2, executor_memory="2g", executor_instances=2,
    resources={"instance_type": "Standard_E8S_V3", "runtime_version": "3.4.0"},   # serverless Spark
    # compute="<attached Synapse pool>"                                          # instead of resources
    inputs={"titanic_data": Input(type="uri_file", path="azureml://datastores/workspaceblobstore/paths/data/titanic.csv", mode="direct")},
)
ml_client.jobs.create_or_update(spark_job)
```

The job's identity needs Contributor + **Storage Blob Data Contributor** on the storage. Monitoring jobs also run on serverless Spark.

## 11. Sweep jobs

```python
from azure.ai.ml.sweep import Choice, Uniform, BanditPolicy

job_for_sweep = job(reg_rate=Choice(values=[0.01, 0.1, 1]))        # 🧪 lab 03; 🛠 max_depth=Choice([5, 10, 20, 50])
sweep_job = job_for_sweep.sweep(
    compute="train-cluster",
    sampling_algorithm="grid",                 # "random" | "grid" | "bayesian"
    primary_metric="training_accuracy_score",  # EXACT name the script logs with mlflow
    goal="Maximize",                           # or "Minimize"
    early_termination_policy=BanditPolicy(slack_factor=0.1, evaluation_interval=1, delay_evaluation=5),
)
sweep_job.set_limits(max_total_trials=4, max_concurrent_trials=2, timeout=7200)   # also trial_timeout
ml_client.jobs.create_or_update(sweep_job)
```

| Sampling | Allowed distributions | Note |
|---|---|---|
| Grid | `Choice` only | The only way to try **every** combination [Q142](../../../practice/mlops/q142-sweep-distributions-exhibit.md) |
| Random | All | Sobol: `RandomSamplingAlgorithm(seed=…, rule="sobol")` |
| Bayesian | **`Choice`, `Uniform`, `QUniform` only** [Q160](../../../practice/mlops/q160-bayesian-distributions.md) | No early termination; **lower `max_concurrent_trials`** converges better [Q138](../../../practice/mlops/q138-bayesian-concurrency.md); ≥ 20 × #params trials |

| Policy | Cancels a trial when | Cue |
|---|---|---|
| `BanditPolicy(slack_factor=0.25)` / `(slack_amount=0.2)` | Below `best/(1+slack_factor)` or `best − slack_amount` | "compared with the **best** run" [Q62](../../../practice/mlops/q062-bandit-slack-factor.md) [Q158](../../../practice/mlops/q158-bandit-delay-interval.md) |
| `MedianStoppingPolicy()` | Below the median of all trials' running averages | "all runs" [Q23](../../../practice/mlops/q023-early-termination-relative-policies.md) |
| `TruncationSelectionPolicy(truncation_percentage=20)` | In the worst X% | "percentage of worst runs" [Q23](../../../practice/mlops/q023-early-termination-relative-policies.md) |

`evaluation_interval=1` = check every report; `delay_evaluation=5` = skip the first 5.
`slack_factor=0.1` → cancel below ≈ 91% of the best [Q158](../../../practice/mlops/q158-bandit-delay-interval.md). `Normal(10, 3)` = mean 10, SD 3;
`Uniform(0.05, 0.1)` = any value in between; `Choice(range(3,5))` = 3 or 4 [Q142](../../../practice/mlops/q142-sweep-distributions-exhibit.md).
Details: [sweep-jobs.md](sweep-jobs.md).

## 12. AutoML

```python
from azure.ai.ml import automl, Input
from azure.ai.ml.constants import AssetTypes

job = automl.classification(                      # also regression, forecasting, image_classification, text_classification…
    compute="train-cluster",
    experiment_name="diabetes-automl",
    training_data=Input(type=AssetTypes.MLTABLE, path="./data/diabetes"),   # MLTable required
    target_column_name="Diabetic",
    primary_metric="AUC_weighted",                # 🛠; the lab uses "accuracy"
    n_cross_validations=5,
    enable_model_explainability=True,
)
job.set_limits(timeout_minutes=60, trial_timeout_minutes=20, max_trials=5,
               max_concurrent_trials=4, enable_early_termination=True)
job.set_training(blocked_training_algorithms=["LogisticRegression"], enable_onnx_compatible_models=True)
job.set_featurization(mode="auto")               # "auto" | "off" | "custom"
ml_client.jobs.create_or_update(job)
```

| `set_limits` | Scope | Default |
|---|---|---|
| `timeout_minutes` | **Whole job** | 6 days |
| `trial_timeout_minutes` | **Each trial** | 1 month |
| `max_trials` | Job | 1,000 |
| `max_concurrent_trials` | Job | 1 (capped by nodes) |
| `enable_early_termination` | Job | off; earliest stop at iteration 31 |

[Q170](../../../practice/mlops/q170-automl-set-limits.md): `timeout_minutes=60` is **not** a per-trial limit.
Primary metrics: classification `accuracy`, `AUC_weighted`, `average_precision_score_weighted`,
`norm_macro_recall`, `precision_score_weighted`; regression `spearman_correlation`,
`normalized_root_mean_squared_error`, `r2_score`, `normalized_mean_absolute_error`.
Vision data = **JSONL** wrapped in an MLTable [Q156](../../../practice/mlops/q156-automl-vision-jsonl.md). Steps: compute → configure → submit → review [Q65](../../../practice/mlops/q065-automl-job-steps.md).
Details: [automl.md](automl.md).

## 13. Components, pipelines, schedules

```python
from azure.ai.ml import load_component, Input
from azure.ai.ml.dsl import pipeline

prep = load_component(source="./components/prep.yml")        # loaded = usable, NOT registered [Q147](../../../practice/mlops/q147-load-and-register-component.md)
train = load_component(source="./components/train.yml")
ml_client.components.create_or_update(train)                # registered = listed, versioned [Q147](../../../practice/mlops/q147-load-and-register-component.md)

@pipeline(default_compute="train-cluster")
def diabetes_pipeline(raw_data):
    p = prep(input_data=raw_data)
    t = train(training_data=p.outputs.output_data)           # wiring output → input sets the order
    return {"model": t.outputs.model_output}

pipeline_job = diabetes_pipeline(Input(type="uri_file", path="azureml:diabetes-data:1"))
pipeline_job.settings.default_compute = "train-cluster"
ml_client.jobs.create_or_update(pipeline_job, experiment_name="pipeline-diabetes")
```

Component from a Python function [Q111](../../../practice/mlops/q111-command-component-decorator.md):

```python
from mldesigner import command_component, Input, Output

@command_component(name="train_image_classification", version="1",
                   environment=dict(conda_file="conda.yaml", image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04"))
def train_component(input_data: Input(type="uri_folder"), output_model: Output(type="uri_folder"), epochs=10):
    from model_train import train            # sibling file model_train.py
    train(input_data, output_model, epochs)
```

Schedules (🛠 `ml/pipelines/train_schedule.yml`, Sundays 04:00 UTC):

```python
from azure.ai.ml.entities import JobSchedule, RecurrenceTrigger, RecurrencePattern
trigger = RecurrenceTrigger(frequency="week", interval=1,
                            schedule=RecurrencePattern(week_days=["sunday"], hours=4, minutes=0))
ml_client.schedules.begin_create_or_update(JobSchedule(name="weekly", trigger=trigger, create_job=pipeline_job)).result()
# CronTrigger(expression="0 4 * * 0") is the alternative; delete = begin_disable(...) then begin_delete(...)
```

"Repeatable and auditable training instead of notebooks" → **pipelines** [Q114](../../../practice/mlops/q114-fabrikam-training-pipelines.md).
Details: [components-and-pipelines.md](components-and-pipelines.md).

## 14. MLflow tracking

```python
import mlflow

mlflow.set_tracking_uri(ml_client.workspaces.get(name).mlflow_tracking_uri)  # only from a laptop; jobs/instances set it [Q100](../../../practice/mlops/q100-mlflow-tracking-uri-log-metric.md)
mlflow.set_experiment("classification-experiment")      # creates it if missing; groups runs [Q20](../../../practice/mlops/q020-mlflow-tracking-script.md)
mlflow.autolog()                                         # or mlflow.sklearn.autolog()
with mlflow.start_run() as run:
    mlflow.log_param("max_iter", 200)
    mlflow.log_metric("accuracy", acc)
    mlflow.sklearn.log_model(model, "model")             # 2nd arg = artifact path, NOT the experiment name [Q20](../../../practice/mlops/q020-mlflow-tracking-script.md)
    # mlflow.sklearn.log_model(model, "model", registered_model_name="diabetes-clf")  # log AND register
run.info.run_id
```

| Value | Call |
|---|---|
| One number | `mlflow.log_metric("acc", 0.9)` |
| Number over time | `mlflow.log_metric("loss", v, step=i)` |
| **Boolean** | `mlflow.log_metric("flag", 0)` → **0 = False, 1 = True** (📘; the site said `log_text`) [Q110](../../../practice/mlops/q110-mlflow-log-figure-boolean.md) |
| Several numbers (dict) | `mlflow.log_metrics({"a": 1, "b": 2})` [Q115](../../../practice/mlops/q115-mlflow-log-metrics-artifact-run-id.md) |
| A **list** of metric records | `MlflowClient().log_batch(run_id, metrics=[Metric(...)])` [Q135](../../../practice/mlops/q135-log-batch-list-of-metrics.md) |
| Hyperparameter / setting | `mlflow.log_param` / `log_params` (stored as strings) |
| Matplotlib figure object | `mlflow.log_figure(fig, "plot.png")` [Q110](../../../practice/mlops/q110-mlflow-log-figure-boolean.md) |
| Plot already saved to disk / any file | `mlflow.log_artifact("plot.png")` [Q131](../../../practice/mlops/q131-log-metric-log-artifact-plot.md) [Q169](../../../practice/mlops/q169-mlflow-log-table-file.md) |
| A folder | `mlflow.log_artifacts("outputs/")` |
| Dict / DataFrame as a table | `mlflow.log_table(data, "table.json")` |
| Dict as JSON/YAML | `mlflow.log_dict(d, "d.json")` |
| Text | `mlflow.log_text(s, "note.txt")` |
| Image array / PIL | `mlflow.log_image(img, "img.png")` |
| Tag | `mlflow.set_tag("k", "v")` |

Querying [Q168](../../../practice/mlops/q168-mlflow-search-runs-failed.md):

```python
runs = mlflow.search_runs(experiment_names=["experiment1"], max_results=5, order_by=["start_time ASC"],
                          filter_string="metrics.accuracy > 0.8 and params.max_iter = '200'")   # pandas DataFrame
runs[runs.status == "FAILED"]          # statuses: RUNNING, SCHEDULED, FINISHED, FAILED (error), KILLED (cancelled)
from mlflow.tracking import MlflowClient
MlflowClient().get_run(run.info.run_id)     # [Q115](../../../practice/mlops/q115-mlflow-log-metrics-artifact-run-id.md)
```

- Writing a table to a file: `json.dump(table, f)` (to a file) then `log_artifact`; `json.dumps` returns a string [Q169](../../../practice/mlops/q169-mlflow-log-table-file.md).
- Autolog vs. custom: autolog adds params, `training_*` metrics and the `model/` folder 🧪 lab 02.
- Details: [mlflow-tracking.md](mlflow-tracking.md).

MLflow **models** (📘 [log MLflow models](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-log-mlflow-models?view=azureml-api-2),
[deploy MLflow models](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-mlflow-models?view=azureml-api-2)):

```python
from mlflow.models import infer_signature
signature = infer_signature(X_test, y_pred)                 # input + output schema
mlflow.sklearn.log_model(model, artifact_path="classifier", signature=signature,
                         input_example=X_train.sample(n=1), pip_requirements=["scikit-learn==1.5.1"])

from mlflow.pyfunc import PythonModel, PythonModelContext
class ModelWrapper(PythonModel):                            # custom model: implement predict (load_context optional)
    def load_context(self, context: PythonModelContext): self.enc = load(context.artifacts["encoder"])
    def predict(self, context: PythonModelContext, data, params=None): return self.model.predict_proba(data)
mlflow.pyfunc.log_model(artifact_path="classifier", python_model=ModelWrapper(model),
                        artifacts={"encoder": "encoder.pkl"}, signature=signature)

mlflow.sklearn.load_model(uri)    # original object      mlflow.pyfunc.load_model(uri)   # generic .predict()
```

- The **`MLmodel`** file is the model's source of truth: `flavors` (e.g. `python_function`, `sklearn`), `signature`,
  `run_id`, `mlflow_version`, and `conda.yaml` / `python_env.yaml` beside it.
- **Signature**: recommended, not required. With it, Azure ML validates inputs and generates the swagger and the studio **Test** tab.
- **Versions**: the `azureml-mlflow` plugin supports MLflow ≤ 2.16.2 (2.17+ unsupported, per the docs on 2026-10-31).

## 15. Models: register, archive, share, package

```python
from azure.ai.ml.entities import Model
from azure.ai.ml.constants import AssetTypes

model = Model(name="diabetes-clf", type=AssetTypes.MLFLOW_MODEL,           # or CUSTOM_MODEL
              path=f"azureml://jobs/{job_name}/outputs/artifacts/paths/model/")   # from a run's artifacts [Q103](../../../practice/mlops/q103-register-mlflow-run-model.md)
ml_client.models.create_or_update(model)                                   # new version each time
# MLflow way: mlflow.register_model(f"runs:/{run_id}/model", "diabetes-clf")

ml_client.models.archive(name="diabetes-clf", version="1")    # hidden from lists, kept for audit/rollback [Q41](../../../practice/mlops/q041-archive-model-versions.md) [Q63](../../../practice/mlops/q063-archive-model-version.md) 🛠
ml_client.models.restore(name="diabetes-clf", version="1")
ml_client.models.share(name="diabetes-clf", version="2",      # workspace → registry 🛠 `az ml model share`
                       registry_name="mlreg-diabetes", share_with_name="diabetes-clf", share_with_version="2")
```

- Use a registry model: `"azureml://registries/mlreg-diabetes/models/diabetes-clf/versions/2"` [Q36](../../../practice/mlops/q036-registry-assets-across-workspaces.md).
- Create a registry (CLI only in the docs; 🧪 lab 05): `az ml registry create --file registry.yml -g <rg>` with
  `name` (2–32 chars, fixed forever), `location`, `replication_locations: [{location: ...}]` (the primary listed again; can't change).
  Holds models, environments, components, data; not compute, jobs or endpoints. Access: Reader to use, **AzureML Registry User** to read/write assets, Contributor/Owner to create.
- **Endpoint with no outbound internet** → `ml_client.models.package(...)` (a `ModelPackage`: model + dependencies baked into an image), then deploy the package [Q49](../../../practice/mlops/q049-package-model-no-egress.md).
- Archive ≠ delete ≠ unregister: only archive keeps it [Q63](../../../practice/mlops/q063-archive-model-version.md).

## 16. Feature store and the feature retrieval spec

📘 [Feature retrieval specification](https://learn.microsoft.com/en-us/azure/machine-learning/feature-retrieval-concepts?view=azureml-api-2)
(package `azureml-featurestore`; ≥ 1.2.1 for online lookup). Docs only. Concepts: [feature-store.md](feature-store.md).

```python
from azureml.featurestore import FeatureStoreClient
from azure.ai.ml.identity import AzureMLOnBehalfOfCredential

fs = FeatureStoreClient(credential=AzureMLOnBehalfOfCredential(), subscription_id=..., resource_group_name=..., name="my-fs")
features = fs.resolve_feature_uri(["accounts:1:numPaymentRejects1dPerUser"])     # feature_set:version:feature
fs.generate_feature_retrieval_spec("./model_folder", features)                  # writes feature_retrieval_spec.yaml

# training: point-in-time join on observation data (Spark)
from azureml.featurestore import get_offline_features
training_df = get_offline_features(features=features, observation_data=obs_df, timestamp_column="timestamp")
```

```python
# score.py init(): online lookup with the spec packaged inside the model
from azure.identity import ManagedIdentityCredential
from azureml.featurestore import FeatureStoreClient, init_online_lookup, get_online_features
def init():
    global features
    cred = ManagedIdentityCredential()
    features = FeatureStoreClient(credential=cred).resolve_feature_retrieval_spec(model_dir)
    init_online_lookup(features, cred)
```

- File name **`feature_retrieval_spec.yaml`** (can't be renamed), packaged **with the model artifact** → lineage + no per-environment config [Q24](../../../practice/mlops/q024-feature-store-entities.md).
- Pipeline route: the built-in `feature_retrieval` component (inputs `input_model` *or* `feature_retrieval_spec`, `observation_data`, `timestamp_column`; output `output_data` with the spec inside) → copy the spec into the model output.
- Entities: **feature store** · **entity** (index columns, reused) · **feature set specification** (source, PySpark transform, index + timestamp columns, materialization settings) · **feature set asset** (the registered, versioned spec) · **materialization** (offline ADLS Gen2, online Redis).

## 17. Online endpoints

```python
from azure.ai.ml.entities import ManagedOnlineEndpoint, ManagedOnlineDeployment, CodeConfiguration

endpoint = ManagedOnlineEndpoint(name="diabetes-ep", auth_mode="key")      # "key" | "aml_token" | "aad_token"
ml_client.online_endpoints.begin_create_or_update(endpoint).result()

blue = ManagedOnlineDeployment(
    name="blue", endpoint_name="diabetes-ep",
    model="azureml:diabetes-clf:2",
    environment="azureml:diabetes-score-env:1",                            # MLflow model: env + code optional (no-code)
    code_configuration=CodeConfiguration(code="./score", scoring_script="score.py"),
    instance_type="Standard_DS3_v2", instance_count=1,
    app_insights_enabled=True,
)
ml_client.online_deployments.begin_create_or_update(blue).result()

endpoint.traffic = {"blue": 90, "green": 10}            # split [Q54](../../../practice/mlops/q054-traffic-split-validation.md) [Q69](../../../practice/mlops/q069-split-traffic.md); rollback = {"blue": 100, "green": 0} [Q37](../../../practice/mlops/q037-rollback-failed-deployment.md)
endpoint.mirror_traffic = {"green": 10}                 # shadow: copies, responses discarded
ml_client.online_endpoints.begin_create_or_update(endpoint).result()

ml_client.online_endpoints.invoke(endpoint_name="diabetes-ep", request_file="sample.json", deployment_name="green")
ml_client.online_deployments.get_logs(name="blue", endpoint_name="diabetes-ep", lines=50)   # container_type="storage-initializer" for model download
```

Auth and testing (📘 [endpoint auth](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-authenticate-online-endpoint?view=azureml-api-2)):

| `auth_mode` | Expires? | Get it |
|---|---|---|
| `key` | **No** (rotate) | `ml_client.online_endpoints.get_keys(name).primary_key` |
| `aml_token` | Yes (`expiry_time_utc`, `refresh_after_time_utc`) | `get_keys(name).access_token` |
| `aad_token` | Yes (Entra lifetime, ~60–90 min) | Entra token; **managed online endpoints only**; RBAC `score/action` |

CLI: `az ml online-endpoint get-credentials -n ep`. AzureML Data Scientist can list keys and tokens.

- **Debug locally first** (Docker): `ml_client.online_deployments.begin_create_or_update(dep, local=True)` / `az ml online-deployment create --local`.
- MLflow model payload: `{"input_data": {"columns": [...], "index": [0], "data": [[...]]}}` (not MLflow's own `dataframe_split`); no CSV on online endpoints.
- No-code MLflow deployment: Azure ML builds the environment from the model's conda deps (+ `azureml-inference-server-http`, `azureml-ai-monitoring`); provide a script only to customise, and then an environment too.

| Deployment error | Usually means |
|---|---|
| `ImageBuildFailure` | Environment build failed (registry auth, timeout); read the build log |
| `OutOfQuota` | CPU/cluster/disk/memory/role-assignment/endpoint/region quota |
| `BadArgument` | Can't download the image or model, auth problem, MLflow model + private network |
| `ResourceNotReady` | Container crashes: `score.py` error, missing dependency, probes too tight, `init()` too slow |
| `ResourceNotFound` | Missing resource, or a private container registry |
| `OperationCanceled` | Pre-empted by a higher-priority operation; retry |

| Scoring HTTP | Meaning |
|---|---|
| 401 | Bad/expired key or token, no permission |
| 404 | No deployment with traffic > 0 |
| 408 | `request_timeout_ms` exceeded |
| 424 | Model container returned non-200 (see `ms-azureml-model-error-*` headers) |
| 429 | Too many concurrent requests / rate limit |
| 500 | Azure ML infrastructure |

Scoring script [Q39](../../../practice/mlops/q039-scoring-script-init-run.md) [Q153](../../../practice/mlops/q153-scoring-script-purpose.md) (🛠 `ml/score/score.py`, trimmed):

```python
def init():                                   # once, when the container starts
    global model
    model = mlflow.sklearn.load_model(os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model_output"))

def run(raw_data):                            # per request
    df = pd.DataFrame(json.loads(raw_data)["data"])
    return json.dumps({"diabetes": model.predict(df).tolist()})
```

- Canary order: create new deployment → small % → monitor → increase; **keep the old one** for rollback [Q118](../../../practice/mlops/q118-canary-rollout-steps.md).
- Autoscale = Azure Monitor autoscale on the deployment [Q116](../../../practice/mlops/q116-managed-online-autoscale.md). Not `score()`/`predict()`/`main()` in the script.
- 🛠 My project does all of this in YAML + `az ml online-endpoint update --traffic` (`deploy.yml`, `shift-traffic.yml`). Details: [online-endpoints.md](online-endpoints.md).

## 18. Batch endpoints

```python
from azure.ai.ml.entities import BatchEndpoint, BatchDeployment

ml_client.batch_endpoints.begin_create_or_update(BatchEndpoint(name="diabetes-batch")).result()
dep = BatchDeployment(name="default", endpoint_name="diabetes-batch", model="azureml:diabetes-clf:2",
                      compute="train-cluster",            # a cluster (low priority allowed) [Q83](../../../practice/mlops/q083-low-priority-compute-cluster.md)
                      instance_count=2, mini_batch_size=10, max_concurrency_per_instance=2,
                      output_action="append_row", output_file_name="predictions.csv")
ml_client.batch_deployments.begin_create_or_update(dep).result()
job = ml_client.batch_endpoints.invoke(endpoint_name="diabetes-batch",
                                       input=Input(type=AssetTypes.URI_FOLDER, path="azureml:new-patients:1"))
```

Batch script: `init()` + `run(mini_batch)` (a list of file paths) returning rows.
"Millions of records, scheduled, files" → batch; "synchronous, low latency" → online [Q57](../../../practice/mlops/q057-online-vs-batch-endpoints.md).

## 19. Monitoring

Collect production data from a **custom** `score.py` (🛠 the root cause of my "No data found"):

```python
from azureml.ai.monitoring import Collector          # package azureml-ai-monitoring
inputs_collector = Collector(name="model_inputs")    # in init()
outputs_collector = Collector(name="model_outputs")
context = inputs_collector.collect(df)               # in run()
outputs_collector.collect(output_df, context)        # correlates the two
```

Plus `data_collector` on the deployment (YAML or `DataCollector(collections=...)`). The YAML alone collects nothing for a custom script.

Monitor (SDK names to recognise):

```python
from azure.ai.ml.entities import (MonitorSchedule, MonitorDefinition, MonitoringTarget, AlertNotification,
                                  DataDriftSignal, PredictionDriftSignal, DataQualitySignal, ServerlessSparkCompute)
monitor = MonitorSchedule(name="diabetes-monitor", trigger=RecurrenceTrigger(frequency="day", interval=1),
    create_monitor=MonitorDefinition(
        compute=ServerlessSparkCompute(instance_type="standard_e4s_v3", runtime_version="3.4"),
        monitoring_target=MonitoringTarget(ml_task="classification", endpoint_deployment_id="azureml:diabetes-ep:blue"),
        alert_notification=AlertNotification(emails=["me@example.com"])))
ml_client.schedules.begin_create_or_update(monitor).result()
```

Signals: data drift (inputs vs. training/recent), prediction drift (outputs), data quality,
feature attribution drift, model performance (needs ground truth), custom.
Act on thresholds → alerts → Event Grid → retraining pipeline [Q81](../../../practice/mlops/q081-drift-monitoring-alerts.md) [Q95](../../../practice/mlops/q095-alert-rules-autoscaling.md) [Q101](../../../practice/mlops/q101-monitor-alert-retrain-order.md).
Endpoint metrics: request latency, requests per minute, connections active [Q98](../../../practice/mlops/q098-endpoint-traffic-metrics.md).
Details: [monitoring-ms-learn.md](monitoring-ms-learn.md).

## 20. Responsible AI and Fairlearn

RAI dashboard as a pipeline of `azureml` registry components (🛠 `ml/experiments/responsible_ai/submit_rai_pipeline.py`) [Q119](../../../practice/mlops/q119-rai-counterfactual-pipeline.md):

```python
registry_client = MLClient(credential, registry_name="azureml")
constructor = registry_client.components.get(name="rai_tabular_insight_constructor", label="latest")
counterfactual = registry_client.components.get(name="rai_tabular_counterfactual", label="latest")
# also rai_tabular_explanation, rai_tabular_erroranalysis, rai_tabular_causal
gather = registry_client.components.get(name="rai_tabular_insight_gather", label="latest")
# constructor → tool components (each takes constructor.outputs.rai_insights_dashboard) → gather
```

Needs a **registered MLflow model** and MLTable train/test data [Q38](../../../practice/mlops/q038-rai-dashboard-register-first.md).
Counterfactual = minimal change that flips a prediction; causal = effect of an intervention [Q117](../../../practice/mlops/q117-rai-counterfactual-causal.md) [Q154](../../../practice/mlops/q154-rai-causal-counterfactual.md).

Fairlearn [Q7](../../../practice/mlops/q007-fairlearn-without-retraining.md) [Q71](../../../practice/mlops/q071-fairlearn-gridsearch-demographic-parity.md):

```python
from fairlearn.metrics import MetricFrame, selection_rate
from fairlearn.postprocessing import ThresholdOptimizer
from fairlearn.reductions import GridSearch, ExponentiatedGradient, DemographicParity, EqualizedOdds

mf = MetricFrame(metrics={"accuracy": accuracy_score, "selection_rate": selection_rate},
                 y_true=y_test, y_pred=y_pred, sensitive_features=X_test["Ethnicity"])
mf.by_group; mf.difference()

ThresholdOptimizer(estimator=model, constraints="demographic_parity", prefit=True)   # no retraining
GridSearch(estimator, constraints=DemographicParity())                                # retrains
```

Details: [responsible-ai-fairlearn.md](responsible-ai-fairlearn.md).

## 21. Notebook and terminal bits

| Need | Answer |
|---|---|
| Install into the running kernel | `%pip install …` (not `!pip`) [Q105](../../../practice/mlops/q105-pip-magic-current-kernel.md) |
| New Jupyter kernel | `conda create -n env` → `conda activate env` → install packages → `python -m ipykernel install --user --name env` [Q11](../../../practice/mlops/q011-kernel-create-environment.md) [Q143](../../../practice/mlops/q143-kernel-commands-order.md) |
| Keep variables | **Stop the kernel** [Q122](../../../practice/mlops/q122-preserve-notebook-state.md); change kernel/compute or reset compute wipes state [Q29](../../../practice/mlops/q029-reset-notebook-state.md) |
| Clone a private repo | compute instance → terminal → `ssh-keygen` → `cat ~/.ssh/id_rsa.pub` → add the **public** key to GitHub → `git clone` [Q52](../../../practice/mlops/q052-git-clone-ssh.md) [Q148](../../../practice/mlops/q148-clone-private-repo-steps.md) |

## 22. GitHub Actions

📘 [GitHub Actions with Azure ML](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-github-actions-machine-learning?view=azureml-api-2): **OIDC is recommended**; a service-principal secret is "less secure and not recommended".
🧪 The labs use the secret (`AZURE_CREDENTIALS`); 🛠 my project uses OIDC.

```yaml
on:
  pull_request:            # 🧪 train-dev.yml: PR = the gate (with branch protection)
  workflow_dispatch:
permissions:
  id-token: write          # REQUIRED for OIDC
  contents: read
jobs:
  train:
    runs-on: ubuntu-latest
    environment: prod      # GitHub environment: required reviewers, env-scoped secrets
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}          # OIDC: app registration or user-assigned MI
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}          #   with a federated credential for this repo/branch/environment
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          # creds: ${{ secrets.AZURE_CREDENTIALS }}         # the secret way (lab), instead of the three above
      - run: az extension add -n ml -y
      - run: az ml job create -f src/job.yml -g $RG -w $WS --stream
```

- Federated credential **subject** must match: `repo:<org>/<repo>:ref:refs/heads/main`, `:pull_request`, or `:environment:prod` 🛠 (a real bug).
- Provisioning on change: `on: push: paths: ["infra/**"]` + `az deployment group create -f main.bicep` [Q80](../../../practice/mlops/q080-iac-github-actions-service-principal.md) [Q150](../../../practice/mlops/q150-iac-bicep-github-action.md).
- Comment-triggered (`issue_comment`) workflows run from the default branch; check the commenter's permission 🧪 lab 07.
- Details: [github-actions-azureml.md](github-actions-azureml.md).

## 23. CLI ↔ SDK map

| Task | CLI v2 (🛠 my project, 🧪 labs) | SDK v2 |
|---|---|---|
| Submit a job from YAML | `az ml job create -f job.yml --stream` | `ml_client.jobs.create_or_update(load_job("job.yml"))` |
| Data asset | `az ml data create -f data.yml` | `ml_client.data.create_or_update(Data(...))` |
| Component | `az ml component create -f train.yml` | `ml_client.components.create_or_update(...)` |
| Register model | `az ml model create --name m --path azureml://jobs/<job>/outputs/artifacts/paths/model/ --type mlflow_model` | `ml_client.models.create_or_update(Model(...))` |
| Archive model | `az ml model archive --name m --version 1` | `ml_client.models.archive(...)` |
| Share to registry | `az ml model share --name m --version 2 --registry-name r --share-with-name m --share-with-version 2` | `ml_client.models.share(...)` |
| Traffic split / rollback | `az ml online-endpoint update -n ep --traffic "blue=100 green=0"` | `endpoint.traffic = {...}` + `begin_create_or_update` |
| Deployment logs | `az ml online-deployment get-logs -n blue -e ep` | `ml_client.online_deployments.get_logs(...)` |
| Invoke | `az ml online-endpoint invoke -n ep --request-file s.json` | `ml_client.online_endpoints.invoke(...)` |
| Infrastructure | `az deployment group create -g rg -f main.bicep` [Q35](../../../../GenAIOps-ai-300/practice/q035-bicep-group-deployment.md) [Q123](../../../practice/mlops/q123-cli-deploy-bicep-declare.md) | — (Bicep/ARM) |

## 24. Near-miss traps

| Right | Wrong but tempting | Q |
|---|---|---|
| `mltable.load("./folder")` | `load("./folder/MLTable")`, `load("./folder/*.txt")` | [Q47](../../../practice/mlops/q047-load-mltable.md) |
| `from_delimited_files` (no MLTable file) | `load` | [Q144](../../../practice/mlops/q144-mltable-from-delimited-files.md) |
| `azure.ai.ml.constants` for `AssetTypes` | `azure.ai.ml.entities` | [Q113](../../../practice/mlops/q113-automl-image-mltable-input.md) |
| `container_name` | `container`, `blob_container` | [Q124](../../../practice/mlops/q124-blob-datastore-account-key.md) |
| `SasTokenConfiguration` for time-limited | account key, service principal | [Q146](../../../practice/mlops/q146-blob-datastore-sas.md) |
| `log_metrics(dict)` / `log_metric(k, v)` | swapped | [Q115](../../../practice/mlops/q115-mlflow-log-metrics-artifact-run-id.md) |
| `log_batch` for a list | `log_metric` | [Q135](../../../practice/mlops/q135-log-batch-list-of-metrics.md) |
| Boolean → `log_metric` 0/1 | `log_text`, `log_param` | [Q110](../../../practice/mlops/q110-mlflow-log-figure-boolean.md) |
| `log_artifact` for a saved file | `log_figure` (needs the figure object), `log_image` | [Q131](../../../practice/mlops/q131-log-metric-log-artifact-plot.md) |
| `json.dump(obj, f)` | `json.dumps` | [Q169](../../../practice/mlops/q169-mlflow-log-table-file.md) |
| `FAILED` = error, `KILLED` = cancelled | "aborted" = FAILED | [Q168](../../../practice/mlops/q168-mlflow-search-runs-failed.md) |
| `log_model(model, "model")` → artifact path `model` | "uses the experiment name" | [Q20](../../../practice/mlops/q020-mlflow-tracking-script.md) |
| `--training_data ${{inputs.training_data}}` | `--trainingdata`, literal name, positional file | [Q58](../../../practice/mlops/q058-command-arg-literal-name.md)–[Q60](../../../practice/mlops/q060-command-arg-positional-file.md) |
| `.amlignore` | `.gitignore` when both exist | [Q112](../../../practice/mlops/q112-amlignore-over-gitignore.md) |
| `MLClient.from_config` + `command` | `Workspace`, `@command_component` | [Q159](../../../practice/mlops/q159-mlclient-command-job.md) |
| `load_component` then `components.create_or_update` | `create_or_update` alone from a path | [Q147](../../../practice/mlops/q147-load-and-register-component.md) |
| `timeout_minutes` = whole job | "per trial" (that's `trial_timeout_minutes`, default 1 month) | [Q170](../../../practice/mlops/q170-automl-set-limits.md) |
| Bandit = vs. best; truncation = worst X% | swapped | [Q23](../../../practice/mlops/q023-early-termination-relative-policies.md) [Q158](../../../practice/mlops/q158-bandit-delay-interval.md) |
| Bayesian: Choice, Uniform, QUniform | Normal, LogUniform | [Q160](../../../practice/mlops/q160-bayesian-distributions.md) |
| Grid = every combination, `Choice` only | random | [Q142](../../../practice/mlops/q142-sweep-distributions-exhibit.md) |
| `init()` load, `run()` score | `main()`, `score()`, `predict()` | [Q39](../../../practice/mlops/q039-scoring-script-init-run.md) |
| Traffic back to old deployment | delete and redeploy, bigger compute | [Q37](../../../practice/mlops/q037-rollback-failed-deployment.md) |
| Archive the version | delete, unregister | [Q63](../../../practice/mlops/q063-archive-model-version.md) |
| `models.package` for no egress | registry, private endpoint | [Q49](../../../practice/mlops/q049-package-model-no-egress.md) |
| `%pip` | `!pip` | [Q105](../../../practice/mlops/q105-pip-magic-current-kernel.md) |
| `tier="low_priority"`, `min_instances=0` | lower `max_instances` | [Q163](../../../practice/mlops/q163-cluster-cost-tier-min-instances.md) |
| `distribution={"type": "PyTorch", "process_count_per_instance": <GPUs per node>}` + `instance_count=<nodes>` | `process_count_per_instance` = nodes | — |
| InfiniBand = "r" SKU (`NC24rs_v3`) | `NC24s_v3` | — |
| `generate_feature_retrieval_spec` → `feature_retrieval_spec.yaml` in the model folder | separate config per environment | [Q24](../../../practice/mlops/q024-feature-store-entities.md) |
| `permissions: id-token: write` for OIDC | secrets only | — |
| `key` auth never expires; `aml_token`/`aad_token` do | swapped | — |
| `local=True` to debug a deployment | redeploy to Azure each time | — |
| Serverless spot: `queue_settings={"job_tier": "Spot"}` | `tier="low_priority"` (that's a cluster) | — |
## 25. Exam vs. lab vs. my project

| Topic | 📘 Exam answer | 🧪 Lab | 🛠 My project |
|---|---|---|---|
| GitHub → Azure auth | **OIDC** federated credential (or managed identity); no secrets | Service-principal client secret (`AZURE_CREDENTIALS`) | OIDC |
| How code drives Azure ML | SDK v2 *and* CLI v2 + YAML both appear | Notebooks with SDK v2 (labs 01–04), CLI in workflows | YAML + CLI; SDK v2 only in `ml/experiments/` |
| Dev → prod | Registries share assets; both patterns valid | Retrain in prod on prod data | Train once, promote the same version via the registry |
| Rollout | Blue/green traffic split, mirror, rollback by traffic | Optional, UI | `deploy.yml` 0% slot + `shift-traffic.yml` |
| Environment | Curated or custom, versioned | Curated `sklearn` | Custom image + conda, versioned |
| Monitoring reference | Training data for data drift; validation data for prediction drift | Training data | Out-of-box (recent production) |
| Infra as code | Bicep + CLI, GitHub Actions | CLI scripts | Bicep + `infra.yml` |

When a question offers the lab's shortcut and the documented best practice,
pick the documented one. When it offers my project's choice and a 📘 option,
pick 📘.
