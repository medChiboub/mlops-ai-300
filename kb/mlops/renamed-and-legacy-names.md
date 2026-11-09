# Renamed and legacy names (AI-300 trap list)

AI chatbots (and old blog posts) confidently answer with **v1** or
**pre-rename** names. The exam uses current names. Paste this table into
any AI session before studying, and when an answer uses a left-column
name, check it against the docs.

✅ = stated on the cited Microsoft Learn page (read 2026-11-09). ▢ = from
SDK knowledge, not stated as a pair on those pages: verify before relying
on it.

Sources:
- [Upgrade to v2](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-migrate-from-v1) (`migrate`)
- [CLI & SDK v2](https://learn.microsoft.com/en-us/azure/machine-learning/concept-v2) (`v2`)
- [What is Microsoft Foundry?](https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry) (`foundry`)

## Support dates (the exam assumes v2)

| What | Status | Source |
|---|---|---|
| **CLI v1** (`azure-cli-ml` extension, `az ml` v1) | Support **ended September 30, 2025** | ✅ migrate, v2 |
| **SDK v1** (`azureml-core`) | **Deprecated March 31, 2025**; support **ends June 30, 2026** (already past) | ✅ migrate (deprecation date), v2 (end date) |
| ACI / AKS **web services** deployed with SDK/CLI v1 | "now considered as **legacy**" (no end date stated) | ✅ migrate |
| Current tools | Python SDK **`azure-ai-ml`** (v2), Azure CLI **`ml` extension** v2 | ✅ v2 |

## Azure ML: v1 → v2 (MLOps half)

| Old name (v1) | Current name (v2) | Source / note |
|---|---|---|
| Datasets | **Data assets** | ✅ migrate: "Datasets are renamed to data assets" |
| `FileDataset` | `uri_folder` (Folder) | ✅ migrate |
| `TabularDataset` | `mltable` (Table) | ✅ migrate |
| Experiments + runs + pipelines | **Jobs** (with a type: `command`, `sweep`, `pipeline`, `automl`, `spark`) | ✅ migrate: "consolidated into jobs". An experiment name still groups jobs |
| `Run.log()` (v1 run logging) | **MLflow** (`mlflow.log_metric`, autolog) | ▢ (labs 01–02 use only MLflow) |
| `ScriptRunConfig`, Estimators, `Experiment.submit()` | **Command job**: `command()` → `ml_client.jobs.create_or_update()`, or `type: command` YAML | ▢ (migrate links a comparison article) |
| `HyperDriveConfig` | **Sweep job**: `command(...).sweep()` | ▢ |
| `AutoMLConfig` | `automl.classification()` / `regression()` … (an AutoML job) | ▢ (migrate links a comparison article) |
| `PythonScriptStep` / pipelines v1 | **Components** + `@pipeline` (a pipeline job) | ▢ |
| `ParallelRunStep` | **Parallel job** in a pipeline; for inference → **managed batch endpoint** | ✅ migrate: "ParallelRunStep in a pipeline → Managed batch endpoint" |
| `SynapseSparkStep` (deprecated) | **Spark job / Spark component** on serverless Spark or an attached Synapse pool | ▢ (lab 07 monitoring) |
| Web service on **ACI** | **Local endpoint** (testing only) or **managed online endpoint** | ✅ migrate |
| Web service on **AKS** | **Managed online endpoint** or a **Kubernetes online endpoint** | ✅ migrate |
| `Model.deploy()` + `InferenceConfig` | Endpoint + **deployment** (`ManagedOnlineEndpoint` / `ManagedOnlineDeployment`) | ▢ (lab 07) |
| Workspace connection | **Connection** | ✅ migrate |
| `Workspace.set_secret` / `get_secret` | **Not in v2**: use Key Vault directly | ✅ migrate |
| `DataDriftDetector` (v1 dataset monitors) | **Model monitoring** (a schedule with signals on serverless Spark) | ▢ (lab 07) |
| `ModelDataCollector` (`azureml-monitoring`) | **Data collector** (`DataCollector`; the `Collector` SDK in `azureml-ai-monitoring`) | ▢ (lab 07: the model's conda file pins `azureml-ai-monitoring==1.0.0`) |
| Designer classic prebuilt components | Not usable with v2 data assets | ✅ migrate |
| Notebook VM | **Compute instance** (`AmlCompute`, `ComputeInstance` are fully available in v2) | ✅ migrate (v2 availability); ▢ the old "Notebook VM" name |
| `az ad sp create-for-rbac --sdk-auth` | `--json-auth` (and preferably **OIDC**, with no secret) | Seen in lab 06: the CLI warns `--sdk-auth` is deprecated |
| Private-endpoint workspace in `v1_legacy_mode` | That flag **blocks v2 APIs**: turn it off to use v2 | ✅ migrate |

**Not renamed:** environments and models created in v1 still work in v2
(✅ migrate). Compute instance and compute cluster keep their names.

## Foundry (GenAIOps half, for the other repo)

| Previous | Current | Source |
|---|---|---|
| **Azure AI Studio → Azure AI Foundry** | **Microsoft Foundry** | ✅ foundry ("Evolution of Foundry") |
| Azure AI Services | **Foundry Tools** | ✅ foundry |
| Foundry (classic) portal | **Foundry** (new portal) | ✅ foundry |
| Hub + Azure OpenAI + Azure AI Services | A single **Foundry resource, with projects** | ✅ foundry. Hub-based projects stay in the classic portal; "new investments are focused on Foundry projects" |
| Assistants API (Agents v0.5/v1) | **Responses API (Agents v2)** | ✅ foundry |
| `azure-ai-inference`, `azure-ai-generative`, `azure-ai-ml`, `AzureOpenAI()` | **`azure-ai-projects` 2.x** + `OpenAI()` | ✅ foundry |
| An Azure OpenAI resource | Upgradeable to a **Foundry resource** (keeps endpoint, keys and state) | ✅ foundry. No new product name stated |

## A real case of the trap (lab 07)

Google's AI said "Canada East doesn't support serverless Spark in Azure
ML". Its sources were about **Azure Databricks** serverless compute, a
different product. Our tests showed the opposite (the same failure in
Canada Central; Spark had worked in Canada East on another subscription).
**Rule:** when an AI answer cites a different product's docs, or no docs
at all, it's guessing.
