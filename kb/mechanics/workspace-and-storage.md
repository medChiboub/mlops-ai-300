# Workspace and its storage

## The one idea

An Azure ML **workspace** is mostly a *catalog and control point*. It stores
names, versions, job history and permissions. Almost everything heavy (files,
data, logs, models, images, secrets) lives in **other Azure resources** that
the workspace is wired to. `az ml workspace create` created five resources,
not one:

```
rg-ai300-l0533925c724d4c839e
├── mlw-ai300-l0533925c724d4c839e      the workspace: catalog, job history, RBAC, API endpoint
├── mlwai300storage56d80847e           Storage account: data, code, job outputs, model files
├── mlwai300keyvaultc809e2fa           Key Vault: secrets (storage keys, connection credentials)
├── mlwai300insights8756902e           Application Insights: telemetry from deployed endpoints (lab 07)
├── mlwai300logalyti115a22a4           Log Analytics: the backing store behind App Insights
└── (Container Registry)               not created yet; appears on the first custom
                                       environment image build or deployment
```

So "delete the workspace" doesn't free the storage, and "someone has access to
the storage account" means they can read your data even without workspace
permissions. That's why network and RBAC questions on the exam always cover
the dependent resources too.

## Datastores: named connections into storage

A **datastore** is not storage. It's a *registered pointer plus credentials*
to a container or file share. Code refers to `azureml://datastores/<name>/paths/...`
and never deals with account keys. My workspace got four automatically
(`az ml datastore list`):

| Datastore | Points at | What goes there |
|---|---|---|
| `workspaceblobstore` (**default**) | blob container `azureml-blobstore-5907…` | Uploaded data: `az ml data create` put both CSV uploads under `LocalUpload/<hash>/` |
| `workspaceartifactstore` | blob container `azureml` | Job artifacts: logs, outputs, MLflow-logged models and files |
| `workspaceworkingdirectory` | file share `code-391ff5ac…` | **Notebooks and code**: my `git clone` in §2 landed here, under `Users/mohamedd.chiboubb/` |
| `workspacefilestore` | file share `azureml-filestore-5907…` | Legacy default file share (SDK v1 era); rarely used now |

The storage account also has `insights-logs-auditevent` and
`insights-metrics-pt1m` containers. Those hold Azure diagnostic logs, not ML
data.

## What happened in §2, mechanically

When I ran `git clone` in the compute instance terminal, the files went to
the **`code-391ff5ac…` Azure Files share**, which every compute instance in
the workspace mounts at `~/cloudfiles/code/`. The Studio **Files** pane is a
browser view of that same share. That's why:

- the files survive stopping or deleting the compute instance (they aren't on
  the VM's disk)
- another user's compute instance can't see my `Users/mohamedd.chiboubb/`
  folder by default in Studio, but anyone with storage access can
- the ↻ refresh was needed: the Files pane doesn't watch the share live

Studio added `.amlignore` files. When a job is submitted from a folder, Azure
ML uploads that folder as the job's **code snapshot**, and `.amlignore` (same
syntax as `.gitignore`) controls what's left out.

## Key Vault and identity, briefly

The datastores above connect with the **storage account key**, and the
workspace keeps that key in Key Vault. The alternative, used by my production
project, is **identity-based** access, where a managed identity or my Entra
ID user is granted storage RBAC roles and no key is involved. Exam angle: an
identity-based datastore means the *caller's* identity needs a data-plane
role such as *Storage Blob Data Reader*. That's a common "why does my job get
403 on data" scenario.

## Lab vs. my project

My production project's Bicep declares the same resource set (workspace +
storage + key vault + App Insights + ACR) explicitly, so each is named,
reviewed and repeatable. Here the CLI generated names like
`mlwai300storage56d80847e` for me.
