# Fabric Deployment Pipeline: 3-stage promotion (Dev -> UAT -> Prod)
#
# The microsoft/fabric provider models stages INLINE on the pipeline resource
# (a stages = [...] list); there is no separate stage-workspace resource. Stage
# order follows the list order: index 0 = Dev, 1 = UAT, 2 = Prod. Each stage
# optionally binds a workspace_id.

resource "fabric_deployment_pipeline" "main" {
  display_name = "Hearst Fabric Release"
  description  = "Automated promotion pipeline for Dev -> UAT -> Prod workspaces"

  stages = [
    {
      display_name = "Development"
      description  = "Development stage (Git-connected workspace)."
      is_public    = false
      workspace_id = fabric_workspace.workspaces["dev"].id
    },
    {
      display_name = "UAT"
      description  = "User acceptance testing stage (receives from Dev)."
      is_public    = false
      workspace_id = fabric_workspace.workspaces["uat"].id
    },
    {
      display_name = "Production"
      description  = "Production stage (receives from UAT; manual approval gate)."
      is_public    = true
      workspace_id = fabric_workspace.workspaces["prod"].id
    }
  ]
}
