from pyspark.sql.functions import col, window, count, desc

def run_activity_stream(spark, stream_df):
    """
    Spark Structured Streaming Job.
    Listens for live bot actions and aggregates activity counts within a temporal window.
    """
    # Define aggregation window of 5 minutes with 1 minute slide
    windowed_counts = stream_df.withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window("timestamp", "5 minutes", "1 minute"),
            "action_type"
        ).count()
        
    # Write trending stream to console/Kafka for real-time dashboard updates
    query = windowed_counts.writeStream \
        .outputMode("complete") \
        .format("console") \
        .start()
    
    return query
