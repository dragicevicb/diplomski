import logging
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import json
import requests
from kafka import KafkaProducer
import time

default_args = {
    'owner': 'diplomski',
    'start_date': datetime(2024, 2, 7, 8, 00)
}


def get_data():
    try:
        response = requests.get(
            'http://api:8086/getData')
        if response.status_code == 200:
            data = response.json()
            return data.get('sentence', 'No sentence received')
        else:
            logging.error(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error: {e}")
        return None


def load_to_kafka():
    curr_time = time.time()

    producer = KafkaProducer(
        bootstrap_servers=['broker:29092'],
        max_block_ms=5000
    )
    while True:
        if time.time() > curr_time + 60:
            break
        try:
            data = get_data()
            producer.send("news_data", json.dumps(data).encode('utf-8'))
            time.sleep(2)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            continue


with DAG('stream_data',
         default_args=default_args,
         schedule_interval=None,
         catchup=False) as dag:
    streaming_task = PythonOperator(
        task_id='load_to_kafka',
        python_callable=load_to_kafka
    )