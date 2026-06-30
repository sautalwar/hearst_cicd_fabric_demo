# Main infrastructure: Azure resource group

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name # Default: rg-hearst-fabric-cicd
  location = var.location            # Default: eastus

  tags = {
    Project     = "Hearst Fabric CI/CD Demo"
    Environment = "Multi-stage (Dev/UAT/Prod)"
    ManagedBy   = "Terraform"
  }
}
