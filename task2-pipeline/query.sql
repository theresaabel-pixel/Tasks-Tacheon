-- ============================================================
-- Marketing Weather Pipeline: Chennai Hourly Weather Summary
-- Table: your_project.weather_pipeline.chennai_hourly_weather
-- ============================================================


-- -------------------------------------------------------
-- Query 1: Daily summary — avg temp, humidity, rain hours
-- -------------------------------------------------------
SELECT
    SUBSTR(timestamp_utc, 1, 10)            AS date,
    ROUND(AVG(temperature_c), 2)            AS avg_temp_c,
    ROUND(MAX(temperature_c), 2)            AS max_temp_c,
    ROUND(MIN(temperature_c), 2)            AS min_temp_c,
    ROUND(AVG(humidity_pct), 2)             AS avg_humidity_pct,
    ROUND(AVG(feels_like_delta_c), 2)       AS avg_feels_like_delta_c,
    ROUND(SUM(precipitation_mm), 2)         AS total_precipitation_mm,
    COUNTIF(is_raining = TRUE)              AS rainy_hours,
    COUNT(*)                                AS total_hours
FROM
    `your_project.weather_pipeline.chennai_hourly_weather`
GROUP BY
    date
ORDER BY
    date DESC;


-- -------------------------------------------------------
-- Query 2: Heat stress distribution across all hours
-- -------------------------------------------------------
SELECT
    heat_stress_category,
    COUNT(*)                                AS total_hours,
    ROUND(AVG(temperature_c), 2)           AS avg_temp_c,
    ROUND(AVG(humidity_pct), 2)            AS avg_humidity_pct,
    ROUND(AVG(feels_like_delta_c), 2)      AS avg_feels_like_delta_c
FROM
    `your_project.weather_pipeline.chennai_hourly_weather`
GROUP BY
    heat_stress_category
ORDER BY
    total_hours DESC;


-- -------------------------------------------------------
-- Query 3: Hottest hours of the day on average
-- Top 5 hours ranked by average apparent temperature
-- -------------------------------------------------------
SELECT
    SUBSTR(timestamp_local, 12, 5)          AS hour_of_day,
    ROUND(AVG(apparent_temperature_c), 2)   AS avg_apparent_temp_c,
    ROUND(AVG(temperature_c), 2)            AS avg_actual_temp_c,
    ROUND(AVG(humidity_pct), 2)             AS avg_humidity_pct,
    COUNT(*)                                AS data_points
FROM
    `your_project.weather_pipeline.chennai_hourly_weather`
GROUP BY
    hour_of_day
ORDER BY
    avg_apparent_temp_c DESC
LIMIT 5;


-- -------------------------------------------------------
-- Query 4: Days with extreme heat — actionable alert view
-- Flags any day where max apparent temp exceeded 42°C
-- -------------------------------------------------------
SELECT
    SUBSTR(timestamp_utc, 1, 10)            AS date,
    ROUND(MAX(apparent_temperature_c), 2)   AS max_apparent_temp_c,
    ROUND(MAX(temperature_c), 2)            AS max_actual_temp_c,
    COUNTIF(heat_stress_category = 'extreme_heat') AS extreme_heat_hours
FROM
    `your_project.weather_pipeline.chennai_hourly_weather`
GROUP BY
    date
HAVING
    MAX(apparent_temperature_c) > 42
ORDER BY
    max_apparent_temp_c DESC;