# =============================================================================
# AZURE KEY VAULT (Secrets System of Record)
# Owner: the security engineering team
# Purpose: Centralized, encrypted storage for SP credentials, GitHub PAT, and other secrets
# Encryption: AES-256 at rest (Microsoft-managed keys), TLS 1.2+ in transit
# =============================================================================

# -----------------------------------------------------------------------------
# Key Vault Resource
# -----------------------------------------------------------------------------
resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name # Must be globally unique (3-24 chars, alphanumeric + hyphen)
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = var.tenant_id

  # SKU: Standard (secrets only, sufficient for this use case)
  # Premium adds HSM-backed keys; not needed for demo
  sku_name = "standard"

  # RBAC-based access control (preferred over legacy access policies)
  # All secret access is governed by Azure RBAC roles:
  #   - Key Vault Secrets Officer (admin/Terraform; read + write)
  #   - Key Vault Secrets User (service principal; read-only)
  rbac_authorization_enabled = true # RBAC-based access control (preferred over legacy access policies)

  # Soft delete: 90-day retention after deletion (protects against accidental loss)
  soft_delete_retention_days = 90

  # Purge protection: prevent permanent deletion until retention expires
  # CRITICAL for production; prevents malicious/accidental purge
  purge_protection_enabled = true

  # Network security: deny public access by default, allowlist required IPs/services
  # For demo: allow GitHub Actions runners (hosted IPs are dynamic, so "AllowAllNetworks")
  # For production: use private endpoint + deny public access
  public_network_access_enabled = true # Set to false + add private endpoint for hardened deployments

  network_acls {
    bypass         = "AzureServices" # Allow Azure first-party services (e.g., Fabric if using managed identity)
    default_action = "Allow"         # Change to "Deny" + add IP allowlist for production

    # Example: Restrict to specific GitHub Actions IP ranges (uncomment for production)
    # ip_rules = [
    #   "13.64.0.0/16",    # GitHub Actions West US
    #   "13.65.0.0/16",    # GitHub Actions West US 2
    #   # Add your organization's IPs here
    # ]
  }

  tags = {
    Environment = "All"
    ManagedBy   = "Terraform"
    Purpose     = "FabricCICDSecrets"
    Encryption  = "AES-256-AtRest-TLS-InTransit"
  }
}

# -----------------------------------------------------------------------------
# RBAC Assignments for Key Vault Access
# -----------------------------------------------------------------------------

# Admin (var.admin_object_id) → Key Vault Secrets Officer (read + write)
resource "azurerm_role_assignment" "kv_admin_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.admin_object_id

  # This assignment must complete before Terraform can write secrets
  # (the Terraform identity must have write access)
}

# Service Principal → Key Vault Secrets User (read-only)
# Workflows authenticate as the SP and read secrets at runtime
resource "azurerm_role_assignment" "kv_sp_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azuread_service_principal.fabric_cicd.object_id

  depends_on = [
    azuread_service_principal.fabric_cicd
  ]
}

# -----------------------------------------------------------------------------
# Secrets (values encrypted at rest and transmitted over TLS 1.2+)
# -----------------------------------------------------------------------------
# Note: The actual secret resources (fabric-sp-client-id, fabric-sp-client-secret,
# fabric-tenant-id, github-pat) are defined in identity.tf to keep identity/secrets
# co-located. This file provides the vault infrastructure.

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "key_vault_id" {
  description = "The resource ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "The name of the Key Vault (used in workflows to retrieve secrets)"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "The URI of the Key Vault (used in Azure CLI/SDK calls)"
  value       = azurerm_key_vault.main.vault_uri
  sensitive   = true
}
