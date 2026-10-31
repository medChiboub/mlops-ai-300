# Responsible AI: Fairlearn mitigation

Started after practice question [Q7](../../practice/archive/q007-fairlearn-without-retraining.md).
My production project tried the Azure ML **Responsible AI dashboard**
(`ml/experiments/responsible_ai/`, blocked on an RBAC grant). This note
covers the **Fairlearn** side: *changing* a model's behavior, not just
measuring it.

## The one idea

Fairlearn has two jobs:
- **Assess:** `MetricFrame` computes a metric (accuracy, selection rate,
  recall…) per group of a sensitive feature, and shows the disparity
  between groups.
- **Mitigate:** algorithms that reduce that disparity. They come in **three
  families**, depending on *when* they act.

| Family | Acts on | Retrains the model? | Algorithms |
|---|---|---|---|
| **Pre-processing** | The training **data** (removes correlation with the sensitive feature) | Yes: you train on the transformed data | `fairlearn.preprocessing.CorrelationRemover` |
| **Reductions** (in-processing) | **Training** itself: refits the estimator under a fairness constraint | Yes, repeatedly | `fairlearn.reductions.ExponentiatedGradient`, `fairlearn.reductions.GridSearch` |
| **Post-processing** | The trained model's **predictions** (group-specific thresholds) | **No** | `fairlearn.postprocessing.ThresholdOptimizer` |

## Exam cues

- "**Avoid retraining**" or "the model is already trained" →
  **`ThresholdOptimizer`** with `prefit=True`.
- "Fix it in the data before training" → `CorrelationRemover`.
- "Train a model that satisfies a fairness constraint" →
  `ExponentiatedGradient` (finds a randomized blend of models) or
  `GridSearch` (tries a grid of constraint trade-offs and returns candidate
  models).
- **Constraints** used by the reductions and post-processing:
  `DemographicParity` (equal selection rates) and `EqualizedOdds` (equal
  true-positive and false-positive rates).

## Trade-offs

- `ThresholdOptimizer` needs the **sensitive feature at prediction time**,
  because thresholds are per group. That may be impossible or legally
  sensitive in production.
- Mitigation usually trades away some overall accuracy for a smaller
  disparity. Compare both before choosing.
- Azure ML's **Responsible AI dashboard** (error analysis, explanations,
  fairness assessment, counterfactuals) is for *assessment*. Fairlearn's
  mitigators are what *change* the model's outcomes.

## Assessing: the RAI dashboard and cohorts

From practice question [Q12](../../practice/archive/q012-rai-before-registration.md).

The Azure ML **Responsible AI dashboard** answers different questions with
different tools:

| Tool | Answers |
|---|---|
| **Error analysis** | *Where* does the model fail? Finds cohorts with high error rates |
| **Fairness / model overview by cohort** | Do metrics differ across **sensitive groups**? |
| **Feature importance (explanations)** | *Why* does it predict this? Global and per-prediction (transparency) |
| Counterfactuals (what-if) | What minimal change flips the prediction? |
| Causal analysis | What happens to the outcome if we intervene on a feature? |
| Data analysis | Is the data balanced and representative? |

- A **cohort** is a defined subgroup (for example `gender = F`, or
  `age < 25`). Metrics on the **global cohort** (everyone) **hide** subgroup
  disparities.
- Before registration: cohort error/fairness analysis (fairness + segment
  errors), plus feature importance (transparency). Latency and schema checks
  are operational, not Responsible AI.

## Creating the dashboard

From practice question [Q38](../../practice/archive/q038-rai-dashboard-register-first.md).

- **Studio (no-code):** the model must be **registered** first (MLflow
  format supported). Then Models → model → **Responsible AI** → create the
  dashboard, choosing components (explanations, error analysis,
  counterfactuals, causal) and the train/test **MLTable** data.
- **SDK/CLI:** a pipeline. The *RAI insights constructor* → tool components
  → *gather*. My production project's `ml/experiments/responsible_ai/` used
  this; the constructor worked, and the tools were blocked by RBAC.
- Not prerequisites: deploying to an endpoint, converting the model format,
  or precomputing explanations.
