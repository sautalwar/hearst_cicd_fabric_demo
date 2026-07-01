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

**Screen:** Show the architecture diagram (from README.md or a slide).

---

### STEP 1: Make a Code Change (3 minutes)

**What to do:**
1. **Screen:** GitHub repo, `main` branch
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
7. Commit and push:
   ```powershell
   git add .
   git commit -m "Add ingestion start timestamp logging"
   git push -u origin demo/add-comment
   ```

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

7. Wait for CI to complete (~1-2 minutes)
8. **Screen:** Show the green checkmark ✅ next to the workflow
10. Click **Merge pull request** → **Confirm merge**

---

### STEP 3: Dev Workspace Syncs Automatically (2 minutes)

**What to do:**
1. **Screen:** GitHub Actions → `cd-dev-sync` workflow (should auto-trigger on merge to `main`)
2. Click the running workflow to show logs

3. Wait for workflow to complete (~30 seconds)
4. **Screen:** Fabric Portal → Dev workspace
5. Open the notebook (`nb_hearst_ingest`)
7. Scroll to the added line in the notebook code → **highlight the new log statement**

---

### STEP 4: Promote to UAT & Run Tests (5 minutes)

**What to do:**
1. **Screen:** GitHub Actions → Workflows
2. Click **Run workflow** → Select `cd-promote-uat.yml` → **Run workflow**

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
8. Scroll to the new log statement → **highlight it**

---

### STEP 5: Approve & Promote to Production (5 minutes)

**What to do:**
1. **Screen:** GitHub Actions → Workflows
2. Click **Run workflow** → Select `cd-promote-prod.yml` → **Run workflow**
3. **Screen:** Show the workflow pausing with status **"Waiting for approval"**

4. **Screen:** Click the workflow run → Click **Review deployments**

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
12. Scroll to the new log statement → **highlight it**

---

### STEP 6: Show the Deployment Pipeline History (2 minutes)

**What to do:**
1. **Screen:** Fabric Portal → Deployment Pipelines → "Hearst Fabric Release"
2. Click **Deployment history**

3. **Optionally:** Click a deployment to show details (items deployed, deployment rules applied)

---

### STEP 7: Demonstrate Rollback (Optional, 3 minutes)

**What to do (if time allows):**
2. **Screen:** Terminal
3. In Git:
   ```powershell
   git revert <last-commit-sha>
   git push origin main
   ```
5. **Screen:** GitHub Actions → Run `cd-dev-sync.yml`
6. Wait for sync → Run `cd-promote-uat.yml` → (Skip approval for demo) → Run `cd-promote-prod.yml`
7. **Screen:** Fabric Portal → Prod workspace → Show the log statement is gone

---

### CLOSING: Key Takeaways (2 minutes)

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
