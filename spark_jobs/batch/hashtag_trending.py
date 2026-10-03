from pyspark.sql.functions import col, count, desc, window

def run_hashtag_trending(spark, input_df=None):
    """
    Daily Hashtag Trending Job.
    Aggregates hashtag mentions and ranks them by popularity within the last 24h.
    """
    if input_df is None:
        # Fallback to loading from MongoDB if no DF provided
        input_df = spark.read.format("mongo").load()
    
    trending_df = input_df.select("hashtag", "timestamp") \
        .groupBy("hashtag") \
        .agg(count("*").alias("mention_count")) \
        .orderBy(desc("mention_count"))
    
    # Save results to analytics collection
    trending_df.write.format("mongo").mode("append").save()
    return trending_df
