# ⚡ Apache Spark Jobs Module

> Powering Big Data analytics and ML-based recommendations for the InstaBot platform.

---

## 🏛️ Architecture Overview

The `spark_jobs/` module handles high-performance ETL, batch processing, and machine learning by connecting directly to our data lakes and live databases.

```
       ┌───────────────┐          ┌───────────────┐
       │   MONGODB     │◄─────────┤ Apache Spark  ├──────────┐
       │ (JSON Data)   │          │ (ETL Engine)  │          │
       └───────────────┘          └───────┬───────┘          │
                                          │                  │
       ┌───────────────┐          ┌───────▼───────┐  ┌───────▼───────┐
       │      S3       │◄─────────┤  POSTGRESQL   │  │  DATABRICKS   │
       │ (Parquet/CSV) │          │ (Analytics)   │  │ (Cloud Jobs)  │
       └───────────────┘          └───────────────┘  └───────────────┘
```

---

## 📂 Module Structure

- **`spark_app.py`**: The main entry point for the Spark session, including MongoDB/SQL connectors.
- **`batch/`**: Daily and weekly ETL jobs for hashtag trending and user engagement aggregation.
- **`ml/`**: Machine Learning pipelines for user-collaborative filtering (ALS) and post recommendations.
- **`streaming/`**: Real-time Spark Streaming for live activity monitoring and hashtag counters.
- **`Dockerfile`**: A specialized Bitnami Spark image with pre-configured JARs for MongoDB and AWS connectivity.

---

## 🚀 Getting Started

### 1. Build & Run with Docker

Spark is fully containerized! You can launch the Spark master and its dependencies using the root `docker-compose.yml`.

```powershell
# Build the spark image
docker build -f infradocker/spark.Dockerfile . -t instabot-spark

# Run as a container service
docker run instabot-spark python3 spark_app.py
```

### 2. Manual Spark Submit (For EMR/Databricks)

```bash
spark-submit \
  --master local[*] \
  --packages org.mongodb.spark:mongo-spark-connector_2.12:3.0.1 \
  spark_app.py
```

---

## 📊 Core Data Jobs

### 1️⃣ Hashtag Trending Analysis
Aggregates and ranks hashtags discovered during the last 24 hours from the MongoDB `profiles` collection.

### 2️⃣ User Engagement ETL
Extracts like/comment counts per user across all scraped posts, calculating the "Total Engagement Weight" for each user.

### 3️⃣ ALS Recommendation Engine (MLlib)
Uses Alternating Least Squares (ALS) to generate user similarities and recommend new profiles to explore based on interaction history.

---

## 🔧 Environment Variables

The Spark engine reads the following values from the global environment:

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | Connection URI for the data lake | `mongodb://mongodb:27017` |
| `SPARK_MASTER` | Spark Master address for clustering | `local[*]` |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket for cold storage (Parquet) | `instabot-media` |

---

## 📈 Roadmap Status
- **Batch Processing**: ✅ 100%
- **ML Jobs**: ✅ 100%
- **Streaming**: ✅ 100%
- **SQL Analytics**: ✅ 100%
- **Data Pipelines**: ✅ 100%
