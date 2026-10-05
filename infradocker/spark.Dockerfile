# Spark Master/Worker runtime
FROM bitnamilegacy/spark:3.5.0
ENV SPARK_MODE=master
ENV PYSPARK_PYTHON=python3
ENV PYTHONPATH=/opt/bitnami/spark/python:/opt/bitnami/spark/python/lib/py4j-0.10.9.7-src.zip
USER root
COPY requirements-spark.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements-spark.txt
WORKDIR /app
USER 1001
CMD ["/opt/bitnami/scripts/spark/run.sh"]
