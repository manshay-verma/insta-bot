import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, window, desc

def create_spark_session(app_name="InstaBotAnalytics"):
    """Initialize Spark session with necessary connectors."""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.mongodb.input.uri", os.environ.get("MONGODB_URI", "mongodb://mongodb:27017/instabot.profiles")) \
        .config("spark.mongodb.output.uri", os.environ.get("MONGODB_URI", "mongodb://mongodb:27017/instabot.analytics")) \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
        .get_create()

def run_hashtag_analysis(spark):
    """Example ETL job: Aggregate trending hashtags."""
    # This would normally load from MongoDB/S3
    df = spark.read.format("mongo").load()
    
    trending = df.groupBy("hashtag") \
        .agg(count("*").alias("count")) \
        .orderBy(desc("count"))
        
    trending.write.format("mongo").mode("append").save()
    return trending

if __name__ == "__main__":
    spark = create_spark_session()
    print("Spark Session Created Successfully.")
    # run_hashtag_analysis(spark)
    spark.stop()
