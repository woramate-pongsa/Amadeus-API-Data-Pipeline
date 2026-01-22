import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from airflow.decorators import dag
import pendulum
from airflow.operators.bash import BashOperator
from airflow.providers.amazon.aws.transfers.s3_to_redshift import S3ToRedshiftOperator

dag_folder = os.path.dirname(__file__)
env_path = os.path.join(dag_folder, ".env")
load_dotenv(env_path)

PROJECT_PATH=os.getenv("PROJECT_PATH")
S3_BUCKET_NAME=os.getenv("S3_BUCKET_NAME")

today = datetime.now()
s3_key_path = f"staging/flights_price/search_date={today.strftime("%Y-%m-%d")}/"

PROJECT_PATH = os.getenv("PROJECT_PATH")
DBT_HOST = os.getenv("DBT_HOST")
DBT_USER = os.getenv("DBT_USER")
DBT_PASSWORD = os.getenv("DBT_PASSWORD")
DBT_PORT = os.getenv("DBT_PORT")
DBT_DBNAME = os.getenv("DBT_DBNAME")
DBT_SCHEMA = os.getenv("DBT_SCHEMA")

DBT_ENV = {
    "DBT_PROFILES_DIR": f"{PROJECT_PATH}/dbt",
    "DBT_HOST": DBT_HOST,
    "DBT_USER": DBT_USER,
    "DBT_PASSWORD": DBT_PASSWORD,
    "DBT_PORT": DBT_PORT,
    "DBT_DBNAME": DBT_DBNAME,
    "DBT_SCHEMA": DBT_SCHEMA
}

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

@dag (
    dag_id="full_pipeline",
    default_args=default_args,
    start_date=pendulum.today("UTC").add(days=-1),
    schedule="@daily",
    catchup=False,
    tags=["production", "airflow", "pipeline"]
)

def run_dag():

    t1_extract_flight_price_to_s3 = BashOperator(
        task_id="extract_flight_price_to_s3",
        bash_command=f"cd {PROJECT_PATH}/scripts && python3 extract_flight_price.py"
    )

    t2_load_s3_to_redshift = S3ToRedshiftOperator(
        task_id="load_s3_to_redshift",
        schema="public",
        table="flight_price",
        s3_bucket=S3_BUCKET_NAME,
        s3_key=s3_key_path,
        copy_options=["FORMAT AS PARQUET"],
        redshift_conn_id="redshift_default",
        aws_conn_id="aws_default",
        method="APPEND"
    )

    t3_dbt_run_model = BashOperator(
        task_id="dbt_run_model",
        bash_command="cd {PROJECT_PATH}/dbt && dbt run --profiles-dir .",
        env={**os.environ, **DBT_ENV}
    )

    t4_dbt_test_model = BashOperator(
        task_id="dbt_test_model",
        bash_command="cd {PROJECT_PATH}/dbt && dbt test",
        env={**os.environ, **DBT_ENV}
    )

    t1_extract_flight_price_to_s3 >> t2_load_s3_to_redshift >> t3_dbt_run_model >> t4_dbt_test_model

run_dag()