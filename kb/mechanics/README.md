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
