# Databricks notebook source
# MAGIC %md
# MAGIC # UAT Validation Notebook: Ingest Verification
# MAGIC 
# MAGIC Validates that the `lh_hearst_bronze` lakehouse and its `bronze.sample_events` table
# MAGIC have been deployed correctly to the UAT environment.
# MAGIC 
# MAGIC **Failure mode:** Assertions raise exceptions; the notebook run fails → UAT gate blocks promotion.

# COMMAND ----------

import sys
from pyspark.sql import SparkSession

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Verify Lakehouse Connectivity

# COMMAND ----------

spark = SparkSession.builder.getOrCreate()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Assert Table Exists and Has Rows

# COMMAND ----------

# Verify bronze.sample_events exists
try:
    df = spark.table("lh_hearst_bronze.bronze.sample_events")
    row_count = df.count()
    print(f"✓ Table lh_hearst_bronze.bronze.sample_events exists with {row_count} rows")
    assert row_count > 0, "Table is empty — expected at least 1 row after deployment"
except Exception as e:
    print(f"✗ FAILED: Table lh_hearst_bronze.bronze.sample_events not accessible: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Assert Expected Columns Present

# COMMAND ----------

expected_columns = {"event_id", "event_timestamp", "event_type", "user_id"}
actual_columns = set(df.columns)

missing = expected_columns - actual_columns
if missing:
    raise AssertionError(f"Missing expected columns: {missing}")

print(f"✓ All expected columns present: {actual_columns}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Basic Data Quality Checks

# COMMAND ----------

# Check for nulls in critical columns
null_counts = df.select(
    [spark_sum(col(c).isNull().cast("int")).alias(c) for c in ["event_id", "event_timestamp"]]
).collect()[0].asDict()

for col_name, null_ct in null_counts.items():
    if null_ct > 0:
        raise AssertionError(f"Column {col_name} has {null_ct} NULL values — expected zero")

print("✓ No NULLs in critical columns (event_id, event_timestamp)")

# COMMAND ----------

# Import for aggregations
from pyspark.sql.functions import col, sum as spark_sum

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC All validation checks passed. Lakehouse ingest is verified for UAT.
