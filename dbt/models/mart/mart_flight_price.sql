{{
    config(
        materialized="incremental",
    )
}}

with flight_price AS (
    SELECT * FROM {{ ref("stg_flight_price") }}
),

airport AS (
    SELECT * FROM {{ ref("stg_airport_data") }}
),

airline AS (
    SELECT * FROM {{ ref("stg_airline_data") }}
),

aircraft_data AS (
    SELECT * FROM {{ ref("stg_aircraft_data") }}
)

SELECT
    f.flight_pk,
    f.price_checked_at,
    f.departure_date,
    to_char(f.departure_date, 'Day') AS departure_day_name,
    datediff(day, f.price_checked_at, f.departure_date) AS lead_time_days,
    f.origin AS origin_code,
    f.destination AS destination_code,
    al.city_name AS destination_city,
    f.airline_code,
    al.airline_name,
    ac.aircraft_code,
    ac.aircraft_model,
    f.flight_price AS price
    f.currency,
    f.seat_availability,
    f.duration
FROM 
    stg_flight_price f
LEFT JOIN airport ap ON f.origin = ap.airport_code
LEFT JOIN airline al ON f.airline_code = al.airline_code
LEFT JOIN aircraft ac ON f.aircraft_code = ac.aircraft_code