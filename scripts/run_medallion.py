"""
Orchestrate Fabric Notebook medallion pipeline: Bronze → Silver → Gold.

Triggers notebooks sequentially via Fabric Jobs API (POST .../items/{notebookId}/jobs/instances),
polls each Long-Running Operation (LRO) to completion, then starts the next stage.

Environment variables required:
  AZURE_CLIENT_ID          - Service principal client ID
  AZURE_CLIENT_SECRET      - Service principal client secret
  AZURE_TENANT_ID          - Azure AD tenant ID
  FABRIC_WORKSPACE_ID      - Target workspace ID (Dev/UAT/Prod)
  BRONZE_NOTEBOOK_ID       - nb_hearst_bronze_ingest item ID
  SILVER_NOTEBOOK_ID       - nb_hearst_silver_transform item ID
  GOLD_NOTEBOOK_ID         - nb_hearst_gold_build item ID

Exit codes:
  0 - All notebooks succeeded
  1 - Authentication failure, missing env vars, or any notebook failed
"""

import os
import sys
import time
import requests
from fabric_auth import get_token


def run_notebook(workspace_id: str, notebook_id: str, notebook_name: str, headers: dict) -> bool:
    """
    Trigger a Fabric Notebook job and poll until completion.
    
    Args:
        workspace_id: Fabric workspace GUID
        notebook_id: Notebook item GUID
        notebook_name: Display name for logging
        headers: HTTP headers with Authorization bearer token
    
    Returns:
        bool: True if notebook succeeded, False otherwise
    """
    # Start notebook job
    run_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{notebook_id}/jobs/instances?jobType=RunNotebook"
    
    print(f"🚀 Starting {notebook_name}...")
    response = requests.post(run_url, headers=headers)
    
    if response.status_code not in [200, 202]:
        print(f"❌ Failed to start {notebook_name} (status {response.status_code})", file=sys.stderr)
        print(f"   Response: {response.text}", file=sys.stderr)
        return False
    
    job_data = response.json()
    job_instance_id = job_data.get("id")
    
    if not job_instance_id:
        print(f"❌ No job instance ID returned for {notebook_name}", file=sys.stderr)
        return False
    
    print(f"   Job instance ID: {job_instance_id}")
    
    # Poll job status until completion
    status_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{notebook_id}/jobs/instances/{job_instance_id}"
    poll_interval = 10  # seconds
    max_wait = 1800  # 30 minutes max
    elapsed = 0
    
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        
        status_response = requests.get(status_url, headers=headers)
        
        if status_response.status_code != 200:
            print(f"❌ Failed to poll {notebook_name} status (status {status_response.status_code})", file=sys.stderr)
            return False
        
        status_data = status_response.json()
        job_status = status_data.get("status", "Unknown")
        
        if job_status in ["Completed", "Succeeded"]:
            print(f"✅ {notebook_name} completed successfully ({elapsed}s)")
            return True
        elif job_status in ["Failed", "Cancelled"]:
            error_msg = status_data.get("failureReason", "No details provided")
            print(f"❌ {notebook_name} failed: {error_msg}", file=sys.stderr)
            return False
        else:
            print(f"   {notebook_name} status: {job_status} ({elapsed}s elapsed)")
    
    print(f"❌ {notebook_name} timed out after {max_wait}s", file=sys.stderr)
    return False


def main():
    """Execute medallion pipeline: Bronze → Silver → Gold."""
    
    # Read environment variables
    workspace_id = os.getenv("FABRIC_WORKSPACE_ID")
    bronze_id = os.getenv("BRONZE_NOTEBOOK_ID")
    silver_id = os.getenv("SILVER_NOTEBOOK_ID")
    gold_id = os.getenv("GOLD_NOTEBOOK_ID")
    
    if not all([workspace_id, bronze_id, silver_id, gold_id]):
        print("❌ Error: Missing required environment variables", file=sys.stderr)
        print("   Required: FABRIC_WORKSPACE_ID, BRONZE_NOTEBOOK_ID, SILVER_NOTEBOOK_ID, GOLD_NOTEBOOK_ID", file=sys.stderr)
        sys.exit(1)
    
    # Acquire Fabric API token
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("MEDALLION PIPELINE ORCHESTRATOR")
    print(f"Workspace: {workspace_id}")
    print("=" * 60)
    
    # Execute notebooks in sequence
    pipeline = [
        (bronze_id, "Bronze Ingest"),
        (silver_id, "Silver Transform"),
        (gold_id, "Gold Build")
    ]
    
    for notebook_id, notebook_name in pipeline:
        success = run_notebook(workspace_id, notebook_id, notebook_name, headers)
        if not success:
            print("\n❌ Pipeline failed — aborting remaining stages", file=sys.stderr)
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Medallion pipeline completed successfully")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
