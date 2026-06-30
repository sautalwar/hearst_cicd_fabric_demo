"""
UAT Data Quality Tests

Pytest-style checks for null violations, uniqueness, and referential basics.
Queries the Fabric Warehouse via pyodbc (SQL endpoint).
Failures return nonzero exit → blocks promotion in cd-promote-uat.

Connection details are environment-driven (no secrets in code):
  FABRIC_WAREHOUSE_ENDPOINT — e.g., <workspace_id>.datawarehouse.fabric.microsoft.com
  AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID — SP auth
"""

import os
import pytest
import pyodbc
from typing import Optional


def get_warehouse_connection() -> pyodbc.Connection:
    """
    Acquire a connection to the Fabric Warehouse SQL endpoint using SP auth.
    Token acquisition is handled via ODBC ActiveDirectoryServicePrincipal auth.
    """
    endpoint = os.environ["FABRIC_WAREHOUSE_ENDPOINT"]
    client_id = os.environ["AZURE_CLIENT_ID"]
    client_secret = os.environ["AZURE_CLIENT_SECRET"]
    
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server={endpoint};"
        f"Database=wh_hearst;"
        f"UID={client_id};"
        f"PWD={client_secret};"
        f"Authentication=ActiveDirectoryServicePrincipal;"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )
    
    return pyodbc.connect(conn_str)


@pytest.fixture(scope="module")
def warehouse_conn():
    """Provide a shared connection for all tests in this module."""
    conn = get_warehouse_connection()
    yield conn
    conn.close()


class TestWarehouseDataQuality:
    """Data quality checks against wh_hearst sales schema."""
    
    def test_customer_no_null_customer_id(self, warehouse_conn):
        """Assert sales.customer.customer_id has no NULLs."""
        cursor = warehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sales.customer WHERE customer_id IS NULL")
        null_count = cursor.fetchone()[0]
        assert null_count == 0, f"sales.customer has {null_count} NULL customer_id rows"
    
    def test_customer_unique_customer_id(self, warehouse_conn):
        """Assert sales.customer.customer_id is unique."""
        cursor = warehouse_conn.cursor()
        cursor.execute("""
            SELECT customer_id, COUNT(*) as dup_count
            FROM sales.customer
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        assert len(duplicates) == 0, f"Duplicate customer_id values: {duplicates}"
    
    def test_order_no_null_order_id(self, warehouse_conn):
        """Assert sales.order.order_id has no NULLs."""
        cursor = warehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sales.[order] WHERE order_id IS NULL")
        null_count = cursor.fetchone()[0]
        assert null_count == 0, f"sales.order has {null_count} NULL order_id rows"
    
    def test_order_unique_order_id(self, warehouse_conn):
        """Assert sales.order.order_id is unique."""
        cursor = warehouse_conn.cursor()
        cursor.execute("""
            SELECT order_id, COUNT(*) as dup_count
            FROM sales.[order]
            GROUP BY order_id
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        assert len(duplicates) == 0, f"Duplicate order_id values: {duplicates}"
    
    def test_order_referential_integrity_customer(self, warehouse_conn):
        """Assert all sales.order.customer_id values exist in sales.customer."""
        cursor = warehouse_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM sales.[order] o
            WHERE NOT EXISTS (
                SELECT 1 FROM sales.customer c WHERE c.customer_id = o.customer_id
            )
        """)
        orphan_count = cursor.fetchone()[0]
        assert orphan_count == 0, f"{orphan_count} orphan orders with invalid customer_id"
    
    def test_order_amount_non_negative(self, warehouse_conn):
        """Assert sales.order.amount is non-negative (if column exists)."""
        cursor = warehouse_conn.cursor()
        # Check if amount column exists first
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'sales' AND TABLE_NAME = 'order' AND COLUMN_NAME = 'amount'
        """)
        if cursor.fetchone()[0] == 0:
            pytest.skip("sales.order.amount column does not exist")
        
        cursor.execute("SELECT COUNT(*) FROM sales.[order] WHERE amount < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} orders with negative amount"


if __name__ == "__main__":
    # Allow running directly for local testing
    pytest.main([__file__, "-v"])
