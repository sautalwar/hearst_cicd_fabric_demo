# Hearst Fabric CI/CD — Terraform Setup (Self-Contained)

This `infra/` package is **self-contained**: fill in a handful of values and
`terraform apply` builds the whole environment from scratch — the **Fabric F-SKU
capacity**, three **workspaces** (Dev/UAT/Prod), the **deployment pipeline**, the
**security identity** + **Key Vault**, and an **example workload** you can actually
see and run. State is **local by default**, so you can clone and run immediately.

> Everything here was authored with **GitHub Copilot** — Terraform across three
> providers, plus the automation, pipelines, tests, and docs.

---

## 1. Prerequisites

- **Azure subscription** + permission to create a resource group, Key Vault, and a
  Fabric capacity.
- Permission to **create an Entra app registration / service principal** (for `identity.tf`).
- A **Microsoft Fabric tenant** with these admin settings enabled:
  *Service principals can use Fabric APIs*, *Users can create Fabric items*.
- **Register the resource providers once** (auto-registration is intentionally disabled for speed):
  `az provider register --namespace Microsoft.Fabric` and `az provider register --namespace Microsoft.KeyVault`.
- Tooling: **Terraform >= 1.6**, **Azure CLI** (`az login`).

---

## 2. Fill in your values

```powershell
cd infra
cp terraform.tfvars.example terraform.tfvars   # then edit terraform.tfvars
```

Minimum you must set:

| Variable | What it is |
|----------|------------|
| `subscription_id` | Your Azure subscription GUID |
| `tenant_id` | Your Entra tenant GUID |
| `admin_object_id` | Your user/group object ID (gets Admin on workspaces + Key Vault) |
| `key_vault_name` | A globally-unique Key Vault name |

### Capacity — the one decision that matters

The package **prefers an existing capacity** and **creates one only if you don't
give it one**:

| You set… | Result |
|----------|--------|
| `existing_capacity_name = "My Capacity"` | Looks it up by name and **reuses** it |
| `capacity_id = "<guid>"` | Binds directly to that capacity |
| **both blank** (default) | **Creates a new** `F2` capacity (`capacity_sku`) |

`F2` is the **minimum SKU** that runs this workload (Spark, Warehouse, Lakehouse,
pipelines). Bump `capacity_sku` to `F64` if you want Copilot-in-Fabric features.

---

## 3. Run it

```powershell
terraform init
terraform plan      # review what will be created
terraform apply     # type "yes"
```

---

## 4. What you get (start → finish)

| Step | File | Result |
|------|------|--------|
| Resource group | `main.tf` | `rg-hearst-fabric-cicd` |
| **Capacity** | `capacity.tf` | Existing capacity reused, or a new **F-SKU** capacity created |
| Identity | `identity.tf` | Service principal `sp-hearst-fabric-cicd` (least-privilege) |
| Key Vault | `keyvault.tf` | RBAC vault holding all secrets |
| Workspaces | `workspaces.tf` | **Hearst Fabric Dev / UAT / Prod**, bound to the capacity |
| Pipeline | `deployment_pipeline.tf` | **Hearst Fabric Release** (Dev → UAT → Prod stages) |
| **Example workload** | `example_workload.tf` | **Lakehouse + Warehouse + Notebook + Data Pipeline** in Dev |
| Outputs | `outputs.tf` | Workspace/pipeline/capacity IDs + example item IDs |

After apply, `terraform output` shows `capacity_mode` (created vs reused) and
`example_workload_item_ids`.

---

## 5. Optional add-ons

- **GitHub Git integration** (Dev workspace ↔ GitHub): set `enable_git_integration = true`
  after creating a Fabric Git ConfiguredConnection, then set `github_connection_id`.
- **Remote state** (team/CI): see `backend.tf` — uncomment the `azurerm` backend and
  re-run `terraform init` with the `-backend-config` flags.
- **Turn off the example workload:** `deploy_example_workload = false`.

---

## 6. Clean up

```powershell
terraform destroy
```

> A newly **created** capacity is billed while it exists — `terraform destroy`
> removes it. A **reused** existing capacity is left untouched.
