# Fabric notebook: nb_hearst_ingest
# SCAFFOLD — Real Git sync will regenerate/refine this content

# META
# language: python
# kernel: pyspark

# CELL 1
# Markdown
"""
# Hearst Data Ingestion Notebook

This notebook demonstrates ingesting sample event data into the **lh_hearst_bronze** lakehouse.

**Schema-enabled lakehouse:** bronze.sample_events

**Environment-specific binding:** This notebook will be parameterized per stage (DEV/UAT/PROD)
via Fabric deployment rules so it points to the correct lakehouse per environment.
"""

# CELL 2
# Import libraries
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
from pyspark.sql.functions import current_timestamp
from datetime import datetime

# CELL 3
# Create sample event data
print("🔵 Creating sample events dataframe...")

schema = StructType([
    StructField("event_id", IntegerType(), False),
    StructField("event_type", StringType(), False),
    StructField("user_id", StringType(), False),
    StructField("timestamp", TimestampType(), False),
    StructField("properties", StringType(), True)
])

sample_data = [
    (1, "page_view", "user_123", datetime(2026, 6, 23, 10, 15, 0), '{"page": "/home"}'),
    (2, "click", "user_456", datetime(2026, 6, 23, 10, 20, 0), '{"element": "subscribe_button"}'),
    (3, "page_view", "user_789", datetime(2026, 6, 23, 10, 25, 0), '{"page": "/articles/tech"}'),
    (4, "scroll", "user_123", datetime(2026, 6, 23, 10, 30, 0), '{"depth": 75}'),
    (5, "exit", "user_456", datetime(2026, 6, 23, 10, 35, 0), '{"session_duration_sec": 300}')
]

df = spark.createDataFrame(sample_data, schema)

print(f"✅ Created {df.count()} sample event records")
df.show(5, truncate=False)

# CELL 4
# Write to lakehouse: bronze schema, sample_events table
print("🔵 Writing to lakehouse: lh_hearst_bronze.bronze.sample_events...")

# In production, this lakehouse reference would be parameterized per stage
# via deployment rules (DEV → dev lakehouse, UAT → uat lakehouse, PROD → prod lakehouse)
df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("lh_hearst_bronze.bronze.sample_events")

print("✅ Ingestion complete!")

# CELL 5
# Verify write
verify_df = spark.sql("SELECT COUNT(*) as record_count FROM lh_hearst_bronze.bronze.sample_events")
verify_df.show()

print("🔵 Sample query: Top 3 event types")
spark.sql("""
    SELECT event_type, COUNT(*) as count
    FROM lh_hearst_bronze.bronze.sample_events
    GROUP BY event_type
    ORDER BY count DESC
    LIMIT 3
""").show()

# CELL 6
# Schema introspection
print("🔵 Table schema:")
spark.sql("DESCRIBE EXTENDED lh_hearst_bronze.bronze.sample_events").show(truncate=False)

print("✅ Notebook execution complete")
print("📝 REMINDER: Deployment pipelines move METADATA, not DATA.")
print("   Each stage (UAT/PROD) needs its own schema/seed strategy.")
