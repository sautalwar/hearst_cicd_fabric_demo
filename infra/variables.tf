# Variables for the Hearst Fabric CI/CD infrastructure

# --- Azure subscription and identity ---

variable "subscription_id" {
  description = "Azure subscription ID for the deployment"
  type        = string
}

variable "tenant_id" {
  description = "Entra ID (Azure AD) tenant ID"
  type        = string
}

variable "admin_object_id" {
  description = "Entra object ID (user or group) to grant Admin role on workspaces (for bootstrapping)"
  type        = string
}

# --- Resource names and location ---

variable "location" {
  description = "Azure region for the resource group and resources"
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group for project resources"
  type        = string
  default     = "rg-hearst-fabric-cicd"
}

variable "key_vault_name" {
  description = "Name of the Azure Key Vault for secrets (must be globally unique, 3-24 alphanumeric/hyphens)"
  type        = string
  default     = "kv-hearst-fabric"
}

# --- Microsoft Fabric ---

variable "capacity_id" {
  description = "Optional: a Fabric capacity GUID to bind workspaces to directly. Leave blank to reuse by name (existing_capacity_name) or to create a new capacity."
  type        = string
  default     = ""
}

variable "existing_capacity_name" {
  description = "Optional: display name of an EXISTING Fabric capacity to look up and reuse. Leave blank (with capacity_id blank) to create a new capacity."
  type        = string
  default     = ""
}

variable "new_capacity_name" {
  description = "Name for a NEW Fabric capacity when one is created (3-63 lowercase letters/numbers). Used only when capacity_id and existing_capacity_name are both blank."
  type        = string
  default     = "caphearstfabricdemo"
}

variable "capacity_sku" {
  description = "F-SKU for a newly created capacity. F2 is the minimum that runs this workload (Spark, Warehouse, Lakehouse, pipelines). F64+ unlocks Copilot in Fabric."
  type        = string
  default     = "F2"
}

variable "capacity_admin_members" {
  description = "Admins for a newly created capacity: Entra user UPNs and/or service-principal object IDs. Defaults to the identity running Terraform."
  type        = list(string)
  default     = []
}

variable "skip_capacity_state_validation" {
  description = "Set true if the Terraform identity cannot list capacities (skips the Active-state check when assigning capacity to workspaces)."
  type        = bool
  default     = false
}

variable "deploy_example_workload" {
  description = "When true, Terraform provisions an example workload (lakehouse, warehouse, notebook, data pipeline) so the customer sees real items created end-to-end."
  type        = bool
  default     = true
}

variable "example_workspace" {
  description = "Which workspace the example workload is created in (dev, uat, or prod)."
  type        = string
  default     = "dev"
}

# --- GitHub integration ---

variable "github_owner" {
  description = "GitHub organization or user account owning the repo"
  type        = string
  default     = "ORG" # Placeholder; replace with actual org/user
}

variable "github_repo" {
  description = "GitHub repository name for Fabric Git integration"
  type        = string
  default     = "hearst_cicd_fabric_demo"
}

variable "github_branch" {
  description = "Git branch to sync with Dev workspace"
  type        = string
  default     = "main"
}

variable "github_directory" {
  description = "Directory in the GitHub repo containing Fabric items"
  type        = string
  default     = "/fabric"
}

variable "enable_git_integration" {
  description = "When true, connects the Dev workspace to GitHub (requires a pre-created Fabric Git ConfiguredConnection in github_connection_id). Default false so a first apply is fully self-contained."
  type        = bool
  default     = false
}

variable "github_connection_id" {
  description = "ID of the pre-created Fabric Git ConfiguredConnection (for SP-driven GitHub integration). Format: /providers/Microsoft.Fabric/git/connections/{connectionName}. Required only when enable_git_integration = true."
  type        = string
  default     = ""
  # Manual setup required: create GitHub PAT with repo scope, configure connection in Fabric portal or via API
}

variable "github_pat" {
  description = "GitHub Personal Access Token for Git operations (only if not using ConfiguredConnection). Never commit this value."
  type        = string
  default     = ""
  sensitive   = true
}

# --- Secrets (for Key Vault and GitHub Secrets mirroring) ---
# (SP client id/secret are created in identity.tf and stored directly in Key Vault;
#  no input variables are needed for them.)
