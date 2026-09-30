# End-to-end flow (labs 06–07)

How the repo, GitHub Actions, Entra ID and Azure ML fit together, and what
happens, in which order, when you open a PR, comment `/train-prod` and
comment `/deploy-prod`. Everything here matches the real workflow files and
resources of this redo. (GitHub renders these Mermaid diagrams.)

Contents: [1. Architecture](#1-architecture-where-everything-lives) ·
[2. The whole loop (flowchart)](#2-the-whole-loop-flowchart) ·
[3. Sequence: PR → dev training](#3a-sequence-pull-request--dev-training-train-devyml) ·
[/train-prod](#3b-sequence-train-prod-train-prodyml) ·
[/deploy-prod](#3c-sequence-deploy-prod-deploy-prodyml) ·
[monitoring](#3d-sequence-traffic--monitoring-studio-set-up-runs-on-a-schedule)

## 1. Architecture: where everything lives

```mermaid
flowchart LR
  subgraph GH["GitHub: medChiboub/mlops-ai-300 (public)"]
    direction TB
    MAIN["branch main<br/>protected: PR required"]
    FEAT["feature branch<br/>e.g. feature/lab07-dev-training"]
    PR["Pull request"]
    subgraph WF["Workflows (.github/workflows)"]
      W6["manual-trigger-job.yml<br/>workflow_dispatch + pull_request"]
      WD["train-dev.yml<br/>workflow_dispatch + pull_request (paths)"]
      WP["train-prod.yml<br/>issue_comment /train-prod"]
      WDP["deploy-prod.yml<br/>issue_comment /deploy-prod"]
    end
    subgraph CFG["Settings"]
      RSEC["repo secret AZURE_CREDENTIALS"]
      RVAR["repo variables<br/>AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME"]
      EDEV["environment dev<br/>secret AZURE_CREDENTIALS"]
      EPROD["environment prod<br/>secret AZURE_CREDENTIALS<br/>required reviewer: me"]
    end
    FEAT --> PR --> MAIN
  end

  RUNNER["GitHub-hosted runner<br/>ubuntu-latest, az + ml 2.44.1"]

  subgraph ENTRA["Microsoft Entra ID"]
    APP["App registration sp-mslearn-mlops-github<br/>2 client secrets"]
    SP["Service principal<br/>same appId"]
    APP --- SP
  end

  subgraph AZ["Azure: rg-ai300-l0533925c724d4c839e (canadaeast)"]
    WS["Workspace mlw-ai300-l…"]
    CL["aml-cluster<br/>0–2 x DS11_v2"]
    DDEV["data diabetes-dev-folder"]
    DPROD["data diabetes-prod-folder"]
    EP["Managed online endpoint<br/>diabetes-endpoint-0533925c"]
    DEP["deployment blue<br/>D2as_v4 x1, data collector"]
    MON["Model monitor<br/>serverless Spark, schedule"]
    ST["workspace storage<br/>blobstore, collected data"]
    WS --- CL
    WS --- DDEV
    WS --- DPROD
    WS --- EP --- DEP
    DEP -->|model_inputs and outputs| ST
    MON -->|reads| ST
  end

  subgraph IDLE["Lab 05 (idle, not used by any workflow)"]
    L5["rg-ai300-dev-… / rg-ai300-prod-… workspaces<br/>rg-ai300-reg-… registry"]
  end

  WF -->|runs on| RUNNER
  RSEC -.->|credentials JSON| RUNNER
  EDEV -.->|credentials JSON| RUNNER
  EPROD -.->|credentials JSON after approval| RUNNER
  RVAR -.->|names| RUNNER
  RUNNER -->|azure/login as| SP
  SP -->|Contributor on this RG only| WS
  RUNNER -->|az ml job create / python deploy script| WS
```

Key points:
- **One workspace** plays both "dev" and "prod". They're distinguished only by
  the **data asset** (`--set …path=`) and the **GitHub environment** (secret +
  gate). Lab 05's separate workspaces sit idle.
- **One identity** for everything (the same service principal behind all three
  `AZURE_CREDENTIALS`), limited to one resource group.
- The **runner only submits**; training runs on `aml-cluster`, serving on
  the endpoint's own managed compute.

## 2. The whole loop (flowchart)

```mermaid
flowchart TD
  A["Change training code or job.yml<br/>on a feature branch"] --> B["Open PR into main"]
  B --> C{"PR touches src/train-model-parameters.py<br/>or src/job.yml?"}
  C -->|yes| D["train-dev.yml runs automatically<br/>env dev, no approval"]
  C -->|no| B2["only manual-trigger-job.yml runs<br/>(it runs on every PR)"]
  D --> E["Command job on aml-cluster<br/>data: diabetes-dev-folder"]
  E --> F["Bot comments dev Accuracy / AUC on the PR"]
  F --> G{"Dev metrics OK?"}
  G -->|no| A
  G -->|yes| H["I comment /train-prod"]
  H --> I["train-prod.yml queued<br/>env prod: waits for approval"]
  I --> J{"I approve?"}
  J -->|reject| A
  J -->|approve| K["Command job on aml-cluster<br/>PR's code, data: diabetes-prod-folder"]
  K --> L["Bot comments prod Accuracy / AUC + Studio link"]
  L --> M{"Prod metrics OK?"}
  M -->|no| A
  M -->|yes| N["I comment /deploy-prod"]
  N --> O["deploy-prod.yml queued<br/>env prod: waits for approval"]
  O --> P{"I approve?"}
  P -->|approve| Q["Endpoint + deployment blue<br/>model/ folder (committed, 2023)<br/>traffic blue = 100"]
  Q --> R["Bot comments endpoint name"]
  R --> S["Test in Studio: Test tab"]
  S --> T["Set up model monitor in Studio<br/>data drift, daily"]
  T --> U{"Drift / problem?<br/>(after about a day of traffic)"}
  U -->|new model is bad| V["Rollback: new deployment<br/>+ traffic 100 to it, 0 to blue<br/>archive the bad version"]
  U -->|data changed| A
  U -->|no| T
  B --> Z["Merge PR when done"]
```

What the loop really does, in this lab (the honest version):
- **Dev and prod data are byte-identical**, so prod metrics = dev metrics.
- **`/deploy-prod` deploys the committed `model/` folder**, never the model
  `train-dev`/`train-prod` just trained. Retraining changes the PR comments,
  not the endpoint.
- The 🧪 lab shortcuts vs. the 📘 recommended designs are in the lab 07 file.

## 3a. Sequence: pull request → dev training (`train-dev.yml`)

```mermaid
sequenceDiagram
  autonumber
  actor Me
  participant GH as GitHub (PR 3)
  participant R as Runner
  participant ID as Entra ID (service principal)
  participant AML as Azure ML workspace
  participant CL as aml-cluster
  Me->>GH: open PR (changes src/job.yml, script)
  GH->>R: pull_request event → start train-dev (environment dev)
  R->>R: checkout PR code, install az ml 2.44.1
  R->>ID: azure/login with dev AZURE_CREDENTIALS
  ID-->>R: token (Contributor on rg-ai300-l…)
  R->>AML: find RG and workspace by prefix rg-ai300-l / mlw-ai300-l
  R->>AML: az ml job create -f src/job.yml --set data=diabetes-dev-folder --stream
  AML->>CL: queue command job, scale 0 → 1 node
  CL-->>AML: run train-model-parameters.py, log Accuracy/AUC (MLflow), write metrics.json
  AML-->>R: streamed log (Accuracy: …, AUC: …)
  R->>R: grep Accuracy / AUC from training_output.log
  R->>GH: github-script: comment dev metrics on the PR
  GH-->>Me: comment "Dev training workflow completed … Accuracy, AUC"
```

## 3b. Sequence: `/train-prod` (`train-prod.yml`)

```mermaid
sequenceDiagram
  autonumber
  actor Me
  participant GH as GitHub (PR 3)
  participant R as Runner
  participant ID as Entra ID (service principal)
  participant AML as Azure ML workspace
  participant CL as aml-cluster
  Me->>GH: comment "/train-prod"
  GH->>GH: issue_comment event → train-prod from MAIN's workflow file
  GH-->>Me: job waiting: environment prod needs review
  Me->>GH: Review deployments → Approve
  GH->>R: start job (prod secret released only now)
  R->>R: checkout refs/pull/3/head (the PR's code), install az ml 2.44.1
  R->>ID: azure/login with prod AZURE_CREDENTIALS
  R->>AML: az ml job create -f src/job.yml --set data=diabetes-prod-folder --name diabetes-train-prod-RUNID
  AML->>CL: run the job
  R->>AML: az ml job stream (wait)
  R->>AML: az ml job download --output-name metrics_output
  AML-->>R: metrics.json with accuracy and auc
  R->>GH: comment prod metrics + job name + Studio link
  GH-->>Me: comment "Prod training workflow completed …"
```

## 3c. Sequence: `/deploy-prod` (`deploy-prod.yml`)

```mermaid
sequenceDiagram
  autonumber
  actor Me
  participant GH as GitHub (PR 3)
  participant R as Runner
  participant ID as Entra ID (service principal)
  participant AML as Azure ML workspace
  participant EP as Online endpoint diabetes-endpoint-0533925c
  Me->>GH: comment "/deploy-prod"
  GH-->>Me: job waiting: environment prod needs review
  Me->>GH: Approve
  GH->>R: start job
  R->>R: checkout PR code, Python 3.10, pip install azure-ai-ml azure-identity
  R->>ID: azure/login with prod AZURE_CREDENTIALS
  R->>AML: detect RG/workspace; endpoint name = diabetes-endpoint- + first 8 chars of suffix
  R->>AML: python src/deploy_to_online_endpoint.py (SDK, DefaultAzureCredential)
  AML->>EP: create endpoint if missing (auth: key)
  AML->>EP: create/update deployment blue: Model(path=./model) MLflow, Standard_D2as_v4 x1, DataCollector(model_inputs, model_outputs)
  Note over AML,EP: builds an image for the 2023 model (Python 3.8, MLflow 1.30, sklearn 0.24.1); can take 10+ min
  AML->>EP: traffic blue = 100
  R-->>GH: print scoring URI; comment endpoint + deployment name
  GH-->>Me: comment "Deployment workflow completed"
```

## 3d. Sequence: traffic → monitoring (Studio set-up, runs on a schedule)

```mermaid
sequenceDiagram
  autonumber
  actor Me
  participant EP as Endpoint / deployment blue
  participant ST as Workspace blob storage
  participant MON as Model monitor (schedule)
  participant SP as Serverless Spark
  Me->>EP: Test tab: POST input_data (8 features)
  EP-->>Me: prediction
  EP->>ST: data collector writes model_inputs / model_outputs (JSONL)
  Me->>MON: Studio → Monitoring: create monitor (data drift, reference = training data, daily)
  MON->>SP: on schedule: compute drift (production window vs reference)
  SP->>ST: read collected production data
  Note over MON,SP: needs at least about 1 day of collected traffic (1-day lookback minimum)
  SP-->>MON: drift metrics per feature
  MON-->>Me: results in Studio, optional email alert
```

## Where the humans are

| Decision | Who | How it's enforced |
|---|---|---|
| Code change reaches `main` | me (merge) | branch protection: PR required |
| Retrain on prod data | me (`/train-prod` + approve) | `environment: prod` required reviewer |
| Deploy to the endpoint | me (`/deploy-prod` + approve) | `environment: prod` required reviewer |
| Who may trigger at all | only prior contributors | interaction limits (public repo) |
| Roll back / retrain after drift | me | a monitoring signal is evidence, not an automatic action |
