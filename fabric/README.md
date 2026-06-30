# Fabric Content — Hearst CI/CD Demo

This folder contains Microsoft Fabric items serialized by **Git integration** from the **DEV workspace**.

---

## 🏅 Medallion Architecture — Digital Audience & Subscription Analytics

This project implements a **bronze → silver → gold** medallion architecture for Hearst's digital properties (Cosmopolitan, Esquire, Good Housekeeping, ELLE, Car and Driver).

**Data Product:** Hearst Digital Audience & Subscription Analytics  
**Target:** Direct Lake-optimized star schema for real-time Power BI reporting  
**Volume:** ~90 days of synthetic data (~650K events, 50K subscribers, 2K content items)

---

## 📦 Items in this project

### Medallion Notebooks

| Item | Type | Layer | Purpose |
|------|------|-------|---------|
| **nb_hearst_bronze_ingest** | Notebook | Bronze | Generate synthetic raw data: `raw_engagement`, `raw_subscriptions`, `raw_ad_impressions`, `raw_content` |
| **nb_hearst_silver_transform** | Notebook | Silver | Cleanse & conform: deduplication, type enforcement, surrogate keys |
| **nb_hearst_gold_build** | Notebook | Gold | Build star schema: 6 dimensions + 3 facts optimized for Direct Lake |

### Lakehouses

| Item | Type | Schema | Purpose |
|------|------|--------|---------|
| **lh_hearst_bronze** | Lakehouse | `bronze` | Raw data landing zone; unstructured/semi-structured ingestion |
| **lh_hearst_gold** | Lakehouse | **`gold`** ⭐ | **Direct Lake source** — dimensional star schema for Power BI semantic models |

### Legacy Items (for CI/CD demonstration)

| Item | Type | Schema / Content | Purpose |
|------|------|------------------|---------|
| **nb_hearst_ingest** | Notebook | PySpark ingestion to `lh_hearst_bronze.bronze.sample_events` | Original demo notebook (preserved for CI/CD workflow validation) |
| **wh_hearst** | Warehouse | Schema: `sales` <br> Tables: `customer`, `order` <br> View: `v_sales_summary` | Analytical warehouse for sales reporting |
| **sqldb_hearst** | SQL Database | Schema: `app` <br> Table: `config` | Application configuration store |

---

## ⚠️ CRITICAL: Metadata vs. Data

**Fabric Deployment Pipelines move METADATA, not DATA.**

- ✅ **What IS promoted:** item definitions, notebook code, schema DDL, view/function definitions
- ❌ **What is NOT promoted:** lakehouse tables/rows, warehouse data rows, Delta files, shortcuts

### Data seeding strategy (per stage)

Each environment (DEV / UAT / PROD) must independently:

1. **Execute DDL** (Warehouse/SQL DB): Run the `definition/ddl.sql` scripts post-deploy to create schemas and tables.
2. **Seed configuration data**: Insert environment-specific values (see SQL comments for templates).
3. **Run ingestion notebooks**: Execute `nb_hearst_ingest` (or similar) to populate lakehouse tables.
4. **Configure shortcuts**: Point to stage-specific ADLS Gen2 / OneLake paths if using external data.

**Recommendation:** Automate post-deploy seeding via a GitHub Actions step that:
- Executes DDL scripts using the Fabric SQL endpoint REST API or ODBC
- Runs seed notebooks via the Fabric Jobs API
- Validates schema with test queries (see `/tests` folder)

---

## 📐 Medallion Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🥉 BRONZE LAYER — Raw Data Ingestion                                   │
│                                                                          │
│  nb_hearst_bronze_ingest.Notebook (PySpark synthetic generator)         │
│    ↓ Generates ~90 days of deterministic synthetic data                 │
│  lh_hearst_bronze.Lakehouse (schema: bronze)                            │
│    - raw_engagement      (~500K events: page views, sessions)           │
│    - raw_subscriptions   (50K subscribers: signups, plans, churn)       │
│    - raw_ad_impressions  (~100K impressions: campaigns, revenue)        │
│    - raw_content         (2K articles: brands, sections, authors)       │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🥈 SILVER LAYER — Cleansed & Conformed                                 │
│                                                                          │
│  nb_hearst_silver_transform.Notebook                                    │
│    - Deduplication by natural keys                                      │
│    - Type enforcement & null handling                                   │
│    - Surrogate key generation (content_key, subscriber_key)             │
│    - Audit columns (load_timestamp)                                     │
│  lh_hearst_silver.Lakehouse (schema: silver) — NOT YET CREATED          │
│    - silver_engagement, silver_subscriptions, silver_ad_impressions,    │
│      silver_content                                                     │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🥇 GOLD LAYER — Star Schema for Direct Lake                            │
│                                                                          │
│  nb_hearst_gold_build.Notebook                                          │
│    - Builds dimensional star schema                                     │
│    - Optimized for Direct Lake (INT keys, no complex types)             │
│  lh_hearst_gold.Lakehouse (schema: gold) ⭐ DIRECT LAKE SOURCE          │
│                                                                          │
│  DIMENSIONS (Type-2 SCD ready):                                         │
│    - dim_date       (date_key, date, year, quarter, month, weekday)    │
│    - dim_brand      (brand_key, brand_name) [5 Hearst brands]          │
│    - dim_content    (content_key, title, section, content_type)        │
│    - dim_subscriber (subscriber_key, signup_date_key, plan, region)    │
│    - dim_platform   (platform_key, platform) [web, ios, android]       │
│    - dim_campaign   (campaign_key, campaign_name, advertiser)          │
│                                                                          │
│  FACTS (Additive measures):                                             │
│    - fct_engagement    (date_key, brand_key, content_key,               │
│                         subscriber_key, platform_key, page_views,       │
│                         sessions, time_on_page_sec)                     │
│    - fct_subscription  (date_key, brand_key, subscriber_key,            │
│                         active_flag, new_flag, churned_flag, mrr)       │
│    - fct_ad            (date_key, brand_key, campaign_key,              │
│                         platform_key, impressions, clicks, ad_revenue)  │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          [Power BI Semantic Model]
                          (Direct Lake mode — no ETL!)
```

### Legacy / CI/CD Demo Items

```
┌─────────────────────────────────────┐
│   wh_hearst.Warehouse               │ (Sales analytics — legacy)
│   Schema: sales                      │
│   Tables: customer, order            │
│   View: v_sales_summary              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   sqldb_hearst.SQLDatabase          │ (Config store — legacy)
│   Schema: app                        │
│   Table: config                      │
└─────────────────────────────────────┘
```

---

## 🔧 Deployment rules (parameterization)

When promoting from DEV → UAT → PROD, **deployment rules** rewrite environment-specific bindings:

| Binding type | Example | Purpose |
|--------------|---------|---------|
| Lakehouse default | `nb_hearst_ingest` → lakehouse reference | Point to UAT/PROD lakehouse instead of DEV |
| Warehouse connection | Embedded SQL in notebooks | Rewrite connection strings per stage |
| SQL DB connection | Application config | Rewrite API endpoints, feature flags |
| Data source paths | Shortcuts to ADLS | Point to UAT/PROD storage accounts |

**Implementation:** Use the `set_deployment_rules.py` script (see `/scripts`) to configure these bindings
via the Fabric Deployment Pipeline REST API after Terraform creates the pipeline.

---

## 🚀 Git sync workflow

1. **Develop in DEV workspace** (only workspace connected to Git)
2. **Commit to Git** from the Fabric portal or via API
3. **GitHub Actions** (on merge to `main`) calls `updateFromGit` to sync changes back to DEV
4. **Deploy API** promotes changes from DEV → UAT → PROD via the deployment pipeline
5. **Post-deploy hooks** execute DDL and seed scripts in each target stage

---

## 📁 Item folder structure

Each Fabric item is serialized as a folder with:

- **`.platform`** — JSON metadata (type, displayName, logicalId)
- **Item-specific files:**
  - Notebook: `notebook-content.py` (or `.ipynb`)
  - Lakehouse: `lakehouse.metadata.json`, `shortcuts.metadata.json`
  - Warehouse: `definition/ddl.sql`
  - SQL Database: `definition/ddl.sql`

**Example:**
```
fabric/
├─ nb_hearst_ingest.Notebook/
│  ├─ .platform
│  └─ notebook-content.py
├─ lh_hearst_bronze.Lakehouse/
│  ├─ .platform
│  └─ lakehouse.metadata.json
├─ wh_hearst.Warehouse/
│  ├─ .platform
│  └─ definition/
│     └─ ddl.sql
└─ sqldb_hearst.SQLDatabase/
   ├─ .platform
   └─ definition/
      └─ ddl.sql
```

---

## 🧪 Testing strategy

See `/tests` folder for:

- **Schema validation notebooks** (run in UAT post-deploy)
- **T-SQL assertion scripts** (verify table existence, row counts, constraints)
- **Data quality checks** (Great Expectations / pytest on sample data)

**Workflow:** The `cd-promote-uat.yml` GitHub Actions workflow automatically runs the UAT test suite
after deploying DEV → UAT. Failures block promotion to PROD.

---

## 📚 References

- [Fabric Deployment Pipelines](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines)
- [Fabric Git Integration](https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration)
- [Lakehouse schema-enabled mode](https://learn.microsoft.com/fabric/data-engineering/lakehouse-schemas)
- [Fabric Warehouse T-SQL reference](https://learn.microsoft.com/fabric/data-warehouse/tsql-surface-area)

---

---

## 🎯 Direct Lake Optimization

The **gold layer star schema** is specifically designed for Direct Lake semantic models:

- ✅ **Schema-enabled lakehouse** with explicit `gold` schema
- ✅ **Integer surrogate keys** (not BIGINT) — Direct Lake optimized
- ✅ **No complex types** (arrays, structs) — all scalar columns
- ✅ **Conformed dimensions** shared across facts (snowflake-free)
- ✅ **Additive measures** with proper granularity
- ✅ **Date dimension** with calendar attributes (year, quarter, month, weekday)
- ✅ **Delta table format** via `saveAsTable()` with schema prefix

**Connect a Power BI semantic model to `lh_hearst_gold` and point to the `gold` schema** for zero-ETL real-time reporting.

---

## 🧪 Local Testing

For local development and validation without Fabric Spark, use the standalone generator:

```bash
# Generate synthetic CSVs locally
python data/generate_synthetic.py

# Output: data/seed/raw_*.csv (4 files, ~650K total records)
```

The local generator produces identical data to the bronze notebook (same deterministic seed), useful for:
- Pre-flight validation before Fabric deployment
- Unit testing transformation logic
- Data profiling and schema verification
- Local pandas/polars prototyping

---

## 📊 Data Volumes (per environment)

| Layer | Tables | Records | Storage (approx) |
|-------|--------|---------|------------------|
| Bronze | 4 raw tables | ~650K | ~50 MB (Delta) |
| Silver | 4 cleansed tables | ~650K | ~50 MB (Delta) |
| Gold | 6 dims + 3 facts | ~660K | ~55 MB (Delta) |

**Note:** These are synthetic volumes for demo purposes. Production Hearst data would scale to billions of events.

---

## 🔄 Medallion Execution Order

**Run notebooks in sequence:**

1. **Bronze**: `nb_hearst_bronze_ingest` — generates raw data (~5-10 min)
2. **Silver**: `nb_hearst_silver_transform` — cleanses & conforms (~3-5 min)
3. **Gold**: `nb_hearst_gold_build` — builds star schema (~5-8 min)

**Total runtime: ~15-25 minutes** (one-time per environment; incremental refresh TBD)

**Automation:** Post-deployment hooks in GitHub Actions should execute these notebooks via Fabric Jobs API to seed UAT/Prod after promotion.

---

**Last updated:** 2026-06-23  
**Medallion architecture complete:** Bronze → Silver → Gold with Direct Lake-optimized star schema
