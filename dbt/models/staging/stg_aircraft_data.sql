WITH source AS (
    SELECT * FROM {{ source("raw_data", "aircraft_data") }}
),

aircraft_data_transformed AS (
    SELECT
        iata_code AS aircraft_code,
        airplane_model AS aircraft_model,
    FROM source
)

SELECT * FROM aircraft_data_transformed