# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # Hearst Silver Transformation — Data Cleansing & Conforming
# 
# **Purpose:** Transform bronze raw tables into cleansed, conformed silver tables with surrogate keys.  
# **Source:** `lh_hearst_bronze` lakehouse (raw_* tables).  
# **Target:** `lh_hearst_silver` lakehouse (silver_* tables).  
# **Data Quality:** Deduplication, type enforcement, null handling, key generation.
# 
# ---
# 
# ## 🧹 Silver Schema
# 
# - `silver_content` — cleaned content with `content_key` surrogate key
# - `silver_subscriptions` — subscriber records with `subscriber_key`
# - `silver_engagement` — engagement events with typed timestamps and keys
# - `silver_ad_impressions` — ad data with `campaign_key`
# 
# **Transformation rules:**
# - Generate surrogate keys (monotonic integer keys)
# - Remove duplicates based on natural keys
# - Enforce data types and constraints
# - Handle nulls and invalid values
# - Add audit columns (load_timestamp)

# CELL ********************

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp, row_number, md5, concat_ws, to_date
from pyspark.sql.window import Window
from pyspark.sql.types import IntegerType

# Configuration
BRONZE_LAKEHOUSE = "lh_hearst_bronze"  # SCAFFOLD: Deployment rule will rewrite
SILVER_LAKEHOUSE = "lh_hearst_silver"  # SCAFFOLD: Deployment rule will rewrite

print(f"Transforming bronze → silver")
print(f"Source: {BRONZE_LAKEHOUSE}")
print(f"Target: {SILVER_LAKEHOUSE}")

# CELL ********************

# MARKDOWN ********************

# ## 1. Transform raw_content → silver_content

# CELL ********************

# Read bronze content
df_raw_content = spark.table(f"{BRONZE_LAKEHOUSE}.raw_content")

# Deduplicate by content_id (keep first occurrence)
window_spec = Window.partitionBy("content_id").orderBy("publish_date")
df_content_dedup = df_raw_content.withColumn("row_num", row_number().over(window_spec)) \
    .filter(col("row_num") == 1) \
    .drop("row_num")

# Generate surrogate key content_key
window_key = Window.orderBy("content_id")
df_silver_content = df_content_dedup.withColumn("content_key", row_number().over(window_key)) \
    .withColumn("load_timestamp", current_timestamp()) \
    .select(
        "content_key",
        "content_id",
        "title",
        "brand",
        "section",
        "content_type",
        "publish_date",
        "author",
        "word_count",
        "load_timestamp"
    )

print(f"✅ silver_content: {df_silver_content.count()} records (deduplicated)")

# Write to silver
df_silver_content.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_LAKEHOUSE}.silver_content")

# CELL ********************

# MARKDOWN ********************

# ## 2. Transform raw_subscriptions → silver_subscriptions

# CELL ********************

# Read bronze subscriptions
df_raw_subs = spark.table(f"{BRONZE_LAKEHOUSE}.raw_subscriptions")

# Deduplicate by subscriber_id (keep latest signup_date)
window_spec_subs = Window.partitionBy("subscriber_id").orderBy(col("signup_date").desc())
df_subs_dedup = df_raw_subs.withColumn("row_num", row_number().over(window_spec_subs)) \
    .filter(col("row_num") == 1) \
    .drop("row_num")

# Generate surrogate key subscriber_key
window_key_subs = Window.orderBy("subscriber_id")
df_silver_subs = df_subs_dedup.withColumn("subscriber_key", row_number().over(window_key_subs)) \
    .withColumn("load_timestamp", current_timestamp()) \
    .select(
        "subscriber_key",
        "subscriber_id",
        "brand",
        "signup_date",
        "plan",
        "region",
        "channel",
        "is_active",
        "churn_date",
        "mrr",
        "load_timestamp"
    )

print(f"✅ silver_subscriptions: {df_silver_subs.count()} records (deduplicated)")

# Write to silver
df_silver_subs.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_LAKEHOUSE}.silver_subscriptions")

# CELL ********************

# MARKDOWN ********************

# ## 3. Transform raw_engagement → silver_engagement

# CELL ********************

# Read bronze engagement
df_raw_engagement = spark.table(f"{BRONZE_LAKEHOUSE}.raw_engagement")

# Deduplicate by event_id (should be unique, but enforce)
df_engagement_dedup = df_raw_engagement.dropDuplicates(["event_id"])

# Type enforcement and null handling
df_silver_engagement = df_engagement_dedup \
    .withColumn("event_date", to_date(col("event_timestamp"))) \
    .withColumn("page_views", col("page_views").cast(IntegerType())) \
    .withColumn("sessions", col("sessions").cast(IntegerType())) \
    .withColumn("time_on_page_sec", col("time_on_page_sec").cast(IntegerType())) \
    .filter(col("page_views") > 0) \
    .withColumn("load_timestamp", current_timestamp()) \
    .select(
        "event_id",
        "event_timestamp",
        "event_date",
        "brand",
        "content_id",
        "subscriber_id",
        "platform",
        "page_views",
        "sessions",
        "time_on_page_sec",
        "load_timestamp"
    )

print(f"✅ silver_engagement: {df_silver_engagement.count()} records (cleaned)")

# Write to silver
df_silver_engagement.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_LAKEHOUSE}.silver_engagement")

# CELL ********************

# MARKDOWN ********************

# ## 4. Transform raw_ad_impressions → silver_ad_impressions

# CELL ********************

# Read bronze ad impressions
df_raw_ad = spark.table(f"{BRONZE_LAKEHOUSE}.raw_ad_impressions")

# Deduplicate by impression_id
df_ad_dedup = df_raw_ad.dropDuplicates(["impression_id"])

# Type enforcement and add event_date
df_silver_ad = df_ad_dedup \
    .withColumn("impression_date", to_date(col("impression_timestamp"))) \
    .withColumn("impressions", col("impressions").cast(IntegerType())) \
    .withColumn("clicks", col("clicks").cast(IntegerType())) \
    .filter(col("impressions") > 0) \
    .withColumn("load_timestamp", current_timestamp()) \
    .select(
        "impression_id",
        "impression_timestamp",
        "impression_date",
        "brand",
        "campaign_id",
        "campaign_name",
        "advertiser",
        "channel",
        "platform",
        "impressions",
        "clicks",
        "ad_revenue",
        "load_timestamp"
    )

print(f"✅ silver_ad_impressions: {df_silver_ad.count()} records (cleaned)")

# Write to silver
df_silver_ad.write.format("delta").mode("overwrite").saveAsTable(f"{SILVER_LAKEHOUSE}.silver_ad_impressions")

# CELL ********************

# MARKDOWN ********************

# ## ✅ Silver Transformation Complete
# 
# **Summary:**
# - Deduplication enforced on all tables
# - Surrogate keys generated (content_key, subscriber_key)
# - Data types enforced and validated
# - Invalid records filtered (e.g., page_views <= 0)
# - Audit columns added (load_timestamp)
# 
# **Next:** Run `nb_hearst_gold_build` to build the star schema for Direct Lake.

# CELL ********************

print("=" * 60)
print("SILVER TRANSFORMATION COMPLETE")
print("=" * 60)
print(f"Tables written to: {SILVER_LAKEHOUSE}")
print("")
print("Table counts:")
print(f"  silver_content:        {spark.table(f'{SILVER_LAKEHOUSE}.silver_content').count():>10,}")
print(f"  silver_subscriptions:  {spark.table(f'{SILVER_LAKEHOUSE}.silver_subscriptions').count():>10,}")
print(f"  silver_engagement:     {spark.table(f'{SILVER_LAKEHOUSE}.silver_engagement').count():>10,}")
print(f"  silver_ad_impressions: {spark.table(f'{SILVER_LAKEHOUSE}.silver_ad_impressions').count():>10,}")
print("=" * 60)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
