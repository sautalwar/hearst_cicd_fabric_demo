# =============================================================================
# FABRIC CAPACITY RESOLUTION (F-SKU)
# Owner: the platform engineering team
# =============================================================================
# Goal: make the package self-contained. All three workspaces are bound to ONE
# Fabric capacity, resolved in this priority order:
#
#   1. var.capacity_id set            -> use that Fabric capacity GUID directly.
#   2. var.existing_capacity_name set -> look the capacity up BY NAME and reuse it.
#   3. both blank (default fallback)  -> CREATE a new F-SKU capacity (var.capacity_sku,
#                                        minimum F2 for this workload).
#
# Note on Terraform semantics: a data source errors if nothing matches, so
# "find-or-create" can't be a single silent lookup. We express intent explicitly:
# give a name/id to REUSE, or leave both blank to CREATE. All paths resolve to
# local.effective_capacity_id (a Fabric capacity GUID — the form fabric_workspace
# expects; the ARM id exported by azurerm_fabric_capacity is NOT the same value).

locals {
  capacity_id_provided   = trimspace(var.capacity_id) != ""
  capacity_name_provided = trimspace(var.existing_capacity_name) != ""
  create_new_capacity    = !local.capacity_id_provided && !local.capacity_name_provided
}

# --- Path 2: reuse an EXISTING capacity by display name ----------------------
data "fabric_capacity" "existing" {
  count        = (!local.capacity_id_provided && local.capacity_name_provided) ? 1 : 0
  display_name = var.existing_capacity_name

  lifecycle {
    postcondition {
      condition     = self.state == "Active"
      error_message = "Fabric capacity '${var.existing_capacity_name}' was found but is not Active. Activate it, correct the name, or leave BOTH capacity_id and existing_capacity_name blank to create a new one."
    }
  }
}

# --- Path 3: CREATE a new F-SKU capacity ------------------------------------
resource "azurerm_fabric_capacity" "new" {
  count               = local.create_new_capacity ? 1 : 0
  name                = var.new_capacity_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  # Capacity admins: Entra user UPNs and/or service-principal object IDs.
  # Falls back to the identity running Terraform when none are supplied.
  administration_members = length(var.capacity_admin_members) > 0 ? var.capacity_admin_members : [data.azuread_client_config.current.object_id]

  sku {
    name = var.capacity_sku # F2 is the minimum that runs Spark/Warehouse/Lakehouse/pipelines
    tier = "Fabric"
  }

  tags = {
    Project   = "Hearst Fabric CI/CD Demo"
    ManagedBy = "Terraform"
    Purpose   = "FabricWorkloadCapacity"
  }
}

# Resolve the NEW capacity's Fabric GUID (workspace.capacity_id needs the GUID,
# not the ARM resource id that azurerm_fabric_capacity exports).
data "fabric_capacity" "created" {
  count        = local.create_new_capacity ? 1 : 0
  display_name = var.new_capacity_name
  depends_on   = [azurerm_fabric_capacity.new]
}

locals {
  effective_capacity_id = (
    local.capacity_id_provided ? var.capacity_id :
    local.capacity_name_provided ? data.fabric_capacity.existing[0].id :
    data.fabric_capacity.created[0].id
  )
}
