# Model monitoring: the Microsoft Learn way (exam view)

[monitoring.md](monitoring.md) explains how monitoring worked (and failed) in
**my** lab run. This file is the other half: **what Microsoft documents**,
the catalog the exam draws from. When an exam option sounds plausible, check
it against the tables here.

Sources: 📘 Microsoft Learn, read 2026-10-31:
*Model monitoring concepts* (`concept-model-monitoring`),
*Monitor model performance in production* (`how-to-monitor-model-performance`),
*Collect production data* (`how-to-collect-production-data`),
*Monitor online endpoints* (`how-to-monitor-online-endpoints`),
*Use Event Grid* (`how-to-use-event-grid`). Items marked **▢ verify** came
from a truncated page and should be checked on the live page before relying
on them.

## The one idea

There are **two different kinds of monitoring**, and the exam mixes them:

| | **Model monitoring** | **Endpoint (operational) monitoring** |
|---|---|---|
| Question it answers | Is the *model* still right? (drift, quality, performance) | Is the *service* healthy? (latency, errors, CPU) |
| Data | Collected inputs/outputs (JSONL in blob) vs. reference data | Azure Monitor metrics and logs |
| Runs on | A scheduled job on **serverless Spark** | Built into Azure Monitor |
| Set up with | `az ml schedule create` (a monitor *is* a schedule) | Diagnostic settings, alert rules, Application Insights |

Exam cue: "latency increased" or "requests failing" → endpoint monitoring.
"Predictions getting worse" or "input distribution changed" → model
monitoring.

## The 6 signals

| Signal | Compares | Production data | Reference data | Metrics | Status |
|---|---|---|---|---|---|
| **Data drift** | Distribution of model **inputs** | Model inputs | Recent past production **or** training data | Jensen-Shannon Distance, Population Stability Index, Normalized Wasserstein Distance, Two-Sample Kolmogorov-Smirnov Test, Pearson's Chi-Squared Test | Not preview |
| **Prediction drift** | Distribution of model **outputs** | Model outputs | Recent past production **or** validation data | Same as data drift, plus Chebyshev Distance | Not preview |
| **Data quality** | Integrity of inputs | Model inputs | Recent past production **or** training data | Null value rate, Data type error rate, Out-of-bounds rate | Not preview |
| **Feature attribution drift** | Feature **importance**, production vs. training | Model inputs **and** outputs | **Training data (required)** | Normalized discounted cumulative gain (NDCG) | Preview |
| **Model performance** | Predictions vs. **ground truth** | Model outputs | **Ground truth (required)** | Classification: Accuracy, Precision, Recall · Regression: MAE, MSE, RMSE | Preview |
| **Generation safety and quality** (GenAI) | GPT-assisted evaluation | Prompt, completion, context | N/A | Groundedness, Relevance, Fluency, Similarity, Coherence | Preview |

You can also add a **custom signal** via a custom monitoring signal component.

Metric types in the YAML samples (numerical vs. categorical):

| Signal | Numerical example | Categorical example |
|---|---|---|
| Data drift | `jensen_shannon_distance` | `pearsons_chi_squared_test` |
| Data quality | `null_value_rate` | `out_of_bounds_rate` |
| Feature attribution drift | `normalized_discounted_cumulative_gain` | — |

How the data quality metrics work:
- **Null value rate:** nulls per feature. 10 nulls in 100 rows is 10%.
- **Data type error rate:** the type is **inferred from the reference data**.
- **Out-of-bounds rate:** numerical bounds are the reference's min to max
  (for example `[0, 100]`). Categorical bounds are the set of values seen in
  the reference.

Thresholds: out-of-box uses **"smart defaults"**, and the docs don't publish
the numbers. Values in samples, like `jensen_shannon_distance: 0.01`, are
examples, not defaults.

## Out-of-box vs. advanced

| | **Out-of-box (basic)** | **Advanced** |
|---|---|---|
| When | Online endpoint + data collection enabled **at deployment** | Anything more specific |
| Signals | Data drift, prediction drift, data quality (automatic) | Any of the 6, multiple at once |
| Reference data | **Recent past production data** (not training data) | Your choice: training, validation, ground truth |
| Thresholds | Smart defaults | You set `metric_thresholds` |
| Features | All | Top N by importance (`top_n_feature_importance`) or a named list |
| Alerts | Email to **whoever created the monitor** | Per-signal `alert_enabled`, `alert_notification.emails` |

**Feature importance** appears only if the reference data is the **training
data** and you set `reference_data.data_column_names.target_column`.

Three ways to create one:
- **Studio:** Manage → **Monitoring** → **Add**. The wizard goes Basic
  settings → Configure data asset → Select signals → Notifications → Review.
- **CLI:** a YAML file and `az ml schedule create -f monitor.yml`.
- **SDK v2:** `MonitorSchedule` + `MonitorDefinition`, then
  `ml_client.schedules.begin_create_or_update(...)`.

```yaml
$schema: http://azureml/sdk-2-0/Schedule.json
name: diabetes-monitor
trigger:
  type: recurrence
  frequency: day            # minute | hour | day | week | month
  interval: 1
  schedule: {hours: 3, minutes: 15}
create_monitor:
  compute:
    instance_type: standard_e4s_v3   # serverless Spark, E-series only
    runtime_version: "3.4"
  monitoring_target:
    ml_task: classification          # classification | regression | question_answering
    endpoint_deployment_id: azureml:<endpoint>:<deployment>
  monitoring_signals:                # omit this whole block = out-of-box
    advanced_drift:
      type: data_drift
      reference_data:
        input_data: {path: azureml:diabetes-training:1, type: mltable}
        data_context: training
        data_column_names: {target_column: Diabetic}
      features: {top_n_feature_importance: 10}
      alert_enabled: true
      metric_thresholds:
        numerical: {jensen_shannon_distance: 0.01}
        categorical: {pearsons_chi_squared_test: 0.02}
  alert_notification:
    emails: [me@example.com]
```

## Windows: what gets compared

Two settings per window, both in ISO 8601 (`P7D` = 7 days):
- **Lookback window size:** how much data.
- **Lookback window offset:** how far back the window *ends*, measured from
  the run time.

| Setting | Default |
|---|---|
| Production window size | Your monitoring **frequency** (daily monitor → `P1D`) |
| Production offset | `P0D` (ends now) |
| Reference window size | The **full dataset** |
| Reference offset | **2 × the production window size** |

Rule for no overlap: **reference offset ≥ production size + production
offset**. With a daily monitor and the documented defaults, production is
the last day `[T-1D, T)` and the reference ends 2 days back, at `T-2D`.

What my production project actually saw, reverse-engineered from a real
error message (its `docs/MONITORING.md`), was an out-of-box reference of
`[T-3D, T-1D)`, ending 1 day back. So don't memorize the exact boundary.
Memorize the principle: **the two windows never overlap, so a brand-new
endpoint needs traffic older than the production window** before a run has
anything to compare. That's why the first run can't succeed on day one, as I
hit in lab 07. To control it, pin a fixed reference window with
`window_start_date` and `window_end_date`, or use training data as the
reference.

Frequency guidance: daily for heavy traffic, otherwise weekly or monthly.

## Compute: serverless Spark

- Monitors always run on **serverless Spark pools**, never on your compute
  cluster.
- Allowed sizes: `Standard_E4s_v3`, `E8s_v3`, `E16s_v3`, `E32s_v3`,
  `E64s_v3`.
- Spark has **its own quota**. My lab 07 monitor failed because Spark never
  started on my subscription, in two regions.
- Spark likes simple data: "**Only basic `MLTable` files have guaranteed
  support.**"
- **Not supported with managed VNet `allow_only_approved_outbound`.** See
  [network-isolation.md](network-isolation.md).

## Data collection: where production data comes from

```yaml
# deployment YAML
data_collector:
  sampling_rate: 1.0          # 1.0 = 100% of requests
  rolling_rate: Hour          # Minute | Hour | Day | Month | Year
  collections:
    model_inputs:  {enabled: 'True'}
    model_outputs: {enabled: 'True'}
```

| Deployment type | What you do | Why |
|---|---|---|
| **MLflow, no scoring script** | Studio **Data collection → Enabled** (or the YAML above) | Azure ML auto-instruments scoring |
| **Custom `score.py`** | The YAML **and** the Collector SDK in `score.py` | The YAML alone collects nothing |
| **Batch endpoint or outside Azure ML** | Collect it yourself, register it as a data asset, add a **preprocessing component** | No collector exists for these |

Collector SDK (package `azureml-ai-monitoring`):

```python
from azureml.ai.monitoring import Collector
def init():
    global inputs_collector, outputs_collector
    inputs_collector  = Collector(name='model_inputs')    # up to 5 collectors
    outputs_collector = Collector(name='model_outputs')
def run(data):
    context = inputs_collector.collect(data)           # pandas DataFrame only
    result  = model.predict(data)
    outputs_collector.collect(result, context)         # context links input ↔ output
```

Things to remember:
- **`collect()` only logs pandas DataFrames.** Anything else isn't logged and
  reports an error.
- The names **`model_inputs` / `model_outputs`** are what monitoring finds
  automatically.
- **Payload logging:** collections named `request` / `response` need no code
  change, but the data isn't guaranteed to be tabular, so monitoring then
  needs a preprocessing component.
- **Correlation ID:** generated automatically (`correlationid`), or set your
  own with `BasicCorrelationContext(id=...)`. Requests sent close together
  get **batched** under one ID. Microsoft recommends logging your own ID as a
  column.
- **Where it lands:**
  `workspaceblobstore/paths/modelDataCollector/{endpoint}/{deployment}/{collection}/{yyyy}/{MM}/{dd}/{HH}/{instance}.jsonl`.
- **Custom destination:** set `data.path` to another datastore. The identity
  then needs **Storage Blob Data Contributor** on it.
- **Payloads over 4 MB** are stored as separate raw files with a pointer in
  the JSONL.

## Model performance: needs ground truth

You can't monitor accuracy without the real outcomes, and **Azure ML doesn't
collect them for you**: "If you don't have ground truth data, you can't
perform model performance monitoring."

1. Collect outputs with a unique ID per row (the correlation ID, or your own
   column).
2. When the real outcome arrives, log it **in your application** with the
   same ID.
3. Register those outcomes as a **ground truth data asset**.
4. Add a `model_performance` signal that **joins the two on the ID column**,
   then computes accuracy/precision/recall or MAE/MSE/RMSE.

▢ verify: the YAML uses `data_context: ground_truth`, and
`data_column_names` with `prediction`, `actual` and `correlation_id`.

Batched rows get suffixed IDs (`test_0`, `test_1`, …). That's the reason for
logging your own ID column.

## Alerts and retraining triggers

| Mechanism | What it does |
|---|---|
| **Email** (built in) | Sent when any threshold is exceeded. Defaults to the monitor's creator; `alert_notification.emails` adds recipients |
| **Azure Event Grid** | Routes Azure ML events to Azure Functions, Logic Apps, Event Hubs, Data Factory or a webhook. This is how you **automate a reaction**, such as starting a retraining job |
| **Azure Monitor alert rules** | For **endpoint** metrics (latency, CPU). Not drift |

Microsoft's own retraining example: "if the accuracy of your classification
model in production dips below a certain threshold, you can use **Event Grid
to begin a retraining job** that uses collected ground truth data."

Event types the Event Grid page lists. **None of them is a drift event.**

| Event type | Raised when |
|---|---|
| `Microsoft.MachineLearningServices.RunCompleted` | A run completes |
| `Microsoft.MachineLearningServices.RunStatusChanged` | A run's status changes |
| `Microsoft.MachineLearningServices.ModelRegistered` | A model or version is registered |
| `Microsoft.MachineLearningServices.ModelDeployed` | Models are deployed to an endpoint |

- **Failed operations raise no event.** A failed deployment doesn't fire
  `ModelDeployed`.
- Filter with `--included-event-types` and `--subject-begins-with`.
- Prerequisites: Contributor or Owner on the workspace, and the
  `Microsoft.EventGrid` provider registered.

Exam-shaped answer: **threshold breached → alert → Event Grid → Logic App /
Function → submit the training pipeline.** Promotion after retraining still
needs its own gate.

## Endpoint (operational) monitoring

**Metrics** come from Azure Monitor automatically:
- **Endpoint level:** request latency, requests per minute, new connections
  per second, network bytes.
- **Deployment level:** CPU/GPU, memory and disk usage, down to individual
  instances.
- Use them for alert rules (signal + threshold + action group) and for
  **autoscale**.

**Logs** have to be turned on: endpoint → Monitoring → **Diagnostic
settings** → send to Log Analytics. The connection can take up to an hour.

| Log category | Contains |
|---|---|
| `AmlOnlineEndpointTrafficLog` | Each request: response code, model status, durations, throttling delays, request IDs |
| `AmlOnlineEndpointConsoleLog` | Container stdout/stderr (your `print()` from `score.py`) |
| `AmlOnlineEndpointEventLog` | Container lifecycle: `Pulled`, `Started`, `BackOff`, `LivenessProbeFailed`, `ReadinessProbeFailed`, … |

- **Application Insights:** a toggle on the deployment (Studio:
  "Application Insights diagnostics"). Gives live metrics, transaction
  search, failures and performance views.
- **Bandwidth throttling:** shows up in the network bytes metric and the
  response trailers `ms-azureml-bandwidth-request-delay-ms` /
  `-response-delay-ms`.

Debugging map:
- "Container keeps restarting" → **EventLog** (`BackOff`, probe failures).
- "My score.py error" → **ConsoleLog**.
- "Which requests failed, and how slow were they?" → **TrafficLog**.

## Prerequisites and RBAC

- **Monitors and data collection:** Owner, Contributor, or a custom role with
  `Microsoft.MachineLearningServices/workspaces/onlineEndpoints/*`.
- **Event Grid:** Contributor or Owner on the workspace.
- **Endpoint metrics:** Reader on the endpoint.
- **Supported targets:** managed online endpoints and Kubernetes online
  endpoints. Anything else means bringing your own production data.
- **Credential-less data access:** attach a user-assigned managed identity
  to the workspace, grant it access to the datastore, and set
  `systemDatastoresAuthMode` to `identity`.

Best practices Microsoft lists:
- Start monitoring **right after deployment**.
- Pick thresholds with the data scientists to **avoid alert fatigue**.
- Combine signals (data drift + feature attribution drift).
- Use **training data as the reference for data drift and quality**, and
  **validation data for prediction drift**.
- Monitor the top N features to cut cost and noise.
- Add model performance as soon as ground truth exists.

## Lab way vs. my production project vs. the docs

| | Lab 07 | My production project | What the docs emphasize |
|---|---|---|---|
| Setup | Studio wizard | `endpoints/monitor.dev.yml` via `az ml schedule create` | All three are equivalent |
| Mode | Advanced: training data as reference | Out-of-box: past production as reference | Know both, and **which reference each uses** |
| Collection | No-code MLflow, auto-instrumented | Custom `score.py` with the Collector SDK | When the SDK is required |
| Alerts | Email | Email only; retraining not wired | Event Grid for automated reactions |
| Result | Never ran (Spark blocked) | Collection verified; no successful run | — |

## Symptom to action: data vs. model vs. serving

From practice questions [Q22, Q26, Q28](../../practice/archive/q022-q026-q028-signal-to-action.md).
First decide **which layer** is failing:

| Symptom | Layer | First action |
|---|---|---|
| Input distributions differ from training | **Data** | Data drift signal / drift metrics |
| Accuracy falls with nothing redeployed | **Model** (concept drift) | Predictions vs. ground truth → retrain on recent data |
| Errors right after an update | **Deployment** | Deployment/container logs (`az ml online-deployment get-logs`, EventLog, ConsoleLog) |
| Wrong answers, no errors | **Code / model version** | Check `score.py` and the deployed model version |
| Slow or timing out under load | **Capacity** | Endpoint metrics → autoscale / more instances |

Distractors in these questions: "restart the endpoint", "rebuild the
container image", "increase traffic allocation". None of them diagnoses
anything.

## Exam traps

1. Out-of-box reference = **recent past production**, not training data.
2. Out-of-box needs data collection **enabled at deployment time**, on an
   **online** endpoint.
3. A custom `score.py` needs the **Collector SDK**. The YAML alone collects
   nothing.
4. `collect()` takes **pandas DataFrames** only.
5. Model performance needs **ground truth you collect yourself**.
6. Feature attribution drift needs **training data** as reference, plus
   inputs **and** outputs collected.
7. Prediction drift's recommended reference is **validation** data. Data
   drift's is **training** data.
8. Monitors run on **serverless Spark**, E-series sizes only, not your
   cluster.
9. Monitoring is **not supported** with `allow_only_approved_outbound`.
10. Latency, CPU and errors are **Azure Monitor endpoint metrics**, not model
    monitoring signals.
11. Event Grid's built-in Azure ML events are run/model/deployment events,
    and **failures emit no event**.
12. Feature attribution drift, model performance and the GenAI signal are
    **preview**.

## Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> You enable data collection on a new online deployment and create an out-of-box monitor. What does it compare production data against?<br><br>A) The training data asset<br>B) The validation data<br>C) Recent past production inference data from the same deployment<br>D) Ground truth</summary>

> **✅ Answer: C.** Out-of-box uses recent past production data. Training data as the reference is an advanced-setup choice.
</details>

---

<details>
<summary><strong>2.</strong> Your deployment uses a custom <code>score.py</code>. Data collection is enabled in the deployment YAML, but no data appears in blob storage. What's missing?<br><br>A) A larger instance type<br>B) <code>Collector(name='model_inputs')</code> / <code>Collector(name='model_outputs')</code> calls in <code>score.py</code><br>C) An Event Grid subscription<br>D) Application Insights</summary>

> **✅ Answer: B.** Only no-code MLflow deployments are auto-instrumented. A custom scoring script has to call the Collector SDK itself.
</details>

---

<details>
<summary><strong>3.</strong> You want to know whether production accuracy has dropped. What do you need that Azure ML doesn't collect for you?<br><br>A) Model inputs<br>B) Model outputs<br>C) Ground truth (the real outcomes), logged with the same ID as the predictions<br>D) A serverless Spark pool</summary>

> **✅ Answer: C.** The model performance signal joins predictions with ground truth on a shared ID. Collecting and registering the ground truth is your job.
</details>

---

<details>
<summary><strong>4.</strong> Which signal requires the training data as its reference?<br><br>A) Data quality<br>B) Prediction drift<br>C) Feature attribution drift<br>D) Data drift</summary>

> **✅ Answer: C.** It compares feature importance in production with feature importance in training, so it can't work without the training data. The others can use past production data.
</details>

---

<details>
<summary><strong>5.</strong> Users report that the endpoint has become slow. Where do you look first?<br><br>A) A data drift signal<br>B) The endpoint's request latency metric in Azure Monitor, and <code>AmlOnlineEndpointTrafficLog</code><br>C) The feature attribution drift signal<br>D) The MLflow run</summary>

> **✅ Answer: B.** Latency is an operational metric. Model monitoring watches the data and predictions, not the service.
</details>

---

<details>
<summary><strong>6.</strong> The endpoint's container keeps restarting. Which log category shows why?<br><br>A) <code>AmlOnlineEndpointTrafficLog</code><br>B) <code>AmlOnlineEndpointEventLog</code><br>C) The model monitoring signal history<br>D) The data collector JSONL</summary>

> **✅ Answer: B.** EventLog records container lifecycle events like <code>BackOff</code> and <code>LivenessProbeFailed</code>. ConsoleLog shows the container's own output.
</details>

---

<details>
<summary><strong>7.</strong> You want accuracy dropping below a threshold to automatically start a retraining job. What's Microsoft's documented building block?<br><br>A) A cron trigger on the training pipeline<br>B) Azure Event Grid, routing to a Logic App or Azure Function that submits the job<br>C) Application Insights live metrics<br>D) Raising the alert threshold</summary>

> **✅ Answer: B.** Email alerts notify a person. Event Grid is how you automate a reaction.
</details>

---

<details>
<summary><strong>8.</strong> A daily out-of-box monitor is created on a brand-new endpoint, and its first run finds no reference data. Why?<br><br>A) Spark isn't installed<br>B) The reference window must lie entirely before the production window, so a brand-new endpoint has no traffic old enough to fill it yet<br>C) Out-of-box needs ground truth<br>D) The sampling rate defaults to zero</summary>

> **✅ Answer: B.** The windows never overlap (reference offset ≥ production size + production offset). Fixes: wait for older traffic, pin a fixed reference window, or use training data as the reference.
</details>

---

<details>
<summary><strong>9.</strong> Your workspace uses a managed VNet in <code>allow_only_approved_outbound</code> mode. What happens to model monitoring?<br><br>A) It works normally<br>B) It's not supported in that isolation mode<br>C) It moves to your compute cluster<br>D) It only supports data quality</summary>

> **✅ Answer: B.** The concepts page lists this as a limitation. If monitoring is required, plan the network mode around it.
</details>

---

[← mechanics index](README.md) · [How monitoring worked in my lab run](monitoring.md) · [Network isolation](network-isolation.md)
