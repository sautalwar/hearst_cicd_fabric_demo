# Terraform and provider version constraints

terraform {
  required_version = ">= 1.6"

  required_providers {
    # Azure Resource Manager provider (for Key Vault, resource groups, etc.)
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0" # Pin to 4.x; verify latest stable at https://registry.terraform.io/providers/hashicorp/azurerm
    }

    # Microsoft Fabric provider (for workspaces, deployment pipelines, Git integration)
    fabric = {
      source  = "microsoft/fabric"
      version = "~> 1.0" # Pin to 1.x; verify latest stable at https://registry.terraform.io/providers/microsoft/fabric
    }

    # Entra ID (Azure AD) provider (for the service principal + app registration in identity.tf)
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0" # Pin to 3.x; verify latest stable at https://registry.terraform.io/providers/hashicorp/azuread
    }
  }
}

# Azure provider configuration
provider "azurerm" {
  features {
    # Enable purge protection safety for Key Vault (prevents accidental permanent deletion)
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
  # Skip automatic resource-provider registration: it's slow (enumerates every RP) and needs
  # extra permissions. Ensure Microsoft.Fabric + Microsoft.KeyVault are registered once on the
  # subscription before apply (see infra/SETUP.md). For a plan, registration isn't needed.
  resource_provider_registrations = "none"

  # Authentication: uses Azure CLI, SP env vars, or Managed Identity
  # Set AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET for SP auth
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

# Microsoft Fabric provider configuration
provider "fabric" {
  # Authentication: uses Azure AD token for https://api.fabric.microsoft.com
  # Inherits credentials from azurerm or explicit SP env vars
  # Requires tenant admin setting: "Service principals can use Fabric APIs" enabled
}
