import os
import io
import json
import time
import boto3
import pyarrow
import logging
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S" 
)
logger = logging.getLogger(__name__)

dag_folder = os.path.dirname(__file__)
env_path = os.path.join(dag_folder, ".env")
load_dotenv(env_path)

today = datetime.now()
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
TOKEN_URL = os.getenv("TOKEN_URL")
DATA_URL = os.getenv("DATA_URL")

OUTPUT_DIR = "data/raw_flights"
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

s3_client = boto3.client("s3", region_name=AWS_REGION)

# Use ID and Secert to exchange Auth Token 
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
        logger.exception("Exchange Auth Token failed")
        return None

# Define target dates which are 7, 30, and 90 days
def get_target_dates():
    target_days = [7, 30, 90]
    date_list = []

    for days in target_days:
        future_date = today + timedelta(days=days)
        date_list.append(future_date.strftime("%Y-%m-%d"))
    return date_list

# Fetch flights price data as raw data from BBK to each destination
def extract_flights(token, origin, destination, departure_date):
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": 1,
        "currencyCode": "THB",
        "max": 10
    }
    try:
        response = requests.get(DATA_URL, headers=headers, params=params)
        if response.status_code == 429:
            time.sleep(2)
            response = requests.get(DATA_URL, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            logger.info(f"Error: {response.status_code}\n{response.text}")
            return None
        
    except Exception:
        logger.exception("Extract data failed")
        return None

# Load flights price as a raw data to local in 'data/raw_flights'
def load_data(raw_data, origin, destination, search_date, departure_date):
    if not raw_data or "data" not in raw_data:
        return

    processed_list = []
    for offer in raw_data["data"]:
        try:
            aircraft_code = None
            try:
                first_segment = offer["itineraries"][0]["segments"][0]
                aircraft_code = first_segment["aircraft"]["code"]
            except (KeyError, IndexError):
                pass

            flight_info = {
                "search_date": search_date,
                "departure_date": departure_date,
                "origin": origin,
                "destination": destination,
                "airline_code": offer["validatingAirlineCodes"][0],
                "aircraft_code": aircraft_code,
                "price": float(offer["price"]["total"]),
                "currency": offer["price"]["currency"],
                "seat_availability": offer["numberOfBookableSeats"],
                "duration": offer["itineraries"][0]["duration"]
            }
            processed_list.append(flight_info)
        except KeyError as e:
            logger.warning(f"Missing data: {e} | {origin}-{destination}")
            continue
    flight_name = f"{origin}_{destination}"
    file_name = f"{OUTPUT_DIR}/flights_{search_date}_{flight_name}.json"

    with open(file_name, "a", encoding="utf-8") as f:
        for entry in processed_list:
            json.dump(entry, f)
            f.write("\n")
    logger.info(f"Loading {len(processed_list)} flights for {origin} to {destination} on {departure_date}")
    return file_name
    
# Load raw data from local 'data/raw_flights' to Amazon S3(Data Lake)
def load_to_s3_and_delete_local(local_file_path, s3_file_path):
    try:
        # Load in .json form (In term of raw data)
        s3_path_raw = f"raw/{s3_file_path}.json"
        s3_client.upload_file(local_file_path, S3_BUCKET_NAME, s3_path_raw)
        logger.info(f"Complete loading data to S3 in .json form (raw zone)")
        
        # Load in .parquet form (In term of staging)
        s3_path_staging = f"staging/{s3_file_path.replace('.json', '.parquet')}"
        df = pd.read_json(local_file_path, lines=True)
        
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, engine="pyarrow", index=False)
        parquet_buffer.seek(0)
        s3_client.upload_fileobj(parquet_buffer, S3_BUCKET_NAME, s3_path_staging)
        logger.info(f"Complete loading data to S3 in .parquet form (staging zone)")

        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        
    except Exception:
        logger.exception("Loading data to S3 failed")

def main():
    token = get_auth_token()
    if not token:
        return

    with open("routes_config.json", "r") as f:
        routes = json.load(f)

    target_dates = get_target_dates()
    date_today = datetime.now().strftime("%Y-%m-%d")

    logger.info("Starting flight price extraction and loading to S3")
    logger.info("--------------------------------------------------")
    for route in routes:
        origin = route["origin"]
        destination = route["destination"]
        logger.info("\n")
        logger.info(f"Processing Route: {origin} to {destination}")

        for dept_date in target_dates:
            raw_data = extract_flights(token, origin, destination, dept_date)

            if raw_data:
                # f"data/raw_flights/flights_2026-01-02_BKK_LHR.json"
                local_file = load_data(raw_data, origin, destination, date_today, dept_date)

                if local_file:
                    file_name = os.path.basename(local_file) # flights_2026-01-02_BKK_LHR.json
                    # s3://woramate-demo-s3-v1/raw_data/flights_price/{file_name}
                    s3_path = f"flights_price/search_date={today.strftime("%Y-%m-%d")}/{file_name[-12:-5]}"
                    load_to_s3_and_delete_local(local_file, s3_path)

            time.sleep(2)
    logger.info("--------------------------------------------------")
    logger.info("Complete flight price extraction and loading to S3")

if __name__ == "__main__":
    main()