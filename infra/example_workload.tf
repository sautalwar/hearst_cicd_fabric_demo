# =============================================================================
# EXAMPLE WORKLOAD (provisioned by Terraform)
# Owner: the data engineering team
# =============================================================================
# So the customer can SEE a real workload created end-to-end by Terraform — not
# just empty workspaces. Toggle with var.deploy_example_workload (default true).
# These items live in the example workspace (default: dev) and are intentionally
# simple so `terraform apply` is fast and reliable. The Notebook ships with a tiny
# PySpark example (examples/notebook-content.py) that writes a sample table into
# the example Lakehouse when a user runs it in Fabric.

locals {
  example_count        = var.deploy_example_workload ? 1 : 0
  example_workspace_id = fabric_workspace.workspaces[var.example_workspace].id
}

# --- Lakehouse: raw/curated storage for the demo ----------------------------
resource "fabric_lakehouse" "example" {
  count        = local.example_count
  display_name = "lh_hearst_example"
  description  = "Example lakehouse provisioned by Terraform (landing/curated storage for the demo workload)."
  workspace_id = local.example_workspace_id
}

# --- Warehouse: SQL serving layer for the demo ------------------------------
resource "fabric_warehouse" "example" {
  count        = local.example_count
  display_name = "wh_hearst_example"
  description  = "Example warehouse provisioned by Terraform (SQL serving layer for the demo workload)."
  workspace_id = local.example_workspace_id
}

# --- Notebook: a runnable PySpark example -----------------------------------
resource "fabric_notebook" "example" {
  count        = local.example_count
  display_name = "nb_hearst_example"
  description  = "Example PySpark notebook provisioned by Terraform; writes a sample table into lh_hearst_example."
  workspace_id = local.example_workspace_id
  format       = "py"

  definition = {
    "notebook-content.py" = {
      source          = "${path.module}/examples/notebook-content.py"
      processing_mode = "None" # ship the file as-is (no token templating)
    }
  }
}

# --- Data Pipeline: orchestration shell -------------------------------------
# Created as a named item so customers see the pipeline surface. Attach an
# activity (e.g., run nb_hearst_example) in the portal, or supply a
# pipeline-content.json definition to manage it fully as code.
resource "fabric_data_pipeline" "example" {
  count        = local.example_count
  display_name = "pl_hearst_example"
  description  = "Example data pipeline provisioned by Terraform (orchestration shell for the demo workload)."
  workspace_id = local.example_workspace_id
}
