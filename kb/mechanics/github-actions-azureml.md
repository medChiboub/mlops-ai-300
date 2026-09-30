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
