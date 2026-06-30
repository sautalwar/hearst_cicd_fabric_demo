# Hearst — Microsoft Fabric CI/CD

**A self-contained, automated CI/CD pipeline for Microsoft Fabric — provisioned with Terraform and orchestrated with GitHub Actions, promoting changes from Dev → UAT → Production through a native Fabric Deployment Pipeline.**

You fill in a few values, run one command, and Terraform builds the entire environment — the Fabric capacity, three workspaces, the deployment pipeline, the security identity and secret store, and an example workload — then GitHub Actions promotes any change from Dev to Production automatically.

---

## Quickstart (one command)

```powershell
cd infra
cp terraform.tfvars.example terraform.tfvars   # fill in subscription, tenant, admin object id, Key Vault name
./deploy.ps1                                    # plan only (creates nothing) — auto-fills params, writes a run report
./deploy.ps1 -Apply                             # create the resources after reviewing the plan
```

`deploy.ps1` signs you in (Azure CLI), auto-derives the mandatory parameters from your session, prompts only for anything missing, applies sensible defaults for the rest, runs `init → validate → plan`, and generates `infra/run-report.html` showing exactly what it will build. You never choose which `.tf` file runs first — Terraform orders the whole module automatically.

> **Full setup guide:** see **[infra/SETUP.md](infra/SETUP.md)**.

---

## What gets deployed

| Layer | Resources |
|-------|-----------|
| Foundation | Azure resource group |
| Identity | Entra service principal (least-privilege Fabric/Power BI roles) + client secret |
| Secrets | Azure Key Vault (RBAC, purge protection) holding all credentials |
| **Capacity** | **Reuses an existing Fabric capacity** if you name one, or **creates a new F-SKU capacity** (default **F2**, the minimum for this workload) |
| Workspaces | **Dev / UAT / Prod** workspaces, bound to the capacity |
| Pipeline | Native Fabric **Deployment Pipeline** (Dev → UAT → Prod) |
| Example workload | A **Lakehouse, Warehouse, Notebook, and Data Pipeline** so you see real items created end-to-end |

A first `terraform apply` is fully self-contained: Git integration is **off by default** and state is **local by default**, so you can clone and run immediately.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     GitHub (Single Source of Truth)                       │
│                       main branch → /fabric folder                        │
└──────────┬───────────────────────────────┬───────────────────────────────┘
           │ CI (PR)                        │ CD (merge to main)
           │ • lint notebooks               │ • updateFromGit → Dev
           │ • validate Fabric items        │ • deploy Dev → UAT (+ tests)
           │ • terraform plan               │ • deploy UAT → Prod (manual gate)
           ▼                                ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │           Fabric Deployment Pipeline: "Hearst Fabric Release"            │
  ├──────────────────────┬──────────────────────┬─────────────────────────┤
  │  Stage 1: DEV WS     │  Stage 2: UAT WS     │  Stage 3: PROD WS        │
  │  (Git-connected)     │  (deploy target)     │  (deploy target, gated)  │
  └──────────────────────┴──────────────────────┴─────────────────────────┘
                          ▲
       Terraform provisions: capacity · workspaces · pipeline · Git wiring · Key Vault · identity
```

**Division of responsibility**
- **Terraform (`infra/`)** — slow-changing infrastructure (capacity, workspaces, pipeline, Git wiring, Key Vault, identity).
- **Git + Deployment Pipeline (`fabric/`)** — fast-changing content (notebooks, lakehouses, warehouse/SQL schemas, semantic model).
- **GitHub Actions (`.github/workflows/`)** — orchestration (CI validation, sync, promote, test).

**Key principle:** only the Dev workspace is Git-connected. UAT and Prod receive content exclusively through the Deployment Pipeline — a single source of truth, no environment drift.

---

## How a change promotes itself

1. A developer edits a notebook or schema and opens a **Pull Request** → **CI** lints, validates Fabric items, runs semantic-model best-practice checks, runs `terraform plan`, and scans for secrets.
2. The PR is merged to `main` → **Dev** syncs via `updateFromGit`.
3. **Dev → UAT** deploys through the pipeline and runs the **automated test suite**.
4. **UAT → Prod** deploys behind a **manual approval gate** in GitHub.
5. The change is live in Production, fully traceable to the commit.

---

## Repository structure

```
hearst_cicd_fabric_demo/
├─ infra/                          # Terraform (one module, applied in dependency order)
│  ├─ deploy.ps1                   # one-command orchestrator (init → validate → plan/apply + report)
│  ├─ SETUP.md                     # step-by-step setup guide
│  ├─ providers.tf / backend.tf    # providers (azurerm/fabric/azuread) + local-state default
│  ├─ identity.tf / keyvault.tf    # service principal + Key Vault + secrets
│  ├─ capacity.tf                  # reuse-or-create F-SKU capacity
│  ├─ workspaces.tf                # Dev/UAT/Prod workspaces + role assignments
│  ├─ deployment_pipeline.tf       # Fabric Deployment Pipeline (3 stages)
│  ├─ git_integration.tf           # Dev-only Git connection (optional)
│  ├─ example_workload.tf          # example lakehouse/warehouse/notebook/pipeline
│  └─ variables.tf / outputs.tf / terraform.tfvars.example
│
├─ fabric/                         # Fabric items (Git-synced from the Dev workspace)
│  ├─ nb_hearst_bronze_ingest / silver_transform / gold_build .Notebook
│  ├─ lh_hearst_bronze / lh_hearst_gold .Lakehouse
│  ├─ wh_hearst.Warehouse / sqldb_hearst.SQLDatabase
│  ├─ sm_hearst_audience.SemanticModel / rpt_hearst_exec.Report
│  └─ agent_hearst_analytics.DataAgent
│
├─ scripts/                        # Python automation + tf_run_report.ps1
├─ tests/                          # data quality, SQL assertions, semantic-model BPA, DAX
├─ docs/                           # architecture, runbook, demo script, secrets handling
├─ .github/workflows/              # ci-validate, cd-dev-sync, cd-promote-uat, cd-promote-prod
└─ data/                           # synthetic data generator
```

---

## Prerequisites

- An **Azure subscription** + permission to create a resource group, Key Vault, and a Fabric capacity.
- Permission to **create an Entra app registration / service principal**.
- A **Microsoft Fabric tenant** with *Service principals can use Fabric APIs* and *Users can create Fabric items* enabled.
- **Register the resource providers once** (auto-registration is disabled for speed):
  `az provider register --namespace Microsoft.Fabric` and `--namespace Microsoft.KeyVault`.
- Tooling: **Terraform ≥ 1.6** and **Azure CLI** (`az login`).

---

## Security & secrets

| Store | Encryption at rest | In transit |
|-------|-------------------|------------|
| Azure Key Vault (system of record) | AES-256 (MS-managed keys) | TLS 1.2+ |
| Terraform state | SSE (Azure Storage) when remote backend is enabled | HTTPS-only |
| GitHub Environment Secrets | Encrypted (libsodium) | TLS; masked in logs |

- No plaintext secrets in code, logs, or committed files; `.gitignore` blocks `*.tfvars`, `.env`, plan files.
- CI runs **gitleaks**; workflows mask tokens; the service principal has **least-privilege** roles.

---

## Testing

This package was verified with a **live `terraform plan`** against a real tenant — **25 resources planned, 0 errors** — plus `terraform validate` and `tflint` (clean). A plan creates nothing, so the full graph is proven with zero footprint. See **[hearst_e2e_test_report.html](hearst_e2e_test_report.html)** and **[infra/run-report.html](infra/run-report.html)**.

---

## Key gotchas

1. **Deployment pipelines move metadata, not data** — each environment needs its own data seeding.
2. **Dev-only Git connection** — UAT and Prod are never Git-connected; they receive content only via the pipeline.
3. **Tenant admin settings are mandatory** — without them, service-principal automation fails silently.
4. **A newly created F-SKU capacity is billable** while it exists; `terraform destroy` removes it (an existing capacity you reuse is left untouched).
5. **Provider versions are pinned** in `providers.tf` to keep builds reproducible.

---

## Documentation

- **[infra/SETUP.md](infra/SETUP.md)** — one-command setup, parameters, what gets created.
- **[docs/architecture.md](docs/architecture.md)** — detailed design and change flow.
- **[docs/runbook.md](docs/runbook.md)** — operations, setup, rollback.
- **[docs/demo-script.md](docs/demo-script.md)** — click-by-click walkthrough.
- **[docs/secrets-handling.md](docs/secrets-handling.md)** — secret encryption and rotation.

---

## License

MIT License (or as per your organization's policy).
