# Demo Script — Hearst Approach A: Audience Analytics with CI/CD

**A click-by-click LIVE demo walkthrough for presenting the Hearst Approach A solution: medallion architecture + Direct Lake semantic model + Power BI report + data agent + automated CI/CD.**

**Duration:** 25-30 minutes  
**Audience:** Business stakeholders, BI/data engineers, IT leadership  
**Goal:** Show a complete, working CI/CD pipeline for Microsoft Fabric with a real business use case

---

## Pre-Demo Setup (30 minutes before showtime)

### Environment Checklist

- [ ] All three workspaces (Dev, UAT, Prod) are provisioned and visible in Fabric portal
- [ ] Dev workspace is Git-connected to GitHub repository (`main` branch, `/fabric` folder)
- [ ] Medallion notebooks have been run successfully in all three environments (bronze → silver → gold)
- [ ] Semantic model `sm_hearst_audience` is in **Direct Lake** mode and connected to `lh_hearst_gold`
- [ ] Report `rpt_hearst_exec` renders without errors in Dev, UAT, and Prod
- [ ] Data agent `agent_hearst_analytics` is enabled and responds to test queries
- [ ] Deployment pipeline is created with three stages assigned to the correct workspaces
- [ ] Deployment rules are configured (lakehouse bindings per stage)

### Browser Tab Setup (for smooth transitions)

Open these tabs **before** starting the demo:
1. **GitHub Repo** — `main` branch view (https://github.com/<your-org>/hearst_cicd_fabric_demo)
2. **GitHub Actions** — Workflows page (https://github.com/<your-org>/hearst_cicd_fabric_demo/actions)
3. **Fabric Portal — Dev Workspace** (https://app.fabric.microsoft.com/workspace/ws_hearst_dev)
4. **Fabric Portal — UAT Workspace** (https://app.fabric.microsoft.com/workspace/ws_hearst_uat)
5. **Fabric Portal — Prod Workspace** (https://app.fabric.microsoft.com/workspace/ws_hearst_prod)
6. **Fabric Portal — Deployment Pipeline** (https://app.fabric.microsoft.com/deployment-pipelines/<pipeline-id>)
7. **Power BI Report (Prod)** — Direct link to the report in Prod workspace

### Prepare a Sample Change (DO NOT COMMIT YET)

Create a feature branch and stage a small, visible change:

```powershell
git checkout main
git pull origin main
git checkout -b demo/add-measure
```

Edit `fabric/sm_hearst_audience.SemanticModel/definition/measures.tmdl`:
```dax
// Add this measure:
measure 'New Subscriber Growth %' = 
    DIVIDE(
        [New Subscribers],
        [Active Subscribers],
        0
    ) * 100
    formatString: "0.00%"
```

**Do NOT commit or push yet** — you'll do this live during the demo.

### Screen Layout Recommendation

- **Primary screen:** Fabric Portal (full-screen browser)
- **Secondary screen:** VS Code (for code editing), PowerShell (for Git commands), and demo notes

---

## Demo Flow (25-30 minutes)

---

### INTRO: Set the Stage (3 minutes)

**[Screen: Slide deck or architecture diagram]**

**[Screen: Switch to architecture diagram or README.md file on GitHub]**

Show the high-level flow:
```
GitHub (main) → Dev Workspace → UAT → Prod
                  ↑ Git-connected   ↑ Deploy API   ↑ Deploy API (gated)
                  ↑ updateFromGit   ↑ + Tests      ↑ + Approval
```

---

### ACT 1: The Business Problem (2 minutes)

**[Screen: Power BI Report (Prod)]**

**[DO]** Open the `rpt_hearst_exec` report in Prod workspace.

**[EXPECT]** The visuals filter to show Cosmopolitan-only metrics.

---

### ACT 2: The Data Agent (3 minutes)

**[Screen: Fabric Portal — Data Agent in Prod]**

**[DO]** Open `agent_hearst_analytics` in Prod workspace.

**[TYPE]** In the agent chat interface: **"What was Cosmopolitan's churn rate last month?"**

**[EXPECT]** The agent responds in 3-5 seconds with a natural-language answer:
> "Cosmopolitan's churn rate in May 2026 was 9.8%. This was calculated from 487 churned subscribers out of 4,963 active subscribers."

**[DO]** Click **Show details** (or **View DAX**) in the agent response.

**[EXPECT]** The agent shows the DAX query:
```dax
EVALUATE
SUMMARIZECOLUMNS(
    dim_brand[brand_name],
    dim_date[month_name],
    "Churned Subscribers", [Churned Subscribers],
    "Active Subscribers", [Active Subscribers],
    "Churn Rate %", [Churn Rate %]
)
ORDER BY dim_date[date_key] DESC
```

**[TYPE]** Another question: **"Which brand had the highest eCPM last quarter?"**

**[EXPECT]** The agent responds with the brand and eCPM value (e.g., "ELLE had the highest eCPM at $12.47 in Q1 2026").

---

### ACT 3: Make a Change in Dev (4 minutes)

**[Screen: VS Code — local clone of the repo]**

I'll add this as a DAX measure to the semantic model."

**[DO]** Open `fabric/sm_hearst_audience.SemanticModel/definition/measures.tmdl` in VS Code.

**[TYPE]** Add the following measure at the end of the file:
```dax
measure 'New Subscriber Growth %' = 
    DIVIDE(
        [New Subscribers],
        [Active Subscribers],
        0
    ) * 100
    formatString: "0.00%"
```

**[DO]** Save the file.

**[Screen: PowerShell terminal]**

**[TYPE]** Git commands:
```powershell
git add .
git commit -m "Add New Subscriber Growth % measure"
git push origin demo/add-measure
```

**[EXPECT]** Git push succeeds.

---

### ACT 4: Open a Pull Request (2 minutes)

**[Screen: GitHub Repo — Pull Requests tab]**

**[DO]** Click **New pull request** button.

**[DO]** Select:
- Base: `main`
- Compare: `demo/add-measure`

**[TYPE]** Title: `Add New Subscriber Growth % measure`

**[TYPE]** Description:
> "Adds a new DAX measure requested by CFO: New Subscriber Growth % (new signups as % of active base).
> 
> - Formula: `DIVIDE([New Subscribers], [Active Subscribers], 0) * 100`
> - Format: Percentage with 2 decimals
> - No breaking changes"

**[EXPECT]** GitHub Actions CI workflow triggers automatically (you'll see a yellow dot next to the PR).

---

### ACT 5: CI Validation (2 minutes)

**[Screen: GitHub Actions — CI workflow run]**

**[DO]** Click on the CI workflow run (the yellow dot should turn to a green checkmark or red X).

**[EXPECT]** After ~2-3 minutes, the CI workflow completes successfully (green checkmark).

Now I can merge this PR."

**[Screen: GitHub PR page]**

**[EXPECT]** The PR is merged into `main`.

---

### ACT 6: CD Pipeline — Dev Sync (3 minutes)

**[Screen: GitHub Actions — CD-Dev-Sync workflow]**

**[DO]** Click on the **CD-Dev-Sync** workflow run (triggered by the merge to `main`).

**[EXPECT]** The workflow shows:
```
✅ Authenticate with service principal
✅ Call updateFromGit API for Dev workspace
✅ Poll LRO (long-running operation) until complete
✅ Dev workspace updated successfully
```

**[Screen: Fabric Portal — Dev Workspace]**

**[DO]** Refresh the Dev workspace page.

**[DO]** Open `sm_hearst_audience` semantic model.

**[EXPECT]** The new measure **"New Subscriber Growth %"** appears in the measure list.

---

### ACT 7: Promote to UAT with Quality Gates (4 minutes)

**[Screen: Fabric Portal — Deployment Pipeline]**

**[DO]** Open the deployment pipeline view.

**[DO]** Review the deployment preview:
- Items to deploy: `sm_hearst_audience` (semantic model)
- Deployment rules: Rewrite lakehouse binding from Dev to UAT

**[EXPECT]** The deployment starts (progress spinner).

**[Screen: GitHub Actions — CD-Promote-UAT workflow]**

**[DO]** Open the **CD-Promote-UAT** workflow run.

**[EXPECT]** After ~3-4 minutes, the workflow shows:
```
✅ Deploy Dev → UAT successful
✅ Data quality tests: 12 passed, 0 failed
✅ DAX reconciliation: 10 measures validated (including the new measure)
✅ BPA: 15 rules checked, 0 violations
✅ UAT quality gates PASSED — ready for Production
```

**Fallback (if gates fail):**
If the quality gates fail during the demo:
- **[DO]** Click on the failed test step in GitHub Actions.
- **[DO]** Skip to ACT 9 (rollback demo) or conclude with a note: "In a real scenario, I'd fix the issue in Dev, open a new PR, and re-run the pipeline."

---

### ACT 8: Promote to Production (Manual Approval) (3 minutes)

**[Screen: GitHub Actions — CD-Promote-Prod workflow (paused)]**

**[DO]** Open the **CD-Promote-Prod** workflow.

**[EXPECT]** The workflow shows a **"Waiting for approval"** banner.

**[DO]** Click **Review deployments** button (or **Approve** in GitHub UI).

**[DO]** Select **Production** environment.

**[EXPECT]** The workflow resumes and executes:
```
✅ Manual approval granted
✅ Deploy UAT → Prod successful
✅ Prod smoke test: connectivity OK
✅ Deployment complete
```

**[Screen: Fabric Portal — Prod Workspace]**

**[DO]** Open `sm_hearst_audience` in Prod workspace.

**[DO]** View the measure list (or open the report).

**[EXPECT]** The new measure **"New Subscriber Growth %"** is present.

**[Screen: Power BI Report (Prod)]**

**[DO]** Open `rpt_hearst_exec` report.

**[DO]** Add a card visual (or table) showing the new measure: **New Subscriber Growth %**.

**[EXPECT]** The visual displays a percentage (e.g., "2.34%").

---

### ACT 9: Test the Data Agent with the New Measure (2 minutes)

**[Screen: Fabric Portal — Data Agent in Prod]**

**[DO]** Open `agent_hearst_analytics` in Prod workspace.

**[TYPE]** In the agent chat: **"What is our new subscriber growth rate for Cosmopolitan?"**

**[EXPECT]** The agent responds:
> "Cosmopolitan's new subscriber growth rate is 2.12%. This is based on 105 new subscribers and 4,963 active subscribers."

---

### CLOSING: Summary & Recap (2 minutes)

**[Screen: Architecture diagram or slide deck]**

This entire flow is:
- **Automated**: No manual deployments or copy-paste errors
- **Gated**: Quality checks prevent bugs from reaching Production
- **Auditable**: Every change is tracked in Git with commit history
- **Fast**: From PR merge to Prod deployment in under 15 minutes

And the best part? This works for **any Fabric item** — notebooks, warehouses, pipelines, semantic models, reports, even data agents."

**[Screen: GitHub Repo — README.md or docs/]**

Thank you! Questions?"

---

## Fallback Scenarios (What If Things Go Wrong?)

### Scenario 1: Git Sync Fails in Dev

**Symptom:** The `updateFromGit` API call returns an error (e.g., "conflict detected" or "authentication failed").

**[DO]** In Fabric portal (Dev workspace), go to **Source control** → **View conflicts**.

**[DO]** Select "Git version" and resolve the conflict.

---

### Scenario 2: UAT Quality Gates Fail

**Symptom:** The `run_uat_tests.py` script exits with code 1 (test failure).

**[Screen: GitHub Actions — test failure logs]**

**[DO]** Expand the failed test step.

**[EXPECT]** Example failure:
```
[ERROR] DAX reconciliation failed: Measure 'New Subscriber Growth %' returned 2.34%, but SQL query returned 2.41% (7% relative difference, exceeds 1% tolerance)
```

In a real scenario, I'd:
1. Investigate the root cause (review the DAX formula and SQL query)
2. Fix the issue in Dev (either the measure or the ETL logic)
3. Open a new PR with the fix
4. Re-run the promotion workflow

The key point: **bad code never reaches Production**. The quality gates blocked it."

---

### Scenario 3: Deployment Takes Too Long

**Symptom:** The deployment is stuck at "Deploying..." for more than 5 minutes.

Let me check the deployment status via the Fabric API."

**[DO]** Open PowerShell and run:
```powershell
cd scripts
python check_deployment_status.py --pipeline-id <pipeline-id> --deployment-id <deployment-id>
```

---

### Scenario 4: Report Doesn't Render in Prod

**Symptom:** The report opens but shows blank visuals or errors.

**[DO]** Open the semantic model `sm_hearst_audience` in Prod.

**[DO]** Check the connection info (Settings → Connection).

**[EXPECT]** If the semantic model is in "import mode" instead of "Direct Lake":

Let me verify the deployment rules."

**[DO]** In the deployment pipeline, click **Deployment settings** → **Prod stage** → **Data source rules**.

**[DO]** In Prod workspace, run `nb_hearst_bronze_ingest` → `nb_hearst_silver_transform` → `nb_hearst_gold_build`.

---

## Timing & Pacing

| Act | Duration | Cumulative |
|-----|----------|------------|
| Intro | 3 min | 3 min |
| Act 1 (Business Problem) | 2 min | 5 min |
| Act 2 (Data Agent) | 3 min | 8 min |
| Act 3 (Make Change) | 4 min | 12 min |
| Act 4 (Pull Request) | 2 min | 14 min |
| Act 5 (CI Validation) | 2 min | 16 min |
| Act 6 (Dev Sync) | 3 min | 19 min |
| Act 7 (UAT Promotion + Gates) | 4 min | 23 min |
| Act 8 (Prod Approval & Deploy) | 3 min | 26 min |
| Act 9 (Data Agent Test) | 2 min | 28 min |
| Closing | 2 min | 30 min |

**Tips for staying on time:**
- **Pre-stage all browser tabs** — no searching for URLs mid-demo
- **Use bookmarks or shortcuts** for frequently accessed pages
- **Skip optional steps** if running long (e.g., show the BPA log instead of running it live)
- **Have a "fast-forward" slide** ready: "In the interest of time, I'll show you the result after the deployment completes..."

---

## Post-Demo: Q&A Prompts

After the demo, expect these common questions:

### Q1: "How do you handle secrets (API keys, passwords)?"

**Answer:** "Great question. All secrets are stored in Azure Key Vault and synchronized to GitHub Environment Secrets. They're never committed to Git. We use a service principal with client secret authentication, and the secret is rotated every 90 days. The CI/CD workflows use `::add-mask::` to hide secrets in logs. For extra security, we can switch to federated credentials (OIDC), which eliminates secrets entirely."

### Q2: "What if someone makes a change directly in Fabric instead of going through Git?"

**Answer:** "Our architecture prevents this by design: only the Dev workspace is Git-connected. UAT and Prod receive changes **exclusively** via the deployment pipeline — they can't sync from Git directly. If someone tries to manually edit an item in UAT or Prod, it creates drift, and the next deployment will overwrite their change. We enforce a 'Git is the source of truth' policy: all changes must go through pull requests."

### Q3: "How long does a typical deployment take?"

**Answer:** "From PR merge to Prod deployment: ~15-20 minutes total. The breakdown:
- CI validation (BPA + Terraform): ~2-3 minutes
- Dev sync (updateFromGit): ~2-3 minutes
- UAT deployment + quality gates: ~5-7 minutes
- Prod deployment (manual approval + deploy): ~3-5 minutes

The longest part is the quality gates (data quality + DAX reconciliation), but that's intentional — we'd rather wait a few extra minutes than deploy bad code."

### Q4: "Does this work for non-Fabric items (e.g., Azure Data Factory, Databricks)?"

**Answer:** "This demo focuses on native Fabric items (notebooks, lakehouses, semantic models), but the pattern is **extensible**. You can:
- Add Terraform modules for Databricks notebooks or Azure Data Factory pipelines
- Use ADF's ARM template export + parameterization for multi-environment deployment
- Integrate Databricks Repos (Git sync) and Jobs API into the same CI/CD workflow
- The core principle — Git-driven, tested, gated promotion — applies to any data platform."

### Q5: "What about data? How do you seed UAT and Prod with test data?"

**Answer:** "Excellent question. Fabric Deployment Pipelines move **metadata** (schemas, code, definitions), not **data** (table rows, Delta files). For data seeding:
- **Dev**: We run the medallion notebooks to generate synthetic data (~650K events, deterministic seed)
- **UAT**: Post-deployment, a GitHub Actions step executes the same notebooks via Fabric Jobs API to seed UAT
- **Prod**: We either copy a snapshot from UAT or run the notebooks with production-like data sources

For real-world scenarios, you'd integrate with your existing data ingestion pipelines (e.g., ADF, Synapse Pipelines, or external ETL tools)."

---

## Conclusion

This demo script is designed for a **25-30 minute live walkthrough** that shows:
1. **The business value** (real-time analytics, conversational AI)
2. **The technical architecture** (medallion, Direct Lake, CI/CD)
3. **The developer experience** (Git-driven, automated, gated)
4. **The operational benefits** (quality gates, auditability, rollback)

**Preparation is key:**
- Rehearse the demo 2-3 times before presenting
- Verify all environments are working ~30 minutes before showtime
- Have fallback slides ready for common failure scenarios
- Know your audience: adjust technical depth based on their background

**Last updated:** 2026-06-23  
**Tested on:** Fabric TRIAL (60-day, F64 capacity equivalent)
