# Network isolation: the Microsoft Learn way (exam view)

Exam skill: **"Restrict network access to Machine Learning workspaces."** My
lab workspace and my production project both used **public network access,
no private endpoints** (lab 06 §2, `infra/modules/workspace.bicep`). So this
file is the docs only. I've never built it, so learn the model and the
traps.

Sources: 📘 Microsoft Learn, read 2026-10-31:
*Plan for network isolation* (`how-to-network-isolation-planning`),
*Managed virtual network* (`how-to-managed-network`),
*Configure a private endpoint* (`how-to-configure-private-link`),
*Network isolation for managed online endpoints* (`concept-secure-online-endpoint`),
*Network isolation for registries* (`how-to-registry-network-isolation`),
*Secure workspace resources using VNets* (`how-to-network-security-overview`).

## The one idea: inbound and outbound are separate problems

```
             INBOUND                                   OUTBOUND
   who can reach the workspace?          what can the workspace and its compute reach?

 you / CI / clients ──► [workspace] ──► storage, key vault, ACR, PyPI, MCR, internet...
                          ▲                         ▲
   public_network_access  │                         │  managed virtual network
   + private endpoint     │                         │  (isolation_mode + outbound rules)
   + selected IP ranges   │                         │
```

Microsoft splits it into three areas:
1. **Inbound** to the workspace.
2. **Outbound** from the workspace.
3. **Outbound** from compute.

| Control | Secures | Mechanism |
|---|---|---|
| `public_network_access` (PNA) | Inbound | `Enabled`, `Disabled`, or "Enabled from selected IP addresses" |
| **Private endpoint** (`amlworkspace`) | Inbound | A private IP for the workspace in **your** VNet |
| **Managed VNet** | Outbound, for the workspace and managed compute | `isolation_mode` + outbound rules, in a VNet in **Microsoft's** tenant |

Trap: **a managed VNet doesn't give inbound isolation.** "Securing your
workspace with a managed network provides network isolation for outbound
access... An Azure Virtual Network that you create and manage provides
network isolation inbound access to the workspace."

## Two approaches: managed (recommended) vs. custom VNet

| | **Managed network isolation** (recommended) | **Custom network isolation** (your own VNet) |
|---|---|---|
| Compute's VNet lives in | Microsoft's tenant | Your tenant |
| Setup | Minimal: Azure ML creates and maintains it | You build subnets, NSGs, UDRs, DNS |
| **Managed online endpoints** | ✅ Supported | ❌ Not supported |
| **Serverless Spark** | ✅ Supported | ❌ Not supported |
| No-code MLflow deployment, foundation models | ✅ | ❌ |
| On-premises / non-Azure resources | Limited | ✅ |
| Firewall and NSG logging | ❌ Not supported | ✅ |
| Non-HTTPS endpoints | ❌ Not supported | ✅ |
| Cost | Feature is free; you pay for Private Link and Azure Firewall (FQDN rules) | Your own network resources |

Exam cue:
- "Minimal overhead", "managed online endpoints", "serverless Spark" →
  **managed VNet**.
- "Company policy", "on-prem connectivity", "must log the firewall" →
  **custom VNet**.

## Managed VNet: the 3 isolation modes

| Mode | YAML value | Portal label | Allows outbound to |
|---|---|---|---|
| **Allow internet outbound** | `allow_internet_outbound` | Private with Internet Outbound | Everything on the internet |
| **Allow only approved outbound** | `allow_only_approved_outbound` | Private with Approved Outbound | Only what your outbound rules allow |
| **Disabled** | — | — | Not restricted, or you're using your own VNet |

When to pick which:
- **Internet outbound:** you want unrestricted access to PyPI, conda,
  Hugging Face and similar.
- **Approved outbound:** you want to **minimize data exfiltration**, and
  you'll pre-stage the artifacts you need or allow-list them.

```yaml
# workspace.yml
managed_network:
  isolation_mode: allow_only_approved_outbound
  outbound_rules:
    - name: pypi
      type: fqdn                    # only valid in approved-outbound mode; uses Azure Firewall
      destination: pypi.org
    - name: frontdoor
      type: service_tag             # only valid in approved-outbound mode
      destination: {service_tag: AzureFrontDoor.FirstParty, protocol: TCP, port_ranges: "443"}
    - name: mydata
      type: private_endpoint        # valid in both modes
      destination:
        service_resource_id: /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<acct>
        subresource_target: blob
        spark_enabled: true         # needed for serverless Spark
```

```bash
az ml workspace create -n ws -g rg --managed-network allow_internet_outbound
az ml workspace update -n ws -g rg --managed-network allow_only_approved_outbound
az ml workspace provision-network -n ws -g rg --include-spark   # provision now, with Spark
az ml workspace show -n ws -g rg --query managed_network
az ml workspace outbound-rule list --workspace-name ws -g rg
```

### Outbound rule types

| Type | In which mode | Notes |
|---|---|---|
| **Private endpoint** | Both | The way to reach Azure resources privately. **Use it for Storage**: an FQDN rule can't reach Azure Storage in approved mode |
| **Service tag** | Approved only | For example `AzureMachineLearning`, `AzureActiveDirectory`, `BatchNodeManagement.<region>` |
| **FQDN** | Approved only | **Ports 80 and 443 only.** The first FQDN rule deploys an **Azure Firewall**: Standard SKU by default, `firewall_sku: basic` optional, **Premium not supported**, so no URL filtering. It adds cost and about 10 minutes to provisioning |

### Rules added for you

- **Private endpoint rules** to the workspace, its default storage, key vault
  and container registry.
  - In **allow internet outbound**: only for those resources that have
    public access disabled.
  - In **allow only approved outbound**: always, whatever their access
    setting.
- **No service-tag or FQDN rules are added for you.** In approved mode, every
  other destination (PyPI, Hugging Face, VS Code…) is a rule you add.

Required service tags, for managed or custom VNets alike:

| Tag | Direction | Why |
|---|---|---|
| `AzureMachineLearning` | In + Out | Compute create/update/delete; the service itself (ports 443, 8787, 18881, UDP 5831) |
| `BatchNodeManagement.<region>` | Out | The Azure Batch back end for compute instances and clusters |
| `AzureActiveDirectory` | Out | Entra ID authentication |
| `AzureResourceManager` | Out | Creating resources from the CLI or SDK |
| `AzureFrontDoor.FirstParty`, `MicrosoftContainerRegistry` | Out | Microsoft's Docker images |
| `AzureMonitor` | Out | Logs and metrics, if Azure Monitor isn't secured |
| `VirtualNetwork` | Out | When private endpoints exist in the VNet or a peered VNet |

"Service tags as the ONLY security boundary isn't sufficient. For tenant
level isolation, use private endpoints when possible."

### Timing and one-way doors

- **The managed VNet isn't created with the workspace.** It's created when
  the first compute is created (about **30 minutes**), or when you provision
  it yourself. Microsoft recommends provisioning it yourself first, and it's
  **required** before the first online deployment, unless a compute instance
  already provisioned it.
- **The workspace's private endpoints aren't created automatically** either.
  They arrive with the first compute or a forced provisioning.
- **Disable public network access before provisioning**, or the workspace's
  private endpoints may not be created in the managed VNet.
- **One-way doors:**
  - Once managed isolation is on, **you can't disable it**.
  - Approved outbound **can't go back** to internet outbound.
- **Existing compute must be deleted** (instances, clusters, online
  endpoints) before you switch an existing workspace to a managed VNet.
  There's no migration path.
- Use **`managedNetworkKind v1`**. v2 is in preview.

### Serverless Spark in a managed VNet

- It needs a storage private endpoint with `spark_enabled: true`, plus
  provisioning with `--include-spark`.
- In approved-outbound mode, **conda packages in the Spark session
  configuration fail to install**. Upload a self-contained wheel and pass it
  as `py_files` instead. "Setting an FQDN outbound rule won't bypass this."
- **Model monitoring isn't supported with `allow_only_approved_outbound`.**
  See [monitoring-ms-learn.md](monitoring-ms-learn.md).

## Inbound: public access, private endpoint, IP ranges

**Public network access:**
- Set it with `az ml workspace update --set public_network_access=Disabled`,
  or `public_network_access: Disabled` in YAML.
- `allow_public_access_when_behind_vnet` is the old SDK v1 property, and SDK
  v1 is deprecated.
- **Turning public access on doesn't delete private endpoints.**
  **Deleting private endpoints doesn't make the workspace public.** The two
  settings are independent.

**Workspace private endpoint:**
```bash
az network private-endpoint create --name ws-pe --vnet-name vnet --subnet snet \
  --private-connection-resource-id "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.MachineLearningServices/workspaces/<ws>" \
  --group-id amlworkspace --connection-name workspace -l <region>
```
- Subresource: **`amlworkspace`**.
- Private DNS zones: **`privatelink.api.azureml.ms`** and
  **`privatelink.notebooks.azure.net`**.
- Before you start, disable network policies for private endpoints on the
  subnet.
- **Don't use `172.17.0.0/16`**, because it's Docker's bridge range.
- A workspace can have **multiple private endpoints**, one per client VNet.
- Each VNet with a workspace private endpoint must also reach the workspace's
  **storage, key vault and ACR**.

**Selected IP ranges** (inbound allow-list without going fully private):
```bash
az ml workspace update -g rg -n ws --public-network-access Enabled \
  --network-acls "16.17.18.19,16.17.18.0/24"     # "none" resets it
```
- Up to **200 rules**, **public IPv4 only**, set only **after** the
  workspace exists.
- **Selected IPs alone, without a managed VNet or private endpoint, can make
  compute instance provisioning fail.** Managed online deployments also fail
  with selected IPs unless the managed VNet is on.

**Control plane vs. data plane:**
- Private endpoints cover the **data plane**: Studio, the SDK, APIs, scoring.
- **Control plane** operations (creating, updating or deleting the workspace
  and compute) still go through **Azure Resource Manager over the public
  network**.

**How people and CI reach a private workspace:**
- **VPN gateway** (point-to-site or site-to-site), **ExpressRoute**, or
  **Azure Bastion to a jump-box VM** in the VNet.
- Plan **DNS** for VPN and ExpressRoute.
- **GitHub-hosted runners can't reach it.** Use **self-hosted runners**
  inside, or peered to, the VNet. This one comes from my lab 06 notes
  ([github-actions-azureml.md](github-actions-azureml.md)); the pages don't
  mention CI.

**Studio behind a VNet:**
- The client needs a private (or service) endpoint to the **default storage
  account** for notebooks and datasets.
- Some features are off by default when storage is in a VNet: data preview,
  AutoML submission from Studio, labeling, and others.
- Use Edge or Chrome, because Firefox has known issues.

## Dependent resources

| Resource | How it's secured | Must-know |
|---|---|---|
| **Key Vault** | Service or private endpoint | **Enable "Allow trusted Microsoft services to bypass this firewall"** even when you have private endpoints. Azure ML reads secrets service-side, and private endpoints don't cover that |
| **Storage** | Private endpoint (or service + private) | Default storage must be in the **same VNet** as the workspace (a different subnet is fine). **You can't have a private endpoint and a service endpoint at the same time** |
| **Container Registry** | Private endpoint, plus "Allow trusted services" | **Images can't be built with ACR Tasks behind a private link.** See below |
| **Application Insights** | Through **Azure Monitor Private Link Scope (AMPLS)** | — |

Dependencies can live in **another subscription**, but **must be in the same
tenant**.

**Image builds behind a VNet** (a classic exam question):
- With private link, the workspace can't build images with ACR Tasks, so it
  falls back to **serverless compute**.
- That fallback only works if storage and ACR **aren't** network-restricted.
- If they are, **set `image_build_compute` to a compute cluster** you've
  already created:

```bash
az ml workspace update -n ws -g rg --image-build-compute mycompute
```

- It **can't be set in the portal**.
- The build cluster needs a path to package repositories. In approved mode,
  add outbound rules for them.

## Compute

**Managed VNet:**
- Compute instances, clusters, serverless compute and managed online
  endpoints **all use it automatically**.
- **You can't put compute in your own VNet** while using a managed VNet.
- **Clusters must be in the workspace's region.**
- **Kubernetes and attached VMs aren't supported.**

**Your own VNet:**
- Compute must share the workspace's **VNet, region and subscription**.
- **No public IP is recommended.**
  - With a public IP, you get a load balancer and must allow inbound from the
    `AzureMachineLearning` service tag (NSG + UDR past your firewall).
  - Without one, a private link service handles inbound, so there's no
    inbound rule to maintain.
- No public IP? SSH with `az ml compute connect-ssh`.

**Turning private link on or off after compute exists** doesn't update that
compute, so recreate it.

Every compute instance, cluster node and private endpoint uses **one private
IP**. Size your subnets for that.

## Managed online endpoints

**Inbound:**
- Set it on the **endpoint**:
  `az ml online-endpoint create -f endpoint.yml --set public_network_access=disabled`.
- Clients then score **through the workspace's private endpoint**. The
  endpoint shares it.
- For manual DNS, add the wildcard A record
  `*.<workspace-guid>.inference.<region>.privatelink.api.azureml.ms`.

**Outbound:**
- **Enable the workspace managed VNet.** Every managed online deployment
  then uses it to reach the workspace, storage, ACR, key vault and MCR.
- The **legacy** per-deployment flag `egress_public_network_access=disabled`
  gave each deployment its own VNet with 3 private endpoints. It **can't be
  changed after creation**, isn't recommended, and **doesn't apply once the
  workspace has a managed VNet**.

| Workspace PNA | Endpoint PNA | Result |
|---|---|---|
| Disabled | Disabled | Fully private (the recommended combination) |
| Disabled | Enabled | Public traffic rejected at the workspace |
| Selected IPs | Disabled | Workspace honors the IP list; endpoint is private |
| Selected IPs | Enabled | Both honor the IP list |

Other rules:
- **Batch endpoints** have no public-access flag and no selected-IP support.
  They're private when the workspace is.
- `v1_legacy_mode` must be `false`, or you can't create managed online
  endpoints.
- A workspace private endpoint created **before 2022-05-24** must be
  recreated.
- Control plane operations (create, delete, get keys) still go through ARM
  publicly.

## Registries

- **Private endpoint for the registry:** disable public access with
  `az ml registry update --public-network-access Disabled`, then add a
  private endpoint **in the same subnet as the workspace's**.
- Also secure the registry's **managed storage and ACR**. They sit in the
  managed resource group `azureml-rg-<registry>_<GUID>`.
- The registry FQDN is `<guid>.registry.<region>.privatelink.api.azureml.ms`.
  There's no public FQDN to fall back on, so **your DNS must resolve it**.
- **Sharing from a secure workspace to a private registry fails** if the
  asset's storage has public access disabled. Fix it on the workspace
  storage: "Enabled from selected virtual networks and IP addresses", plus a
  resource-instance rule for `Microsoft.MachineLearningServices/registries`.
- **You can't create an environment directly** in a private registry whose
  ACR has public access disabled. Create it in a workspace and share it.
- **Studio only shows models** for a private registry. Use the CLI or SDK for
  other assets.
- Deploying a registry model to a legacy isolated endpoint creates the
  registry private endpoints automatically.

## Prerequisites and RBAC

- **Provider:** register **`Microsoft.Network`** for the managed VNet.
- **CLI:** keep the `ml` extension current. The managed VNet dates from
  2023-05-23.
- **Private endpoint permissions:** the identity creating managed-VNet
  private endpoints needs
  `workspaces/privateEndpointConnections/read` and `/write`.
- **Since 2025-04-30 these aren't granted automatically.** Microsoft
  recommends the **Azure AI Enterprise Network Connection Approver** role for
  the workspace managed identity. Default workspace resources are covered
  from creation.
- **Locks:** no scope locks on the workspace or its resource group. The
  managed VNet is deleted with the workspace.

## Lab vs. my production project vs. the docs

| | Lab (`setup.sh`) | My production project (Bicep) | Docs' recommendation |
|---|---|---|---|
| Workspace PNA | Enabled | `publicNetworkAccess: 'Enabled'` | Disabled + private endpoint |
| Outbound | No managed VNet | No managed VNet | Managed VNet, approved outbound for exfiltration control |
| Key Vault | Defaults | RBAC, soft delete, public | Private endpoint + trusted-services bypass |
| Storage | Defaults | TLS 1.2, no public blobs, public endpoint | Private endpoint |
| ACR | `az ml workspace create` defaults | Basic, admin disabled | Private endpoint; set `image_build_compute` |
| CI | GitHub-hosted runner | GitHub-hosted runner | Self-hosted runner in the VNet once private |
| Endpoint | Public, key auth | Public, key auth | `public_network_access: disabled` |

Why neither went private: a private workspace breaks GitHub-hosted runners
and needs VPN or Bastion to even open Studio. That's real infrastructure
cost for a learning project. This is my production project's open AI-300 gap
(`docs/AI-300.md`), deliberately left as reading.

## Foundry: the same model

From practice question [Q33](../../practice/genaiops/q033-foundry-private-network.md).
Microsoft Foundry resources follow the same two halves:

- **Inbound:** **disable public network access** + **private endpoints** for
  clients.
- **Outbound:** a **managed virtual network**, with managed private
  endpoints to dependent resources (storage, AI Search, Key Vault…).

"Disable all inbound access" is a distractor, because private-endpoint
access is still inbound. Authentication method and subscription placement
aren't network controls.

## Exam traps

1. A **managed VNet = outbound** isolation. **Inbound** = PNA + private
   endpoint.
2. **Managed VNet is recommended.** A custom VNet doesn't support managed
   online endpoints or serverless Spark.
3. **FQDN and service-tag rules only exist in approved-outbound mode.**
   Private endpoint rules work in both.
4. **FQDN rules can't reach Azure Storage.** Use a private endpoint.
5. FQDN rules cost money (Azure Firewall), ports 80/443 only, no Premium
   SKU.
6. Once managed isolation is on, it **can't be disabled**. Approved can't go
   back to internet outbound.
7. The managed VNet and the workspace's private endpoints appear at the
   **first compute** or a **manual provision**, not at workspace creation.
   Provision it before the first online deployment.
8. Removing private endpoints **doesn't** make the workspace public.
   Enabling public access **doesn't** remove them.
9. Behind a private link, **ACR Tasks can't build images**. Set
   `image_build_compute` (CLI or SDK only).
10. Key Vault needs **"Allow trusted Microsoft services"** even with private
    endpoints.
11. Selected-IP rules: public **IPv4** only, up to 200, and alone they can
    break compute instance provisioning.
12. Control plane goes through ARM publicly. Private endpoints cover the data
    plane.
13. Endpoint egress follows the **workspace managed VNet**. The legacy
    `egress_public_network_access` flag doesn't apply then, and can't be
    changed after creation anyway.
14. **Model monitoring isn't supported with approved-outbound.** Spark conda
    installs fail there too, so use a wheel via `py_files`.
15. A private workspace means **GitHub-hosted runners can't reach it**. Use
    self-hosted runners in the VNet.

## Self-check

Click a question to reveal its answer. Answer before opening.

<details>
<summary><strong>1.</strong> You enable a managed VNet in <code>allow_only_approved_outbound</code> mode. Can people on the internet still open the workspace in Studio?<br><br>A) No, the managed VNet blocks all access<br>B) Yes, unless you also set <code>public_network_access</code> to <code>Disabled</code> (and add a private endpoint for your own clients). The managed VNet only controls outbound traffic<br>C) Only via Bastion<br>D) Only from Azure regions</summary>

> **✅ Answer: B.** Inbound and outbound are separate controls. The managed VNet is the outbound half.
</details>

---

<details>
<summary><strong>2.</strong> You need managed online endpoints and serverless Spark with minimal network maintenance. Which approach?<br><br>A) A custom VNet with NSGs and UDRs<br>B) Managed network isolation<br>C) Public access with IP rules only<br>D) The legacy <code>egress_public_network_access</code> flag on each deployment</summary>

> **✅ Answer: B.** A custom VNet doesn't support managed online endpoints or serverless Spark, and Microsoft recommends the managed network.
</details>

---

<details>
<summary><strong>3.</strong> In approved-outbound mode, a job must read from another storage account. You add an FQDN rule for <code>mystorage.blob.core.windows.net</code>, and it still fails. Why?<br><br>A) FQDN rules need port 8787<br>B) FQDN rules can't be used for Azure Storage in approved-outbound mode. Add a private endpoint outbound rule (subresource <code>blob</code>) instead<br>C) The firewall SKU must be Premium<br>D) Storage needs a service-tag rule for <code>AzureMachineLearning</code></summary>

> **✅ Answer: B.** The docs say this explicitly. Premium firewall isn't even supported by the managed VNet.
</details>

---

<details>
<summary><strong>4.</strong> After you secure the workspace's ACR and storage with private endpoints, environment image builds start failing. What do you configure?<br><br>A) Make ACR public again<br>B) Set the workspace's <code>image_build_compute</code> to an existing compute cluster (with the CLI or SDK, because the portal can't set it)<br>C) Raise the ACR SKU<br>D) Add an FQDN rule for <code>azurecr.io</code></summary>

> **✅ Answer: B.** Behind a private link, ACR Tasks can't build. The serverless fallback only works when storage and ACR aren't network-restricted.
</details>

---

<details>
<summary><strong>5.</strong> You delete the workspace's private endpoint. Is the workspace now publicly reachable?<br><br>A) Yes<br>B) No. Public access is controlled only by <code>public_network_access</code>, independently of private endpoints<br>C) Only from Azure<br>D) Only through Studio</summary>

> **✅ Answer: B.** The reverse is also true: enabling public access doesn't remove existing private endpoints.
</details>

---

<details>
<summary><strong>6.</strong> Your workspace is fully private. A GitHub Actions workflow running on <code>ubuntu-latest</code> can't submit jobs. What fixes it?<br><br>A) Switch from a client secret to OIDC<br>B) Run the workflow on a self-hosted runner inside (or peered to) the workspace's VNet<br>C) Grant Owner instead of Contributor<br>D) Add an FQDN outbound rule for <code>github.com</code></summary>

> **✅ Answer: B.** GitHub-hosted runners come from the public internet. Authentication isn't the problem; network reachability is.
</details>

---

<details>
<summary><strong>7.</strong> The workspace uses a managed VNet, but a deployment was created with <code>egress_public_network_access=disabled</code>. Which controls its outbound traffic?<br><br>A) The deployment flag<br>B) The workspace managed VNet. The legacy flag no longer applies once the workspace has a managed VNet<br>C) Both, whichever is stricter<br>D) Neither</summary>

> **✅ Answer: B.** Microsoft says to avoid setting the legacy flag in that case. It also can't be changed after creation.
</details>

---

<details>
<summary><strong>8.</strong> You want to tighten a workspace from <code>allow_internet_outbound</code> to <code>allow_only_approved_outbound</code>, and later loosen it back. What's true?<br><br>A) Both changes are allowed at any time<br>B) Tightening to approved outbound is allowed, but you can't go back from approved to internet outbound, and you can never disable managed isolation once it's on<br>C) Neither change is allowed<br>D) Only through the portal</summary>

> **✅ Answer: B.** These are one-way doors. Plan the mode before you create compute.
</details>

---

<details>
<summary><strong>9.</strong> Which two private DNS zones does a workspace private endpoint use?<br><br>A) <code>privatelink.blob.core.windows.net</code> and <code>privatelink.vaultcore.azure.net</code><br>B) <code>privatelink.api.azureml.ms</code> and <code>privatelink.notebooks.azure.net</code><br>C) <code>privatelink.azurecr.io</code> only<br>D) <code>privatelink.azureml.net</code> and <code>privatelink.studio.azure.com</code></summary>

> **✅ Answer: B.** Option A lists zones for storage and key vault, which belong to those resources' own private endpoints.
</details>

---

[← mechanics index](README.md) · [Model monitoring, the Microsoft Learn way](monitoring-ms-learn.md) · [GitHub Actions ↔ Azure ML](github-actions-azureml.md)
