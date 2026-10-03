# Spark Master/Worker runtime
FROM bitnami/spark:3.5.0
ENV SPARK_MODE=master
ENV PYSPARK_PYTHON=python3
USER root
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements.txt
WORKDIR /app
USER 1001
CMD ["/opt/bitnami/scripts/spark/run.sh"]
