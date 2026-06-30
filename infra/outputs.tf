# Outputs: workspace and pipeline IDs for GitHub Actions workflows

# --- Workspace IDs (consumed by cd-dev-sync, cd-promote-* workflows) ---

output "workspace_id_dev" {
  description = "ID of the Development workspace (Git-connected)"
  value       = fabric_workspace.workspaces["dev"].id
}

output "workspace_id_uat" {
  description = "ID of the UAT workspace"
  value       = fabric_workspace.workspaces["uat"].id
}

output "workspace_id_prod" {
  description = "ID of the Production workspace"
  value       = fabric_workspace.workspaces["prod"].id
}

# --- Deployment pipeline IDs ---

output "deployment_pipeline_id" {
  description = "ID of the deployment pipeline"
  value       = fabric_deployment_pipeline.main.id
}

# Stage IDs or order indices (used by deploy_stage.py to specify source and target stages)
output "pipeline_stage_dev_order" {
  description = "Stage order for Dev (0 = first stage)"
  value       = 0
}

output "pipeline_stage_uat_order" {
  description = "Stage order for UAT (1 = second stage)"
  value       = 1
}

output "pipeline_stage_prod_order" {
  description = "Stage order for Prod (2 = third stage)"
  value       = 2
}

# --- Resource group ---

output "resource_group_name" {
  description = "Name of the Azure resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Azure region of the resource group"
  value       = azurerm_resource_group.main.location
}

# --- Key Vault (if the keyvault.tf exposes it) ---

# output "key_vault_id" {
#   description = "ID of the Azure Key Vault"
#   value       = azurerm_key_vault.main.id
# }

# --- Service principal (if the identity.tf exposes it) ---

# output "service_principal_client_id" {
#   description = "Client (application) ID of the service principal"
#   value       = azuread_application.fabric_sp.client_id
#   sensitive   = true
# }

# Note: Mark any secret-bearing outputs as sensitive = true to prevent them from appearing in logs

# --- Capacity resolution (self-contained package) ---

output "capacity_mode" {
  description = "How the Fabric capacity was resolved for the workspaces"
  value = (
    local.create_new_capacity ? "created-new (${var.capacity_sku})" :
    local.capacity_name_provided ? "reused-existing-by-name (${var.existing_capacity_name})" :
    "reused-existing-by-id"
  )
}

output "effective_capacity_id" {
  description = "The Fabric capacity GUID all three workspaces are bound to"
  value       = local.effective_capacity_id
}

# --- Example workload (null when var.deploy_example_workload = false) ---

output "example_workload_item_ids" {
  description = "IDs of the example Fabric items provisioned by Terraform (lakehouse, warehouse, notebook, data pipeline)"
  value = var.deploy_example_workload ? {
    lakehouse     = fabric_lakehouse.example[0].id
    warehouse     = fabric_warehouse.example[0].id
    notebook      = fabric_notebook.example[0].id
    data_pipeline = fabric_data_pipeline.example[0].id
  } : null
}
