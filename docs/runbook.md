# Operational Runbook — Hearst Fabric CI/CD Demo

This runbook provides step-by-step instructions for **setting up, operating, and troubleshooting** the Hearst Fabric CI/CD demo environment.

---

## Table of Contents

1. [Prerequisites Checklist](#prerequisites-checklist)
2. [Bootstrap: Repository & Azure Setup](#bootstrap-repository--azure-setup)
3. [Terraform Backend Configuration](#terraform-backend-configuration)
4. [Terraform Apply: Provision Infrastructure](#terraform-apply-provision-infrastructure)
5. [Create Fabric GitHub Connection](#create-fabric-github-connection)
6. [Initial Dev Git Sync](#initial-dev-git-sync)
7. [Configure GitHub Environment Protection](#configure-github-environment-protection)
8. [Running CI/CD Workflows](#running-cicd-workflows)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
10. [Rollback Procedures](#rollback-procedures)
11. [Secret Rotation](#secret-rotation)
12. [Teardown](#teardown)

---

## Prerequisites Checklist

Before proceeding, verify the following are in place:

### Azure & Fabric
- [ ] **Existing Fabric capacity** with available capacity units (F SKU or Trial)
  - Capture the `capacity_id` from Fabric Admin Portal → Capacity settings
- [ ] **Tenant admin settings enabled** in Fabric Admin Portal:
  - [ ] Service principals can use Fabric APIs
  - [ ] Service principals can access Git integration APIs
  - [ ] Users can create Fabric items
  - [ ] Git integration (for GitHub)
- [ ] **Bootstrap identity** with:
  - [ ] Azure subscription Contributor role
  - [ ] Permission to create Entra app registrations / service principals
  - [ ] Logged in via `az login`

### GitHub
- [ ] **GitHub repository** created: `<your-org>/hearst_cicd_fabric_demo`
- [ ] **GitHub PAT** (classic or fine-grained) with `repo` scope
- [ ] `gh` CLI installed and authenticated: `gh auth login`

### Local Tools
- [ ] Terraform CLI (`v1.5+`)
- [ ] Azure CLI (`az` version `2.50+`)
- [ ] Python 3.9+ (for helper scripts)
- [ ] Git (`git` version `2.30+`)

---

## Bootstrap: Repository & Azure Setup

### 1. Clone the Repository
```powershell
git clone https://github.com/<your-org>/hearst_cicd_fabric_demo.git
cd hearst_cicd_fabric_demo
```

### 2. Create Azure Resource Group for Terraform State
```powershell
$stateRg = "rg-fabric-cicd-state"
$stateSa = "tfstatefabriccicd"  # Must be globally unique; adjust if needed
$location = "eastus"

az group create --name $stateRg --location $location

az storage account create `
  --name $stateSa `
  --resource-group $stateRg `
  --location $location `
  --sku Standard_LRS `
  --encryption-services blob

az storage container create `
  --name tfstate `
  --account-name $stateSa
```

### 3. Retrieve Storage Account Key (for backend config)
```powershell
az storage account keys list `
  --resource-group $stateRg `
  --account-name $stateSa `
  --query "[0].value" -o tsv
```
Save this key securely; you'll use it in the next step.

---

## Terraform Backend Configuration

### 1. Update `infra/backend.tf`
Edit `infra/backend.tf` and replace placeholders with your values:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-fabric-cicd-state"
    storage_account_name = "tfstatefabriccicd"  # Your storage account
    container_name       = "tfstate"
    key                  = "hearst-fabric-cicd.tfstate"
  }
}
```

### 2. Initialize Terraform Backend
```powershell
cd infra
terraform init `
  -backend-config="access_key=<storage-account-key>"
```

> **Note:** Alternatively, use `az login` with a managed identity or SP that has access to the storage account, and omit the `access_key` flag.

---

## Terraform Apply: Provision Infrastructure

### 1. Create `terraform.tfvars` (Do NOT commit this file!)
```powershell
# infra/terraform.tfvars
tenant_id    = "<your-entra-tenant-id>"
capacity_id  = "<your-fabric-capacity-id>"
github_repo  = "<your-org>/hearst_cicd_fabric_demo"
github_pat   = "<your-github-pat>"

# Optional: override default names
workspace_prefix = "Hearst Fabric"
pipeline_name    = "Hearst Fabric Release"
```

Add `terraform.tfvars` to `.gitignore`:
```powershell
echo "*.tfvars" >> ..\.gitignore
```

### 2. Plan Terraform Changes
```powershell
terraform plan -out=tfplan
```

Review the plan output. Expect to see:
- 3 workspaces (Dev, UAT, Prod)
- 1 deployment pipeline with 3 stages
- 1 Key Vault + secrets
- 1 service principal + client secret
- 1 Git integration resource (Dev only)
- Role assignments

### 3. Apply Terraform
```powershell
terraform apply tfplan
```

> ⏱ **Duration:** 3-5 minutes

### 4. Capture Terraform Outputs
```powershell
terraform output -json > outputs.json
```

Key outputs (you'll need these for GitHub secrets and workflows):
- `dev_workspace_id`
- `uat_workspace_id`
- `prod_workspace_id`
- `deployment_pipeline_id`
- `dev_stage_id`, `uat_stage_id`, `prod_stage_id`
- `service_principal_client_id`
- `service_principal_tenant_id`
- `keyvault_uri`
- `fabric_sp_secret` (marked as sensitive; retrieve separately)

### 5. Retrieve the Service Principal Secret
```powershell
# From Key Vault
$secretName = "fabric-sp-secret"
$kvName = terraform output -raw keyvault_name

az keyvault secret show `
  --vault-name $kvName `
  --name $secretName `
  --query "value" -o tsv
```

**⚠️ Store this securely** — you'll add it to GitHub Secrets in step 7.

---

## Create Fabric GitHub Connection

Fabric requires a **Configured Connection** to link the Dev workspace to GitHub.

### Option A: Manual (Fabric Admin Portal)
1. Navigate to **Fabric Admin Portal** → **Git integrations**
2. Click **+ New connection**
3. Select **GitHub**, provide:
   - Connection name: `GitHub-HearstDemo`
   - GitHub PAT (the one you created in prerequisites)
4. Save the connection
5. Note the **connection ID** (visible in the URL or API response)

### Option B: API-Driven (Advanced)
```powershell
# Call the Fabric Git Connections API to create a connection
# (Requires bearer token with admin permissions)
# Example script: scripts/create_git_connection.py
python scripts/create_git_connection.py `
  --name "GitHub-HearstDemo" `
  --pat $env:GITHUB_PAT
```

### Verify Git Connection in Dev Workspace
1. Open the **Dev workspace** in Fabric Portal
2. Go to **Workspace Settings → Git integration**
3. You should see:
   - Connected to: `<your-org>/hearst_cicd_fabric_demo`
   - Branch: `main`
   - Directory: `/fabric`

If the connection is missing, re-run Terraform or manually link it in the portal.

---

## Initial Dev Git Sync

After Terraform creates the Git integration, the Dev workspace needs an initial sync to pull content from the repo.

### Option 1: Manual Sync (Fabric Portal)
1. In Dev workspace → **Git integration** → Click **Update from Git**
2. Wait for sync to complete (~30 seconds)
3. Verify items appear in the workspace (notebooks, lakehouse, warehouse, SQL database)

### Option 2: API-Driven Sync
```powershell
cd scripts
python update_from_git.py `
  --workspace-id (terraform output -raw dev_workspace_id) `
  --tenant-id $env:AZURE_TENANT_ID `
  --client-id (terraform output -raw service_principal_client_id) `
  --client-secret $env:FABRIC_CLIENT_SECRET
```

> **Note:** If the `/fabric` folder is empty initially, seed the Dev workspace manually (create sample items), then commit them to Git from Dev. This populates the repo, which can then be synced in future workflow runs.

---

## Configure GitHub Environment Protection

GitHub Environments enable secret scoping and manual approval gates.

### 1. Create GitHub Environments
```powershell
gh api -X PUT /repos/<your-org>/hearst_cicd_fabric_demo/environments/Development
gh api -X PUT /repos/<your-org>/hearst_cicd_fabric_demo/environments/UAT
gh api -X PUT /repos/<your-org>/hearst_cicd_fabric_demo/environments/Production
```

### 2. Add Secrets to Each Environment
```powershell
# Development
gh secret set AZURE_TENANT_ID --env Development --body "<tenant-id>"
gh secret set AZURE_CLIENT_ID --env Development --body "<client-id>"
gh secret set FABRIC_CLIENT_SECRET --env Development --body "<secret>"
gh secret set DEV_WORKSPACE_ID --env Development --body "<dev-ws-id>"

# UAT
gh secret set AZURE_TENANT_ID --env UAT --body "<tenant-id>"
gh secret set AZURE_CLIENT_ID --env UAT --body "<client-id>"
gh secret set FABRIC_CLIENT_SECRET --env UAT --body "<secret>"
gh secret set UAT_WORKSPACE_ID --env UAT --body "<uat-ws-id>"
gh secret set DEPLOYMENT_PIPELINE_ID --env UAT --body "<pipeline-id>"

# Production
gh secret set AZURE_TENANT_ID --env Production --body "<tenant-id>"
gh secret set AZURE_CLIENT_ID --env Production --body "<client-id>"
gh secret set FABRIC_CLIENT_SECRET --env Production --body "<secret>"
gh secret set PROD_WORKSPACE_ID --env Production --body "<prod-ws-id>"
gh secret set DEPLOYMENT_PIPELINE_ID --env Production --body "<pipeline-id>"
```

### 3. Configure Production Approval Gate (Manual via GitHub UI)
1. Go to **GitHub repo → Settings → Environments → Production**
2. Under **Deployment protection rules**, check **Required reviewers**
3. Add yourself (or a designated approver)
4. Save

> **Result:** The `cd-promote-prod.yml` workflow will pause before deploying to Prod, requiring manual approval.

---

## Running CI/CD Workflows

### Workflow 1: `ci-validate.yml` (Pull Request Validation)
**Trigger:** Opened/updated PR

**What it does:**
- Lints notebooks (`nbqa`, `flake8`, `black`)
- Validates `.platform` JSON files (schema checks)
- Runs `terraform fmt -check`, `terraform validate`, `terraform plan`

**How to run:**
1. Create a branch: `git checkout -b feature/my-change`
2. Edit a notebook or Terraform file
3. Commit and push: `git push -u origin feature/my-change`
4. Open a PR in GitHub
5. CI runs automatically; check the Actions tab

**On failure:** Fix issues, push again. PR cannot merge until CI passes.

---

### Workflow 2: `cd-dev-sync.yml` (Dev Sync on Merge)
**Trigger:** Merge to `main`

**What it does:**
- Acquires SP token
- Calls `POST /workspaces/{dev-ws-id}/git/updateFromGit`
- Polls LRO until sync completes
- Logs success/failure

**How to run:**
- Merge a PR to `main` → workflow auto-triggers
- **Manual trigger:** Go to **Actions → cd-dev-sync → Run workflow**

**Expected output:**
```
✅ Dev workspace synced from main at commit <sha>
```

---

### Workflow 3: `cd-promote-uat.yml` (Deploy Dev → UAT + Tests)
**Trigger:** Manual (`workflow_dispatch`) or chained after `cd-dev-sync`

**What it does:**
1. Calls `set_deployment_rules.py` (apply UAT parameterization)
2. Calls `POST /deploymentPipelines/{id}/deploy` (Dev → UAT)
3. Polls LRO until deployed
4. Runs `run_uat_tests.py` (validation notebooks + SQL assertions)
5. Fails workflow if tests fail

**How to run:**
```powershell
gh workflow run cd-promote-uat.yml
```

Or: Configure `cd-dev-sync.yml` to trigger this workflow on success (uncomment the `workflow_dispatch` call).

**Expected output:**
```
✅ Deployed Dev → UAT (deployment ID: <id>)
✅ UAT tests passed (12/12)
```

**On test failure:**
- Workflow exits with error code 1
- Review test logs in Actions tab
- Fix issues in a new branch → repeat CI/CD cycle

---

### Workflow 4: `cd-promote-prod.yml` (Deploy UAT → Prod, Gated)
**Trigger:** Manual (`workflow_dispatch`)

**What it does:**
1. Pauses for manual approval (GitHub Environment gate)
2. Calls `set_deployment_rules.py` (apply Prod parameterization)
3. Calls `POST /deploymentPipelines/{id}/deploy` (UAT → Prod)
4. Polls LRO until deployed
5. Runs smoke tests (connectivity, schema validation)

**How to run:**
```powershell
gh workflow run cd-promote-prod.yml
```

**Approval step:**
1. Workflow pauses with status "Waiting for approval"
2. Approver receives notification (if configured)
3. Go to **Actions → workflow run → Review deployments**
4. Click **Approve and deploy** or **Reject**

**Expected output:**
```
✅ Deployed UAT → Prod (deployment ID: <id>)
✅ Prod smoke tests passed
```

---

## Monitoring & Troubleshooting

### Common Issues

#### Issue: `updateFromGit` API returns 403 Forbidden
**Cause:** Tenant admin setting "Service principals can access Git integration APIs" is disabled.

**Fix:**
1. Go to **Fabric Admin Portal → Tenant settings**
2. Enable the setting
3. Wait 5-10 minutes for propagation
4. Re-run workflow

---

#### Issue: Deployment pipeline stage shows "No items to deploy"
**Cause:** Dev workspace is empty, or items were not committed to Git.

**Fix:**
1. Open Dev workspace in Fabric Portal
2. Create sample items (notebook, lakehouse)
3. Go to **Git integration → Commit to Git**
4. Push to `main`
5. Re-run `cd-dev-sync.yml` → then retry promotion

---

#### Issue: UAT tests fail with "Table not found"
**Cause:** Deployment pipeline moves metadata, not data. UAT warehouse/lakehouse has no tables/rows.

**Fix:**
- Seed UAT with sample data using a script (e.g., `seed_uat_data.py`)
- Or: Create a Fabric shortcut from UAT lakehouse to a shared data source

---

#### Issue: GitHub Actions shows "Secret not found"
**Cause:** Environment secret is missing or scoped to wrong environment.

**Fix:**
```powershell
gh secret set FABRIC_CLIENT_SECRET --env UAT --body "<secret>"
```

Verify with:
```powershell
gh secret list --env UAT
```

---

#### Issue: Terraform apply fails with "Capacity not found"
**Cause:** `capacity_id` in `terraform.tfvars` is incorrect or the capacity doesn't exist.

**Fix:**
1. Go to **Fabric Admin Portal → Capacity settings**
2. Copy the correct `capacity_id` (a GUID)
3. Update `terraform.tfvars`
4. Re-run `terraform apply`

---

### Logs & Diagnostics

#### View Fabric API Logs
- **Dev workspace logs:** Fabric Portal → Dev workspace → **Settings → Activity log**
- **Deployment pipeline logs:** Fabric Portal → Deployment pipeline → **Deployment history**

#### View GitHub Actions Logs
```powershell
gh run list --workflow=cd-promote-uat.yml --limit 5
gh run view <run-id> --log
```

#### Enable Workflow Debug Logging
1. Go to **GitHub repo → Settings → Secrets → Actions**
2. Add secret: `ACTIONS_RUNNER_DEBUG` = `true`
3. Re-run workflow → detailed logs appear

---

## Rollback Procedures

### Rollback Dev
**Scenario:** A bad change was synced to Dev.

**Steps:**
1. Revert the Git commit:
   ```powershell
   git revert <bad-commit-sha>
   git push origin main
   ```
2. Re-run `cd-dev-sync.yml` → Dev syncs to the reverted state

---

### Rollback UAT
**Scenario:** A bad deployment reached UAT.

**Steps:**
1. Revert Git to a known-good commit:
   ```powershell
   git revert <bad-commit-sha>
   git push origin main
   ```
2. Sync Dev (`cd-dev-sync.yml`)
3. Re-deploy Dev → UAT (`cd-promote-uat.yml`)

**Alternative (faster):**
- Manually re-deploy a previous known-good stage (if you tagged Git commits by release version)

---

### Rollback Prod
**Scenario:** A bad deployment reached Prod.

**Steps:**
1. Revert Git to the last stable release tag:
   ```powershell
   git checkout v1.2.0  # Last known-good release
   git checkout -b hotfix/rollback-prod
   git push origin hotfix/rollback-prod
   ```
2. Merge hotfix to `main`
3. Sync Dev (`cd-dev-sync.yml`)
4. Deploy Dev → UAT (`cd-promote-uat.yml`)
5. Deploy UAT → Prod (`cd-promote-prod.yml` with approval)

**Emergency bypass (not recommended):**
- Manually export a backup of the last stable Prod workspace items (via Fabric API or portal)
- Import them back into Prod

---

## Secret Rotation

Service-principal secrets should be rotated periodically (every 90-180 days).

### Automated Rotation
```powershell
cd scripts
./rotate_sp_secret.ps1 `
  -TenantId <tenant-id> `
  -ClientId <client-id> `
  -KeyVaultName <kv-name>
```

**What it does:**
1. Generates a new client secret in Entra
2. Updates Key Vault with the new secret
3. Updates GitHub Environment secrets via `gh` CLI
4. (Optionally) revokes the old secret after a grace period

**Manual steps:**
1. Go to **Entra Admin Center → App registrations → <SP> → Certificates & secrets**
2. Add a new client secret
3. Update Key Vault:
   ```powershell
   az keyvault secret set `
     --vault-name <kv-name> `
     --name fabric-sp-secret `
     --value "<new-secret>"
   ```
4. Update GitHub secrets:
   ```powershell
   gh secret set FABRIC_CLIENT_SECRET --env Development --body "<new-secret>"
   gh secret set FABRIC_CLIENT_SECRET --env UAT --body "<new-secret>"
   gh secret set FABRIC_CLIENT_SECRET --env Production --body "<new-secret>"
   ```
5. Test a workflow run to verify the new secret works
6. Delete the old secret from Entra (after 24-48 hours)

---

## Teardown

To completely remove the demo environment:

### 1. Delete Fabric Workspaces (Optional)
```powershell
# Terraform destroy will remove workspace metadata, but not the workspace itself if manually created
# Manually delete via Fabric Portal if needed
```

### 2. Terraform Destroy
```powershell
cd infra
terraform destroy -var="capacity_id=<id>" -var="github_pat=<pat>"
```

> ⚠️ **Warning:** This deletes the service principal, Key Vault, and all Terraform-managed resources. Fabric workspaces may need manual deletion.

### 3. Delete Terraform State Storage (Optional)
```powershell
az storage container delete --name tfstate --account-name tfstatefabriccicd
az storage account delete --name tfstatefabriccicd --resource-group rg-fabric-cicd-state
az group delete --name rg-fabric-cicd-state --yes
```

### 4. Revoke GitHub PAT
1. Go to **GitHub → Settings → Developer settings → Personal access tokens**
2. Revoke the PAT used for Fabric Git integration

### 5. Delete GitHub Environment Secrets
```powershell
gh secret delete FABRIC_CLIENT_SECRET --env Development
gh secret delete FABRIC_CLIENT_SECRET --env UAT
gh secret delete FABRIC_CLIENT_SECRET --env Production
```

---

## Summary

This runbook covers the complete lifecycle:
- **Setup:** Bootstrap → Terraform → Git connection → GitHub secrets
- **Operations:** Run workflows, monitor logs, troubleshoot issues
- **Maintenance:** Rotate secrets, roll back bad deployments
- **Teardown:** Clean up all resources

For architectural context, see [architecture.md](architecture.md). For a live demo walkthrough, see [demo-script.md](demo-script.md).
