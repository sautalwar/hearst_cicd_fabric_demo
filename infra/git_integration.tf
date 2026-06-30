# Fabric workspace Git integration (Dev workspace ONLY)
#
# IMPORTANT: Only the Development workspace is connected to GitHub. UAT and Prod
# receive content exclusively via the deployment pipeline (no direct Git sync).
# This prevents two competing sources of truth in higher environments.

resource "fabric_workspace_git" "dev" {
  count        = var.enable_git_integration ? 1 : 0 # Off by default so a first apply is fully self-contained
  workspace_id = fabric_workspace.workspaces["dev"].id

  # How to reconcile workspace vs. Git on first connect (PreferWorkspace keeps current Dev content)
  initialization_strategy = "PreferWorkspace"

  git_provider_details = {
    git_provider_type = "GitHub"
    owner_name        = var.github_owner     # GitHub org or user
    repository_name   = var.github_repo      # Repository name
    branch_name       = var.github_branch    # Default: main
    directory_name    = var.github_directory # Default: /fabric
  }

  # Authentication: Fabric ConfiguredConnection (pre-created GitHub PAT/OAuth connection).
  # Manual one-time setup: create a GitHub PAT with repo scope, then create the Fabric
  # connection (portal or POST https://api.fabric.microsoft.com/v1/connections) and pass
  # its id as var.github_connection_id.
  git_credentials = {
    source        = "ConfiguredConnection"
    connection_id = var.github_connection_id
  }
}

# TODO: Verify exact attribute names against the latest microsoft/fabric provider docs:
# https://registry.terraform.io/providers/microsoft/fabric/latest/docs/resources/workspace_git
