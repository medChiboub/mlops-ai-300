# Bicep and `az deployment`: scopes and what a template does

Started after practice question [Q35](../../practice/genaiops/q035-bicep-group-deployment.md).
My production project is all Bicep (`infra/main.bicep` + `.bicepparam`), so
this mainly names what I already did.

## Deployment scope = the CLI command + `targetScope`

| Command | `targetScope` | Deploys into |
|---|---|---|
| `az deployment group create --resource-group <rg>` | `'resourceGroup'` (default) | An **existing** resource group |
| `az deployment sub create --location <loc>` | `'subscription'` | The subscription (for example, to *create* resource groups) |
| `az deployment mg create` | `'managementGroup'` | A management group |
| `az deployment tenant create` | `'tenant'` | The tenant |

- `az deployment group create` **doesn't create the resource group.** It
  must exist (or use a subscription-scope template that creates it).
- **Another subscription:** choose it in the CLI (`--subscription <id>` or
  `az account set`). The resource-group-scoped template needs **no**
  `subscriptionId` parameter.
- `--parameters key=value` or a `.bicepparam` file supplies params. An
  undeclared symbol (like a `name` that's never defined) fails at build.
- `az deployment group what-if` previews the changes.

## Identity in a template

`identity: { type: 'SystemAssigned' }` gives **that one resource** its own
managed identity. Nothing else inherits it: child or related resources (for
example Foundry **projects**) have their own identities and need their own
role assignments.
