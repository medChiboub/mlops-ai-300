# Sweep jobs (hyperparameter tuning)

## The one idea

A **sweep job** is a command job run many times, once per hyperparameter
combination, as **trials** under one parent job. Each trial is a normal
command job with different argument values. The parent reads the metric
each trial logs with MLflow and reports the best trial.

```
base command job  ──job(reg_rate=Choice([...]))──▶  command job with a search space
                   ──.sweep(sampling, primary_metric, goal)──▶  sweep job
                   ──create_or_update──▶  parent sweep job
                                           ├─ trial 0: train.py --reg_rate 0.01
                                           ├─ trial 1: train.py --reg_rate 0.1
                                           └─ trial 2: train.py --reg_rate 1
```

## What the training script must do

The Microsoft Learn module says it *must*:
1. **Take each tuned hyperparameter as an argument** (`--reg_rate`).
2. **Log the target metric with MLflow** (`mlflow.log_metric`), under **exactly
   the name** given as `primary_metric`. Module assessment: a `print()` or
   `logging.info()` isn't enough.

The lab's `experimentation/src/train.py` logs `training_accuracy_score`, which
is the `primary_metric`. **Watch the name:** it looks like autolog's training
metric, but the script computes it on **`X_test`** (held-out data). So the
sweep optimizes test accuracy under a misleading name.

## The four decisions

**1. Search space**: what values each hyperparameter can take.

| Kind | Expressions | Example |
|---|---|---|
| Discrete | `Choice(values=[…])` (a list, `range`, or a tuple); `QUniform`, `QLogUniform`, `QNormal`, `QLogNormal` (rounded to a step `q`) | `Choice(values=[0.01, 0.1, 1])` ← the lab |
| Continuous | `Uniform`, `LogUniform`, `Normal`, `LogNormal` | `Normal(mu=10, sigma=3)` |

**2. Sampling**: which combinations get tried.

| Method | Tries | Restriction | Use when |
|---|---|---|---|
| **Grid** | Every combination | **Discrete (`Choice`) only** | Small search space you can afford in full ← the lab |
| **Random** | Random draws | Discrete and continuous mixed | Large space, first exploration |
| Random + **Sobol** | Random, seeded and more evenly spread | `RandomSamplingAlgorithm(seed=123, rule="sobol")` | You need to reproduce the sweep |
| **Bayesian** | Picks the next values from earlier results | **Only `choice`, `uniform`, `quniform`** | Budget-limited, one trial informs the next |

**3. Early termination**: stop hopeless trials early (optional).

| Policy | Stops a trial when… | Key settings |
|---|---|---|
| **Bandit** | it's worse than the best trial by more than the slack (best 0.9, `slack_amount=0.2` → below 0.7 stops) | `slack_amount` (absolute) or `slack_factor` (ratio) |
| **Median stopping** | its running average is below the median of all trials' running averages | none beyond the two below |
| **Truncation selection** | it's in the worst X% at an interval | `truncation_percentage` |

All three take `evaluation_interval` (check every N metric reports) and
`delay_evaluation` (skip the first N reports). **They only do something if
the metric is logged repeatedly** (per epoch, say). A script that logs the
metric once, like ours, gives nothing to compare mid-run. With a small grid
(the module's example: 6 trials) you don't need a policy. The lab sets none.

**4. Limits**: `set_limits(max_total_trials, max_concurrent_trials, timeout)`.
The lab: `max_total_trials=4, max_concurrent_trials=2, timeout=7200`.

## What actually happened (sweep `quiet_parcel_r5zv90jjw2`)

| Trial | `reg_rate` | Ran (UTC) | `training_accuracy_score` | AUC |
|---|---|---|---|---|
| **`_0`** ← best | 0.01 | 01:55:44 → 01:56:01 (**17 s**) | **0.774** | 0.848281 |
| `_1` | 0.1 | 01:53:12 → 01:55:26 (2 min 14 s) | **0.774** | 0.848326 |
| `_2` | 1.0 | 01:56:03 → 01:56:19 (16 s) | 0.7727 | 0.847963 |

The parent job ran 01:50:36 → 01:57:10 (about 6.5 min in total).

- ✅ **3 trials, not 4.** The grid ran out after 3 combinations;
  `max_total_trials=4` is a ceiling.
- ✅ **2 at a time, sharing the cluster with the lab's test command job.**
  The notebook submitted both at once, and the 2 nodes went to the test job
  and trial `_1` first. `_0` waited for a free node, and `_2` was only created
  once a slot opened. **Jobs share a cluster first-come, first-served; a
  sweep doesn't reserve nodes.**
- ✅ **A warm node is fast.** `_1` landed on a fresh node (about 2 min,
  mostly pulling the image and setting up). `_0` and `_2` reused nodes that
  already had the image: **16–17 s each**. The image pull, not training, is
  the cost.
- ✅ **A tie, broken by trial order.** `reg_rate` 0.01 and 0.1 both scored
  exactly 0.774, and the sweep reports `_0` (0.01) as `best_child_run_id`.
  Their AUCs differ (0.1 is marginally higher), so **with `primary_metric="AUC"`
  the winner would have been 0.1.** The primary metric decides which model
  "wins", even with identical accuracy.
- ✅ **Trials are normal command jobs.** `az ml job show -n <sweep>_0` works,
  unlike AutoML trials (`JobNotSupported`), and each trial is an MLflow run
  with the script's param and metrics.
- ✅ **The input is the registered asset:** `…/data/diabetes-data/versions/1`,
  not an anonymous upload.
- ✅ **The code snapshot is only `src/train.py`**
  (`codes/b79f66ff…`), because the notebook's `%%writefile` creates a clean
  folder. Compare lab 02's snapshot, which included everything in the root
  `src/`.
- ⚠ **The stored sampling algorithm reads `Random`, but the notebook asked for
  `grid`.** `az ml job show` → `sampling_algorithm: {type: random}`; the raw
  REST API → `samplingAlgorithmType: "Random"`. The notebook's executed cell
  says `sampling_algorithm="grid"`. Rebuilding the same sweep locally with
  **SDK 1.35.0 (the notebook's version)** and 1.34.1 serializes
  `samplingAlgorithmType: "Grid"`, so the SDK sends Grid. The behaviour matches
  grid too: 3 unique values, stopped at 3 of 4 allowed. ✅ **Settled: Studio's Overview shows *Grid*.** Every REST jobs API version
  tried (2023-10-01, 2024-04-01, 2024-10-01, 2025-01-01-preview, 2025-06-01,
  2025-09-01) returns `Random`. So the sweep **ran as a grid**, and **the jobs
  API (and therefore `az ml job show`) reads this field back wrongly.** Don't
  trust the CLI for a sweep's sampling method, for example in an audit
  script; Studio shows the real value. Exam answer unchanged: grid = every
  combination, discrete only.
