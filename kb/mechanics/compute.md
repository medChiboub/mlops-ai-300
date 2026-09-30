# Compute: instance vs. cluster

Both are Azure VMs that Azure ML manages for you. They differ in who uses
them, how long they live, and how they're billed.

| | Compute instance `ci0533925c724d4c839e` | Compute cluster `aml-cluster` |
|---|---|---|
| Type | `ComputeInstance` | `AmlCompute` |
| Nodes | Exactly 1 VM | 0 → `max_instances` (0 → 2 here) |
| Who uses it | One user; I'm the assigned owner | Any job submitted to the workspace |
| What runs on it | Jupyter, JupyterLab, VS Code, a terminal, notebook kernels | Jobs only (command, sweep, AutoML, pipeline steps), each in a Docker container |
| Lifetime | Runs until stopped, whether or not I use it | Nodes appear when jobs queue and disappear when idle |
| Billing | **Every minute it's Running** | Only while nodes exist |
| Storage | Mounts the workspace code share at `~/cloudfiles/code/` | Gets the job's code snapshot and inputs per job |
| Size | STANDARD_DS11_V2 (2 vCPU, 14 GB RAM) | Same size, per node |

## My compute instance's real config (`az ml compute show`)

```json
{ "state": "Running", "idle": null, "sched": null, "identity": null, "ssh": false }
```

- **`idle: null`: no idle shutdown.** It bills until someone stops it. Studio
  can set *idle shutdown* (stop after N minutes with no activity) and
  *schedules* (for example, stop at 19:00 every day). Both are exam-relevant
  cost controls. The lab script sets neither.
- **`identity: null`: no managed identity.** So when a notebook calls
  `DefaultAzureCredential()`, there's no identity on the VM to use. That's
  why Studio shows the **Authenticate** prompt: it signs the SDK in *as me*.
  Jobs I submit from the notebook therefore run with my permissions.
- **`ssh: false`**: access is only through Studio's apps (terminal, Jupyter,
  VS Code).

Start and stop: Studio → Compute → Stop, or `az ml compute stop -n <name>`.
Stopping keeps the VM's OS disk. The notebooks are safe regardless, because
they're on the file share (see [workspace-and-storage.md](workspace-and-storage.md)).

## My cluster's real config

```json
{ "tier": "dedicated", "min": 0, "max": 2, "idle": 120, "identity": null }
```

- **`min: 0`**: scales to zero, so it costs nothing when idle. The cost is a
  **cold start**: the first job waits several minutes while a node is
  allocated, boots, and pulls the job's Docker image.
- **`idle: 120`**: a node that has had no work for 120 seconds is released.
  Two jobs a few minutes apart may each pay a cold start. Raising this trades
  money for speed.
- **`tier: dedicated`** vs. **low priority**: low-priority nodes are much
  cheaper but can be taken back by Azure mid-job. They're fine for sweeps
  and AutoML trials that can be retried, and risky for long single jobs.
  **On this subscription the low-priority quota is 0/0**, so it isn't an option.
- **`max: 2`**: at most 2 nodes of 2 vCPUs each = 4 vCPUs. It has to fit
  **Azure ML's own quota** for the DSv2 family, which is **6** in canadaeast.
  The instance's 2 vCPUs come from the same pool: 2 + 4 = **6 of 6**, so
  nothing is left over.
  ⚠ Correction: on day one I checked `az vm list-usage` (the general
  Microsoft.Compute pool, which showed 10) and called that the quota. That's
  the wrong pool. It even showed 0 used while the instance was running. Azure
  ML compute is counted by **`az ml compute list-usage -l <region>`**
  (`standardDSv2Family 4 / 6` during the AutoML run). Monitoring's serverless
  Spark uses yet another pool. When a job sits in *Queued* forever, the cause
  is usually quota or `max_instances`.

## What happens when a job is submitted to the cluster

```
1. SDK/CLI sends the job spec (YAML/JSON) to the workspace REST API
2. Workspace stores the job → status: Queued (NotStarted → Queued)
3. Cluster has 0 free nodes → scale-up request → Azure allocates a VM   (minutes)
4. Node boots, joins the cluster, pulls the environment's Docker image  (cached after first time)
5. Code snapshot + inputs are mounted or downloaded from datastores     → status: Running
6. Job runs; stdout → logs, metrics/artifacts → MLflow / workspaceartifactstore
7. Job ends → status: Completed / Failed / Canceled
8. Node idles 120 s → released → cluster back to 0
```

The exam angle: *Queued* for a long time means capacity or quota.
*Preparing* for a long time means image build or pull. *Failed* before any
of your code's output appears usually means an environment or data-access
problem, not a code problem.

## Lab vs. my project

My project has **no compute instance** (notebooks run on my Mac) and one
cluster, `train-cluster`, where the *compute's* managed identity needed
explicit grants such as `AcrPull`. Here both computes have `identity: null`,
and jobs from notebooks run as me.
