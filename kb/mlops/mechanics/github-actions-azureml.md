# GitHub Actions ↔ Azure ML

## The chain

```
event (workflow_dispatch / pull_request / push / schedule / repository_dispatch / issue_comment)
  → GitHub starts a workflow run on a GitHub-hosted runner (a fresh Ubuntu VM on the public internet)
    → steps: checkout → az extension add -n ml → azure/login (credentials) → az ml job create -f src/job.yml
      → Azure ML runs the job on aml-cluster (the runner only submits and optionally --stream s the logs)
```

The runner **doesn't train anything**. It's a remote control: it signs in to
Azure as an identity and calls the same `az ml` commands I run locally.

## Three things the workflow needs

| What | Where it lives | Lab 06 value |
|---|---|---|
| **Who** it is in Azure | A **secret** (credentials) or an **OIDC federation** (no secret) | `AZURE_CREDENTIALS`: service principal JSON (`clientId`, `clientSecret`, `subscriptionId`, `tenantId`) |
| **What** it may touch | An Azure **role assignment** on that identity | Contributor on `rg-ai300-l…` only |
| **Which** workspace | **Variables** (not secret) | `AZURE_RESOURCE_GROUP`, `AZURE_WORKSPACE_NAME` |

- **Secrets** are encrypted and masked in logs; **variables** are plain
  configuration. A **repository** secret is available to every workflow;
  an **environment** secret only to jobs that declare `environment: <name>`
  (lab 07), and environments can require an approval first.
- **Least privilege:** scope the role to the resource group or workspace, not
  the subscription.

## What `az ad sp create-for-rbac` actually created (verified, lab 06)

```bash
az ad sp create-for-rbac --name "sp-mslearn-mlops-github" --role contributor \
    --scopes "/subscriptions/<sub>/resourceGroups/rg-ai300-l0533925c724d4c839e" --json-auth \
  | gh secret set AZURE_CREDENTIALS -R medChiboub/mlops-ai-300
```

One command, **four things**, in two different places:

```
Microsoft Entra ID (the tenant: identities)                     Azure (the subscription: resources)
┌─────────────────────────────────────────────────┐          ┌──────────────────────────────────────────┐
│ 1. App registration  "sp-mslearn-mlops-github"  │          │ 4. Role assignment                        │
│    appId     a9bd6f2c-…  (the "client ID")       │          │    Contributor                            │
│    objectId  f9c702e5-…                          │          │    → scope: rg-ai300-l0533925c724d4c839e  │
│    3. client secret (password credential)        │          │    → assigned to the SP (objectId 15b1…)  │
│       valid 2026-09-30 → 2027-09-30              │          └──────────────────────────────────────────┘
│       federated credentials: 0 (no OIDC)         │                          ▲
│                                                  │                          │ "this identity may do this, here"
│ 2. Service principal ("Enterprise application")  │──────────────────────────┘
│    same appId a9bd6f2c-…, objectId 15b1f7f7-…    │
│    the identity that actually signs in and holds roles │
└─────────────────────────────────────────────────┘
```

| Object | What it is | Where you see it |
|---|---|---|
| **App registration** | The *definition* of the application: its ID (`appId` = client ID) and its **credentials** (the client secret lives here) | Entra ID → **App registrations** |
| **Service principal** | The app's *identity instance* in this tenant: what signs in and what **roles are assigned to** | Entra ID → **Enterprise applications** |
| **Client secret** | The password (1 year by default). Its value is shown **only once**, at creation | App registration → Certificates & secrets (only the hint `uR9` is visible afterwards) |
| **Role assignment** | Azure RBAC: *identity + role + scope* | Resource group → **Access control (IAM)** |

**The JSON that went into `AZURE_CREDENTIALS`** (`--json-auth` format) holds
`clientId`, `clientSecret`, `subscriptionId` and `tenantId` (plus Azure
endpoint URLs). The `azure/login@v2` step reads it and signs in as the
service principal (`az login --service-principal` under the hood), then
selects the subscription. Every later `az` step in that job runs **as
`sp-mslearn-mlops-github`**, with exactly Contributor on one resource group.

**Why this matters for cleanup:** deleting the role assignment, or even the
resource group, does **not** delete the identity or its secret. You have to
delete the **app registration** (`az ad app delete --id <appId>`), which also
removes its service principal. That's why it's on the final cleanup list.

**Rotation:** `az ad app credential reset --id <appId>` creates a new secret
(and, without `--append`, removes the old one), so `AZURE_CREDENTIALS` must be
updated. With **OIDC** there's nothing to rotate: instead of a password
credential, the app registration gets a **federated credential** (ours has
0) that trusts GitHub tokens for one repo, branch or environment.

## Service principal secret vs. OIDC (the module's key point)

| | Client secret (the lab) | Workload identity federation / OIDC (my project, and the recommended answer) |
|---|---|---|
| What's stored in GitHub | A long-lived secret (valid 1 year here) | Nothing secret: client, tenant and subscription IDs only |
| How login works | `azure/login` sends the secret | GitHub issues a **short-lived OIDC token** per run; Entra ID trusts it through a **federated credential** matching the repo/branch/environment (`subject`) |
| If it leaks | Usable until rotated or expired | Expires in minutes; only valid for the configured subject |
| Workflow needs | `creds: ${{ secrets.AZURE_CREDENTIALS }}` | `permissions: id-token: write` + `client-id`, `tenant-id`, `subscription-id` |
| CLI signal | `az ad sp create-for-rbac --json-auth` warns *"--sdk-auth has been deprecated"* | Federated credential on the app registration |

## Triggers (module unit 6)

| Trigger | Use |
|---|---|
| `pull_request` | Validate a proposed change; the result is a **status check** a branch rule can require |
| `push` (to `main`) | Train or register after an approved merge |
| `workflow_dispatch` | Run by hand from the Actions tab |
| `schedule` | Regular retraining |
| `repository_dispatch` | An **external system** calls the GitHub API; how Azure events (Event Grid → Logic Apps / Functions) start a workflow, since GitHub can't subscribe to Event Grid |
| `issue_comment` | Lab 07's `/train-prod`, `/deploy-prod` ChatOps; runs with **the base repo's secrets**, so it's risky on a public repo |

## GitHub environments (lab 07's `dev` and `prod`)

**A GitHub environment is a named deployment target in the repo's settings.
It has its own secrets and variables, and rules that must pass before a job
can use it.** A job joins it with one line, `environment: prod`. Until the
rules pass, GitHub doesn't start the job and doesn't release its secrets.

### What this repo has (read back 2026-09-30)

| | `dev` | `prod` | Repository level (no environment) |
|---|---|---|---|
| Secrets | `AZURE_CREDENTIALS` | `AZURE_CREDENTIALS` | `AZURE_CREDENTIALS` |
| Variables | none | none | `AZURE_RESOURCE_GROUP`, `AZURE_WORKSPACE_NAME` |
| Protection rules | none | **required reviewer: medChiboub** | none |
| Deployment branch policy | none | none | none |
| Used by | `train-dev.yml` | `train-prod.yml`, `deploy-prod.yml` | `manual-trigger-job.yml`, `send-monitor-traffic.yml` |

All three `AZURE_CREDENTIALS` are **the same service principal** (the
repo copy uses the `rbac` client secret; both environment copies use
`gh-environments-lab07`), with Contributor on the same resource group. So
the environments **don't separate Azure access**. They separate **who
decides and when**. 🧪 This is the lab's shortcut.

### What happens when a `prod` job starts

```
/deploy-prod comment → job declares environment: prod
  → status "Waiting": no runner, no secret exposed
  → the reviewer gets a notification → Review deployments → Approve (or Reject)
  → the runner starts, and secrets.AZURE_CREDENTIALS = the prod environment's value
  → GitHub records a deployment to "prod" (visible under Deployments)
```

- **Name precedence:** environment secret > repository secret >
  organization secret. That's why one name, `AZURE_CREDENTIALS`, works
  everywhere: a job with `environment: prod` gets the prod value, and a job
  without an environment gets the repository value.
- **Rejecting or never approving:** the job doesn't run. It fails after
  30 days waiting.
- **One approval is enough**, even when several reviewers are listed.

### Protection rules available (we use one)

| Rule | What it does | Here |
|---|---|---|
| **Required reviewers** | Up to 6 people or teams; one approval releases the job | ✅ `prod` |
| Prevent self-review | Whoever triggered it can't approve it | ❌ (I'm the only reviewer) |
| Wait timer | Waits N minutes before starting | ❌ |
| **Deployment branches and tags** | Only listed branches can deploy to it (for example `main`) | ❌ (📘 a real `prod` would restrict it) |
| Custom rules (GitHub Apps) | External checks, for example "is monitoring green?" | ❌ |

⚠ Plan limit: on GitHub **Free**, environments with protection rules only
work in **public** repos. That's why this repo was made public in lab 06.
Going private would drop the `prod` gate.

### How a real setup uses environments (📘)

- **Each environment points at a different Azure target**: `prod` holds
  credentials for an identity that can only touch the prod
  workspace/subscription, and `dev` for one that can only touch dev.
  Then the gate protects **real** separation.
- **With OIDC, the environment becomes part of the identity**: the federated
  credential's subject `repo:<owner>/<repo>:environment:prod` makes Entra ID
  trust **only** jobs running in the `prod` environment. There's no secret
  to leak, and a job outside `prod` can't get a prod token at all.
- Exam cue: *"require approval before deploying to production"* → a
  **GitHub environment with required reviewers** (this module's
  assessment).

### Three different "environments" (don't mix them up)

Full comparison, with real examples and exam cues: [three-environments.md](three-environments.md).

| Term | What it is | Example here |
|---|---|---|
| **GitHub environment** | A deployment target plus rules and secrets, in the repo settings | `dev`, `prod` |
| **Azure ML environment** | The Docker image plus Python packages a job runs in | `AzureML-sklearn-1.0-ubuntu20.04-py38-cpu` (lab 02 onward) |
| **Dev/prod environment (stage)** | The architecture idea: separate workspaces, subscriptions or regions per stage | Lab 05's design (deleted); in lab 07, simulated in one workspace |

## One job definition, several environments (`--set`)

Lab 07's `train-dev.yml` and `train-prod.yml` submit **the same
`src/job.yml`** and change only what differs per environment, at submit
time:

```bash
az ml job create -f src/job.yml --set inputs.training_data.path=azureml:diabetes-dev-folder@latest    # dev
az ml job create -f src/job.yml --set inputs.training_data.path=azureml:diabetes-prod-folder@latest   # prod
```

- **Same definition, different configuration:** the reviewed code and job
  definition are exactly what runs in prod; only data, credentials (the
  GitHub environment secret) and, in real setups, the workspace (`-g/-w`)
  change. Separate per-environment YAML copies drift apart.
- `--set` overrides **one field** of the YAML (the SDK equivalent: calling the
  job with new values, `job(reg_rate=…)`). It doesn't change other fields: a
  path override keeps the file's `type:`, so the type must fit both assets.
- The same idea at a bigger scale: my project uses one Bicep template + a
  `.bicepparam` per environment, and one model version promoted through the
  registry.

## `issue_comment` workflows (lab 07's `/train-prod`, `/deploy-prod`)

- They run the workflow file **from the default branch (`main`)**, not from
  the PR. So a fix to such a workflow only takes effect once merged (why
  lab 07's CLI pin went in as its own PR first).
- They run with **the base repo's secrets**, and the lab's versions check out
  **the PR's code** (`refs/pull/<N>/head`): the **pwn-request** risk on
  public repos. Mitigations: restrict who can comment (interaction limits,
  or a permission check in the workflow), and a **protected environment with
  a required reviewer**, so the job pauses before any secret is available.
- `contains(comment.body, '/train-prod')` matches anywhere, even in a quote;
  anchoring to the first line is safer (my project's `chatops.yml`).

## Branch protection vs. workflows

A **workflow** decides *what runs*; a **branch protection rule** (or ruleset)
decides *whether a merge is allowed*: require a PR, approvals, and
**required status checks** (named by the workflow's **job name**). Together
they're the quality gate. On a **private** repo on GitHub Free, protection
returns `403 Upgrade to GitHub Pro`; on a public repo it's free (we checked
both).

## Network

A GitHub-hosted runner comes from the public internet, so the workspace
must allow **public network access**. Ours: `public_network_access:
Enabled`, default action Allow, no IP rules, no managed network, 0 private
endpoints. With a **private** workspace (private endpoints, public access
disabled), you'd use **self-hosted runners** inside the virtual network.
