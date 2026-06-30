"""
Fabric REST API authentication helper using MSAL client credentials flow.

Acquires an Azure AD token for https://api.fabric.microsoft.com/.default
using service principal client credentials (client ID + secret).

Environment variables required:
  AZURE_CLIENT_ID     - Service principal application (client) ID
  AZURE_CLIENT_SECRET - Service principal client secret
  AZURE_TENANT_ID     - Azure AD tenant ID

Security: NEVER prints or logs the client secret or access token.
"""

import os
import sys
from msal import ConfidentialClientApplication


def get_token() -> str:
    """
    Acquire an access token for the Fabric REST API using client credentials flow.
    
    Returns:
        str: Bearer token for Fabric API (https://api.fabric.microsoft.com)
    
    Raises:
        SystemExit: If authentication fails or required env vars are missing
    """
    # Read credentials from environment (GitHub Actions secrets or local .env)
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    
    if not all([client_id, client_secret, tenant_id]):
        print("❌ Error: Missing required environment variables", file=sys.stderr)
        print("   Required: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID", file=sys.stderr)
        sys.exit(1)
    
    # MSAL authority URL (Azure AD endpoint for the tenant)
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    # Fabric API scope (resource identifier for token audience)
    scopes = ["https://api.fabric.microsoft.com/.default"]
    
    # Create MSAL confidential client application
    app = ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority
    )
    
    # Acquire token using client credentials flow
    result = app.acquire_token_for_client(scopes=scopes)
    
    if "access_token" in result:
        print("✅ Successfully acquired Fabric API token", file=sys.stderr)
        return result["access_token"]
    else:
        error = result.get("error", "unknown")
        error_desc = result.get("error_description", "No description")
        print(f"❌ Authentication failed: {error}", file=sys.stderr)
        print(f"   {error_desc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Test: acquire and print token length (never the token itself)
    token = get_token()
    print(f"Token acquired (length: {len(token)} chars)")
