#!/usr/bin/env python3
"""
Hearst Digital Audience & Subscription Analytics — Synthetic Data Generator
Standalone local version (uses pandas instead of PySpark)

Purpose: Generate ~90 days of realistic synthetic data for local testing and validation
         without requiring a Fabric Spark environment.

Output: CSV files written to data/seed/ directory
  - raw_content.csv
  - raw_subscriptions.csv
  - raw_engagement.csv
  - raw_ad_impressions.csv

Usage: python data/generate_synthetic.py
"""

import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Deterministic seed for reproducibility
random.seed(42)

# Configuration
DAYS_OF_DATA = 90
END_DATE = datetime(2026, 6, 23)
START_DATE = END_DATE - timedelta(days=DAYS_OF_DATA)
OUTPUT_DIR = Path(__file__).parent / "seed"

BRANDS = ["Cosmopolitan", "Esquire", "Good Housekeeping", "ELLE", "Car and Driver"]
SECTIONS = ["Fashion", "Beauty", "Home", "Food", "Travel", "Health", "Entertainment", "Auto", "Technology"]
CONTENT_TYPES = ["Article", "Video", "Gallery", "Recipe", "Review"]
PLATFORMS = ["web", "ios", "android"]
SUBSCRIBER_PLANS = ["basic", "premium", "family"]
SUBSCRIBER_REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
CHANNELS = ["organic", "paid_social", "email", "referral", "direct"]
ADVERTISERS = ["BrandX Auto", "LuxuryY Fashion", "TechZ Gadgets", "BeautyA Cosmetics", "HomeB Furnishings"]

print("=" * 70)
print("Hearst Synthetic Data Generator (Local Pandas Version)")
print("=" * 70)
print(f"Generating {DAYS_OF_DATA} days of data from {START_DATE.date()} to {END_DATE.date()}")
print(f"Output directory: {OUTPUT_DIR}")
print("=" * 70)

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_content():
    """Generate content catalog (2000 articles across brands)"""
    print("Generating raw_content...")
    content_data = []
    content_id = 1
    
    for brand in BRANDS:
        for i in range(400):  # 400 articles per brand
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
    
    df = pd.DataFrame(content_data)
    output_path = OUTPUT_DIR / "raw_content.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✅ {len(df):,} records → {output_path}")
    return df


def generate_subscriptions():
    """Generate 50,000 subscribers with signup dates"""
    print("Generating raw_subscriptions...")
    subscription_data = []
    subscriber_id = 1
    
    for _ in range(50000):
        signup_date = START_DATE + timedelta(days=random.randint(0, DAYS_OF_DATA-1))
        plan = random.choice(SUBSCRIBER_PLANS)
        region = random.choice(SUBSCRIBER_REGIONS)
        channel = random.choice(CHANNELS)
        brand = random.choice(BRANDS)
        
        # 10% churn rate
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
    
    df = pd.DataFrame(subscription_data)
    output_path = OUTPUT_DIR / "raw_subscriptions.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✅ {len(df):,} records → {output_path}")
    return df


def generate_engagement():
    """Generate ~500K engagement events across 90 days"""
    print("Generating raw_engagement...")
    engagement_data = []
    event_id = 1
    
    for day_offset in range(DAYS_OF_DATA):
        event_date = START_DATE + timedelta(days=day_offset)
        
        # 5000-7000 events per day
        daily_events = random.randint(5000, 7000)
        
        for _ in range(daily_events):
            brand = random.choice(BRANDS)
            content_id = f"CNT{random.randint(1, 2000):06d}"
            platform = random.choice(PLATFORMS)
            
            # 60% subscriber traffic
            is_subscriber = random.random() < 0.60
            subscriber_id = f"SUB{random.randint(1, 50000):07d}" if is_subscriber else None
            
            page_views = random.randint(1, 12)
            sessions = 1
            time_on_page_sec = page_views * random.randint(30, 300)
            
            engagement_data.append({
                "event_id": f"EVT{event_id:010d}",
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
            event_id += 1
    
    df = pd.DataFrame(engagement_data)
    output_path = OUTPUT_DIR / "raw_engagement.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✅ {len(df):,} records → {output_path}")
    return df


def generate_ad_impressions():
    """Generate ~100K ad impressions across 90 days"""
    print("Generating raw_ad_impressions...")
    ad_data = []
    impression_id = 1
    
    for day_offset in range(DAYS_OF_DATA):
        event_date = START_DATE + timedelta(days=day_offset)
        
        # 1000-1500 ad impressions per day
        daily_impressions = random.randint(1000, 1500)
        
        for _ in range(daily_impressions):
            brand = random.choice(BRANDS)
            campaign_id = f"CMP{random.randint(1, 50):03d}"
            advertiser = random.choice(ADVERTISERS)
            channel = random.choice(["display", "video", "native", "sponsored"])
            platform = random.choice(PLATFORMS)
            
            impressions = random.randint(100, 5000)
            clicks = int(impressions * random.uniform(0.005, 0.03))  # 0.5-3% CTR
            ad_revenue = clicks * random.uniform(0.25, 2.50)
            
            ad_data.append({
                "impression_id": f"IMP{impression_id:010d}",
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
            impression_id += 1
    
    df = pd.DataFrame(ad_data)
    output_path = OUTPUT_DIR / "raw_ad_impressions.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✅ {len(df):,} records → {output_path}")
    return df


def main():
    """Generate all synthetic data files"""
    
    # Generate all datasets
    df_content = generate_content()
    df_subscriptions = generate_subscriptions()
    df_engagement = generate_engagement()
    df_ad = generate_ad_impressions()
    
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"Total records generated:")
    print(f"  Content:        {len(df_content):>10,}")
    print(f"  Subscriptions:  {len(df_subscriptions):>10,}")
    print(f"  Engagement:     {len(df_engagement):>10,}")
    print(f"  Ad Impressions: {len(df_ad):>10,}")
    print(f"  TOTAL:          {len(df_content) + len(df_subscriptions) + len(df_engagement) + len(df_ad):>10,}")
    print("=" * 70)
    print(f"CSV files written to: {OUTPUT_DIR.absolute()}")
    print("")
    print("Next steps:")
    print("  1. Review CSV files in data/seed/")
    print("  2. Upload to Fabric lakehouse or use for local validation")
    print("  3. Run medallion notebooks in Fabric to build the star schema")
    print("=" * 70)


if __name__ == "__main__":
    main()
