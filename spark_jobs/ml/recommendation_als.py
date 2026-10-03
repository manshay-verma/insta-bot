from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import col

def train_recommendation_model(spark, ratings_df):
    """
    Train an ALS model based on user-post interactions (ratings/likes).
    Provides collaborative filtering recommendations.
    """
    # ALS parameters: rank=10, maxIter=10, regParam=0.1
    als = ALS(
        userCol="user_id", 
        itemCol="post_id", 
        ratingCol="rating", 
        nonnegative=True, 
        implicitPrefs=True, 
        coldStartStrategy="drop"
    )
    
    model = als.fit(ratings_df)
    
    # Generate 10 recommendations for each user
    user_recs = model.recommendForAllUsers(10)
    
    # Write recommendations to S3/Parquet for backend retrieval
    user_recs.write.mode("overwrite").parquet("s3a://instabot-analytics/recommendations/als_latest/")
    return model
