# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # Hearst Example Workload — provisioned by Terraform
# 
# This notebook is created automatically by Terraform (`infra/example_workload.tf`)
# as a runnable example of the Fabric workload. It builds a tiny sample table so you
# can see a real item created by Terraform, promoted through the deployment pipeline,
# and executed in Fabric.
# 
# **To run:** attach `lh_hearst_example` as the default lakehouse (left panel), then
# Run All. In production, replace this with real ingestion/transformation logic.

# CELL ********************

from pyspark.sql import Row

# Sample audience data — a stand-in for real ingested data.
rows = [
    Row(brand="Cosmopolitan",   channel="web",    sessions=1820, subscribers=240),
    Row(brand="Esquire",        channel="mobile", sessions=1310, subscribers=180),
    Row(brand="ELLE",           channel="web",    sessions=1605, subscribers=205),
    Row(brand="Car and Driver", channel="app",    sessions=1490, subscribers=150),
]

# CELL ********************

df = spark.createDataFrame(rows)
df.show()

# CELL ********************

# Write the sample table into the Terraform-provisioned lakehouse (lh_hearst_example).
df.write.mode("overwrite").saveAsTable("example_audience")

print("Wrote table: example_audience")
