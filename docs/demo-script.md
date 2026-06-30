# Demo Script — Hearst Fabric CI/CD

**A click-by-click walkthrough for presenting the Hearst Fabric CI/CD demo live.**

Use this script to demonstrate the end-to-end flow: from a code change in GitHub → Dev sync → UAT testing → Production release.

---

## Pre-Demo Setup (30 minutes before presentation)

### 1. Verify All Infrastructure is Running
```powershell
# Check Terraform outputs
cd infra
terraform output

# Expected outputs:
# - dev_workspace_id, uat_workspace_id, prod_workspace_id
# - deployment_pipeline_id
# - service_principal_client_id
```

### 2. Confirm GitHub Secrets are Configured
```powershell
gh secret list --env Development
gh secret list --env UAT
gh secret list --env Production
```

Expected secrets in each environment:
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `FABRIC_CLIENT_SECRET`
- `<ENV>_WORKSPACE_ID` (e.g., `DEV_WORKSPACE_ID`)
- `DEPLOYMENT_PIPELINE_ID` (UAT and Production only)

### 3. Open Browser Tabs (for smooth demo flow)
- **Tab 1:** GitHub repository (`main` branch view)
- **Tab 2:** GitHub Actions page
- **Tab 3:** Fabric Portal → Dev workspace
- **Tab 4:** Fabric Portal → UAT workspace
- **Tab 5:** Fabric Portal → Prod workspace
- **Tab 6:** Fabric Portal → Deployment Pipeline view

### 4. Prepare a Sample Change
Create a feature branch with a small, visible change (e.g., add a comment to a notebook or add a new SQL table):

```powershell
git checkout main
git pull
git checkout -b demo/add-comment
```

Edit `fabric/nb_hearst_ingest.Notebook/notebook-content.py`:
```python
# Demo change: Log ingestion start time
print(f"[DEMO] Ingestion started at {datetime.now()}")
```

**Do NOT commit yet** — you'll do this live during the demo.

### 5. Reset UAT and Prod (Optional, for Clean Demo)
If you've run the demo before, reset UAT and Prod to a known baseline:
1. Manually delete items in UAT and Prod workspaces (or use Fabric API script)
2. Re-deploy a "baseline" version from Dev → UAT → Prod

This ensures the demo shows a clean promotion with visible changes.

---

## Demo Flow (20-25 minutes)

### INTRO: Set the Stage (2 minutes)

**What to say:**
> "Today I'm showing you Hearst's Microsoft Fabric CI/CD pipeline. The goal is to demonstrate a fully automated, GitHub-driven deployment flow across three environments: Development, UAT, and Production.
>
> The architecture uses native Fabric Deployment Pipelines for promotion, with GitHub Actions orchestrating the automation. Only the Dev workspace is Git-connected; UAT and Prod receive content exclusively via the pipeline, which prevents two competing sources of truth.
>
> Let's walk through a real change: I'll edit a notebook, open a pull request, merge it, and watch it flow all the way to Production — with automated testing in UAT and a manual approval gate before Prod."

**Screen:** Show the architecture diagram (from README.md or a slide).

---

### STEP 1: Make a Code Change (3 minutes)

**What to do:**
1. **Screen:** GitHub repo, `main` branch
2. **Say:** "First, I'll create a feature branch and make a small change to our ingestion notebook."
3. In terminal:
   ```powershell
   git checkout -b demo/add-comment
   ```
4. Open `fabric/nb_hearst_ingest.Notebook/notebook-content.py` in VS Code (share your screen)
5. Add a visible change:
   ```python
   # Demo: Log ingestion start timestamp
   print(f"[DEMO] Ingestion started at {datetime.now()}")
   ```
6. **Say:** "This is a simple logging statement. In a real scenario, this could be a new data transformation, a schema change, or a bug fix."
7. Commit and push:
   ```powershell
   git add .
   git commit -m "Add ingestion start timestamp logging"
   git push -u origin demo/add-comment
   ```

**What to say:**
> "Now I've pushed my branch to GitHub. Let's open a pull request."

---

### STEP 2: Open a Pull Request & Watch CI Run (4 minutes)

**What to do:**
1. **Screen:** GitHub repo → Pull Requests
2. Click **New pull request**
   - Base: `main`
   - Compare: `demo/add-comment`
3. **Title:** "Add ingestion start timestamp logging"
4. **Description:** "Demo change: adds a log statement to track when ingestion begins."
5. Click **Create pull request**
6. **Screen:** GitHub Actions tab (show the `ci-validate` workflow starting)

**What to say:**
> "The moment I opened the PR, our CI workflow kicked off. It's running:
> - **Notebook linting** (flake8, black) to catch code quality issues
> - **JSON validation** on the `.platform` files (Fabric item metadata)
> - **Terraform plan** to ensure infrastructure changes (if any) are valid
>
> This is our first quality gate. No changes reach `main` unless they pass CI."

7. Wait for CI to complete (~1-2 minutes)
8. **Screen:** Show the green checkmark ✅ next to the workflow
9. **Say:** "CI passed! Now I'll merge the PR."
10. Click **Merge pull request** → **Confirm merge**

**What to say:**
> "The change is now in `main`. Let's see what happens next."

---

### STEP 3: Dev Workspace Syncs Automatically (2 minutes)

**What to do:**
1. **Screen:** GitHub Actions → `cd-dev-sync` workflow (should auto-trigger on merge to `main`)
2. Click the running workflow to show logs

**What to say:**
> "The merge to `main` triggered our Dev sync workflow. It's calling the Fabric API — specifically, `POST /workspaces/{dev-id}/git/updateFromGit` — to pull the latest code from GitHub into the Dev workspace.
>
> This is an **explicit, deterministic sync**. We control exactly when Dev reflects `main`, which makes downstream promotions predictable."

3. Wait for workflow to complete (~30 seconds)
4. **Screen:** Fabric Portal → Dev workspace
5. Open the notebook (`nb_hearst_ingest`)
6. **Say:** "Let's verify the change landed in Dev."
7. Scroll to the added line in the notebook code → **highlight the new log statement**

**What to say:**
> "There it is! The Dev workspace now has our logging change. This is the single source of truth. Now let's promote it to UAT."

---

### STEP 4: Promote to UAT & Run Tests (5 minutes)

**What to do:**
1. **Screen:** GitHub Actions → Workflows
2. Click **Run workflow** → Select `cd-promote-uat.yml` → **Run workflow**

**What to say:**
> "I'm manually triggering the UAT promotion. In production, you'd likely chain this automatically after Dev sync. The workflow will:
> 1. Apply **deployment rules** (parameterization for UAT — e.g., rewriting lakehouse bindings)
> 2. Call the **Fabric Deployment Pipeline API** to deploy from Dev to UAT
> 3. Run **automated tests** in UAT — validation notebooks, SQL assertions, data quality checks
>
> If any test fails, the workflow stops, and we don't promote to Prod."

3. **Screen:** Watch the workflow logs in real-time
4. **Highlight key log lines:**
   - `🔧 Applying UAT deployment rules...`
   - `🚀 Deploying Dev → UAT (deployment ID: <id>)...`
   - `⏳ Polling LRO: status=Running...`
   - `✅ Deployment succeeded!`
   - `🧪 Running UAT tests...`
   - `✅ UAT tests passed (12/12)`

5. **Screen:** Fabric Portal → UAT workspace
6. Open the notebook in UAT
7. **Say:** "Let's confirm the change is in UAT."
8. Scroll to the new log statement → **highlight it**

**What to say:**
> "Perfect! The notebook in UAT now has our change, and all tests passed. This means UAT is stable and ready for production release."

---

### STEP 5: Approve & Promote to Production (5 minutes)

**What to do:**
1. **Screen:** GitHub Actions → Workflows
2. Click **Run workflow** → Select `cd-promote-prod.yml` → **Run workflow**
3. **Screen:** Show the workflow pausing with status **"Waiting for approval"**

**What to say:**
> "Here's our **manual approval gate**. The workflow calls GitHub Environments protection rules. Before deploying to Production, a human must review and approve the release.
>
> This is critical for governance. Even in a highly automated pipeline, you want a final checkpoint before changes go live."

4. **Screen:** Click the workflow run → Click **Review deployments**
5. **Say:** "In a real scenario, I'd review:
   - UAT test results (already passed)
   - The change log (what's in this release)
   - Any business considerations (e.g., is it a safe time to deploy?)
>
> For this demo, I'll approve it now."

6. Check **Production** → Click **Approve and deploy**
7. **Screen:** Show the workflow resuming
8. **Highlight key log lines:**
   - `🔓 Approval received, proceeding to Production deployment`
   - `🔧 Applying Prod deployment rules...`
   - `🚀 Deploying UAT → Prod (deployment ID: <id>)...`
   - `✅ Deployment succeeded!`
   - `🧪 Running Prod smoke tests...`
   - `✅ Smoke tests passed`

9. **Screen:** Fabric Portal → Prod workspace
10. Open the notebook in Prod
11. **Say:** "And there's our change in Production!"
12. Scroll to the new log statement → **highlight it**

**What to say:**
> "We've now completed the full cycle:
> - Code change in GitHub
> - CI validation on PR
> - Automatic sync to Dev on merge
> - Promotion to UAT with automated testing
> - Manual approval
> - Deployment to Production with smoke tests
>
> The entire flow is auditable — every deployment has a GitHub Actions log, and every change is traceable back to a Git commit and PR."

---

### STEP 6: Show the Deployment Pipeline History (2 minutes)

**What to do:**
1. **Screen:** Fabric Portal → Deployment Pipelines → "Hearst Fabric Release"
2. Click **Deployment history**

**What to say:**
> "Fabric tracks every deployment. Here you can see:
> - Who triggered the deployment (our service principal)
> - Which stage it went from/to (Dev → UAT, UAT → Prod)
> - Timestamp and status
> - Which items were deployed
>
> This is your audit trail. If something goes wrong in Prod, you can trace it back to the exact deployment and Git commit."

3. **Optionally:** Click a deployment to show details (items deployed, deployment rules applied)

---

### STEP 7: Demonstrate Rollback (Optional, 3 minutes)

**What to do (if time allows):**
1. **Say:** "Let's say we discover a bug in Production. How do we roll back?"
2. **Screen:** Terminal
3. In Git:
   ```powershell
   git revert <last-commit-sha>
   git push origin main
   ```
4. **Say:** "I've reverted the change in Git. Now I'll re-run the sync and promotion workflows."
5. **Screen:** GitHub Actions → Run `cd-dev-sync.yml`
6. Wait for sync → Run `cd-promote-uat.yml` → (Skip approval for demo) → Run `cd-promote-prod.yml`
7. **Screen:** Fabric Portal → Prod workspace → Show the log statement is gone

**What to say:**
> "Rollback is just another deployment. We revert in Git, sync Dev, promote through UAT (with tests), and release to Prod. The pipeline ensures rollbacks are as safe as forward deployments."

---

### CLOSING: Key Takeaways (2 minutes)

**What to say:**
> "To recap, here's what we demonstrated:
>
> 1. **Git as single source of truth** — All changes start in GitHub; Fabric workspaces reflect what's in Git.
> 2. **Environment isolation** — Only Dev is Git-connected; UAT and Prod receive content via the deployment pipeline, preventing drift.
> 3. **Automated testing** — UAT tests run automatically; failures block production promotion.
> 4. **Manual governance** — A human approval gate before Production, ensuring business alignment.
> 5. **Full auditability** — Every deployment is logged in GitHub Actions and Fabric, traceable to a commit and PR.
> 6. **Infrastructure-as-code** — Terraform provisions workspaces, pipelines, secrets, and Git wiring — repeatable and version-controlled.
>
> This architecture is production-ready. The patterns scale to larger teams, more environments (e.g., add a Pre-Prod stage), and additional Fabric item types (Power BI reports, data pipelines, etc.).
>
> All the code is in the repo, including runbooks, architecture docs, and helper scripts. You can clone it, run `terraform apply`, and have your own CI/CD pipeline in under an hour."

**Screen:** Show the README or repo structure one last time.

---

## Q&A Preparation

### Expected Questions & Answers

#### Q: "What happens if a test fails in UAT?"
**A:** The `cd-promote-uat.yml` workflow exits with failure status. GitHub Actions marks the run as failed, and the promotion to Prod is blocked. The team gets a notification (via email or Slack integration), investigates the failure, fixes it in a new PR, and re-runs the cycle.

#### Q: "Does the deployment pipeline copy data (e.g., lakehouse tables) between environments?"
**A:** No. Fabric Deployment Pipelines move **metadata** (notebook code, schemas, definitions), not data (rows, files). Each environment needs its own data seeding strategy — sample data for Dev/UAT, real data for Prod. We use scripts (`seed_uat_data.py`) or Fabric shortcuts to populate tables.

#### Q: "Can this work with Power BI reports and semantic models?"
**A:** Yes! Deployment pipelines support Power BI items. You'd extend the Terraform to include `fabric_powerbi_report` and `fabric_semantic_model` resources, and the same promotion flow applies. Deployment rules can parameterize data source connections for reports.

#### Q: "How do you handle secrets (e.g., database connection strings)?"
**A:** All secrets live in **Azure Key Vault** (system of record) and are mirrored to **GitHub Environment Secrets** (runtime). The service principal secret is encrypted at rest (AES-256 in Key Vault, libsodium in GitHub). Workflows pull secrets at runtime; they never appear in code or logs (masked via `::add-mask::`). We rotate secrets every 90 days using an automated script. See [docs/secrets-handling.md](secrets-handling.md) for details.

#### Q: "What if someone manually edits an item in UAT or Prod?"
**A:** Manual edits in UAT/Prod are **overwritten** on the next deployment from the pipeline, because the pipeline is the source of truth. This is intentional — it enforces discipline. If you need to make a change, do it in Git (via PR), not in the portal. We lock down UAT/Prod workspace permissions so only the service principal (and emergency admins) can edit.

#### Q: "How long does a full Dev → UAT → Prod deployment take?"
**A:**
- Dev sync: ~30 seconds
- UAT deployment: ~2-3 minutes (deploy + tests)
- Prod deployment: ~2 minutes (deploy + smoke tests)
- **Total (excluding manual approval wait):** ~5-6 minutes

Manual approval typically adds 5-60 minutes (depending on reviewer availability).

#### Q: "Can this be adapted for trunk-based development vs. feature branches?"
**A:** Yes. The demo uses feature branches + PRs for clarity, but trunk-based development works too. You'd:
- Commit directly to `main` (with short-lived branches)
- CI runs on every push to `main`
- Dev syncs immediately
- Promote to UAT/Prod on a schedule or on-demand

The core pattern (Git → Dev → UAT → Prod via pipeline) remains the same.

#### Q: "What about rollbacks? Can you roll back just one item?"
**A:** Yes. The deployment API supports deploying specific items (by item ID). You can:
1. Roll back a single notebook in Git (revert just that file)
2. Deploy only that notebook through the pipeline

Or: Keep a "last known good" Git tag (e.g., `v1.2.0`) and redeploy the entire tag if needed.

---

## Post-Demo Cleanup (Optional)

If you're doing multiple demo runs, reset the environment:

### 1. Delete the Demo Branch
```powershell
git branch -d demo/add-comment
git push origin --delete demo/add-comment
```

### 2. Revert the Change in `main`
```powershell
git revert <last-commit-sha>
git push origin main
```

### 3. Re-sync Dev
```powershell
gh workflow run cd-dev-sync.yml
```

### 4. (Optional) Clear UAT and Prod
Manually delete items in UAT and Prod workspaces, or redeploy a baseline.

---

## Summary

This demo script provides a **repeatable, audience-friendly walkthrough** that shows:
- The value of Git-driven CI/CD for Fabric
- How native Deployment Pipelines integrate with GitHub Actions
- The safety of automated testing + manual approval gates
- Full auditability and rollback capabilities

Tailor the script to your audience (technical vs. business) by adjusting the level of detail in the **"What to say"** sections.

For deeper technical details, point viewers to [architecture.md](architecture.md) and [runbook.md](runbook.md).
