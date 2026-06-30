# UAT Test Suite

This directory contains the **User Acceptance Testing (UAT)** suite that gates promotion from Dev → UAT → Prod in the Hearst Fabric CI/CD pipeline.

## Philosophy

> **The deployment pipeline only proves *deployability*; tests prove *correctness*.**

When the CD workflow deploys from Dev to UAT, it automatically runs this test suite via `scripts/run_uat_tests.py`. If **any test fails**, promotion to Production is **BLOCKED** (the workflow exits nonzero).

---

## Layered Quality Gates

The Hearst pipeline enforces a **three-layer quality gate strategy**:

| Layer | When | Tool | What It Validates |
|-------|------|------|-------------------|
| **CI Gate** | PR (before merge) | BPA + Terraform validate + Gitleaks | Semantic model schema, DAX syntax, naming conventions, Direct Lake config, secrets scanning |
| **UAT Gate** | Dev→UAT promotion | Data quality + DAX reconciliation | Runtime correctness: gold lakehouse data integrity + semantic model measures match source data |
| **Prod Gate** | UAT→Prod promotion | Smoke test | Basic connectivity and query execution (minimal sanity check) |

### Gate Philosophy

1. **CI catches structural/syntactic errors** before they reach Dev
2. **UAT validates runtime correctness** after deployment (data + measures)
3. **Prod verifies deployment success** without re-running full UAT suite

---

## Test Components

### 0. CI Gate: Best Practice Analyzer (`tests/semantic_model/`)

**`bpa_rules.json`** — Best Practice Analyzer ruleset for `sm_hearst_audience`:
- **Measures must have formatString** (severity 2)
- **No calculated columns where measure suffices** (performance, severity 1)
- **Relationships valid** (no inactive-rel ambiguity, severity 3)
- **Naming conventions** (foreign keys end with `_key`, severity 1)
- **Hidden foreign keys** (usability, severity 1)
- **Dimension tables have primary key** (integrity, severity 2)
- **No orphan measures** (measures on dim tables, severity 1)
- **Direct Lake partition mode** (all tables use DirectLake, severity 3)
- **Direct Lake expressionSource** (must reference `lh_hearst_gold`, severity 3)

**`run_bpa.md`** — Documentation and CLI commands for running BPA with Tabular Editor 2.

**Execution:** Runs in **CI workflow** (`ci-validate.yml`) on every PR. Uses Tabular Editor 2 CLI to analyze the TMDL model definition. Exits nonzero on violations with severity ≥ 2 (warnings/errors).

**Purpose:** Catch semantic model definition errors (syntax, schema, naming) **before** they reach Dev workspace.

---

### 1. Validation Notebooks (`tests/notebooks/`)

**`nb_validate_ingest.py`** — PySpark notebook that asserts:
- Lakehouse `lh_hearst_bronze` and table `bronze.sample_events` exist and are accessible
- Table has at least 1 row (not empty after deployment)
- Expected columns are present (`event_id`, `event_timestamp`, `event_type`, `user_id`)
- No NULLs in critical columns

**Execution:** Triggered via Fabric Job/Run API (long-running operation); polled until completion.

---

### 2. SQL Assertions (`tests/sql/`)

**`assert_warehouse.sql`** — Warehouse schema/table checks:
- `sales` schema exists
- `sales.customer` and `sales.order` tables exist
- Tables are not empty
- Optional: referential integrity checks

**`assert_sqldb.sql`** — SQL Database schema/table checks:
- `app` schema exists
- `app.config` table exists
- Table is not empty

**Execution:** Run via `sqlcmd` (or pyodbc) against the Fabric SQL endpoints; failures use `RAISERROR` to return nonzero exit codes.

---

### 3. Data Quality Tests — Warehouse (`tests/data_quality/test_data_quality.py`)

**`test_data_quality.py`** — Pytest-style checks (pyodbc → Warehouse SQL endpoint):
- **NULL checks:** No NULLs in primary key columns (`customer_id`, `order_id`)
- **Uniqueness:** Primary keys are unique (no duplicates)
- **Referential integrity:** `sales.order.customer_id` values exist in `sales.customer`
- **Business rules:** e.g., order amounts are non-negative (if column exists)

**Execution:** `pytest tests/data_quality/test_data_quality.py -v` — any assertion failure → nonzero exit.

**Dependencies:** Installed from `tests/data_quality/requirements.txt` (pytest, pyodbc, requests).

---

### 4. Data Quality Tests — Gold Lakehouse (`tests/data_quality/test_gold_quality.py`)

**Gold star schema checks** (pyodbc → lh_hearst_gold SQL endpoint):
- **Table existence:** All dims and facts exist and have rows > 0
- **No NULL surrogate keys:** `*_key` columns have no NULLs
- **Dimension uniqueness:** Primary keys are unique (no duplicates)
- **Referential integrity:** Every fact `*_key` exists in its dimension
- **Date continuity:** `dim_date` has no gaps (consecutive dates)
- **Non-negative measures:** `page_views`, `sessions`, `mrr`, `impressions`, `clicks`, `ad_revenue` ≥ 0
- **Business rules:** `clicks ≤ impressions` (impossible to have more clicks than impressions)

**Execution:** `pytest tests/data_quality/test_gold_quality.py -v` — any assertion failure → nonzero exit.

---

### 5. DAX Reconciliation (`tests/semantic_model/dax_reconciliation.py`)

**Semantic model measure validation** — reconciles DAX measures against gold lakehouse source data:

| Measure | DAX Expression | SQL Reconciliation |
|---------|---------------|-------------------|
| Page Views | `SUM(fct_engagement[page_views])` | `SELECT SUM(page_views) FROM gold.fct_engagement` |
| Sessions | `SUM(fct_engagement[sessions])` | `SELECT SUM(sessions) FROM gold.fct_engagement` |
| MRR | `SUM(fct_subscription[mrr])` | `SELECT SUM(mrr) FROM gold.fct_subscription` |
| Active Subscribers | `DISTINCTCOUNT(fct_subscription[subscriber_key]) WHERE active_flag=1` | `SELECT COUNT(DISTINCT subscriber_key) FROM gold.fct_subscription WHERE active_flag=1` |
| New Subscribers | `COUNTROWS(fct_subscription) WHERE new_flag=1` | `SELECT COUNT(*) FROM gold.fct_subscription WHERE new_flag=1` |
| Churned Subscribers | `COUNTROWS(fct_subscription) WHERE churned_flag=1` | `SELECT COUNT(*) FROM gold.fct_subscription WHERE churned_flag=1` |
| Ad Revenue | `SUM(fct_ad[ad_revenue])` | `SELECT SUM(ad_revenue) FROM gold.fct_ad` |
| Ad Impressions | `SUM(fct_ad[impressions])` | `SELECT SUM(impressions) FROM gold.fct_ad` |
| Ad Clicks | `SUM(fct_ad[clicks])` | `SELECT SUM(clicks) FROM gold.fct_ad` |

**Connection methods:**
- **DAX:** Fabric REST API `executeQueries` endpoint (XMLA-compatible)
- **SQL:** pyodbc → lh_hearst_gold SQL endpoint

**Tolerance:** ±1% relative difference (handles floating-point rounding)

**Execution:** `python tests/semantic_model/dax_reconciliation.py` — exits nonzero if any measure fails reconciliation.

**Purpose:** This is the **final UAT gate** — it proves the semantic model is mathematically correct and matches the gold lakehouse data. If this fails, the model definition or ETL logic has a bug.

---

## Orchestration

**`scripts/run_uat_tests.py`** is the master orchestrator:
1. Acquires a Fabric API bearer token (SP client credentials)
2. Triggers the validation notebook run via Fabric Job/Run API (polls LRO)
3. Executes SQL assertion scripts against Warehouse and SQL Database
4. Runs pytest warehouse data-quality checks
5. Runs pytest gold lakehouse quality checks
6. Runs DAX reconciliation (semantic model vs gold tables)
7. Aggregates results and **exits nonzero if anything fails** → blocks promotion

### Environment Variables

The test suite requires:
```bash
AZURE_CLIENT_ID              # Service principal client ID
AZURE_CLIENT_SECRET          # Service principal secret (from Key Vault)
AZURE_TENANT_ID              # Azure AD tenant ID
FABRIC_UAT_WORKSPACE_ID      # The UAT workspace GUID
FABRIC_WAREHOUSE_ENDPOINT    # e.g., <workspace>.datawarehouse.fabric.microsoft.com
FABRIC_SQLDB_ENDPOINT        # (optional) SQL Database endpoint if separate
FABRIC_SQL_ENDPOINT          # lh_hearst_gold lakehouse SQL endpoint
FABRIC_SEMANTIC_MODEL_ID     # sm_hearst_audience semantic model GUID
```

> **Security:** Secrets are **never hardcoded**. They are sourced from Azure Key Vault and passed as GitHub Environment secrets at workflow runtime.

## Local Testing

To run the UAT suite locally (for development/debugging):

1. **Install dependencies:**
   ```bash
   pip install -r tests/data_quality/requirements.txt
   ```

2. **Set environment variables** (use UAT workspace values from Key Vault):
   ```bash
   export AZURE_CLIENT_ID="..."
   export AZURE_CLIENT_SECRET="..."
   export AZURE_TENANT_ID="..."
   export FABRIC_UAT_WORKSPACE_ID="..."
   export FABRIC_WAREHOUSE_ENDPOINT="..."
   export FABRIC_SQL_ENDPOINT="..."
   export FABRIC_SEMANTIC_MODEL_ID="..."
   ```

3. **Run the orchestrator:**
   ```bash
   python scripts/run_uat_tests.py
   ```

   Exit code 0 = all tests passed; exit code 1 = failures detected.

## CI/CD Integration

### Workflow: `cd-promote-uat.yml`

```yaml
- name: Run UAT Test Suite
  env:
    AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
    AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
    AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    FABRIC_UAT_WORKSPACE_ID: ${{ secrets.FABRIC_UAT_WORKSPACE_ID }}
    FABRIC_WAREHOUSE_ENDPOINT: ${{ secrets.FABRIC_WAREHOUSE_ENDPOINT }}
    FABRIC_SQL_ENDPOINT: ${{ secrets.FABRIC_SQL_ENDPOINT }}
    FABRIC_SEMANTIC_MODEL_ID: ${{ secrets.FABRIC_SEMANTIC_MODEL_ID }}
  run: python scripts/run_uat_tests.py

- name: Block promotion on test failure
  if: failure()
  run: |
    echo "❌ UAT tests failed — promotion to Production BLOCKED"
    exit 1
```

### Promotion Gate

- **Dev → UAT:** Deployment proceeds automatically; UAT tests run afterward.
- **UAT → Prod:** If UAT tests **FAIL**, the workflow stops and does not trigger `cd-promote-prod.yml`.
- **Prod smoke test:** After Prod deployment, a minimal smoke test verifies basic connectivity (not a full UAT re-run).

---

## Smoke Test vs UAT

| Aspect | UAT Suite (run_uat_tests.py) | Smoke Test (Prod) |
|--------|------------------------------|-------------------|
| **Scope** | Comprehensive: notebooks, SQL assertions, data quality, DAX reconciliation | Minimal: connectivity + basic query |
| **Duration** | Minutes (notebook LRO + pytest + DAX queries) | Seconds (quick sanity check) |
| **Failure mode** | Blocks promotion to Prod | Alerts + rollback (optional) |
| **Purpose** | Gate promotion: prove correctness | Verify Prod deploy succeeded |

---

## Test Coverage

| Item Type | CI Gate (BPA) | UAT Gate (Data Quality + DAX) |
|-----------|---------------|-------------------------------|
| **Semantic Model** | Schema, naming, DAX syntax, Direct Lake config, measure formatString, relationship validity | DAX measure reconciliation vs gold lakehouse source data |
| **Gold Lakehouse** | — | Table existence, row counts, NULL checks, dimension uniqueness, referential integrity, date continuity, non-negative measures, business rules |
| **Warehouse** | — | Schema/table existence, row counts, referential integrity, NULL checks, uniqueness |
| **SQL Database** | — | Schema/table existence, row counts |
| **Lakehouse (Bronze)** | — | Table existence, row count, schema validation |
| **Notebooks** | — | Execution validation (can run in UAT, assertions pass) |

---

## Extending the Suite

To add new tests:

1. **BPA rules (CI):** Edit `tests/semantic_model/bpa_rules.json` to add new rules (use DAX expression syntax); test locally with Tabular Editor 2 CLI before committing.
2. **Notebooks:** Add new `.py` files under `tests/notebooks/` (use `# CELL` markers for Fabric notebook format).
3. **SQL assertions:** Add new `.sql` files under `tests/sql/`; use `RAISERROR` for failures.
4. **Data quality:** Add new pytest test methods to `test_data_quality.py` or `test_gold_quality.py`, or create new test modules.
5. **DAX reconciliation:** Add new measures to the `tests` list in `dax_reconciliation.py` with corresponding SQL queries.
6. **Update orchestrator:** Modify `scripts/run_uat_tests.py` to include new test execution logic (if adding a new test category).

---

## Known Limitations

- **BPA CLI (CI):** Requires Tabular Editor 2 installation (Windows runners recommended for GitHub Actions). Linux runners require Mono/Wine.
- **Notebook run API:** The current implementation uses a placeholder for the Fabric Job/Run API; the actual endpoint and payload structure depend on the notebook item ID. Implement with:
  ```python
  POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/notebooks/{notebookId}/jobs/instances
  ```
  Poll the returned run ID until completion.

- **SQL execution:** The orchestrator currently simulates SQL script execution. Implement with `sqlcmd` (requires ODBC driver) or `pyodbc` for portability:
  ```python
  conn = pyodbc.connect(conn_str)
  with open(script_path) as f:
      cursor.executescript(f.read())
  ```

- **DAX executeQueries API:** The Fabric REST API `executeQueries` endpoint is relatively new (as of 2024). Fallback: use XMLA endpoint with `pyadomd` (requires ADOMD.NET client).
- **Lakehouse data seeding:** The deployment pipeline deploys **metadata** (schemas, tables), not **data**. If UAT requires seed data, add a data-loading step before running tests (e.g., a notebook that copies sample rows from a known source).

---

## Support

For questions or issues with the UAT suite, contact:
- **the quality engineering team** — owns test suite design, execution, and gates
- **the platform engineering team** — owns CI/CD workflow integration and orchestration scripts
- **the data engineering team** — owns Fabric content definitions that tests validate
