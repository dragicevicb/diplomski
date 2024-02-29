import logging
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from kafka.admin import KafkaAdminClient, NewTopic

default_args = {
    'owner': 'diplomski',
    'start_date': datetime(2024, 2, 7, 8, 00)
}


def setup_kafka_topic():
    try:
        admin_client = KafkaAdminClient(bootstrap_servers='broker:29092')
        new_topic = NewTopic(name='news_data', num_partitions=1, replication_factor=1)
        admin_client.create_topics([new_topic])
        admin_client.close()
    except Exception as e:
        logging.error(f"Error when setting up Kafka topic: {e}")


with DAG('setup_spark',
         default_args=default_args,
         schedule_interval=None,
         catchup=False) as dag:
    setup_task = PythonOperator(
        task_id='setup_kafka_topic',
        python_callable=setup_kafka_topic
    )

    spark_task = SparkSubmitOperator(
        task_id="run_spark_job",
        application="/opt/airflow/dags/scripts/process_data.py",
        conn_id="spark_conn",
        packages="org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,"
                 "com.datastax.spark:spark-cassandra-connector_2.12:3.4.1",
        verbose=False
    )

    setup_task >> spark_task
