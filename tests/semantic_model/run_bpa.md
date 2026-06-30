# Running Best Practice Analyzer on sm_hearst_audience

## Overview

This directory contains a **Best Practice Analyzer (BPA)** ruleset for the Hearst Audience & Subscription semantic model (`sm_hearst_audience`). BPA validates DAX, schema, naming conventions, and Direct Lake configuration to catch errors **before** they reach production.

BPA is part of the **CI quality gate**: any BPA violation with severity ≥ 2 **fails the build**.

---

## Prerequisites

### 1. Tabular Editor 2 CLI

Download and install **Tabular Editor 2** (free, open-source):
- **Download:** https://github.com/TabularEditor/TabularEditor/releases
- **Installer:** `TabularEditor.Installer.msi` (Windows)
- **CLI executable:** `TabularEditor.exe` (installed to `C:\Program Files (x86)\Tabular Editor\` by default)

> **Note:** Tabular Editor 3 (commercial) also supports BPA, but TE2 CLI is sufficient for CI automation.

### 2. TMDL Semantic Model Source

The semantic model must be saved in **TMDL format** (Tabular Model Definition Language) in the `fabric/sm_hearst_audience.SemanticModel/definition/` directory. This is the default for Fabric Git-integrated workspaces.

---

## Running BPA Locally

### Command

From the repository root, run:

```powershell
& "C:\Program Files (x86)\Tabular Editor\TabularEditor.exe" `
  "fabric\sm_hearst_audience.SemanticModel\definition\model.tmdl" `
  -B "tests\semantic_model\bpa_rules.json" `
  -V
```

### Flags

- `-B <ruleset.json>` — Path to the BPA rules JSON file (this directory)
- `-V` — **Verbose mode**: outputs all violations to stdout (required for CI parsing)
- (Optional) `-E` — **Error on violation**: exits with code 1 if any rule is violated (use for strict CI gating)

### Exit Codes

- **0** — No violations (all rules passed)
- **1** — One or more violations detected (if `-E` flag is used)

---

## CI Integration (GitHub Actions)

### Workflow: `ci-validate.yml`

Add this step to `.github/workflows/ci-validate.yml` (after linting, before `terraform plan`):

```yaml
- name: Install Tabular Editor 2 CLI (Windows)
  if: runner.os == 'Windows'
  run: |
    Invoke-WebRequest -Uri "https://github.com/TabularEditor/TabularEditor/releases/download/2.17.3/TabularEditor.Installer.msi" -OutFile TabularEditor.msi
    Start-Process msiexec.exe -ArgumentList '/i TabularEditor.msi /quiet /qn' -NoNewWindow -Wait

- name: Run Best Practice Analyzer on sm_hearst_audience
  run: |
    & "C:\Program Files (x86)\Tabular Editor\TabularEditor.exe" `
      "fabric\sm_hearst_audience.SemanticModel\definition\model.tmdl" `
      -B "tests\semantic_model\bpa_rules.json" `
      -V -E
  shell: powershell

- name: Fail build on BPA violations
  if: failure()
  run: |
    echo "❌ BPA violations detected — semantic model does not meet quality standards"
    exit 1
```

### Linux Runners (Alternative)

Tabular Editor 2 CLI can run on Linux via **Mono** or **Wine**, but requires additional setup. For GitHub Actions, prefer **Windows runners** (`runs-on: windows-latest`) for the BPA step.

---

## BPA Ruleset: `bpa_rules.json`

### Included Rules

| ID | Name | Severity | Description |
|----|------|----------|-------------|
| **MEASURE_FORMAT_STRING** | Measures must have formatString | 2 (Warning) | All measures must declare an explicit `formatString` (e.g., `#,##0`, `\$#,##0.00`, `0.00\%`) |
| **NO_CALCULATED_COLUMNS_WHERE_MEASURE_SUFFICES** | Avoid calculated columns for simple aggregations | 1 (Info) | Calculated columns consume storage; prefer measures for SUM/COUNT |
| **RELATIONSHIPS_VALID** | All relationships must be active and valid | 3 (Error) | Inactive relationships without a documented reason create ambiguity |
| **NAMING_CONVENTION_FOREIGN_KEYS** | Foreign key columns must end with '_key' | 1 (Info) | Surrogate keys should follow `*_key` naming (e.g., `date_key`, `brand_key`) |
| **NO_INACTIVE_RELATIONSHIP_AMBIGUITY** | Inactive relationships must be intentional | 2 (Warning) | Inactive relationships require an `InactiveReason` annotation |
| **HIDDEN_FOREIGN_KEYS** | Foreign key columns should be hidden | 1 (Info) | `*_key` columns in fact tables should be hidden from users (use dimension attributes instead) |
| **DIMENSION_TABLES_HAVE_PRIMARY_KEY** | Dimension tables must have a primary key | 2 (Warning) | Each `dim_*` table must have exactly one column marked `IsKey` |
| **NO_ORPHAN_MEASURES** | Measures should belong to fact tables | 1 (Info) | Measures defined on dimension tables confuse users; place in fact or Measures table |
| **DIRECT_LAKE_PARTITION_MODE** | Tables must use Direct Lake partition mode | 3 (Error) | All partitions must declare `mode: directLake` (not import/directQuery) |
| **DIRECT_LAKE_EXPRESSION_SOURCE** | Direct Lake partitions must reference lakehouse | 3 (Error) | All partitions must set `expressionSource: 'DirectLake-lh_hearst_gold'` |
| **MEASURE_AGGREGATION_NOT_NONE** | Key columns should have summarizeBy: none | 1 (Info) | Foreign key columns should not auto-aggregate (use `summarizeBy: none`) |

### Severity Levels

- **3 (Error):** Blocks CI build (critical)
- **2 (Warning):** Reported but does not block (recommended fix)
- **1 (Info):** Best practice suggestion (informational)

### Customizing Rules

To modify or add rules:

1. Edit `tests/semantic_model/bpa_rules.json`
2. Use the **DAX expression syntax** for rule conditions (see Tabular Editor documentation)
3. Test locally with the CLI before committing

---

## Interpreting BPA Output

### Example Output (Violations)

```
Running Best Practice Analyzer on model 'sm_hearst_audience'...

[ERROR] MEASURE_FORMAT_STRING
  Violation: Measure 'Avg Time on Page (sec)' does not have a formatString defined
  Location: Table 'fct_engagement', Measure 'Avg Time on Page (sec)'

[WARNING] HIDDEN_FOREIGN_KEYS
  Violation: Column 'date_key' in table 'fct_engagement' should be hidden
  Location: Table 'fct_engagement', Column 'date_key'

2 violations detected (1 error, 1 warning)
Exit code: 1
```

### Example Output (No Violations)

```
Running Best Practice Analyzer on model 'sm_hearst_audience'...
✓ All rules passed
Exit code: 0
```

---

## UAT Gate

BPA runs in **CI** (on PR) but **not** in the UAT gate. The UAT gate focuses on **runtime validation** (DAX reconciliation, data quality). BPA is a **pre-deployment schema/definition check**.

### Quality Gate Layers

| Gate | When | Tool | What It Validates |
|------|------|------|-------------------|
| **CI** | PR | BPA + Terraform plan | Semantic model schema, DAX syntax, naming, Direct Lake config |
| **UAT** | Dev→UAT deploy | DAX reconciliation + data quality | Runtime correctness: measures match source data |
| **Prod** | UAT→Prod deploy | Smoke test | Basic connectivity and query execution |

---

## Troubleshooting

### `TabularEditor.exe` not found

- Verify installation path: `Get-Command TabularEditor.exe` (PowerShell)
- If installed to a custom location, update the `-E` path in commands

### BPA exits 0 but violations expected

- Ensure `-E` flag is set (exit on violation)
- Check rule `severity` levels: only severity ≥ 2 blocks CI if you filter by exit code

### TMDL parsing errors

- Ensure the semantic model is saved in **TMDL format** (not legacy `.bim` JSON)
- Check for syntax errors in `.tmdl` files (Fabric will surface these on Git sync)

---

## References

- **Tabular Editor 2 GitHub:** https://github.com/TabularEditor/TabularEditor
- **BPA Rules Schema:** https://github.com/microsoft/Analysis-Services/tree/master/BestPracticeRules
- **Direct Lake Documentation:** https://learn.microsoft.com/fabric/onelake/onelake-open-lakehouse-direct-lake
- **TMDL Format:** https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview

---

## Maintenance

- **Owner:** the quality engineering team
- **Frequency:** Run on every PR (CI); update rules when new semantic model patterns emerge
- **Versioning:** BPA rules are versioned with the repo; changes to rules follow the same PR/review process as code
