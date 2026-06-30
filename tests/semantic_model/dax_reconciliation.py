"""
DAX Reconciliation — Semantic Model vs Gold Tables

Validates that key DAX measures in sm_hearst_audience produce the same results
as direct aggregations over the gold lakehouse tables via the SQL endpoint.

This is the **UAT gate** for semantic model correctness: if a measure does not
reconcile to its source data, the model is incorrect and promotion to Prod is BLOCKED.

Connection methods:
  1. Semantic model: Fabric REST API executeQueries (XMLA-compatible DAX endpoint)
  2. Gold tables: pyodbc → lh_hearst_gold SQL endpoint

Environment variables required:
  AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID — SP auth
  FABRIC_UAT_WORKSPACE_ID — UAT workspace GUID
  FABRIC_SQL_ENDPOINT — lh_hearst_gold SQL endpoint (e.g., <workspace_id>.lakehouse.fabric.microsoft.com)

Exit codes:
  0 = all measures reconciled within tolerance
  1 = one or more measures failed reconciliation → blocks promotion
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from decimal import Decimal

import requests
import pyodbc


# ─────────────────────────────────────────────────────────────────────────────
# Auth & Fabric REST API
# ─────────────────────────────────────────────────────────────────────────────

def get_fabric_token() -> str:
    """
    Acquire a bearer token for Fabric REST API using SP client credentials.
    NEVER log the token value.
    """
    tenant_id = os.environ["AZURE_TENANT_ID"]
    client_id = os.environ["AZURE_CLIENT_ID"]
    client_secret = os.environ["AZURE_CLIENT_SECRET"]
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://api.fabric.microsoft.com/.default",
    }
    
    resp = requests.post(token_url, data=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def execute_dax_query(workspace_id: str, dataset_id: str, dax_query: str, token: str) -> Any:
    """
    Execute a DAX query against a semantic model via Fabric REST API executeQueries endpoint.
    Returns the scalar result (first row, first column).
    
    API: POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}/executeQueries
    Body: { "queries": [{ "query": "EVALUATE { <expression> }" }] }
    """
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/semanticModels/{dataset_id}/executeQueries"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "queries": [
            {
                "query": dax_query
            }
        ]
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    # Parse response: data["results"][0]["tables"][0]["rows"][0]["<column_name>"]
    # For a single-value EVALUATE, the first row's first column is the result
    if not data.get("results") or not data["results"][0].get("tables"):
        raise ValueError(f"DAX query returned no results: {dax_query}")
    
    rows = data["results"][0]["tables"][0]["rows"]
    if not rows:
        return 0  # No rows means the measure evaluated to empty (treat as 0)
    
    # Return the first column value (assume single-value result)
    first_key = list(rows[0].keys())[0]
    return rows[0][first_key]


# ─────────────────────────────────────────────────────────────────────────────
# Gold Lakehouse SQL Endpoint (pyodbc)
# ─────────────────────────────────────────────────────────────────────────────

def get_lakehouse_connection() -> pyodbc.Connection:
    """
    Acquire a connection to the gold lakehouse SQL endpoint using SP auth.
    """
    endpoint = os.environ["FABRIC_SQL_ENDPOINT"]
    client_id = os.environ["AZURE_CLIENT_ID"]
    client_secret = os.environ["AZURE_CLIENT_SECRET"]
    
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server={endpoint};"
        f"Database=lh_hearst_gold;"
        f"UID={client_id};"
        f"PWD={client_secret};"
        f"Authentication=ActiveDirectoryServicePrincipal;"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )
    
    return pyodbc.connect(conn_str)


def execute_sql_scalar(conn: pyodbc.Connection, query: str) -> Any:
    """Execute a SQL query and return the scalar result (first row, first column)."""
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    if result is None:
        return 0
    return result[0]


# ─────────────────────────────────────────────────────────────────────────────
# Reconciliation Logic
# ─────────────────────────────────────────────────────────────────────────────

def reconcile_measure(
    measure_name: str,
    dax_expression: str,
    sql_query: str,
    workspace_id: str,
    dataset_id: str,
    token: str,
    lakehouse_conn: pyodbc.Connection,
    tolerance: float = 0.01
) -> bool:
    """
    Reconcile a single measure:
      1. Execute the DAX expression via Fabric REST API
      2. Execute the SQL query against the gold lakehouse
      3. Compare results within tolerance (relative difference)
    
    Returns True if reconciled, False if mismatch.
    """
    print(f"\n[Reconciling] {measure_name}")
    
    # 1. DAX result
    try:
        dax_result = execute_dax_query(workspace_id, dataset_id, dax_expression, token)
        print(f"  DAX result: {dax_result}")
    except Exception as e:
        print(f"  ✗ DAX query failed: {e}")
        return False
    
    # 2. SQL result
    try:
        sql_result = execute_sql_scalar(lakehouse_conn, sql_query)
        print(f"  SQL result: {sql_result}")
    except Exception as e:
        print(f"  ✗ SQL query failed: {e}")
        return False
    
    # 3. Compare (handle None/0 cases)
    dax_val = float(dax_result) if dax_result is not None else 0.0
    sql_val = float(sql_result) if sql_result is not None else 0.0
    
    if sql_val == 0 and dax_val == 0:
        print(f"  ✓ Both zero — reconciled")
        return True
    
    if sql_val == 0:
        print(f"  ✗ SQL returned 0 but DAX returned {dax_val} — MISMATCH")
        return False
    
    relative_diff = abs(dax_val - sql_val) / abs(sql_val)
    print(f"  Relative difference: {relative_diff:.4%}")
    
    if relative_diff <= tolerance:
        print(f"  ✓ Reconciled (within {tolerance:.2%} tolerance)")
        return True
    else:
        print(f"  ✗ MISMATCH (exceeds {tolerance:.2%} tolerance)")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main Reconciliation Suite
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("═════════════════════════════════════════════════════════════════")
    print("  DAX Reconciliation — Semantic Model vs Gold Tables")
    print("═════════════════════════════════════════════════════════════════")
    
    # Check required environment variables
    required_env = [
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "FABRIC_UAT_WORKSPACE_ID",
        "FABRIC_SQL_ENDPOINT",
    ]
    missing = [v for v in required_env if not os.getenv(v)]
    if missing:
        print(f"✗ Missing required environment variables: {missing}")
        sys.exit(1)
    
    workspace_id = os.environ["FABRIC_UAT_WORKSPACE_ID"]
    
    # Acquire token
    try:
        token = get_fabric_token()
        print("✓ Acquired Fabric API token")
    except Exception as e:
        print(f"✗ Failed to acquire token: {e}")
        sys.exit(1)
    
    # Connect to lakehouse SQL endpoint
    try:
        lakehouse_conn = get_lakehouse_connection()
        print("✓ Connected to lh_hearst_gold SQL endpoint")
    except Exception as e:
        print(f"✗ Failed to connect to lakehouse: {e}")
        sys.exit(1)
    
    # Find the semantic model ID (sm_hearst_audience)
    # NOTE: In a real implementation, list items in the workspace and find by name.
    # For this demo, we'll use a placeholder or require it as an env var.
    dataset_id = os.getenv("FABRIC_SEMANTIC_MODEL_ID")
    if not dataset_id:
        print("✗ FABRIC_SEMANTIC_MODEL_ID not set — cannot proceed")
        print("  Hint: List items in the workspace to find the semantic model GUID")
        sys.exit(1)
    
    print(f"✓ Target semantic model: {dataset_id}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # Define reconciliation tests
    # ─────────────────────────────────────────────────────────────────────────
    
    tests = [
        # Engagement measures
        {
            "measure": "Page Views",
            "dax": "EVALUATE { [Page Views] }",
            "sql": "SELECT SUM(page_views) FROM gold.fct_engagement",
        },
        {
            "measure": "Sessions",
            "dax": "EVALUATE { [Sessions] }",
            "sql": "SELECT SUM(sessions) FROM gold.fct_engagement",
        },
        # Subscription measures
        {
            "measure": "MRR",
            "dax": "EVALUATE { [MRR] }",
            "sql": "SELECT SUM(mrr) FROM gold.fct_subscription",
        },
        {
            "measure": "Active Subscribers",
            "dax": "EVALUATE { [Active Subscribers] }",
            "sql": "SELECT COUNT(DISTINCT subscriber_key) FROM gold.fct_subscription WHERE active_flag = 1",
        },
        {
            "measure": "New Subscribers",
            "dax": "EVALUATE { [New Subscribers] }",
            "sql": "SELECT COUNT(*) FROM gold.fct_subscription WHERE new_flag = 1",
        },
        {
            "measure": "Churned Subscribers",
            "dax": "EVALUATE { [Churned Subscribers] }",
            "sql": "SELECT COUNT(*) FROM gold.fct_subscription WHERE churned_flag = 1",
        },
        # Advertising measures
        {
            "measure": "Ad Revenue",
            "dax": "EVALUATE { [Ad Revenue] }",
            "sql": "SELECT SUM(ad_revenue) FROM gold.fct_ad",
        },
        {
            "measure": "Ad Impressions",
            "dax": "EVALUATE { [Ad Impressions] }",
            "sql": "SELECT SUM(impressions) FROM gold.fct_ad",
        },
        {
            "measure": "Ad Clicks",
            "dax": "EVALUATE { [Ad Clicks] }",
            "sql": "SELECT SUM(clicks) FROM gold.fct_ad",
        },
    ]
    
    # Run all reconciliation tests
    results = []
    for test in tests:
        passed = reconcile_measure(
            measure_name=test["measure"],
            dax_expression=test["dax"],
            sql_query=test["sql"],
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            token=token,
            lakehouse_conn=lakehouse_conn,
            tolerance=0.01  # 1% relative tolerance (handles floating-point rounding)
        )
        results.append((test["measure"], passed))
    
    # Close connection
    lakehouse_conn.close()
    
    # Summarize
    print("\n═════════════════════════════════════════════════════════════════")
    print("  Reconciliation Results Summary")
    print("═════════════════════════════════════════════════════════════════")
    all_passed = True
    for measure, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:12} {measure}")
        if not passed:
            all_passed = False
    
    print("═════════════════════════════════════════════════════════════════")
    if all_passed:
        print("  ✓ ALL MEASURES RECONCILED — Semantic model is correct")
        sys.exit(0)
    else:
        print("  ✗ ONE OR MORE MEASURES FAILED — Semantic model does NOT match gold tables")
        print("     Promotion to Production BLOCKED")
        sys.exit(1)


if __name__ == "__main__":
    main()
