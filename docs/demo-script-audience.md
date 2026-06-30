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

**What to say:**

> "Good morning/afternoon. Today I'm showing you Hearst's Approach A for modernizing digital audience and subscription analytics on Microsoft Fabric.
> 
> Hearst publishes iconic brands like Cosmopolitan, Esquire, ELLE, Good Housekeeping, and Car and Driver. We're tracking millions of page views, tens of thousands of subscribers, and ad revenue across web, iOS, and Android platforms.
> 
> The challenge: How do we deliver real-time analytics to executives while maintaining enterprise-grade quality, governance, and change control?
> 
> Our solution combines:
> - **Medallion architecture**: Bronze → Silver → Gold for data quality and separation of concerns
> - **Direct Lake semantic model**: Zero-ETL, real-time Power BI with no refresh windows
> - **Conversational AI**: A data agent that lets business users ask questions in natural language
> - **Automated CI/CD**: GitHub-driven deployment pipeline from Dev → UAT → Prod with quality gates
> 
> Let me show you how this works end-to-end."

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

**[SAY]** "This is our executive dashboard. It shows:
- **Monthly Active Users (MAU)**: Trend over the last 90 days
- **Churn Rate %**: By brand (Cosmopolitan, Esquire, ELLE, etc.)
- **Monthly Recurring Revenue (MRR)**: Subscription revenue by brand
- **Top Content**: Articles with the highest page views
- **Ad Revenue**: Campaign performance and eCPM (effective cost per thousand impressions)"

**[CLICK]** Click on "Cosmopolitan" brand in the slicer.

**[EXPECT]** The visuals filter to show Cosmopolitan-only metrics.

**[SAY]** "This is all powered by a **Direct Lake semantic model** reading directly from our gold lakehouse — no import refresh, no data movement, no lag. Changes in the lakehouse reflect in the report instantly."

---

### ACT 2: The Data Agent (3 minutes)

**[Screen: Fabric Portal — Data Agent in Prod]**

**[DO]** Open `agent_hearst_analytics` in Prod workspace.

**[SAY]** "Now, let's ask the data agent a question. Instead of clicking through filters, I can just ask in natural language."

**[TYPE]** In the agent chat interface: **"What was Cosmopolitan's churn rate last month?"**

**[CLICK]** Send button.

**[EXPECT]** The agent responds in 3-5 seconds with a natural-language answer:
> "Cosmopolitan's churn rate in May 2026 was 9.8%. This was calculated from 487 churned subscribers out of 4,963 active subscribers."

**[SAY]** "Behind the scenes, the agent generated a DAX query against the semantic model. Let me show you the query it used."

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

**[SAY]** "This is the power of combining semantic models with AI — business users don't need to learn Power BI or DAX. They just ask questions."

**[TYPE]** Another question: **"Which brand had the highest eCPM last quarter?"**

**[EXPECT]** The agent responds with the brand and eCPM value (e.g., "ELLE had the highest eCPM at $12.47 in Q1 2026").

**[SAY]** "Now let's see how we maintain and evolve this system using automated CI/CD."

---

### ACT 3: Make a Change in Dev (4 minutes)

**[Screen: VS Code — local clone of the repo]**

**[SAY]** "Let's say the CFO asks for a new metric: **New Subscriber Growth %** — the percentage of new signups relative to the active subscriber base.

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

**[SAY]** "This measure divides new subscribers by active subscribers and formats it as a percentage."

**[DO]** Save the file.

**[Screen: PowerShell terminal]**

**[TYPE]** Git commands:
```powershell
git add .
git commit -m "Add New Subscriber Growth % measure"
git push origin demo/add-measure
```

**[EXPECT]** Git push succeeds.

**[SAY]** "Now I'll open a pull request to merge this change into `main`."

---

### ACT 4: Open a Pull Request (2 minutes)

**[Screen: GitHub Repo — Pull Requests tab]**

**[DO]** Click **New pull request** button.

**[DO]** Select:
- Base: `main`
- Compare: `demo/add-measure`

**[CLICK]** **Create pull request**.

**[TYPE]** Title: `Add New Subscriber Growth % measure`

**[TYPE]** Description:
> "Adds a new DAX measure requested by CFO: New Subscriber Growth % (new signups as % of active base).
> 
> - Formula: `DIVIDE([New Subscribers], [Active Subscribers], 0) * 100`
> - Format: Percentage with 2 decimals
> - No breaking changes"

**[CLICK]** **Create pull request**.

**[EXPECT]** GitHub Actions CI workflow triggers automatically (you'll see a yellow dot next to the PR).

**[SAY]** "GitHub Actions is now running our CI validation suite. Let's see what it checks."

---

### ACT 5: CI Validation (2 minutes)

**[Screen: GitHub Actions — CI workflow run]**

**[DO]** Click on the CI workflow run (the yellow dot should turn to a green checkmark or red X).

**[SAY]** "Our CI pipeline runs three validation checks:
1. **Best Practice Analyzer (BPA)**: Validates the semantic model schema — checks for missing formatStrings, invalid relationships, Direct Lake configuration errors
2. **Terraform Validate**: Ensures infrastructure code is syntactically correct
3. **Gitleaks**: Scans for accidentally committed secrets (API keys, passwords)"

**[EXPECT]** After ~2-3 minutes, the CI workflow completes successfully (green checkmark).

**[SAY]** "All checks passed. The BPA validated that our new measure has a formatString, doesn't break any relationships, and follows naming conventions.

Now I can merge this PR."

**[Screen: GitHub PR page]**

**[CLICK]** **Merge pull request** button.

**[CLICK]** **Confirm merge**.

**[EXPECT]** The PR is merged into `main`.

**[SAY]** "The moment this merges, our CD pipeline triggers automatically. Let's watch it flow through Dev → UAT → Prod."

---

### ACT 6: CD Pipeline — Dev Sync (3 minutes)

**[Screen: GitHub Actions — CD-Dev-Sync workflow]**

**[DO]** Click on the **CD-Dev-Sync** workflow run (triggered by the merge to `main`).

**[SAY]** "The first step is syncing the change into the Dev workspace using Fabric's `updateFromGit` API."

**[EXPECT]** The workflow shows:
```
✅ Authenticate with service principal
✅ Call updateFromGit API for Dev workspace
✅ Poll LRO (long-running operation) until complete
✅ Dev workspace updated successfully
```

**[SAY]** "This takes ~2-3 minutes. Let's verify the change landed in Dev."

**[Screen: Fabric Portal — Dev Workspace]**

**[DO]** Refresh the Dev workspace page.

**[DO]** Open `sm_hearst_audience` semantic model.

**[CLICK]** **Open in Desktop** (or view measure list in the portal).

**[EXPECT]** The new measure **"New Subscriber Growth %"** appears in the measure list.

**[SAY]** "The measure is now live in Dev. Next, we promote it to UAT for testing."

---

### ACT 7: Promote to UAT with Quality Gates (4 minutes)

**[Screen: Fabric Portal — Deployment Pipeline]**

**[DO]** Open the deployment pipeline view.

**[SAY]** "I'm going to deploy from Dev to UAT using the deployment pipeline."

**[CLICK]** The **Deploy** arrow between Dev and UAT stages.

**[DO]** Review the deployment preview:
- Items to deploy: `sm_hearst_audience` (semantic model)
- Deployment rules: Rewrite lakehouse binding from Dev to UAT

**[CLICK]** **Deploy** button.

**[EXPECT]** The deployment starts (progress spinner).

**[SAY]** "While this deploys, our automation is also running the UAT quality gate suite in the background. Let me show you what that entails."

**[Screen: GitHub Actions — CD-Promote-UAT workflow]**

**[DO]** Open the **CD-Promote-UAT** workflow run.

**[SAY]** "After the deployment completes, we run three quality gates:
1. **Data Quality Tests**: Checks gold lakehouse for NULL values, referential integrity, dimension uniqueness, date continuity
2. **DAX Reconciliation**: Validates that every DAX measure matches the source data in the lakehouse (within ±1% tolerance)
3. **BPA (again)**: Re-validates the semantic model in UAT"

**[EXPECT]** After ~3-4 minutes, the workflow shows:
```
✅ Deploy Dev → UAT successful
✅ Data quality tests: 12 passed, 0 failed
✅ DAX reconciliation: 10 measures validated (including the new measure)
✅ BPA: 15 rules checked, 0 violations
✅ UAT quality gates PASSED — ready for Production
```

**[SAY]** "All quality gates passed. This means the new measure is mathematically correct and doesn't break any existing reports. Now we can promote to Production."

**Fallback (if gates fail):**
If the quality gates fail during the demo:
- **[SAY]** "Uh-oh, looks like we caught a bug! This is exactly why we have quality gates. Let me show you the failure."
- **[DO]** Click on the failed test step in GitHub Actions.
- **[SAY]** "For example, if the DAX reconciliation fails, it means the new measure doesn't match the source data — maybe I used the wrong column or formula. We fix it in Dev and re-run the promotion. The pipeline prevents bad code from reaching Production."
- **[DO]** Skip to ACT 9 (rollback demo) or conclude with a note: "In a real scenario, I'd fix the issue in Dev, open a new PR, and re-run the pipeline."

---

### ACT 8: Promote to Production (Manual Approval) (3 minutes)

**[Screen: GitHub Actions — CD-Promote-Prod workflow (paused)]**

**[DO]** Open the **CD-Promote-Prod** workflow.

**[SAY]** "Now we're ready for Production. But notice — this workflow is **paused**, waiting for manual approval. That's our final gate: a human must review and approve before code touches Production."

**[EXPECT]** The workflow shows a **"Waiting for approval"** banner.

**[DO]** Click **Review deployments** button (or **Approve** in GitHub UI).

**[DO]** Select **Production** environment.

**[CLICK]** **Approve and deploy**.

**[EXPECT]** The workflow resumes and executes:
```
✅ Manual approval granted
✅ Deploy UAT → Prod successful
✅ Prod smoke test: connectivity OK
✅ Deployment complete
```

**[SAY]** "The deployment is complete. Let's verify the change is live in Production."

**[Screen: Fabric Portal — Prod Workspace]**

**[DO]** Open `sm_hearst_audience` in Prod workspace.

**[DO]** View the measure list (or open the report).

**[EXPECT]** The new measure **"New Subscriber Growth %"** is present.

**[SAY]** "The measure is now live in Production. Let's test it in the report."

**[Screen: Power BI Report (Prod)]**

**[DO]** Open `rpt_hearst_exec` report.

**[DO]** Add a card visual (or table) showing the new measure: **New Subscriber Growth %**.

**[EXPECT]** The visual displays a percentage (e.g., "2.34%").

**[SAY]** "This measure is now live for all users. And remember — because we're using Direct Lake, this is reading directly from the lakehouse. No refresh delay, no data movement."

---

### ACT 9: Test the Data Agent with the New Measure (2 minutes)

**[Screen: Fabric Portal — Data Agent in Prod]**

**[DO]** Open `agent_hearst_analytics` in Prod workspace.

**[TYPE]** In the agent chat: **"What is our new subscriber growth rate for Cosmopolitan?"**

**[EXPECT]** The agent responds:
> "Cosmopolitan's new subscriber growth rate is 2.12%. This is based on 105 new subscribers and 4,963 active subscribers."

**[SAY]** "The agent automatically discovered the new measure and can now answer questions about it — without any manual configuration or retraining. That's the power of semantic layer + AI."

---

### CLOSING: Summary & Recap (2 minutes)

**[Screen: Architecture diagram or slide deck]**

**[SAY]** "Let me recap what we just saw in under 10 minutes of automation:
1. **Added a new DAX measure** in VS Code
2. **Opened a pull request** → CI validated the schema and detected no issues
3. **Merged to main** → CD synced the change to Dev automatically
4. **Promoted to UAT** → Quality gates validated data integrity and DAX correctness
5. **Approved for Prod** → Manual gate ensured human oversight
6. **Deployed to Prod** → The measure is now live in reports and the data agent

This entire flow is:
- **Automated**: No manual deployments or copy-paste errors
- **Gated**: Quality checks prevent bugs from reaching Production
- **Auditable**: Every change is tracked in Git with commit history
- **Fast**: From PR merge to Prod deployment in under 15 minutes

And the best part? This works for **any Fabric item** — notebooks, warehouses, pipelines, semantic models, reports, even data agents."

**[Screen: GitHub Repo — README.md or docs/]**

**[SAY]** "If you want to try this yourself, the entire solution is open-source and available in this repository. It includes:
- Terraform for infrastructure provisioning
- GitHub Actions for CI/CD orchestration
- Python scripts for Fabric API automation
- A complete medallion architecture with synthetic data
- And a step-by-step runbook for TRIAL capacity setup

Thank you! Questions?"

---

## Fallback Scenarios (What If Things Go Wrong?)

### Scenario 1: Git Sync Fails in Dev

**Symptom:** The `updateFromGit` API call returns an error (e.g., "conflict detected" or "authentication failed").

**[SAY]** "Looks like the Git sync hit an issue. This can happen if someone made a change directly in Fabric instead of going through Git. Let me show you how we handle conflicts."

**[DO]** In Fabric portal (Dev workspace), go to **Source control** → **View conflicts**.

**[SAY]** "We can see which items have conflicts. We resolve them by choosing either 'Git version' or 'Workspace version'. For our CI/CD workflow, Git is the source of truth, so we'd choose 'Git version'."

**[DO]** Select "Git version" and resolve the conflict.

**[SAY]** "In a real production scenario, we'd investigate why someone bypassed Git and remind the team that all changes must go through pull requests."

---

### Scenario 2: UAT Quality Gates Fail

**Symptom:** The `run_uat_tests.py` script exits with code 1 (test failure).

**[SAY]** "Uh-oh, our quality gates caught a problem. This is exactly why we have automated testing — let me show you what failed."

**[Screen: GitHub Actions — test failure logs]**

**[DO]** Expand the failed test step.

**[EXPECT]** Example failure:
```
[ERROR] DAX reconciliation failed: Measure 'New Subscriber Growth %' returned 2.34%, but SQL query returned 2.41% (7% relative difference, exceeds 1% tolerance)
```

**[SAY]** "The test found a mismatch between the DAX measure and the source data. This could mean:
- The DAX formula has a bug (e.g., wrong column reference)
- The lakehouse data has an integrity issue
- The test tolerance is too strict

In a real scenario, I'd:
1. Investigate the root cause (review the DAX formula and SQL query)
2. Fix the issue in Dev (either the measure or the ETL logic)
3. Open a new PR with the fix
4. Re-run the promotion workflow

The key point: **bad code never reaches Production**. The quality gates blocked it."

---

### Scenario 3: Deployment Takes Too Long

**Symptom:** The deployment is stuck at "Deploying..." for more than 5 minutes.

**[SAY]** "Looks like the deployment is taking longer than expected. This can happen if:
- Fabric is under heavy load (rare)
- The workspace has a large number of items (notebooks, datasets, reports)
- A long-running operation (LRO) is stuck

Let me check the deployment status via the Fabric API."

**[DO]** Open PowerShell and run:
```powershell
cd scripts
python check_deployment_status.py --pipeline-id <pipeline-id> --deployment-id <deployment-id>
```

**[SAY]** "In a real scenario, we'd either wait for the deployment to complete or cancel it and retry. Fabric deployments are idempotent, so retrying is safe."

---

### Scenario 4: Report Doesn't Render in Prod

**Symptom:** The report opens but shows blank visuals or errors.

**[SAY]** "The report isn't rendering correctly. Let me troubleshoot."

**[DO]** Open the semantic model `sm_hearst_audience` in Prod.

**[DO]** Check the connection info (Settings → Connection).

**[EXPECT]** If the semantic model is in "import mode" instead of "Direct Lake":

**[SAY]** "Aha! The semantic model fell back to import mode. This can happen if:
- The lakehouse connection string is incorrect
- The deployment rules didn't rewrite the lakehouse binding correctly
- Direct Lake mode isn't supported in this environment (e.g., not using Fabric capacity)

Let me verify the deployment rules."

**[DO]** In the deployment pipeline, click **Deployment settings** → **Prod stage** → **Data source rules**.

**[SAY]** "I can see the deployment rule is configured correctly. The issue might be that the lakehouse in Prod is empty — remember, deployment pipelines move **metadata**, not **data**. Let me run the medallion notebooks in Prod to seed the data."

**[DO]** In Prod workspace, run `nb_hearst_bronze_ingest` → `nb_hearst_silver_transform` → `nb_hearst_gold_build`.

**[SAY]** "After the notebooks finish, the report should render correctly."

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
