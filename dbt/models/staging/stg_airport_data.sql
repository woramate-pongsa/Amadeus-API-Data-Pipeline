WITH source AS (
    SELECT * FROM {{ source("raw_data", "airport_data") }}
),

airport_data_transformed AS (
    SELECT
        IATA AS airport_code,
        Name AS airport_name,
        City AS city_name,
        Country AS country_name,
        Timezone AS timezone
    FROM source
)

SELECT * FROM airport_data_transformed