select
    search_date,
    origin,
    destination,
    min(price) as min_price,
    avg(price) as avg_price,
    max(price) as max_price,
    count(*) as total_flights_found
from {{ ref('stg_flight_prices') }}
group by 1, 2, 3