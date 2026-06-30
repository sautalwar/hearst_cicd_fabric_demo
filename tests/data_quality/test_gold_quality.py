"""
Gold Lakehouse Data Quality Tests

Pytest-style checks for the gold star schema (lh_hearst_gold):
  - Dimensions: dim_date, dim_brand, dim_content, dim_subscriber, dim_platform, dim_campaign
  - Facts: fct_engagement, fct_subscription, fct_ad

Validates:
  1. Table existence and row counts > 0
  2. No NULL surrogate keys (*_key columns)
  3. Dimension uniqueness (primary keys are unique)
  4. Referential integrity (fact foreign keys exist in dimensions)
  5. Date continuity (dim_date has no gaps)
  6. Non-negative measures (revenue, counts, MRR)

Connection: pyodbc → lh_hearst_gold SQL endpoint, SP auth

Environment variables required:
  FABRIC_SQL_ENDPOINT — lh_hearst_gold lakehouse SQL endpoint
  AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID — SP auth

Exit codes:
  0 = all tests passed
  nonzero = one or more tests failed → blocks UAT promotion
"""

import os
import pytest
import pyodbc
from typing import List, Tuple


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


@pytest.fixture(scope="module")
def lakehouse_conn():
    """Provide a shared connection for all tests in this module."""
    conn = get_lakehouse_connection()
    yield conn
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Table Existence and Row Count Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTableExistence:
    """Ensure all gold tables exist and are not empty."""
    
    @pytest.mark.parametrize("table_name", [
        "dim_date",
        "dim_brand",
        "dim_content",
        "dim_subscriber",
        "dim_platform",
        "dim_campaign",
        "fct_engagement",
        "fct_subscription",
        "fct_ad",
    ])
    def test_table_exists_and_has_rows(self, lakehouse_conn, table_name):
        """Assert that the table exists and has at least 1 row."""
        cursor = lakehouse_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM gold.{table_name}")
        row_count = cursor.fetchone()[0]
        assert row_count > 0, f"gold.{table_name} is empty (row count = 0)"


# ─────────────────────────────────────────────────────────────────────────────
# Dimension Quality Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDimensionQuality:
    """Data quality checks for dimension tables."""
    
    @pytest.mark.parametrize("table_name,key_column", [
        ("dim_date", "date_key"),
        ("dim_brand", "brand_key"),
        ("dim_content", "content_key"),
        ("dim_subscriber", "subscriber_key"),
        ("dim_platform", "platform_key"),
        ("dim_campaign", "campaign_key"),
    ])
    def test_dimension_no_null_primary_key(self, lakehouse_conn, table_name, key_column):
        """Assert that the dimension primary key has no NULLs."""
        cursor = lakehouse_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM gold.{table_name} WHERE {key_column} IS NULL")
        null_count = cursor.fetchone()[0]
        assert null_count == 0, f"gold.{table_name}.{key_column} has {null_count} NULL values"
    
    @pytest.mark.parametrize("table_name,key_column", [
        ("dim_date", "date_key"),
        ("dim_brand", "brand_key"),
        ("dim_content", "content_key"),
        ("dim_subscriber", "subscriber_key"),
        ("dim_platform", "platform_key"),
        ("dim_campaign", "campaign_key"),
    ])
    def test_dimension_primary_key_unique(self, lakehouse_conn, table_name, key_column):
        """Assert that the dimension primary key is unique (no duplicates)."""
        cursor = lakehouse_conn.cursor()
        cursor.execute(f"""
            SELECT {key_column}, COUNT(*) as dup_count
            FROM gold.{table_name}
            GROUP BY {key_column}
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        assert len(duplicates) == 0, f"Duplicate {key_column} values in gold.{table_name}: {duplicates}"


# ─────────────────────────────────────────────────────────────────────────────
# Fact Table Quality Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFactQuality:
    """Data quality checks for fact tables."""
    
    @pytest.mark.parametrize("table_name,key_columns", [
        ("fct_engagement", ["date_key", "brand_key", "content_key", "subscriber_key", "platform_key"]),
        ("fct_subscription", ["date_key", "brand_key", "subscriber_key"]),
        ("fct_ad", ["date_key", "brand_key", "campaign_key", "platform_key"]),
    ])
    def test_fact_no_null_foreign_keys(self, lakehouse_conn, table_name, key_columns):
        """Assert that fact table foreign keys have no NULLs."""
        cursor = lakehouse_conn.cursor()
        for key_col in key_columns:
            cursor.execute(f"SELECT COUNT(*) FROM gold.{table_name} WHERE {key_col} IS NULL")
            null_count = cursor.fetchone()[0]
            assert null_count == 0, f"gold.{table_name}.{key_col} has {null_count} NULL values"
    
    @pytest.mark.parametrize("fact_table,fk_column,dim_table,pk_column", [
        ("fct_engagement", "date_key", "dim_date", "date_key"),
        ("fct_engagement", "brand_key", "dim_brand", "brand_key"),
        ("fct_engagement", "content_key", "dim_content", "content_key"),
        ("fct_engagement", "subscriber_key", "dim_subscriber", "subscriber_key"),
        ("fct_engagement", "platform_key", "dim_platform", "platform_key"),
        ("fct_subscription", "date_key", "dim_date", "date_key"),
        ("fct_subscription", "brand_key", "dim_brand", "brand_key"),
        ("fct_subscription", "subscriber_key", "dim_subscriber", "subscriber_key"),
        ("fct_ad", "date_key", "dim_date", "date_key"),
        ("fct_ad", "brand_key", "dim_brand", "brand_key"),
        ("fct_ad", "campaign_key", "dim_campaign", "campaign_key"),
        ("fct_ad", "platform_key", "dim_platform", "platform_key"),
    ])
    def test_referential_integrity(self, lakehouse_conn, fact_table, fk_column, dim_table, pk_column):
        """Assert that all fact foreign keys exist in their dimension tables."""
        cursor = lakehouse_conn.cursor()
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM gold.{fact_table} f
            WHERE NOT EXISTS (
                SELECT 1 FROM gold.{dim_table} d WHERE d.{pk_column} = f.{fk_column}
            )
        """)
        orphan_count = cursor.fetchone()[0]
        assert orphan_count == 0, f"{orphan_count} orphan rows in gold.{fact_table}.{fk_column} (no matching {dim_table}.{pk_column})"


# ─────────────────────────────────────────────────────────────────────────────
# Date Continuity Test
# ─────────────────────────────────────────────────────────────────────────────

class TestDateDimension:
    """Data quality checks specific to dim_date."""
    
    def test_date_continuity_no_gaps(self, lakehouse_conn):
        """
        Assert that dim_date has no gaps (every consecutive date exists).
        This test finds the min and max date, then counts rows — the count should
        equal the number of days between min and max + 1.
        """
        cursor = lakehouse_conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as row_count,
                DATEDIFF(day, MIN(full_date), MAX(full_date)) + 1 as expected_count
            FROM gold.dim_date
        """)
        row = cursor.fetchone()
        row_count = row[0]
        expected_count = row[1]
        assert row_count == expected_count, f"dim_date has gaps: {row_count} rows, expected {expected_count}"


# ─────────────────────────────────────────────────────────────────────────────
# Business Rule Tests (Non-Negative Measures)
# ─────────────────────────────────────────────────────────────────────────────

class TestBusinessRules:
    """Business logic validations on fact table measures."""
    
    def test_engagement_non_negative_page_views(self, lakehouse_conn):
        """Assert fct_engagement.page_views is non-negative."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_engagement WHERE page_views < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} rows in fct_engagement have negative page_views"
    
    def test_engagement_non_negative_sessions(self, lakehouse_conn):
        """Assert fct_engagement.sessions is non-negative."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_engagement WHERE sessions < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} rows in fct_engagement have negative sessions"
    
    def test_subscription_non_negative_mrr(self, lakehouse_conn):
        """Assert fct_subscription.mrr is non-negative."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_subscription WHERE mrr < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} rows in fct_subscription have negative MRR"
    
    def test_ad_non_negative_impressions(self, lakehouse_conn):
        """Assert fct_ad.impressions is non-negative."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_ad WHERE impressions < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} rows in fct_ad have negative impressions"
    
    def test_ad_non_negative_clicks(self, lakehouse_conn):
        """Assert fct_ad.clicks is non-negative."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_ad WHERE clicks < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} rows in fct_ad have negative clicks"
    
    def test_ad_non_negative_revenue(self, lakehouse_conn):
        """Assert fct_ad.ad_revenue is non-negative."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_ad WHERE ad_revenue < 0")
        negative_count = cursor.fetchone()[0]
        assert negative_count == 0, f"{negative_count} rows in fct_ad have negative ad_revenue"
    
    def test_ad_clicks_lte_impressions(self, lakehouse_conn):
        """Assert that ad clicks never exceed impressions (business rule: clicks ≤ impressions)."""
        cursor = lakehouse_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold.fct_ad WHERE clicks > impressions")
        invalid_count = cursor.fetchone()[0]
        assert invalid_count == 0, f"{invalid_count} rows in fct_ad have clicks > impressions (impossible)"


if __name__ == "__main__":
    # Allow running directly for local testing
    pytest.main([__file__, "-v"])
