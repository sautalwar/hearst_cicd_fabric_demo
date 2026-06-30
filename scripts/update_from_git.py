"""
Update Fabric Dev workspace from Git (POST .../git/updateFromGit).

Calls the updateFromGit API to pull the latest changes from the connected GitHub
repository into the Fabric Dev workspace. This is a long-running operation (LRO)
that is polled to completion.

Environment variables required:
  AZURE_CLIENT_ID            - SP client ID
  AZURE_CLIENT_SECRET        - SP client secret
  AZURE_TENANT_ID            - Azure AD tenant ID
  FABRIC_DEV_WORKSPACE_ID    - Fabric Dev workspace ID (GUID)

Exit codes:
  0 - Success (workspace updated from Git)
  1 - Authentication failure, API error, or update failed
"""

import os
import sys
import time
import requests
from fabric_auth import get_token


def update_from_git():
    """Update Fabric Dev workspace from Git and poll until complete."""
    
    # Get workspace ID from environment
    workspace_id = os.getenv("FABRIC_DEV_WORKSPACE_ID")
    if not workspace_id:
        print("❌ Error: FABRIC_DEV_WORKSPACE_ID environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Acquire Fabric API token
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # POST updateFromGit (initiate LRO)
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/git/updateFromGit"
    print(f"🔄 Triggering updateFromGit for workspace {workspace_id}...")
    
    response = requests.post(url, headers=headers, json={})
    
    if response.status_code == 202:
        # Long-running operation accepted; get polling URL from Location or Operation-Location header
        operation_location = response.headers.get("Operation-Location") or response.headers.get("Location")
        if not operation_location:
            print("❌ Error: LRO accepted but no Operation-Location header returned", file=sys.stderr)
            sys.exit(1)
        
        print(f"✅ Update initiated. Polling for completion...")
        poll_lro(operation_location, token)
        print("✅ Dev workspace successfully updated from Git")
        sys.exit(0)
    
    elif response.status_code == 200:
        # Immediate success (no LRO; rare for updateFromGit but possible)
        print("✅ Dev workspace successfully updated from Git (immediate)")
        sys.exit(0)
    
    else:
        print(f"❌ Error: updateFromGit failed with status {response.status_code}", file=sys.stderr)
        print(f"   Response: {response.text}", file=sys.stderr)
        sys.exit(1)


def poll_lro(operation_url: str, token: str, max_attempts: int = 60, interval: int = 5):
    """
    Poll a Fabric long-running operation until completion or failure.
    
    Args:
        operation_url: LRO polling URL (from Operation-Location header)
        token: Bearer token for authorization
        max_attempts: Maximum polling attempts (default: 60 × 5s = 5 minutes)
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
    update_from_git()
