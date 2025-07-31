from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

from crawling import crawl_all

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='crawl_patchnotes_dag',
    description='LoL 패치노트 크롤링 DAG',
    default_args=default_args,
    start_date=datetime(2025, 7, 11),
    schedule_interval='@daily',
    catchup=False,
    tags=['lol', 'crawler']
) as dag:

    crawl_task = PythonOperator(
        task_id='run_patchnote_crawler',
        python_callable=crawl_all
    )

    crawl_task