# Microsoft Fabric workspaces and role assignments

locals {
  # Workspace definitions (shared naming conventions)
  workspaces = {
    dev = {
      name        = "Hearst Fabric Dev"
      description = "Development workspace for Fabric CI/CD demo (Git-connected to GitHub main branch)"
    }
    uat = {
      name        = "Hearst Fabric UAT"
      description = "User acceptance testing workspace (receives content via deployment pipeline from Dev)"
    }
    prod = {
      name        = "Hearst Fabric Prod"
      description = "Production workspace (receives content via deployment pipeline from UAT)"
    }
  }
}

# Create three Fabric workspaces
resource "fabric_workspace" "workspaces" {
  for_each = local.workspaces

  display_name                   = each.value.name
  description                    = each.value.description
  capacity_id                    = local.effective_capacity_id # Resolved in capacity.tf (reuse-by-id, reuse-by-name, or create-new)
  skip_capacity_state_validation = var.skip_capacity_state_validation
}

# Grant the service principal Admin role on all workspaces
# Required for SP to call updateFromGit, deploy, and manage items via API
resource "fabric_workspace_role_assignment" "sp_admin" {
  for_each = fabric_workspace.workspaces

  workspace_id = each.value.id
  principal = {
    id   = azuread_service_principal.fabric_cicd.object_id # SP created in identity.tf
    type = "ServicePrincipal"
  }
  role = "Admin"
}

# Grant the human admin (bootstrap user) Admin role on all workspaces
# Allows manual intervention / troubleshooting without SP
resource "fabric_workspace_role_assignment" "admin_user" {
  for_each = fabric_workspace.workspaces

  workspace_id = each.value.id
  principal = {
    id   = var.admin_object_id
    type = "User" # Or "Group" if using an Entra group
  }
  role = "Admin"
}
