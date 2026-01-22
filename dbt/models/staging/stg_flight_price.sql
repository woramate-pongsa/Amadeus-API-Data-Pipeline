WITH source AS (
    SELECT * FROM {{ source("raw_data", "flight_price") }}
),

flight_price_transformed AS (
    SELECT
        {{
            dbt.utils.generate_surrogate_key([
                "search_date",
                "departure_date",
                "origin",
                "destination",
                "airline_code",
                "price",
                "duration"
            ])
        }} AS flight_pk,
        search_date AS price_checked_at,
        departure_date,
        origin,
        destination,
        airline_code,
        aircraft_code,
        COALESCE(price, 0) AS flight_price,
        currency,
        seat_availability,
        duration
    FROM source
)

SELECT * FROM flight_price_transformed