# Foundry setup: resources, projects, identity

How a Foundry resource and its projects are organised and secured. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

## Foundry resource vs. project

From practice question [Q42](../../practice/genaiops/q042-foundry-resource-vs-project.md).

| Level | Holds | Use for |
|---|---|---|
| **Foundry resource** | Governance, security, networking, model deployments, **shared connections** | One shared resource = central control |
| **Project** (under the resource) | A team's files, agents, evaluations, access | **One project per team** = isolation |

It's the same shape as Azure ML **hub + projects**.

## Identity: key-less access and least privilege

From practice question [Q3](../../practice/genaiops/q003-foundry-keyless-identity-rbac.md).

| Need | Mechanism |
|---|---|
| A service or workload signs in **without stored secrets** | **Managed identity** (Entra ID; Azure manages the credential) |
| Decide **what** a person or identity may do, and **where** | **Azure RBAC role assignment**, scoped to the project, Foundry resource, resource group or subscription |

- A managed identity has **no permissions by itself**. Pair it with role
  assignments (for example a Storage Blob Data role, or a Search index data
  role).
- API keys and secret-based service principals violate a "no stored
  credentials" policy.
- It's the same pattern as my production project's OIDC + scoped
  Contributor, and the lab's service-principal secret is the counterexample.
