# Terraform state backend
#
# DEFAULT: LOCAL STATE. With no backend block, Terraform keeps state in a local
# terraform.tfstate file next to this code. This makes the package clone-and-run
# with zero pre-setup -- ideal for evaluating the end-to-end flow.
#
# OPTIONAL: REMOTE STATE (team-ready). For shared/CI use, store state in Azure
# Storage (encrypted at rest, versioned). Pre-create the storage account + container,
# then uncomment the block below and run:
#   terraform init \
#     -backend-config="resource_group_name=rg-hearst-tf-state" \
#     -backend-config="storage_account_name=sthearstfabrictfstate" \
#     -backend-config="container_name=tfstate" \
#     -backend-config="key=hearst-fabric-cicd.tfstate"
#
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rg-hearst-tf-state"
#     storage_account_name = "sthearstfabrictfstate"
#     container_name       = "tfstate"
#     key                  = "hearst-fabric-cicd.tfstate"
#   }
# }
