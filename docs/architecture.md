# Architecture — Hearst Fabric CI/CD Demo

This document provides an in-depth view of the architectural decisions, patterns, and design principles underlying the Hearst Microsoft Fabric CI/CD demo project.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Terraform vs. Content Split](#terraform-vs-content-split)
3. [Git Connection Strategy](#git-connection-strategy)
4. [Deployment Pipeline Architecture](#deployment-pipeline-architecture)
5. [End-to-End Change Flow](#end-to-end-change-flow)
6. [Authentication & Authorization Model](#authentication--authorization-model)
7. [Environment Parameterization](#environment-parameterization)
8. [Testing & Quality Gates](#testing--quality-gates)
9. [Secrets Management](#secrets-management)
10. [Known Limitations & Trade-offs](#known-limitations--trade-offs)

---

## Design Principles

### 1. Single Source of Truth
The **GitHub repository** (`main` branch) is the authoritative source for all Fabric content. The Dev workspace Git-sync mechanism ensures that Git → Dev is always unidirectional and deterministic.

### 2. Separation of Concerns
- **Infrastructure** (Terraform): Workspaces, pipeline, Git wiring, Key Vault, identity → slow-changing
- **Content** (Git + Deployment Pipeline): Notebooks, lakehouses, schemas → fast-changing
- **Orchestration** (GitHub Actions): CI/CD workflows that tie both together

### 3. Environment Isolation
UAT and Prod workspaces are **never Git-connected**. They receive content exclusively via the Fabric Deployment Pipeline, preventing two competing sources of truth (Git vs. manual edits) and ensuring all changes flow through the pipeline.

### 4. Automation-First
Manual steps are minimized. The only manual intervention point is the **Production approval gate**, reflecting real-world release governance.

### 5. Security by Design
All secrets are encrypted at rest and in transit. Service-principal authentication is preferred over user tokens for automation. Secrets live in Azure Key Vault (system of record) and GitHub Secrets (runtime mirror).

---

## Terraform vs. Content Split

Microsoft recommends separating **infrastructure provisioning** from **content authoring** to avoid Terraform drift on frequently-edited items.

| Terraform Manages | Git + Deployment Pipeline Manages |
|-------------------|----------------------------------|
| Workspaces (creation, capacity binding, role assignments) | Notebooks (code, dependencies) |
| Deployment pipeline (stages, bindings) | Lakehouses (metadata, schema definitions) |
| Git integration resource (Dev only) | Warehouses (T-SQL schema objects, views, procedures) |
| Key Vault + secrets | SQL Databases (tables, schemas, seed data) |
| Service principal (app registration, federated credential) | Deployment rules (parameterization) |

**Why this split?**
- **Terraform** excels at infrastructure-as-code for resources that change infrequently (e.g., creating a new workspace).
- **Fabric's Git sync + deployment pipeline** is purpose-built for iterative content changes (e.g., editing a notebook 50 times in a sprint).
- Attempting to manage notebook code via Terraform would require a `terraform apply` for every code edit, and Terraform would fight Fabric's native authoring tools.

**Key implication:** After Terraform provisions the infrastructure, **day-to-day work happens in Git and Fabric**. Terraform is run only when infrastructure changes (e.g., adding a new environment, rotating a secret, modifying workspace permissions).

---

## Git Connection Strategy

### Dev Workspace: Git-Connected
- The **Dev workspace** is connected to the GitHub repository via the `fabric_workspace_git` Terraform resource.
- Connection points to:
  - Repository: `<your-org>/hearst_cicd_fabric_demo`
  - Branch: `main`
  - Directory: `/fabric`
- Sync mode: **Explicit** (via `updateFromGit` API call triggered by GitHub Actions on merge to `main`).

**Why explicit sync?** Fabric supports auto-sync, but explicit sync gives deterministic control: the CD workflow knows exactly when Dev reflects the latest `main` commit, enabling safe downstream promotion.

### UAT & Prod Workspaces: NOT Git-Connected
- These workspaces have **no Git integration resource**.
- Content arrives exclusively via the **Fabric Deployment Pipeline**'s `deploy` API.
- This prevents:
  - **Competing sources of truth** (e.g., a user manually editing a notebook in UAT, then Git overwriting it)
  - **Drift** (UAT/Prod staying in sync with what was promoted, not what's in an arbitrary branch)

### Git Connection Resource Details
The `fabric_workspace_git` resource requires:
- A **Configured Connection** (created in Fabric Admin Portal or via API)
- A **GitHub PAT** or OAuth app (stored in Key Vault for rotation)
- The service principal must have permission to use Git integration APIs (tenant admin setting)

---

## Deployment Pipeline Architecture

The **Fabric Deployment Pipeline** is a first-class Fabric resource that manages multi-stage promotion.

### Pipeline Structure

```
Deployment Pipeline: "Hearst Fabric Release"
├─ Stage 0 (Development)  → workspace_id: <dev-ws-id>
├─ Stage 1 (UAT)          → workspace_id: <uat-ws-id>
└─ Stage 2 (Production)   → workspace_id: <prod-ws-id>
```

Each stage is bound to a workspace via the `fabric_deployment_pipeline_stage_workspace` resource in Terraform.

### Deployment Flow

1. **Deploy Dev → UAT:**
   - GitHub Actions calls `POST /deploymentPipelines/{id}/deploy`
   - Request body specifies:
     ```json
     {
       "sourceStageOrder": 0,
       "targetStageOrder": 1,
       "items": [/* optional: specific items */],
       "deploymentRules": [/* parameterization */]
     }
     ```
   - API returns a Long-Running Operation (LRO) URL
   - Workflow polls the LRO until `status: "Succeeded"`

2. **Deploy UAT → Prod:**
   - Same API call, but `sourceStageOrder: 1`, `targetStageOrder: 2`
   - **Gated by GitHub Environment protection rule** (manual approval required)

### Deployment Rules (Parameterization)
Deployment rules rewrite environment-specific bindings during promotion. Example:
- Dev lakehouse: `lh_hearst_bronze_dev`
- UAT lakehouse: `lh_hearst_bronze_uat`
- Prod lakehouse: `lh_hearst_bronze_prod`

Without deployment rules, a notebook in UAT would still reference the Dev lakehouse, causing failures.

The `set_deployment_rules.py` script configures these rules via the Deployment Pipeline API before each promotion.

### What Gets Deployed?
- **Metadata:** Notebook code, lakehouse definitions, warehouse schemas, SQL database objects, Power BI reports/datasets (if included).
- **NOT data:** Lakehouse tables (rows) and warehouse data are **not copied**. Each environment needs its own data seeding strategy (scripts, sample data loads, or Fabric shortcuts).

---

## End-to-End Change Flow

### Step-by-Step: From Code to Production

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Developer: Create feature branch, edit notebook, open PR          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CI Workflow (ci-validate.yml): Lint, validate, terraform plan    │
│    • nbqa/flake8/black on notebooks                                  │
│    • JSON schema validation on .platform files                       │
│    • terraform fmt -check / validate / plan                          │
│    → On failure: PR blocked; on success: reviewer approves + merges  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. CD-1 (cd-dev-sync.yml): Sync Dev workspace from main             │
│    • Acquire SP token (client-credentials flow)                      │
│    • POST /workspaces/{dev-ws-id}/git/updateFromGit                 │
│    • Poll LRO until complete                                         │
│    → Dev workspace now matches main                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CD-2 (cd-promote-uat.yml): Deploy Dev → UAT + run tests          │
│    • Call set_deployment_rules.py (apply UAT parameterization)       │
│    • POST /deploymentPipelines/{id}/deploy (source=Dev, target=UAT) │
│    • Poll LRO until deployed                                         │
│    • Call run_uat_tests.py (execute validation notebooks + SQL)     │
│    → On test failure: workflow fails, UAT deployment rolled back     │
│    → On test pass: UAT is stable, ready for Prod                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. CD-3 (cd-promote-prod.yml): Deploy UAT → Prod (manual gate)      │
│    • GitHub Environment "Production" requires approval               │
│    • Approver reviews UAT test results, clicks "Approve"             │
│    • Call set_deployment_rules.py (apply Prod parameterization)      │
│    • POST /deploymentPipelines/{id}/deploy (source=UAT, target=Prod)│
│    • Poll LRO until deployed                                         │
│    • Run smoke tests (basic connectivity, schema validation)         │
│    → Change is now live in Production                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Rollback Strategy
- **Dev:** Roll back Git to a previous commit, re-run `cd-dev-sync.yml`
- **UAT:** Re-deploy from a known-good Dev state (or from Prod if UAT is ahead)
- **Prod:** Re-deploy from UAT (which should always represent the last stable release)

**Best practice:** Tag releases in Git (`v1.0.0`, `v1.1.0`) so you can always re-deploy a specific version.

---

## Authentication & Authorization Model

### Service Principal (SP)
- **Created by Terraform** (`identity.tf`): Entra app registration + service principal
- **Client Secret:** Generated and stored in Azure Key Vault (never in code)
- **Optional OIDC (commented out in Terraform):** Federated credential for GitHub Actions (secretless auth)

### Permissions
The SP requires:
- **Fabric Admin API** delegated permissions (for Git and deployment pipeline operations)
- **Workspace Admin** role on Dev, UAT, and Prod workspaces (assigned via `fabric_workspace_role_assignment` in Terraform)
- **Key Vault Secrets User** role on the Key Vault (to read secrets)

### Token Acquisition
Workflows use `fabric_auth.py` to acquire a bearer token via OAuth 2.0 client-credentials flow:
```python
token = get_fabric_token(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["FABRIC_CLIENT_SECRET"],
)
```

Token is cached for the workflow duration and included in the `Authorization: Bearer <token>` header for all Fabric API calls.

### Least-Privilege Principle
- The SP has **only** the permissions needed for CI/CD (workspace admin, API access).
- It does **not** have subscription-level Azure RBAC roles (except the Terraform bootstrap identity, which is separate).
- GitHub Environment secrets are scoped to specific environments (Development, UAT, Production), not globally accessible.

---

## Environment Parameterization

Different environments often require different configuration values (e.g., lakehouse names, connection strings, data source paths). Fabric's **Deployment Rules** API enables per-stage parameterization.

### Example Deployment Rule
```json
{
  "deploymentRule": {
    "ruleType": "lakehouse",
    "sourceId": "<dev-lakehouse-item-id>",
    "targetId": "<uat-lakehouse-item-id>"
  }
}
```

When deploying Dev → UAT, this rule rewrites all references from the Dev lakehouse to the UAT lakehouse.

### Managed by `set_deployment_rules.py`
This script:
1. Reads environment-specific configuration (from a JSON file or environment variables)
2. Calls the `PATCH /deploymentPipelines/{id}/stages/{stageOrder}/deploymentRules` API
3. Applies rules for:
   - Lakehouses
   - Warehouses
   - SQL Databases
   - Data sources (connection strings)

**Best practice:** Store environment-specific config in `infra/environments/{dev,uat,prod}.json`, checked into Git (non-secret values) or fetched from Key Vault (secret values).

---

## Testing & Quality Gates

### CI (Pull Request Validation)
- **Linting:** `nbqa`, `flake8`, `black` for notebooks; `terraform fmt -check` for Terraform
- **Validation:** JSON schema validation for `.platform` files
- **Static analysis:** Optional: `bandit` for Python security issues, `hadolint` for Dockerfiles
- **Unit tests:** Run Python unit tests (if notebooks include testable functions)
- **Terraform plan:** Ensure infrastructure changes are valid

**Gate:** PR cannot merge until CI passes.

### UAT (Automated Testing Post-Deployment)
- **Validation notebooks:** Execute notebooks in UAT via the Fabric Jobs API; assert expected outputs
- **SQL assertions:** Run SQL scripts that check row counts, data types, constraints
- **Data quality checks:** Great Expectations, custom pytest checks (schema validation, null checks, range checks)

**Gate:** If UAT tests fail, the `cd-promote-uat.yml` workflow exits with failure, and Prod promotion is blocked.

### Prod (Smoke Tests)
- **Connectivity:** Verify the workspace is reachable, items are deployed
- **Schema validation:** Check that expected tables/views exist
- **No data validation:** Prod smoke tests are lightweight (no row-level checks)

---

## Secrets Management

All secrets follow a **dual-store model**: Azure Key Vault is the system of record; GitHub Secrets is the runtime mirror.

### Secret Lifecycle

1. **Creation:** Terraform generates the SP client secret → stores it in Key Vault (`fabric_sp_secret`)
2. **Mirror to GitHub:** Admin manually copies the secret to GitHub Environment Secrets (`FABRIC_CLIENT_SECRET`)
3. **Rotation:** the `rotate_sp_secret.sh` script regenerates the secret in Entra → updates Key Vault → updates GitHub Secrets
4. **Consumption:** Workflows read from GitHub Secrets (faster, integrated with Actions); Python scripts can read from Key Vault via the Azure SDK

### Encryption Guarantees

| Layer | At Rest | In Transit |
|-------|---------|-----------|
| Key Vault | AES-256, MS-managed keys (optional CMK) | TLS 1.2+ |
| GitHub Secrets | Libsodium sealed boxes | TLS; masked in logs |
| Terraform State | Azure Storage SSE | HTTPS-only; `sensitive = true` flags |

### Secret Scanning
- **Pre-commit hook:** `gitleaks` scans staged changes for secrets before commit
- **CI:** `gitleaks` runs on every PR to catch accidental leaks
- **Workflow logs:** GitHub Actions' `::add-mask::` command redacts secrets from logs

See [docs/secrets-handling.md](secrets-handling.md) for detailed procedures.

---

## Known Limitations & Trade-offs

### 1. Deployment Pipelines Move Metadata, Not Data
**Limitation:** Lakehouse tables (rows), warehouse data, and file content are not copied between stages.

**Workaround:** Each environment requires a data seeding strategy:
- **Dev:** Sample/synthetic data for testing
- **UAT:** Production-like data (anonymized if needed)
- **Prod:** Real production data

**Trade-off accepted:** This is a Fabric platform limitation, not a demo flaw.

### 2. SP Support Varies by Item Type
**Limitation:** Some Fabric item types (e.g., certain Power BI reports) may not fully support service-principal operations for Git or deployment.

**Workaround:** The demo focuses on notebooks, lakehouses, and warehouses (well-supported). If an item type fails, have a user-token fallback path.

### 3. Capacity Sharing for Demo
**Decision:** All three workspaces share the same Fabric capacity for simplicity.

**Trade-off:** In production, UAT and Prod should have isolated capacities for performance and cost control. The demo's shared-capacity model is acceptable for POC purposes.

### 4. Manual Approval Gate
**Decision:** Prod deployments require manual approval in GitHub.

**Trade-off:** Slows down the pipeline but reflects real-world governance. Fully automated Prod releases are possible but risky for a demo.

### 5. Terraform Provider Churn
**Risk:** The `microsoft/fabric` Terraform provider is in active development; breaking changes are possible.

**Mitigation:** Pin provider versions in `providers.tf`; test upgrades in a dev environment before applying to UAT/Prod.

### 6. Git Connection Requires Configured Connection
**Limitation:** The `fabric_workspace_git` resource needs a pre-existing `ConfiguredConnection` (created in Fabric Admin Portal or via API).

**Workaround:** The runbook includes a manual step to create the connection. Automating this is possible but adds complexity.

---

## Summary

This architecture balances **automation** (no manual portal clicks after setup), **governance** (manual Prod gate), and **simplicity** (focuses on core Fabric CI/CD patterns, not every edge case). It's designed to be:
- **Repeatable:** Terraform provisions everything; workflows are idempotent
- **Demonstrable:** Clear, linear flow from code change to Prod release
- **Extensible:** Add new environments (Pre-Prod), item types (Power BI), or testing strategies (performance tests) by following the established patterns

For operational details, see [runbook.md](runbook.md). For a live presentation walkthrough, see [demo-script.md](demo-script.md).
