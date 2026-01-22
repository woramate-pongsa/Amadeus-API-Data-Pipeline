WITH source AS (
    SELECT * FROM {{ source("raw_data", "airline_data") }}
),

airline_data_transformed AS (
    SELECT
        IATA AS airline_code,
        Name AS airline_name,
        Country AS country_name
    FROM source
)

SELECT * FROM airline_data_transformed