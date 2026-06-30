"""
Configure Fabric deployment-pipeline deployment rules for Direct Lake rebinding.

On promotion, the semantic model `sm_hearst_audience` must point at the TARGET
stage's gold lakehouse `lh_hearst_gold` (its Direct Lake source). The lakehouse and
the semantic model are created in each workspace via Git sync / the deployment
pipeline — NOT by Terraform — so their item IDs are NOT known ahead of time.

==> This script therefore RESOLVES the item IDs BY NAME at runtime from the target
    workspace (no manual GUID env vars required).

Environment variables required:
  AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID  - service principal
  DEPLOYMENT_PIPELINE_ID                                   - Fabric deployment pipeline GUID
  TARGET_STAGE_ORDER                                       - 1 = UAT, 2 = Prod
  TARGET_WORKSPACE_ID                                      - the target stage's workspace GUID
       (falls back to FABRIC_UAT_WORKSPACE_ID / FABRIC_PROD_WORKSPACE_ID by stage)

Optional overrides (names to resolve; defaults match this project):
  GOLD_LAKEHOUSE_NAME   (default: lh_hearst_gold)
  SEMANTIC_MODEL_NAME   (default: sm_hearst_audience)

Exit codes:
  0 - Success (rules configured) or safe no-op with guidance
  1 - Authentication failure, missing required env, or unrecoverable API error

NOTE: The actual PATCH that creates the rule is left COMMENTED pending verification of
the exact Direct-Lake-rebinding rule payload against the Fabric REST API. Everything up
to that call (auth, ID resolution, payload construction) runs for real, so the script is
deterministic and testable. See the manual portal fallback printed at the end.
Ref: https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines
"""

import os
import sys
import requests
from fabric_auth import get_token

FABRIC_API = "https://api.fabric.microsoft.com/v1"


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"❌ Error: required environment variable {name} is not set", file=sys.stderr)
        sys.exit(1)
    return val


def resolve_item_id(workspace_id: str, item_type: str, display_name: str, token: str) -> str:
    """
    Resolve a Fabric item's ID by its displayName within a workspace.
    item_type examples: 'Lakehouse', 'SemanticModel'. Handles pagination.
    Returns the item id, or exits nonzero if not found.
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FABRIC_API}/workspaces/{workspace_id}/items?type={item_type}"
    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Error listing {item_type} items (status {resp.status_code}): {resp.text}", file=sys.stderr)
            sys.exit(1)
        body = resp.json()
        for item in body.get("value", []):
            if item.get("displayName") == display_name:
                item_id = item.get("id")
                print(f"   ✓ resolved {item_type} '{display_name}' -> {item_id}")
                return item_id
        # follow continuation token if present
        url = body.get("continuationUri")
    print(f"❌ Error: {item_type} '{display_name}' not found in workspace {workspace_id}", file=sys.stderr)
    sys.exit(1)


def set_deployment_rules():
    pipeline_id = _require("DEPLOYMENT_PIPELINE_ID")
    try:
        target_stage = int(_require("TARGET_STAGE_ORDER"))
    except ValueError:
        print("❌ Error: TARGET_STAGE_ORDER must be an integer (1=UAT, 2=Prod)", file=sys.stderr)
        sys.exit(1)

    stage_names = {1: "UAT", 2: "Prod"}
    stage_name = stage_names.get(target_stage, f"Stage {target_stage}")

    # Resolve the TARGET workspace (explicit, or per-stage fallback)
    fallback_env = "FABRIC_UAT_WORKSPACE_ID" if target_stage == 1 else "FABRIC_PROD_WORKSPACE_ID"
    target_workspace_id = os.getenv("TARGET_WORKSPACE_ID") or os.getenv(fallback_env)
    if not target_workspace_id:
        print(f"❌ Error: set TARGET_WORKSPACE_ID (or {fallback_env}) to the {stage_name} workspace GUID", file=sys.stderr)
        sys.exit(1)

    lakehouse_name = os.getenv("GOLD_LAKEHOUSE_NAME", "lh_hearst_gold")
    model_name = os.getenv("SEMANTIC_MODEL_NAME", "sm_hearst_audience")

    token = get_token()

    print(f"⚙️  Resolving item IDs in the {stage_name} workspace ({target_workspace_id})...")
    target_lakehouse_id = resolve_item_id(target_workspace_id, "Lakehouse", lakehouse_name, token)
    target_model_id = resolve_item_id(target_workspace_id, "SemanticModel", model_name, token)

    # Build the Direct Lake rebinding rule for the deployment pipeline stage.
    # The rule says: for the semantic model item, bind its Direct Lake source to the
    # TARGET stage's gold lakehouse.
    url = f"{FABRIC_API}/deploymentPipelines/{pipeline_id}/stages/{target_stage}/deploymentRules"
    payload = {
        "rules": [
            {
                # TODO: confirm ruleType + shape for Direct Lake source rebinding.
                "ruleType": "DatasetSource",
                "itemId": target_model_id,
                "dataSourceType": "Lakehouse",
                "dataSourceDetails": {
                    "type": "Lakehouse",
                    "lakehouseId": target_lakehouse_id,
                    "workspaceId": target_workspace_id,
                },
            }
        ]
    }

    print(f"⚙️  Direct Lake rebinding rule for {stage_name}:")
    print(f"     semantic model {target_model_id}  ->  lakehouse {target_lakehouse_id}")

    # ── The live PATCH is intentionally COMMENTED pending payload-schema verification. ──
    # headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # resp = requests.patch(url, headers=headers, json=payload, timeout=30)
    # if resp.status_code in (200, 204):
    #     print(f"✅ Deployment rules configured for {stage_name}")
    #     sys.exit(0)
    # else:
    #     print(f"❌ Failed to set deployment rules (status {resp.status_code}): {resp.text}", file=sys.stderr)
    #     sys.exit(1)

    print("⚠️  The deployment-rules PATCH is currently COMMENTED OUT pending API-schema confirmation.")
    print(f"     Endpoint : PATCH {url}")
    print(f"     Payload  : {payload}")
    print("     Manual fallback: Fabric portal -> Deployment pipeline -> select the stage ->")
    print(f"        'Deployment rules' -> {model_name} -> Data source rules -> point to {lakehouse_name}.")
    print("     Once verified, uncomment the PATCH block above. The resolved IDs above are real.")
    sys.exit(0)


if __name__ == "__main__":
    set_deployment_rules()
