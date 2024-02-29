import logging
from cassandra.auth import PlainTextAuthProvider
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr, udf
from pyspark.sql.types import StringType, IntegerType
from cassandra.cluster import Cluster
import uuid
import requests


def create_keyspace(session):
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS diplomski
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'};
    """)


def create_table(session):
    session.execute("""
        CREATE TABLE IF NOT EXISTS diplomski.sentiment_data(
            id UUID PRIMARY KEY,
            company_name TEXT,
            sentiment_score INT
        );
    """)


def insert_data(session, **kwargs):
    company_name = kwargs.get('company_name')
    sentiment_score = kwargs.get('sentiment_score')

    try:
        session.execute("""
                INSERT INTO diplomski.sentiment_data(id, company_name, sentiment_score)
                    VALUES (%s, %s, %s)
                """, (
            uuid.uuid4(), company_name, sentiment_score))
    except Exception as e:
        logging.error(f"Couldn't insert data for {company_name} due to exception: {e}")

    return


def create_spark_connection():
    s_conn = None

    try:
        s_conn = SparkSession \
            .builder \
            .appName("SparkDataStreaming") \
            .config("spark.cassandra.connection.host", "cassandra") \
            .getOrCreate()

        s_conn.sparkContext.setLogLevel("WARN")
    except Exception as e:
        logging.error(f"Couldn't create the spark session due to exception: {e}")
    return s_conn


def create_cassandra_connection():
    cass_connection = None
    try:
        authentication = PlainTextAuthProvider(username='cassandra', password='cassandra')
        cluster = Cluster(['cassandra'], auth_provider=authentication)
        cass_connection = cluster.connect()
    except Exception as e:
        logging.error(f"Couldn't create Cassandra connection due to exception: {e}")

    return cass_connection


def get_spark_df(s_conn):
    spark_df = None
    try:
        spark_df = s_conn \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "broker:29092") \
            .option("subscribe", "news_data") \
            .option("failOnDataLoss", "false") \
            .load()
    except Exception as e:
        logging.warning(f"Initial dataframe couldn't be created due to exception: {e}")

    return spark_df


def get_sentiment_score(text):
    url = 'http://ml:8090/getSentimentScore'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json={'text': text}, headers=headers)

    if response.status_code == 200:
        return response.json()['score']
    else:
        return {"error": f"Failed to get sentiment score, status code {response.status_code}"}


def find_company_name(text):
    url = 'http://ml:8090/getCompanyName'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json={'text': text}, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to get company name, status code {response.status_code}"}


def create_selection_df(spark_df):
    df = spark_df \
        .select(col("value").cast("string").alias("value")) \
        .withColumn("company_name", get_company_name_udf(col("value"))) \
        .withColumn("sentiment_score", get_sentiment_score_udf(col("value")))

    df = df.withColumn("id", expr("uuid()"))

    df = df.filter(df.company_name != "")

    df = df.drop("value")

    return df


if __name__ == "__main__":
    spark = create_spark_connection()
    spark_df = get_spark_df(spark)

    get_sentiment_score_udf = udf(get_sentiment_score, IntegerType())
    get_company_name_udf = udf(find_company_name, StringType())

    spark.udf.register("get_sentiment_score_udf", get_sentiment_score_udf)
    spark.udf.register("get_company_name_udf", get_company_name_udf)

    selection_df = create_selection_df(spark_df)

    cassandra_connection = create_cassandra_connection()
    create_keyspace(cassandra_connection)
    create_table(cassandra_connection)

    query = (selection_df.writeStream.format("org.apache.spark.sql.cassandra")
             .option("checkpointLocation", "/tmp/checkpoint")
             .option("keyspace", "diplomski")
             .option("table", "sentiment_data")
             .start())

    query.awaitTermination()
