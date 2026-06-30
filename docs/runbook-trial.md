# Fabric TRIAL Runbook — Hearst Approach A Demo

**Complete step-by-step guide to deploy the Hearst Approach A demo (medallion + Direct Lake semantic model + report + data agent) on a Microsoft Fabric TRIAL capacity.**

Use this runbook when:
- You have a **Fabric TRIAL** (no paid capacity)
- You're doing a live demo or POC walkthrough
- You need a **greenfield** setup from scratch

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Start Fabric Trial](#phase-1-start-fabric-trial)
3. [Phase 2: Create Workspaces](#phase-2-create-workspaces)
4. [Phase 3: Connect Dev Workspace to GitHub](#phase-3-connect-dev-workspace-to-github)
5. [Phase 4: Commit & Sync Fabric Items](#phase-4-commit--sync-fabric-items)
6. [Phase 5: Run Medallion Notebooks](#phase-5-run-medallion-notebooks)
7. [Phase 6: Finalize Direct Lake Semantic Model](#phase-6-finalize-direct-lake-semantic-model)
8. [Phase 7: Publish Report & Enable Data Agent](#phase-7-publish-report--enable-data-agent)
9. [Phase 8: Create Deployment Pipeline](#phase-8-create-deployment-pipeline)
10. [Phase 9: Configure Deployment Rules](#phase-9-configure-deployment-rules)
11. [Phase 10: Promote Dev → UAT → Prod](#phase-10-promote-dev--uat--prod)
12. [Phase 11: Rollback & Troubleshooting](#phase-11-rollback--troubleshooting)
13. [Appendix: Manual Finalize Points](#appendix-manual-finalize-points)

---

## Prerequisites

### Required Accounts & Tools
- [ ] **Microsoft Account** with Fabric trial access (or M365 tenant admin rights)
- [ ] **GitHub Account** with a repository to host the demo code
- [ ] **GitHub Personal Access Token (PAT)** with `repo` scope
- [ ] **Power BI Desktop** (latest version) installed locally
- [ ] **Python 3.9+** installed (for local scripts)
- [ ] **Azure CLI** (`az`) installed and authenticated (optional, for scripting)
- [ ] **GitHub CLI** (`gh`) installed and authenticated (optional, for secrets)

### Fabric Trial Checklist
- [ ] No existing Fabric capacity required (trial capacity will be auto-provisioned)
- [ ] User must have **capacity admin** or **workspace admin** rights in the trial
- [ ] Tenant settings must allow:
  - [ ] Users can create Fabric items
  - [ ] Git integration enabled
  - [ ] Service principals can use Fabric APIs (for CI/CD automation)

---

## Phase 1: Start Fabric Trial

### Step 1.1: Activate Fabric Trial

1. Navigate to [Microsoft Fabric](https://app.fabric.microsoft.com)
2. Sign in with your Microsoft account
3. If prompted, click **Start Trial** (60-day free trial, Fabric capacity equivalent to F64)
4. Accept terms and conditions
5. Wait ~2 minutes for trial provisioning

**Verification:**
- In the Fabric portal, click the ⚙️ icon (top-right) → **Settings** → **Fabric Capacity**
- You should see a capacity named **Trial** with status **Active**

> ⚠️ **Trial limitations:**  
> - 60 days max duration  
> - Cannot add additional capacity units  
> - No SLA or dedicated support  
> - Sufficient for demos up to ~100GB OneLake storage

---

## Phase 2: Create Workspaces

You need **three workspaces** to simulate a Dev → UAT → Prod pipeline:
- **ws_hearst_dev** — Git-connected, developer workspace
- **ws_hearst_uat** — Deployment target for testing
- **ws_hearst_prod** — Production workspace (final stage)

### Step 2.1: Create Dev Workspace

1. In Fabric portal, click **Workspaces** (left nav) → **+ New workspace**
2. Name: `ws_hearst_dev`
3. Description: `Hearst Approach A — Dev (Git-connected)`
4. Advanced settings:
   - License mode: **Trial** (or select your trial capacity)
   - Contributors: Add yourself as **Admin**
5. Click **Apply**

### Step 2.2: Create UAT Workspace

Repeat the above steps:
- Name: `ws_hearst_uat`
- Description: `Hearst Approach A — UAT (deployment target)`
- License mode: **Trial**

### Step 2.3: Create Prod Workspace

Repeat the above steps:
- Name: `ws_hearst_prod`
- Description: `Hearst Approach A — Production`
- License mode: **Trial**

**Verification:**
- You should see all three workspaces listed in the **Workspaces** pane
- Each workspace should show **Trial** badge

> **Alternative (Terraform):**  
> If you prefer Infrastructure-as-Code, run:
> ```powershell
> cd infra
> terraform init
> terraform apply -var="capacity_id=<your-trial-capacity-id>"
> ```
> This will create workspaces, deployment pipeline, and Git integration automatically.  
> For a manual walkthrough, continue below.

---

## Phase 3: Connect Dev Workspace to GitHub

### Step 3.1: Prepare GitHub Repository

1. Fork or clone the Hearst demo repository:
   ```bash
   git clone https://github.com/<your-org>/hearst_cicd_fabric_demo.git
   cd hearst_cicd_fabric_demo
   ```

2. Ensure the `fabric/` folder contains the following items:
   - `nb_hearst_bronze_ingest.Notebook/`
   - `nb_hearst_silver_transform.Notebook/`
   - `nb_hearst_gold_build.Notebook/`
   - `lh_hearst_bronze.Lakehouse/`
   - `lh_hearst_gold.Lakehouse/`
   - `sm_hearst_audience.SemanticModel/`
   - `rpt_hearst_exec.Report/`
   - `agent_hearst_analytics.DataAgent/`

3. Commit and push to `main` branch if not already present

### Step 3.2: Generate GitHub Personal Access Token (PAT)

1. Go to [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Click **Generate new token** (classic)
3. Scopes: Select **`repo`** (full control of private repositories)
4. Expiration: Set to 90 days (or custom)
5. Click **Generate token**
6. **Copy the token** — you'll need it in the next step (it's shown only once!)

### Step 3.3: Connect Dev Workspace to Git

1. In Fabric portal, open workspace **ws_hearst_dev**
2. Click **Workspace settings** (⚙️ icon in top-right)
3. Select **Git integration** (left sidebar)
4. Click **Connect**
5. Fill in:
   - **Source control**: GitHub
   - **Organization**: Your GitHub username or org
   - **Repository**: `hearst_cicd_fabric_demo`
   - **Branch**: `main`
   - **Folder**: `/fabric` (this is critical!)
   - **Authentication**: Paste your GitHub PAT
6. Click **Connect**

**Verification:**
- You should see **Git status: Connected** with a green checkmark
- The **Source control** pane shows the `main` branch and `/fabric` directory

> ⚠️ **Common pitfall:** If you omit `/fabric` as the folder, Fabric will try to sync the entire repo (including infra/, tests/, etc.), which will fail.

---

## Phase 4: Commit & Sync Fabric Items

### Step 4.1: Initial Sync from Git

1. In the Dev workspace, click **Source control** (left nav)
2. You should see a message: **"Your workspace is out of sync with Git"**
3. Click **Update all** (or **Update from Git**)
4. Fabric will pull all items from the `/fabric` folder
5. Wait ~2-5 minutes for sync to complete

**Verification:**
- Refresh the workspace — you should see:
  - 📘 3 Notebooks (bronze ingest, silver transform, gold build)
  - 🏠 2 Lakehouses (lh_hearst_bronze, lh_hearst_gold)
  - 📊 1 Semantic Model (sm_hearst_audience)
  - 📈 1 Report (rpt_hearst_exec)
  - 🤖 1 Data Agent (agent_hearst_analytics)

> **Fallback:** If Git sync fails (e.g., missing PAT permissions), manually create items in the Fabric UI:
> 1. Manually upload notebook `.py` files as new Notebooks
> 2. Create lakehouses manually (New → Lakehouse → name: `lh_hearst_bronze`, `lh_hearst_gold`)
> 3. Semantic model and report will need Power BI Desktop (see Phase 6)

---

## Phase 5: Run Medallion Notebooks

The medallion architecture requires **sequential execution** of three notebooks to build the gold star schema.

### Step 5.1: Run Bronze Ingest Notebook

1. In Dev workspace, open **nb_hearst_bronze_ingest**
2. Click **Run all** (▶️ icon)
3. Wait ~5-10 minutes for execution
4. **Expected output:**
   - 4 Delta tables created in `lh_hearst_bronze`:
     - `bronze.raw_engagement` (~500K rows)
     - `bronze.raw_subscriptions` (~50K rows)
     - `bronze.raw_ad_impressions` (~100K rows)
     - `bronze.raw_content` (~2K rows)

**Verification:**
- Open lakehouse `lh_hearst_bronze` → **Tables** pane
- Confirm all 4 tables exist with expected row counts
- SQL query test:
  ```sql
  SELECT COUNT(*) FROM bronze.raw_engagement;
  -- Expected: ~500,000
  ```

> **Fallback:** If the notebook fails with "lakehouse not found" error:
> - Manually create `lh_hearst_bronze` lakehouse in the workspace
> - Re-run the notebook

### Step 5.2: Run Silver Transform Notebook

1. In Dev workspace, open **nb_hearst_silver_transform**
2. Click **Run all**
3. Wait ~3-5 minutes

**Expected output:**
- 4 Delta tables created in `lh_hearst_silver` (or as configured):
  - `silver.silver_engagement`
  - `silver.silver_subscriptions`
  - `silver.silver_ad_impressions`
  - `silver.silver_content`

> ⚠️ **Known issue:** The silver lakehouse (`lh_hearst_silver`) may not exist in the serialized Git folder. If the notebook fails:
> - Manually create `lh_hearst_silver` lakehouse in the workspace
> - OR: Modify the notebook to write silver tables into `lh_hearst_bronze` (not ideal but works for demo)

### Step 5.3: Run Gold Build Notebook

1. In Dev workspace, open **nb_hearst_gold_build**
2. Click **Run all**
3. Wait ~5-8 minutes

**Expected output:**
- 9 Delta tables created in `lh_hearst_gold.gold` schema:
  - **Dimensions:** `dim_date`, `dim_brand`, `dim_content`, `dim_subscriber`, `dim_platform`, `dim_campaign`
  - **Facts:** `fct_engagement`, `fct_subscription`, `fct_ad`

**Verification:**
- Open lakehouse `lh_hearst_gold` → **Tables** → **gold schema**
- Confirm all 9 tables exist
- SQL query test:
  ```sql
  SELECT COUNT(*) FROM gold.fct_engagement;
  -- Expected: ~500,000
  SELECT COUNT(*) FROM gold.dim_date;
  -- Expected: ~455 (90 days historical + 365 days future)
  ```

**Alternative (Scripted Execution):**
If you prefer to run all three notebooks via Python script:
```powershell
cd scripts
python run_medallion.py `
  --workspace-id <dev-workspace-id> `
  --notebooks nb_hearst_bronze_ingest,nb_hearst_silver_transform,nb_hearst_gold_build `
  --wait-for-completion
```

> ⚠️ **Manual finalize point:** The notebooks must complete successfully before proceeding to the semantic model finalization.

---

## Phase 6: Finalize Direct Lake Semantic Model

The semantic model `sm_hearst_audience` was serialized from Power BI Desktop, but **Direct Lake connections require finalization** in the Fabric workspace.

### Step 6.1: Open Semantic Model in Power BI Desktop

1. Download Power BI Desktop (latest version) if not installed
2. Open Power BI Desktop
3. Click **File** → **Open** → **Browse**
4. Navigate to your local clone: `fabric/sm_hearst_audience.SemanticModel/definition/model.tmdl`
5. ⚠️ **TMDL format not directly openable** — instead:
   - In Fabric portal (Dev workspace), open **sm_hearst_audience** item
   - Click **Open in Desktop** (⬇️ icon)
   - This will launch Power BI Desktop with the model connected to the Fabric workspace

### Step 6.2: Finalize Direct Lake Connection

1. In Power BI Desktop, go to **Home** → **Transform data** → **Transform data**
2. In Power Query Editor, you'll see 9 queries (6 dims + 3 facts)
3. For each query:
   - Right-click → **Advanced Editor**
   - Verify the M code references the lakehouse SQL endpoint:
     ```m
     let
         Source = Sql.Database("<workspace>.datawarehouse.fabric.microsoft.com", "lh_hearst_gold"),
         goldSchema = Source{[Schema="gold"]}[Data],
         dimDate = goldSchema{[Name="dim_date"]}[Data]
     in
         dimDate
     ```
   - If the lakehouse connection is missing or incorrect, you need to **manually reconnect**:
     - Delete all queries
     - **Get Data** → **More** → **OneLake data hub**
     - Select **lh_hearst_gold** lakehouse (SQL endpoint)
     - Select all 9 tables from the `gold` schema
     - Click **Transform Data**
     - Do NOT apply any transformations — just **Close & Apply**

4. Back in Power BI Desktop, go to **Model view**
5. Verify relationships:
   - `fct_engagement[date_key]` → `dim_date[date_key]` (many-to-one)
   - `fct_engagement[brand_key]` → `dim_brand[brand_key]` (many-to-one)
   - `fct_engagement[content_key]` → `dim_content[content_key]` (many-to-one)
   - `fct_engagement[subscriber_key]` → `dim_subscriber[subscriber_key]` (many-to-one)
   - `fct_engagement[platform_key]` → `dim_platform[platform_key]` (many-to-one)
   - (Similar for `fct_subscription`, `fct_ad`)

6. If relationships are missing, manually create them:
   - Drag from `fct_engagement[date_key]` to `dim_date[date_key]`
   - Cardinality: **Many to One (*:1)**
   - Cross filter direction: **Single**
   - Active: **Yes**

7. **Save** the file (File → Save)

### Step 6.3: Publish Semantic Model to Fabric Workspace

1. In Power BI Desktop, click **Home** → **Publish**
2. Select workspace: **ws_hearst_dev**
3. Click **Select**
4. Wait ~1-2 minutes for publish to complete
5. Click **Open 'sm_hearst_audience' in Power BI** (browser link)

**Verification:**
- In Fabric portal (Dev workspace), open **sm_hearst_audience**
- Click **Settings** → **Connection info**
- Verify **Direct Lake** mode is enabled
- Query the model via DAX query:
  ```dax
  EVALUATE
  SUMMARIZECOLUMNS(
      dim_brand[brand_name],
      "Page Views", SUM(fct_engagement[page_views])
  )
  ```
  Expected: 5 brands with page view counts

> ⚠️ **Manual finalize point:** This is the MOST CRITICAL step. If you skip it, the semantic model will not work in reports. The Direct Lake connection MUST be finalized in Power BI Desktop.

---

## Phase 7: Publish Report & Enable Data Agent

### Step 7.1: Verify Report in Workspace

1. In Dev workspace, open **rpt_hearst_exec**
2. The report should render with visualizations showing:
   - Monthly Active Users (MAU) trend
   - Churn Rate % by brand
   - MRR by brand
   - Top content by page views
   - Ad revenue by campaign

**Fallback:** If the report shows errors:
- The semantic model finalization in Phase 6 likely failed
- Re-open the semantic model in Power BI Desktop and re-publish

### Step 7.2: Enable Data Agent

1. In Dev workspace, open **agent_hearst_analytics** (Data Agent item)
2. Click **Settings** (⚙️ icon)
3. Verify the agent is connected to **sm_hearst_audience** semantic model
4. Click **Enable** (if not already enabled)
5. Test the agent:
   - In the agent chat interface, ask: **"What was Cosmopolitan's churn rate last month?"**
   - Expected answer: The agent should query the semantic model and return a percentage (e.g., "Cosmopolitan's churn rate in May 2026 was 9.8%")

**Verification:**
- The agent should respond with a natural-language answer + a DAX query snippet showing how it retrieved the data
- If the agent fails, check:
  - Semantic model is in Direct Lake mode
  - Agent permissions: the agent service principal must have **Read** access to the semantic model

---

## Phase 8: Create Deployment Pipeline

### Step 8.1: Create Pipeline in Fabric Portal

1. In Fabric portal, click **Deployment pipelines** (left nav)
2. Click **+ New pipeline**
3. Name: `Hearst Fabric Release`
4. Description: `Automated CI/CD for Hearst Approach A demo`
5. Click **Create**

### Step 8.2: Add Stages

1. In the pipeline view, you should see a default **Development** stage
2. Click **+ Add stage** (top-right)
3. Name: `UAT`
4. Click **Add**
5. Click **+ Add stage** again
6. Name: `Production`
7. Click **Add**

### Step 8.3: Assign Workspaces to Stages

1. In the **Development** stage card, click **Assign workspace**
2. Select **ws_hearst_dev**
3. Click **Assign**
4. Repeat for **UAT** stage → **ws_hearst_uat**
5. Repeat for **Production** stage → **ws_hearst_prod**

**Verification:**
- The pipeline should show three stages: Development → UAT → Production
- Each stage should have a workspace assigned

---

## Phase 9: Configure Deployment Rules

Deployment rules parameterize environment-specific bindings (lakehouse references, connection strings) per stage.

### Step 9.1: View Deployment Rules (Portal UI)

1. In the deployment pipeline, click **Deployment settings** (⚙️ icon in top-right)
2. Select **UAT** stage
3. Scroll to **Lakehouse** section
4. You should see rules like:
   - **Notebook: nb_hearst_bronze_ingest**
     - Source lakehouse: `lh_hearst_bronze` (Dev)
     - Target lakehouse: `lh_hearst_bronze` (UAT)
   - (Similar for silver and gold notebooks)

### Step 9.2: Set Deployment Rules via Script (Optional)

For automation, use the Python helper script:
```powershell
cd scripts
python set_deployment_rules.py `
  --pipeline-id <pipeline-id> `
  --stage UAT `
  --rules deployment_rules_uat.json

python set_deployment_rules.py `
  --pipeline-id <pipeline-id> `
  --stage Production `
  --rules deployment_rules_prod.json
```

> **Note:** The `deployment_rules_*.json` files define which lakehouse/warehouse bindings to rewrite per stage. Example:
> ```json
> {
>   "dataSourceRules": [
>     {
>       "sourceItem": { "type": "Lakehouse", "displayName": "lh_hearst_gold" },
>       "targetItem": { "type": "Lakehouse", "displayName": "lh_hearst_gold" }
>     }
>   ]
> }
> ```

### Step 9.3: Verify Deployment Rules

1. In the pipeline, click **Compare** (between Dev and UAT stages)
2. You should see a diff showing which items will be deployed
3. Hover over each item to see deployment rules applied

---

## Phase 10: Promote Dev → UAT → Prod

### Step 10.1: Deploy Dev → UAT

1. In the deployment pipeline, click **Deploy** (arrow icon between Dev and UAT stages)
2. Review the deployment preview:
   - Items to deploy: 3 notebooks, 2 lakehouses, 1 semantic model, 1 report, 1 data agent
   - Deployment rules: lakehouse bindings rewritten for UAT
3. Click **Deploy**
4. Wait ~3-5 minutes for deployment to complete

**Verification:**
- Switch to **ws_hearst_uat** workspace
- Verify all items are present (notebooks, lakehouses, semantic model, report, agent)
- ⚠️ **Data is NOT copied** — you need to run the medallion notebooks in UAT

### Step 10.2: Seed UAT Data

1. In UAT workspace, open **nb_hearst_bronze_ingest**
2. Click **Run all**
3. Wait ~5-10 minutes
4. Open **nb_hearst_silver_transform** → **Run all** (~3-5 min)
5. Open **nb_hearst_gold_build** → **Run all** (~5-8 min)

**Verification:**
- Verify `lh_hearst_gold.gold` schema has all 9 tables with expected row counts
- Open **rpt_hearst_exec** in UAT — it should render without errors

### Step 10.3: Run UAT Quality Gates

1. In PowerShell (local machine or GitHub Actions runner):
   ```powershell
   cd scripts
   python run_uat_tests.py
   ```

2. The script will:
   - Run BPA (Best Practice Analyzer) on the semantic model
   - Execute data quality tests (NULL checks, referential integrity, dimension uniqueness)
   - Run DAX reconciliation (semantic model measures vs. gold lakehouse SQL)
   - Exit with code 0 if all tests pass, code 1 if any test fails

**Expected output:**
```
[INFO] Running UAT test suite for ws_hearst_uat
[INFO] BPA: 15 rules checked, 0 violations (severity >= 2)
[INFO] Data quality: 12 tests passed, 0 failed
[INFO] DAX reconciliation: 9 measures validated, 0 mismatches (tolerance ±1%)
[SUCCESS] All UAT tests passed — ready for Production promotion
```

> ⚠️ **If tests fail:** Do NOT promote to Production. Investigate the failure, fix the issue in Dev, and re-deploy to UAT.

### Step 10.4: Deploy UAT → Prod

1. In the deployment pipeline, click **Deploy** (arrow icon between UAT and Prod stages)
2. Review the deployment preview
3. Click **Deploy**
4. Wait ~3-5 minutes

### Step 10.5: Seed Prod Data

Repeat Step 10.2 for **ws_hearst_prod**:
- Run `nb_hearst_bronze_ingest` → `nb_hearst_silver_transform` → `nb_hearst_gold_build` in Prod workspace

### Step 10.6: Run Prod Smoke Test

1. Open **rpt_hearst_exec** in Prod workspace — verify it renders without errors
2. Open **agent_hearst_analytics** in Prod workspace — test a query: "What was ELLE's MRR last month?"
3. Verify the agent responds correctly

**Verification:**
- All items in Prod workspace match UAT (minus environment-specific lakehouse bindings)
- Report and agent function correctly in Prod

---

## Phase 11: Rollback & Troubleshooting

### Rollback Procedure

If a Prod deployment introduces a bug or regression:

1. **Option A: Redeploy from UAT**
   - In the deployment pipeline, deploy UAT → Prod again (overwrites Prod with last known-good state)

2. **Option B: Manual revert in Dev**
   - In Dev workspace, revert the notebook/semantic model to a previous Git commit
   - Commit & sync from Git
   - Re-deploy Dev → UAT → Prod

3. **Option C: Emergency manual fix**
   - Manually edit the item in Prod workspace (bypasses CI/CD)
   - ⚠️ **NOT RECOMMENDED** — this creates drift between Dev/UAT/Prod
   - Only use for critical hotfixes; backport the fix to Dev ASAP

### Troubleshooting Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Git sync fails | Missing PAT or incorrect folder path | Regenerate PAT, verify `/fabric` folder in Git connection settings |
| Notebook fails: "Lakehouse not found" | Lakehouse not created or not synced from Git | Manually create lakehouse in workspace; verify `.platform` file exists in Git |
| Semantic model shows "import mode" instead of "Direct Lake" | Lakehouse connection not finalized | Re-open in Power BI Desktop, reconnect to lakehouse SQL endpoint, re-publish |
| Report shows blank visuals | Semantic model not connected to gold lakehouse data | Verify medallion notebooks completed; check `gold` schema tables have rows |
| Data agent doesn't respond | Agent not connected to semantic model, or semantic model offline | Check agent settings → semantic model binding; refresh semantic model metadata |
| UAT tests fail | Data quality issue or DAX measure mismatch | Review test logs; fix issue in Dev; re-deploy to UAT and re-run tests |
| Deployment pipeline stuck | Long-running deployment or API throttling | Wait 10-15 minutes; check Fabric notifications for errors; retry deployment |
| Trial capacity exhausted | 60-day trial expired or storage limit hit | Upgrade to paid capacity (F2 or higher), or request capacity extension |

---

## Appendix: Manual Finalize Points

This demo has **three unavoidable manual steps** due to Fabric limitations:

### 1. Direct Lake Semantic Model Finalization (Phase 6)

**What:** The semantic model must be opened in Power BI Desktop, reconnected to the lakehouse SQL endpoint, and re-published.

**Why:** TMDL serialization does not include the lakehouse connection string (it's a placeholder `'DirectLake-lh_hearst_gold'`). Fabric cannot automatically resolve this connection.

**How to minimize:**
- Pre-bake a `.pbix` file with the connection pre-configured
- Include a script that uses XMLA endpoint to programmatically set the connection (requires Tabular Editor or AMO client)

### 2. Data Agent Enablement (Phase 7)

**What:** The data agent must be manually enabled and tested in each environment.

**Why:** Data agents are not yet fully supported in Git serialization; the `.DataAgent` folder may not sync correctly.

**How to minimize:**
- Use Fabric REST API to programmatically enable the agent post-deployment
- Script the agent configuration via PowerShell or Python

### 3. Deployment Rules Configuration (Phase 9)

**What:** Deployment rules must be set via the Fabric portal UI or REST API.

**Why:** Deployment rules are not stored in Git; they are pipeline metadata.

**How to minimize:**
- Use the `set_deployment_rules.py` script to automate this step
- Store rules in version-controlled JSON files (`deployment_rules_uat.json`, `deployment_rules_prod.json`)

---

## Summary

You have successfully deployed the Hearst Approach A demo on a Fabric TRIAL capacity. The architecture includes:
- **Medallion pipeline:** Bronze → Silver → Gold (9 Delta tables in gold star schema)
- **Direct Lake semantic model:** 6 dimensions + 3 facts, 15 DAX measures (MRR, Churn Rate %, eCPM)
- **Power BI report:** Executive dashboard with MAU, churn, ad revenue KPIs
- **Data agent:** Conversational AI over the semantic model
- **CI/CD pipeline:** Dev → UAT → Prod with quality gates (BPA + data quality + DAX reconciliation)

**Next steps:**
- Make a change in Dev (e.g., add a DAX measure)
- Commit & sync from Git
- Promote Dev → UAT → verify quality gates → Prod
- Use the companion **demo-script-audience.md** for a live walkthrough

---

**Last updated:** 2026-06-23  
**Tested on:** Fabric TRIAL (60-day, F64 capacity equivalent)
