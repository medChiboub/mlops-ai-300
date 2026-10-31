# Managed feature store

Started after practice question [Q24](../../../practice/mlops/q024-feature-store-entities.md).
My production project deliberately skipped the feature store (`docs/AI-300.md`:
"Package a feature retrieval specification with the model artifact" is
unchecked), so this is docs-only knowledge.

## The one idea

A feature store is a **separate workspace-type resource** that defines
features **once** and serves the **same definitions** to training (offline
store) and inference (online store). That prevents training/serving skew.

## Entities

| Entity | What it is |
|---|---|
| **Entity** | The key that features describe (for example `account_id`) |
| **Feature set specification** | The definition: source data + transformation code + index columns (source files, not yet registered) |
| **Feature set asset** | The **registered, versioned** feature set: what training and serving share |
| **Materialization** | Precomputing values into the offline store (and optionally the online store, Redis) on a schedule or backfill. Performance, not definition |
| **Feature retrieval specification** | The list of feature-set versions and features a model uses. **Packaged with the model**, so the scoring script can look features up |

## Training → inference

1. Training generates a feature retrieval spec, used for training data
   (point-in-time join).
2. The **same spec is saved inside the model folder** and registered with
   the model.
3. At inference, the scoring script loads the spec from the model and
   fetches **online** features with it. No hard-coded feature lists, and no
   per-environment edits.

## Exam cues

| Requirement | Entity |
|---|---|
| "How features are retrieved at inference", "automated lookup in production" | **Feature retrieval specification** |
| "Same feature definitions in training and serving", "versioned, governed" | **Feature set asset** |
| "Low-latency values ready to serve" | **Materialization** (to the online store) |
| "Write the transformation logic" | Feature set specification |
