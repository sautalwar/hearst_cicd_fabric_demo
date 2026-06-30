# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # Hearst Bronze Ingestion — Synthetic Data Generator
# 
# **Purpose:** Generate ~90 days of realistic synthetic audience, subscription, and ad data for Hearst digital properties.  
# **Target:** Bronze layer (`lh_hearst_bronze` lakehouse) — raw Delta tables.  
# **Data Product:** Hearst Digital Audience & Subscription Analytics.  
# **Brands:** Cosmopolitan, Esquire, Good Housekeeping, ELLE, Car and Driver.
# 
# ---
# 
# ## 📊 Bronze Schema
# 
# - `raw_engagement` — page views, sessions, time on page
# - `raw_subscriptions` — subscriber signups, plans, status changes
# - `raw_ad_impressions` — ad campaigns, impressions, clicks, revenue
# - `raw_content` — article/content metadata
# 
# **Note:** This notebook generates synthetic data with a deterministic seed for reproducibility.  
# In production, replace with actual data ingestion from Hearst's data sources.

# CELL ********************

import random
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, expr, monotonically_increasing_id
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType, DateType

# Deterministic seed for reproducibility
random.seed(42)

# CELL ********************

# Configuration
BRONZE_LAKEHOUSE = "lh_hearst_bronze"  # SCAFFOLD: Deployment rule will rewrite this per stage
DAYS_OF_DATA = 90
END_DATE = datetime(2026, 6, 23)
START_DATE = END_DATE - timedelta(days=DAYS_OF_DATA)

BRANDS = ["Cosmopolitan", "Esquire", "Good Housekeeping", "ELLE", "Car and Driver"]
SECTIONS = ["Fashion", "Beauty", "Home", "Food", "Travel", "Health", "Entertainment", "Auto", "Technology"]
CONTENT_TYPES = ["Article", "Video", "Gallery", "Recipe", "Review"]
PLATFORMS = ["web", "ios", "android"]
SUBSCRIBER_PLANS = ["basic", "premium", "family"]
SUBSCRIBER_REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
CHANNELS = ["organic", "paid_social", "email", "referral", "direct"]
ADVERTISERS = ["BrandX Auto", "LuxuryY Fashion", "TechZ Gadgets", "BeautyA Cosmetics", "HomeB Furnishings"]

print(f"Generating {DAYS_OF_DATA} days of data from {START_DATE.date()} to {END_DATE.date()}")

# CELL ********************

# MARKDOWN ********************

# ## 1. Generate raw_content (Hearst articles and content)

# CELL ********************

# Generate content catalog (2000 articles across brands)
content_data = []
content_id = 1

for brand in BRANDS:
    # Each brand gets 400 articles
    for i in range(400):
        section = random.choice(SECTIONS)
        content_type = random.choice(CONTENT_TYPES)
        
        content_data.append({
            "content_id": f"CNT{content_id:06d}",
            "title": f"{brand} {section} {content_type} #{i+1}",
            "brand": brand,
            "section": section,
            "content_type": content_type,
            "publish_date": (START_DATE + timedelta(days=random.randint(0, DAYS_OF_DATA-30))).date(),
            "author": f"Author{random.randint(1, 50)}",
            "word_count": random.randint(300, 2500)
        })
        content_id += 1

# Create DataFrame
content_schema = StructType([
    StructField("content_id", StringType(), False),
    StructField("title", StringType(), False),
    StructField("brand", StringType(), False),
    StructField("section", StringType(), False),
    StructField("content_type", StringType(), False),
    StructField("publish_date", DateType(), False),
    StructField("author", StringType(), True),
    StructField("word_count", IntegerType(), True)
])

df_content = spark.createDataFrame(content_data, schema=content_schema)
print(f"Generated {df_content.count()} content items")

# Write to bronze
df_content.write.format("delta").mode("overwrite").saveAsTable(f"{BRONZE_LAKEHOUSE}.raw_content")
print("✅ raw_content written to bronze")

# CELL ********************

# MARKDOWN ********************

# ## 2. Generate raw_subscriptions (subscriber lifecycle events)

# CELL ********************

# Generate 50,000 subscribers with signup dates spread across 90 days
subscription_data = []
subscriber_id = 1

for _ in range(50000):
    signup_date = START_DATE + timedelta(days=random.randint(0, DAYS_OF_DATA-1))
    plan = random.choice(SUBSCRIBER_PLANS)
    region = random.choice(SUBSCRIBER_REGIONS)
    channel = random.choice(CHANNELS)
    brand = random.choice(BRANDS)
    
    # Some subscribers churn (10% churn rate)
    is_active = random.random() > 0.10
    churn_date = None
    if not is_active:
        churn_date = signup_date + timedelta(days=random.randint(7, DAYS_OF_DATA))
        if churn_date > END_DATE:
            is_active = True
            churn_date = None
    
    subscription_data.append({
        "subscriber_id": f"SUB{subscriber_id:07d}",
        "brand": brand,
        "signup_date": signup_date.date(),
        "plan": plan,
        "region": region,
        "channel": channel,
        "is_active": is_active,
        "churn_date": churn_date.date() if churn_date else None,
        "mrr": 9.99 if plan == "basic" else (14.99 if plan == "premium" else 19.99)
    })
    subscriber_id += 1

subscription_schema = StructType([
    StructField("subscriber_id", StringType(), False),
    StructField("brand", StringType(), False),
    StructField("signup_date", DateType(), False),
    StructField("plan", StringType(), False),
    StructField("region", StringType(), False),
    StructField("channel", StringType(), False),
    StructField("is_active", StringType(), False),
    StructField("churn_date", DateType(), True),
    StructField("mrr", DoubleType(), False)
])

df_subscriptions = spark.createDataFrame(subscription_data, schema=subscription_schema)
print(f"Generated {df_subscriptions.count()} subscription records")

# Write to bronze
df_subscriptions.write.format("delta").mode("overwrite").saveAsTable(f"{BRONZE_LAKEHOUSE}.raw_subscriptions")
print("✅ raw_subscriptions written to bronze")

# CELL ********************

# MARKDOWN ********************

# ## 3. Generate raw_engagement (page views and sessions)

# CELL ********************

# Generate ~500K engagement events across 90 days (5-6K events per day)
engagement_data = []

for day_offset in range(DAYS_OF_DATA):
    event_date = START_DATE + timedelta(days=day_offset)
    
    # Generate 5000-7000 events per day
    daily_events = random.randint(5000, 7000)
    
    for _ in range(daily_events):
        brand = random.choice(BRANDS)
        content_id = f"CNT{random.randint(1, 2000):06d}"
        platform = random.choice(PLATFORMS)
        
        # Subscriber or anonymous user (60% subscriber traffic)
        is_subscriber = random.random() < 0.60
        subscriber_id = f"SUB{random.randint(1, 50000):07d}" if is_subscriber else None
        
        page_views = random.randint(1, 12)
        sessions = 1
        time_on_page_sec = page_views * random.randint(30, 300)
        
        engagement_data.append({
            "event_id": None,  # Will be generated via monotonically_increasing_id
            "event_timestamp": event_date + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            ),
            "brand": brand,
            "content_id": content_id,
            "subscriber_id": subscriber_id,
            "platform": platform,
            "page_views": page_views,
            "sessions": sessions,
            "time_on_page_sec": time_on_page_sec
        })

engagement_schema = StructType([
    StructField("event_id", StringType(), True),
    StructField("event_timestamp", TimestampType(), False),
    StructField("brand", StringType(), False),
    StructField("content_id", StringType(), False),
    StructField("subscriber_id", StringType(), True),
    StructField("platform", StringType(), False),
    StructField("page_views", IntegerType(), False),
    StructField("sessions", IntegerType(), False),
    StructField("time_on_page_sec", IntegerType(), False)
])

df_engagement = spark.createDataFrame(engagement_data, schema=engagement_schema)

# Generate event_id
df_engagement = df_engagement.withColumn(
    "event_id", 
    expr("concat('EVT', lpad(cast(monotonically_increasing_id() as string), 10, '0'))")
)

print(f"Generated {df_engagement.count()} engagement events")

# Write to bronze
df_engagement.write.format("delta").mode("overwrite").saveAsTable(f"{BRONZE_LAKEHOUSE}.raw_engagement")
print("✅ raw_engagement written to bronze")

# CELL ********************

# MARKDOWN ********************

# ## 4. Generate raw_ad_impressions (advertising data)

# CELL ********************

# Generate ~100K ad impressions across 90 days
ad_data = []

for day_offset in range(DAYS_OF_DATA):
    event_date = START_DATE + timedelta(days=day_offset)
    
    # Generate 1000-1500 ad impressions per day
    daily_impressions = random.randint(1000, 1500)
    
    for _ in range(daily_impressions):
        brand = random.choice(BRANDS)
        campaign_id = f"CMP{random.randint(1, 50):03d}"
        advertiser = random.choice(ADVERTISERS)
        channel = random.choice(["display", "video", "native", "sponsored"])
        platform = random.choice(PLATFORMS)
        
        impressions = random.randint(100, 5000)
        clicks = int(impressions * random.uniform(0.005, 0.03))  # 0.5-3% CTR
        ad_revenue = clicks * random.uniform(0.25, 2.50)  # $0.25-$2.50 per click
        
        ad_data.append({
            "impression_id": None,  # Will be generated
            "impression_timestamp": event_date + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            ),
            "brand": brand,
            "campaign_id": campaign_id,
            "campaign_name": f"{advertiser} {channel.title()} Campaign",
            "advertiser": advertiser,
            "channel": channel,
            "platform": platform,
            "impressions": impressions,
            "clicks": clicks,
            "ad_revenue": round(ad_revenue, 2)
        })

ad_schema = StructType([
    StructField("impression_id", StringType(), True),
    StructField("impression_timestamp", TimestampType(), False),
    StructField("brand", StringType(), False),
    StructField("campaign_id", StringType(), False),
    StructField("campaign_name", StringType(), False),
    StructField("advertiser", StringType(), False),
    StructField("channel", StringType(), False),
    StructField("platform", StringType(), False),
    StructField("impressions", IntegerType(), False),
    StructField("clicks", IntegerType(), False),
    StructField("ad_revenue", DoubleType(), False)
])

df_ad = spark.createDataFrame(ad_data, schema=ad_schema)

# Generate impression_id
df_ad = df_ad.withColumn(
    "impression_id", 
    expr("concat('IMP', lpad(cast(monotonically_increasing_id() as string), 10, '0'))")
)

print(f"Generated {df_ad.count()} ad impression records")

# Write to bronze
df_ad.write.format("delta").mode("overwrite").saveAsTable(f"{BRONZE_LAKEHOUSE}.raw_ad_impressions")
print("✅ raw_ad_impressions written to bronze")

# CELL ********************

# MARKDOWN ********************

# ## ✅ Bronze Ingestion Complete
# 
# **Summary:**
# - `raw_content`: 2,000 articles
# - `raw_subscriptions`: 50,000 subscribers
# - `raw_engagement`: ~500K events
# - `raw_ad_impressions`: ~100K impressions
# 
# **Next:** Run `nb_hearst_silver_transform` to cleanse and conform this data.

# CELL ********************

print("=" * 60)
print("BRONZE INGESTION COMPLETE")
print("=" * 60)
print(f"Tables written to: {BRONZE_LAKEHOUSE}")
print("")
print("Table counts:")
print(f"  raw_content:        {spark.table(f'{BRONZE_LAKEHOUSE}.raw_content').count():>10,}")
print(f"  raw_subscriptions:  {spark.table(f'{BRONZE_LAKEHOUSE}.raw_subscriptions').count():>10,}")
print(f"  raw_engagement:     {spark.table(f'{BRONZE_LAKEHOUSE}.raw_engagement').count():>10,}")
print(f"  raw_ad_impressions: {spark.table(f'{BRONZE_LAKEHOUSE}.raw_ad_impressions').count():>10,}")
print("=" * 60)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
