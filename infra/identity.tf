# =============================================================================
# IDENTITY MANAGEMENT (Entra ID Service Principal)
# Owner: the security engineering team
# Purpose: Entra SP for Fabric API automation with least-privilege API permissions
# =============================================================================

# -----------------------------------------------------------------------------
# Entra ID Application Registration
# -----------------------------------------------------------------------------
resource "azuread_application" "fabric_cicd" {
  display_name = "sp-hearst-fabric-cicd"

  # Required API permissions for Fabric and Power BI automation
  # Least-privilege principle: only the scopes needed for workspace/deployment/Git operations
  required_resource_access {
    # Microsoft Power BI Service API (Power BI and Fabric share the same API)
    resource_app_id = "00000009-0000-0000-c000-000000000000"

    # Application permissions (non-delegated; for service principal auth)
    resource_access {
      # Workspace.ReadWrite.All — Required for:
      #   - Creating/managing Dev/UAT/Prod workspaces
      #   - Assigning SP as workspace admin
      #   - Deployment pipeline operations (deploy, get status)
      id   = "2448370f-f988-42cd-909c-6528efd67c1a"
      type = "Role"
    }

    resource_access {
      # Tenant.Read.All — Required for:
      #   - Enumerating capacity IDs
      #   - Reading tenant-level settings during setup
      id   = "4ae1bf56-f562-4747-b7bc-2fa0874ed46f"
      type = "Role"
    }

    resource_access {
      # Item.ReadWrite.All — Required for:
      #   - Git updateFromGit/commitToGit operations
      #   - Reading/updating Fabric item definitions
      id   = "f3d9c7a9-c1e7-4a68-982b-f892c8e54b76"
      type = "Role"
    }
  }

  # Optional: Federated identity credential for GitHub OIDC (secretless auth)
  # Uncomment and configure to remove dependency on client secrets
  # See: https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust
  #
  # After enabling, update workflows to use OIDC token exchange instead of client secret.
  # This provides:
  #   - No secret rotation required
  #   - Per-repo/branch scoping
  #   - GitHub-native audit trail
  #
  # Steps to activate:
  #   1. Uncomment the block below
  #   2. Set var.github_owner and var.github_repo in variables.tf
  #   3. Update cd-*.yml workflows to use azure/login with federated credentials
  #   4. Remove AZURE_CLIENT_SECRET from GitHub Secrets
  #
  # resource "azuread_application_federated_identity_credential" "github_oidc" {
  #   application_id = azuread_application.fabric_cicd.id
  #   display_name   = "github-oidc-hearst-fabric-cicd"
  #   description    = "Allow GitHub Actions in hearst_cicd_fabric_demo repo to authenticate as this SP"
  #   audiences      = ["api://AzureADTokenExchange"]
  #   issuer         = "https://token.actions.githubusercontent.com"
  #   subject        = "repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/main"
  # }
}

# -----------------------------------------------------------------------------
# Service Principal (the identity that workflows authenticate as)
# -----------------------------------------------------------------------------
resource "azuread_service_principal" "fabric_cicd" {
  client_id                    = azuread_application.fabric_cicd.client_id
  app_role_assignment_required = false

  tags = [
    "Environment=All",
    "ManagedBy=Terraform",
    "Purpose=FabricCICD",
    "Rotation=90days"
  ]
}

# -----------------------------------------------------------------------------
# Client Secret (expires after 2 years; rotation required)
# -----------------------------------------------------------------------------
resource "azuread_application_password" "fabric_cicd" {
  application_id = azuread_application.fabric_cicd.id
  display_name   = "github-actions-secret"

  # 2-year expiration; plan rotation before this date
  # Rotation procedure: docs/secrets-handling.md § "SP Secret Rotation"
  end_date = timeadd(timestamp(), "17520h") # 730 days

  # Rotation reminder: Set a calendar alert 60 days before expiration to regenerate
  # this secret, update Key Vault, and mirror to GitHub Secrets.
}

# -----------------------------------------------------------------------------
# Store SP credentials in Key Vault (system of record for secrets)
# All secrets below are encrypted at rest (Azure Key Vault AES-256) and
# transmitted over TLS 1.2+
# -----------------------------------------------------------------------------
resource "azurerm_key_vault_secret" "fabric_sp_client_id" {
  name         = "fabric-sp-client-id"
  value        = azuread_service_principal.fabric_cicd.client_id
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    ManagedBy  = "Terraform"
    SecretType = "ClientID"
    Rotation   = "NotRequired"
  }

  depends_on = [
    azurerm_role_assignment.kv_admin_secrets_officer
  ]
}

resource "azurerm_key_vault_secret" "fabric_sp_client_secret" {
  name         = "fabric-sp-client-secret"
  value        = azuread_application_password.fabric_cicd.value
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    ManagedBy  = "Terraform"
    SecretType = "ClientSecret"
    Rotation   = "Required90Days"
    ExpiresAt  = azuread_application_password.fabric_cicd.end_date
  }

  depends_on = [
    azurerm_role_assignment.kv_admin_secrets_officer
  ]
}

resource "azurerm_key_vault_secret" "fabric_tenant_id" {
  name         = "fabric-tenant-id"
  value        = data.azuread_client_config.current.tenant_id
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    ManagedBy  = "Terraform"
    SecretType = "TenantID"
    Rotation   = "NotRequired"
  }

  depends_on = [
    azurerm_role_assignment.kv_admin_secrets_officer
  ]
}

resource "azurerm_key_vault_secret" "github_pat" {
  count        = var.github_pat != "" ? 1 : 0 # Only store when a PAT is supplied
  name         = "github-pat"
  value        = var.github_pat # Input as TF_VAR_github_pat or in terraform.tfvars (never commit!)
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    ManagedBy  = "Terraform"
    SecretType = "GitHubPAT"
    Rotation   = "Required90Days"
    Purpose    = "FabricGitIntegration"
  }

  depends_on = [
    azurerm_role_assignment.kv_admin_secrets_officer
  ]
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "azuread_client_config" "current" {}

# -----------------------------------------------------------------------------
# Outputs (marked sensitive to prevent leakage in logs/state output)
# -----------------------------------------------------------------------------
output "service_principal_object_id" {
  description = "The object ID of the Fabric CI/CD service principal"
  value       = azuread_service_principal.fabric_cicd.object_id
}

output "service_principal_client_id" {
  description = "The client ID (application ID) of the SP; used in workflows"
  value       = azuread_service_principal.fabric_cicd.client_id
  sensitive   = true
}

output "service_principal_secret_expires" {
  description = "Expiration date of the current client secret (set rotation reminder)"
  value       = azuread_application_password.fabric_cicd.end_date
}
