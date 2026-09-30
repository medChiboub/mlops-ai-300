# Mechanics: what actually happens underneath

The lab files say *what I ran*. These files say *what Azure did when I ran
it*: which resources get involved, what gets created where, and in what order.
There is one file per concept, because the same pieces come back in every lab.

Where possible, examples come from my own workspace
(`mlw-ai300-l0533925c724d4c839e`), not generic docs. Anything marked
**▢ verify** is expected behavior we haven't yet confirmed in a real run. It
gets ticked or corrected once we see it.

| File | Covers | First used in |
|---|---|---|
| [workspace-and-storage.md](workspace-and-storage.md) | What a workspace is, its dependent resources, the 4 datastores, what lives in which container | Lab 01 §1–2 |
| [compute.md](compute.md) | Compute instance vs. compute cluster, lifecycle, billing, identity | Lab 01 §1–2 |
| [data-assets.md](data-assets.md) | `uri_file` vs. `uri_folder` vs. `mltable`, what `az ml data create` uploads, versioning | Lab 01 §1 |
| [automl.md](automl.md) | An AutoML job from submission to best model: featurization, guardrails, trials, CV, ensembles | Lab 01 §3 |
| [mlflow-tracking.md](mlflow-tracking.md) | MLflow ↔ Azure ML mapping, tracking vs. submitting, autolog vs. custom logging, params vs. metrics vs. artifacts | Lab 01 §4 |
| [command-jobs.md](command-jobs.md) | A command job's pieces, code snapshot and `.amlignore`, input upload reuse, environment, logs, job vs. terminal run | Lab 02 §3 |
| [sweep-jobs.md](sweep-jobs.md) | Sweep = one command job run per hyperparameter combination: script requirements, search space, sampling, early termination, limits | Lab 03 |
| [components-and-pipelines.md](components-and-pipelines.md) | Component vs. pipeline vs. pipeline job, component YAML, `@pipeline()` wiring, loaded vs. registered, scheduling | Lab 04 |
| [interfaces.md](interfaces.md) | Script vs. SDK vs. CLI + YAML vs. Studio: four layers over one REST API, the same job both ways | All labs |
| [registries-and-environments.md](registries-and-environments.md) | Assets vs. resources, dev/prod workspaces, two promotion patterns, what a registry provisions (managed RG, Premium ACR, storage), naming rules, RBAC | Lab 05 |
| [github-actions-azureml.md](github-actions-azureml.md) | The workflow → Azure chain, secrets vs. variables, service-principal secret vs. OIDC, triggers, branch protection vs. workflows, network | Lab 06 |
| [job-types.md](job-types.md) | The 5 job types (command, sweep, automl, pipeline, spark), "is a pipeline a set of commands?" nuances, non-job `az ml` actions (register, deploy, schedule) | Labs 01–07 |
| [end-to-end-flow.md](end-to-end-flow.md) | **Diagrams**: architecture (GitHub ↔ Entra ↔ Azure), the whole dev → prod → monitor loop (flowchart), sequence diagrams for PR → train-dev, `/train-prod`, `/deploy-prod`, monitoring; where the humans decide | Labs 06–07 |
| [monitoring.md](monitoring.md) | The 4 layers (request → collector JSONL → monitor on serverless Spark → result), verified collection record, out-of-box vs. advanced reference data, the 1-day window, traps ("Completed but did nothing"), what drift means in this lab | Lab 07 |
| [three-environments.md](three-environments.md) | **"Environment" means 3 things**: Azure ML environment (the runtime: image + packages, curated/custom/auto-created, traced for deployment `blue`), GitHub environment (the gate: secrets + required reviewer), dev/prod environment (the stage: workspaces, isolation, promotion); exam cues for each | Labs 02, 05, 06, 07 |
