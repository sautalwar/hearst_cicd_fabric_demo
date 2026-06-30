"""
Deploy between Fabric deployment pipeline stages (e.g., Dev → UAT or UAT → Prod).

Calls the Fabric deployment pipeline deploy API to promote content from a source
stage to a target stage. This is a long-running operation (LRO) polled to completion.

Environment variables required:
  AZURE_CLIENT_ID          - SP client ID
  AZURE_CLIENT_SECRET      - SP client secret
  AZURE_TENANT_ID          - Azure AD tenant ID
  DEPLOYMENT_PIPELINE_ID   - Fabric deployment pipeline ID (GUID)
  SOURCE_STAGE_ORDER       - Source stage order (0=Dev, 1=UAT, 2=Prod)
  TARGET_STAGE_ORDER       - Target stage order (0=Dev, 1=UAT, 2=Prod)

Exit codes:
  0 - Success (deployment completed)
  1 - Authentication failure, API error, or deployment failed
"""

import os
import sys
import time
import requests
from fabric_auth import get_token


def deploy_stage():
    """Deploy content from source stage to target stage in the deployment pipeline."""
    
    # Get deployment parameters from environment
    pipeline_id = os.getenv("DEPLOYMENT_PIPELINE_ID")
    source_stage = os.getenv("SOURCE_STAGE_ORDER")
    target_stage = os.getenv("TARGET_STAGE_ORDER")
    
    if not all([pipeline_id, source_stage, target_stage]):
        print("❌ Error: Missing required environment variables", file=sys.stderr)
        print("   Required: DEPLOYMENT_PIPELINE_ID, SOURCE_STAGE_ORDER, TARGET_STAGE_ORDER", file=sys.stderr)
        sys.exit(1)
    
    # Convert stage orders to integers
    try:
        source_stage_id = int(source_stage)
        target_stage_id = int(target_stage)
    except ValueError:
        print("❌ Error: SOURCE_STAGE_ORDER and TARGET_STAGE_ORDER must be integers", file=sys.stderr)
        sys.exit(1)
    
    # Acquire Fabric API token
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # POST deploy API (initiate LRO)
    url = f"https://api.fabric.microsoft.com/v1/deploymentPipelines/{pipeline_id}/deploy"
    payload = {
        "sourceStageOrder": source_stage_id,
        "targetStageOrder": target_stage_id,
        "note": f"Automated deployment via GitHub Actions (source: {source_stage_id}, target: {target_stage_id})"
    }
    
    stage_names = {0: "Dev", 1: "UAT", 2: "Prod"}
    source_name = stage_names.get(source_stage_id, f"Stage {source_stage_id}")
    target_name = stage_names.get(target_stage_id, f"Stage {target_stage_id}")
    
    print(f"🚀 Deploying {source_name} → {target_name} (pipeline {pipeline_id})...")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 202:
        # Long-running operation accepted; get polling URL
        operation_location = response.headers.get("Operation-Location") or response.headers.get("Location")
        if not operation_location:
            print("❌ Error: LRO accepted but no Operation-Location header returned", file=sys.stderr)
            sys.exit(1)
        
        print(f"✅ Deployment initiated. Polling for completion...")
        poll_lro(operation_location, token)
        print(f"✅ Deployment {source_name} → {target_name} completed successfully")
        sys.exit(0)
    
    elif response.status_code == 200:
        # Immediate success (no LRO; rare but possible)
        print(f"✅ Deployment {source_name} → {target_name} completed (immediate)")
        sys.exit(0)
    
    else:
        print(f"❌ Error: Deployment failed with status {response.status_code}", file=sys.stderr)
        print(f"   Response: {response.text}", file=sys.stderr)
        sys.exit(1)


def poll_lro(operation_url: str, token: str, max_attempts: int = 120, interval: int = 10):
    """
    Poll a Fabric long-running operation until completion or failure.
    
    Args:
        operation_url: LRO polling URL (from Operation-Location header)
        token: Bearer token for authorization
        max_attempts: Maximum polling attempts (default: 120 × 10s = 20 minutes)
        interval: Seconds between polling attempts
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        response = requests.get(operation_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error: LRO polling failed with status {response.status_code}", file=sys.stderr)
            print(f"   Response: {response.text}", file=sys.stderr)
            sys.exit(1)
        
        result = response.json()
        status = result.get("status", "Unknown")
        
        if status in ["Succeeded", "Completed"]:
            print(f"✅ Operation completed successfully (attempt {attempt})")
            return
        elif status in ["Failed", "Canceled", "Cancelled"]:
            error = result.get("error", {})
            print(f"❌ Operation failed: {status}", file=sys.stderr)
            print(f"   Error: {error}", file=sys.stderr)
            sys.exit(1)
        elif status in ["Running", "InProgress", "NotStarted"]:
            print(f"⏳ Operation in progress... (attempt {attempt}/{max_attempts})")
        else:
            print(f"⚠️  Unknown status: {status} (attempt {attempt}/{max_attempts})")
    
    print(f"❌ Error: Operation timed out after {max_attempts} attempts", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    deploy_stage()
