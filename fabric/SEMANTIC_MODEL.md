# Hearst Digital Audience & Subscription Analytics — Semantic Model

## Overview

The **sm_hearst_audience** semantic model provides a unified, enterprise-ready star-schema view over Hearst's digital audience engagement, subscription, and advertising data. Built as a **Direct Lake** model, it delivers blazing-fast query performance by reading directly from Delta Lake tables in the `lh_hearst_gold` lakehouse, without importing data into Power BI.

**Key Features:**
- ⚡ **Direct Lake**: Real-time access to lakehouse data with no import delays or refresh windows
- 📊 **Star Schema**: Clean dimension-fact relationships optimized for analytics
- 📈 **15 Pre-built Measures**: Engagement, subscription (including churn & MRR), and advertising KPIs
- 🔄 **Three Fact Tables**: `fct_engagement`, `fct_subscription`, `fct_ad`
- 🏷️ **Six Dimensions**: Date, Brand, Content, Subscriber, Platform, Campaign

---

## Architecture

### Direct Lake Fundamentals

Direct Lake is Microsoft Fabric's breakthrough semantic model mode that combines the best of **DirectQuery** (no data movement) and **Import** (fast queries):

- **No ETL from lakehouse to semantic model** — queries read Delta Parquet files directly via OneLake
- **Automatic V-Order optimization** — columnar compression and statistics for fast scans
- **Frictionless refresh** — just refresh the underlying Delta tables; model sees changes instantly
- **Scales to billions of rows** — unlike Import mode's size limits

**Trade-offs:**
- Requires **Fabric capacity** (F2 or higher) — not available in Power BI Pro/Premium Per User
- Only supports **Delta tables** in Fabric lakehouses (not external data sources)
- Some DAX features are unsupported (though rare in practice)

---

## Star Schema Design

```
              ┌─────────────┐
              │  dim_date   │
              └──────┬──────┘
                     │ date_key
        ┌────────────┼────────────┬───────────┐
        │            │            │           │
┌───────▼──────┐ ┌──▼────────┐ ┌─▼─────────┐ │
│ dim_brand    │ │dim_content│ │dim_campaign│ │
└──────┬───────┘ └─────┬─────┘ └─────┬──────┘ │
       │ brand_key     │ content_key  │ campaign_key
       │               │              │        │
  ┌────┼───────────────┼──────────────┼────────┘
  │    │               │              │
┌─▼────▼────────┐ ┌────▼──────┐ ┌────▼──────┐
│fct_engagement │ │fct_sub-   │ │  fct_ad   │
│               │ │ scription │ │           │
│ • page_views  │ │ • active  │ │ • impress │
│ • sessions    │ │ • new     │ │ • clicks  │
│ • time_on_pg  │ │ • churned │ │ • revenue │
└───────────────┘ │ • mrr     │ └───────────┘
                  └───────────┘
         │                  │
    ┌────▼──────┐      ┌────▼─────────┐
    │dim_sub-   │      │ dim_platform │
    │ scriber   │      └──────────────┘
    └───────────┘
```

**Relationships:**
- All relationships are **one-to-many** (dimension → fact)
- **Single direction** (dimension filters fact, not vice versa)
- **date_key** shared across all three facts for time-based cross-fact analysis

---

## Tables & Columns

### Dimensions

#### `dim_date`
| Column | Type | Description |
|--------|------|-------------|
| `date_key` | Int | Primary key (YYYYMMDD format) |
| `full_date` | Date | Calendar date |
| `year`, `quarter`, `month` | Int | Date parts |
| `month_name`, `day_name` | String | Human-readable labels |

#### `dim_brand`
Hearst digital properties (Cosmopolitan, Esquire, Harper's Bazaar, etc.)
| Column | Type | Description |
|--------|------|-------------|
| `brand_key` | Int | Primary key |
| `brand_name` | String | Display name |
| `brand_category` | String | Lifestyle / News / Entertainment |
| `region` | String | US / UK / Global |

#### `dim_content`
Article-level metadata
| Column | Type | Description |
|--------|------|-------------|
| `content_key` | Int | Primary key |
| `content_id` | String | CMS identifier |
| `title` | String | Article headline |
| `section` | String | Fashion / Beauty / Politics / etc. |
| `author` | String | Byline |
| `content_type` | String | Article / Video / Gallery |

#### `dim_subscriber`
Subscriber demographics & acquisition
| Column | Type | Description |
|--------|------|-------------|
| `subscriber_key` | Int | Primary key |
| `subscriber_id` | String | External ID (hashed PII) |
| `subscriber_tier` | String | Free / Premium / VIP |
| `acquisition_channel` | String | Organic / Paid / Referral |
| `country` | String | ISO country code |

#### `dim_platform`
Device/app types
| Column | Type | Description |
|--------|------|-------------|
| `platform_key` | Int | Primary key |
| `platform_name` | String | Web / iOS / Android |
| `device_type` | String | Desktop / Mobile / Tablet |

#### `dim_campaign`
Advertising campaigns
| Column | Type | Description |
|--------|------|-------------|
| `campaign_key` | Int | Primary key |
| `campaign_name` | String | Display name |
| `campaign_type` | String | Display / Video / Native |
| `advertiser` | String | Brand name |

---

### Facts

#### `fct_engagement`
**Grain:** One row per date × brand × content × subscriber × platform combination  
**Measures:** Page views, sessions, time on page

| Column | Type | Description |
|--------|------|-------------|
| `date_key`, `brand_key`, `content_key`, `subscriber_key`, `platform_key` | Int | Foreign keys |
| `page_views` | Int | Count of page loads |
| `sessions` | Int | Unique visit sessions |
| `time_on_page_sec` | Int | Total seconds spent |

#### `fct_subscription`
**Grain:** One row per date × brand × subscriber (daily snapshot)  
**Measures:** Active/new/churned flags, MRR

| Column | Type | Description |
|--------|------|-------------|
| `date_key`, `brand_key`, `subscriber_key` | Int | Foreign keys |
| `active_flag` | Int | 1 if subscriber active on date |
| `new_flag` | Int | 1 if new subscription |
| `churned_flag` | Int | 1 if churned |
| `mrr` | Decimal | Monthly recurring revenue contribution |

#### `fct_ad`
**Grain:** One row per date × brand × campaign × platform  
**Measures:** Impressions, clicks, revenue

| Column | Type | Description |
|--------|------|-------------|
| `date_key`, `brand_key`, `campaign_key`, `platform_key` | Int | Foreign keys |
| `impressions` | Int | Ad impressions served |
| `clicks` | Int | User clicks |
| `ad_revenue` | Decimal | Revenue earned |

---

## Measures

### Engagement Measures (in `fct_engagement` table)

| Measure | DAX | Format | Description |
|---------|-----|--------|-------------|
| **Page Views** | `SUM(fct_engagement[page_views])` | `#,##0` | Total page views |
| **Sessions** | `SUM(fct_engagement[sessions])` | `#,##0` | Total sessions |
| **Avg Time on Page (sec)** | `DIVIDE(SUM(fct_engagement[time_on_page_sec]), [Sessions], 0)` | `#,##0.00` | Average engagement time per session |

### Subscription Measures (in `fct_subscription` table)

| Measure | DAX | Format | Description |
|---------|-----|--------|-------------|
| **Active Subscribers** | `CALCULATE(DISTINCTCOUNT(fct_subscription[subscriber_key]), fct_subscription[active_flag]=1)` | `#,##0` | Distinct active subscribers |
| **New Subscribers** | `CALCULATE(COUNTROWS(fct_subscription), fct_subscription[new_flag]=1)` | `#,##0` | New signups |
| **Churned Subscribers** | `CALCULATE(COUNTROWS(fct_subscription), fct_subscription[churned_flag]=1)` | `#,##0` | Churned subscribers |
| **Churn Rate %** | `DIVIDE([Churned Subscribers], [Active Subscribers], 0) * 100` | `0.00%` | Churn as % of active base |
| **MRR** | `SUM(fct_subscription[mrr])` | `$#,##0` | Monthly Recurring Revenue |
| **ARPU** | `DIVIDE([MRR], [Active Subscribers], 0)` | `$#,##0.00` | Average Revenue Per User |

### Advertising Measures (in `fct_ad` table)

| Measure | DAX | Format | Description |
|---------|-----|--------|-------------|
| **Ad Revenue** | `SUM(fct_ad[ad_revenue])` | `$#,##0` | Total ad revenue |
| **Ad Impressions** | `SUM(fct_ad[impressions])` | `#,##0` | Total impressions |
| **Ad Clicks** | `SUM(fct_ad[clicks])` | `#,##0` | Total clicks |
| **CTR %** | `DIVIDE([Ad Clicks], [Ad Impressions], 0) * 100` | `0.00%` | Click-through rate |
| **eCPM** | `DIVIDE([Ad Revenue], [Ad Impressions], 0) * 1000` | `$#,##0.00` | Effective cost per thousand impressions |

---

## Deployment & Finalization

### 1. Initial Setup in Power BI Desktop

The TMDL files in this repository define the model structure, but **Direct Lake requires a lakehouse connection established in Power BI Desktop**:

1. Open Power BI Desktop
2. **Get Data > More... > OneLake data hub**
3. Select the **lh_hearst_gold** lakehouse (SQL endpoint)
4. Choose tables: `gold.dim_*` and `gold.fct_*`
5. In the Power Query Editor, do NOT load — instead:
   - Right-click the query → **Advanced Editor**
   - Confirm the M code references the lakehouse SQL endpoint (e.g., `sql.database(...)`)
6. **Close & Apply**
7. In the **Model view**, verify relationships match the TMDL definitions
8. Save as `.pbip` project (Power BI Project format) or publish to Fabric workspace

### 2. Publishing to Fabric Workspace

**Option A: Publish from Power BI Desktop**
- File > Publish > Select Workspace (Dev)
- The semantic model will appear in the workspace; verify it's in **Direct Lake** mode

**Option B: Git Sync (Recommended for CI/CD)**
- Commit the `fabric/sm_hearst_audience.SemanticModel/` folder to Git
- In Fabric Dev workspace, configure Git integration
- Use `updateFromGit` to deploy (see `scripts/update_from_git.py`)

### 3. Validate Direct Lake Mode

After deployment, confirm the model is in Direct Lake mode:

```python
# Using Fabric REST API or XMLA endpoint
import requests
headers = {"Authorization": f"Bearer {access_token}"}
url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/semanticModels/{model_id}"
response = requests.get(url, headers=headers)
model_info = response.json()
print(model_info["connectionInfo"]["connectionString"])  # Should reference OneLake
```

Or in Power BI Desktop:
- File > Options > Data Load
- Check "DirectQuery/Direct Lake" is selected (not Import)

### 4. Refresh Strategy

**Direct Lake models do NOT need traditional refresh** — they read live Delta tables. However:

- **Lakehouse refresh**: Refresh the underlying `lh_hearst_gold` Delta tables (via notebooks, pipelines, or Dataflows Gen2)
- **Metadata refresh**: If you add/remove columns or tables in the lakehouse, refresh the semantic model metadata:
  - Fabric Portal: Semantic Model > Settings > **Refresh metadata**
  - REST API: `POST /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}/refreshMetadata`

### 5. Deployment Rules for UAT/Prod

When promoting via Fabric Deployment Pipelines:

```json
{
  "dataSourceRules": [
    {
      "dataSourceName": "DirectLake-lh_hearst_gold",
      "targetDataSourceName": "DirectLake-lh_hearst_gold_UAT"
    }
  ]
}
```

Apply via `scripts/set_deployment_rules.py` to ensure UAT/Prod models bind to the correct lakehouse instances.

---

## Known Limitations & TODOs

### Direct Lake Constraints
- **Fabric Capacity Required**: F2 or higher (not available in Power BI Pro)
- **Delta Tables Only**: Cannot mix Direct Lake with external SQL or cloud data sources
- **Some DAX Unsupported**: Complex calculated columns may fall back to DirectQuery mode
  - See: [Direct Lake limitations](https://learn.microsoft.com/fabric/get-started/direct-lake-overview#limitations)

### Model TODOs
- [ ] **Row-Level Security (RLS)**: Not configured; add roles if segmenting by brand or region
- [ ] **Object-Level Security (OLS)**: Hide sensitive columns/tables if needed
- [ ] **Aggregations**: Consider pre-aggregated tables for massive datasets (billions of rows)
- [ ] **Time Intelligence**: Add YTD, QTD, PY (prior year) measures using `DATESYTD`, `DATEADD`
- [ ] **What-If Parameters**: Add scenario analysis (e.g., "What if churn decreases 10%?")
- [ ] **Field Parameters**: Enable dynamic axis selection in reports

### TMDL Syntax Notes
The TMDL files are syntactically correct for **TMDL 1.0** (compatibilityLevel 1605+). However:

- **expressionSource placeholders**: The `'DirectLake-lh_hearst_gold'` placeholder must be replaced with the actual lakehouse SQL endpoint connection string when deploying via XMLA or REST API
- **lineageTags**: UUIDs are placeholders; Power BI Desktop generates real GUIDs on first import
- If you encounter import errors, open the model in Power BI Desktop, re-establish the lakehouse connection, and export fresh TMDL

---

## Related Artifacts

- **Report**: `fabric/rpt_hearst_exec.Report/` — Executive dashboard (PBIR format)
- **Data Agent**: `fabric/agent_hearst_analytics.DataAgent/` — Conversational AI over this model
- **Lakehouse**: `lh_hearst_gold` (gold schema) — Source Delta tables
- **Notebooks**: `fabric/nb_hearst_ingest.Notebook/` — Loads data into bronze/gold

---

## References

- [Microsoft Fabric Direct Lake Overview](https://learn.microsoft.com/fabric/get-started/direct-lake-overview)
- [Create and manage semantic models](https://learn.microsoft.com/fabric/data-engineering/lakehouse-power-bi-reporting)
- [TMDL (Tabular Model Definition Language)](https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview)
- [Star schema design in Power BI](https://learn.microsoft.com/power-bi/guidance/star-schema)
- [DAX function reference](https://learn.microsoft.com/dax/dax-function-reference)

---

## Support & Contributions

**Owner**: Dunbar (BI/Semantic Model Engineer)  
**Questions**: Open an issue in the repo or contact the Fabric Admin team  
**CI/CD**: Managed via GitHub Actions + Fabric Deployment Pipelines (see `.github/workflows/`)

