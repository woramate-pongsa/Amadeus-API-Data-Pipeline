import os
import json
import time
import boto3
import pyarrow
import logging
import requests
import pandas as pd
from io import StringIO, BytesIO
from dotenv import load_dotenv
from datetime import datetime, timedelta 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S" 
)
logger = logging.getLogger(__name__)

load_dotenv()
today = datetime.now()
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
TOKEN_URL = os.getenv("TOKEN_URL")
DATA_URL = os.getenv("DATA_URL")

AIRPORT_DATA_URL = os.getenv("AIRPORT_DATA_URL")
AIRCRAFT_DATA_URL = os.getenv("AIRCRAFT_DATA_URL")
AIRLINE_DATA_URL = os.getenv("AIRLINE_DATA_URL")

OUTPUT_DIR = "data/raw_flights"
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_FOLDER_NAME = os.getenv("S3_FOLDER_NAME")

AWS_REGION = os.getenv("AWS_REGION")

s3_client = boto3.client("s3", region_name=AWS_REGION)

def get_auth_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": API_SECRET
    }

    try:
        logger.info("Starting Auth Token exchange")
        auth_response = requests.post(TOKEN_URL, headers=headers, data=data)
        auth_response.raise_for_status()
        logger.info("Exchange Auth Token successful")
        return auth_response.json()["access_token"]
    except Exception:
        logging.exception("Exchange Auth Token failed")
        return

def load_data_to_s3(df, s3_file_name):
    csv_buffer = StringIO()
    parquet_buffer = BytesIO()
    
    s3_path_raw = f"raw/{S3_FOLDER_NAME}/{s3_file_name}.csv"
    s3_path_staging = f"staging/{S3_FOLDER_NAME}/{s3_file_name}.parquet"
    try:
        logger.info("Start loading file to S3")
        df.to_csv(csv_buffer, index=False)
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_path_raw, Body=csv_buffer.getvalue())

        df.to_parquet(parquet_buffer, engine="pyarrow", index=False)
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_path_staging, Body=parquet_buffer.getvalue())
        logger.info("Loading file to S3 successful")
    except Exception:
        logger.exception("Load to S3 failed")


def extract_airport_data():
    logger.info("Start extracting and loading airport, aircraft, and airline data to S3")
    cols = ["Airport ID", "Name", "City", "Country", "IATA", "ICAO", "Latitude", "Longitude", "Altitude", "Timezone", "DST", "Tz", "Type", "Source"]

    try:
        logger.info("Start airport data extraction")
        df = pd.read_csv(AIRPORT_DATA_URL, header=None, names=cols)
        df_clean = df[df["IATA"] != "\\N"][["IATA", "Name", "City", "Country", "Timezone"]]

        s3_file_name = "airport/dim_airport"
        load_data_to_s3(df_clean, s3_file_name)
    except Exception:
        logger.exception("Extracting airport data failed")

def extract_aircraft_data():
    try:
        logger.info("Start aircraft data extraction")
        df = pd.read_csv(AIRCRAFT_DATA_URL, sep="^")
        
        if "iata_code" in df.columns and "model" in df.columns:
            df_clean = df[["iata_code", "model"]].dropna().drop_duplicates()

            s3_file_name = "aircraft/dim_aircraft"
            load_data_to_s3(df_clean, s3_file_name)
        else:
            logging.warning("Aircarft data is mismatch")
    except Exception:
        logger.exception("Extracting aircraft data failed")

def extract_airfline_data():
    cols = ["Airline ID", "Name", "Alias", "IATA", "ICAO", "Callsign", "Country", "Active"]

    try:
        logger.info("Start airline data extraction")
        df = pd.read_csv(AIRLINE_DATA_URL, header=None, names=cols)
        df_clean = df[df["Active"] == "Y"][["IATA", "Name", "Country"]]

        s3_file_name = "airline/dim_airline"
        load_data_to_s3(df_clean, s3_file_name)
    except Exception:
        logger.exception("Extracting airline data failed")
    logger.info("Loading airport, aircraft, and airline to S3 successful")

def main():
    extract_airport_data()
    extract_aircraft_data()
    extract_airfline_data()

if __name__=="__main__":
    main()