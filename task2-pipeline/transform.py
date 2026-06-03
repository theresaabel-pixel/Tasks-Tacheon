import pandas as pd
import logging
from datetime import timezone

logger = logging.getLogger(__name__)


def transform(raw: dict, config: dict) -> pd.DataFrame:
    """
    Flatten raw Open-Meteo API response into a clean tabular DataFrame.
    Handles nulls, type coercion, and adds derived analytical fields.
    """
    try:
        hourly = raw["hourly"]
    except KeyError:
        raise ValueError("API response missing 'hourly' key — unexpected response structure")

    logger.info("Flattening hourly API response into tabular format")

    df = pd.DataFrame({
        "timestamp_local":       hourly["time"],
        "temperature_c":         hourly["temperature_2m"],
        "apparent_temperature_c": hourly["apparent_temperature"],
        "humidity_pct":          hourly["relative_humidity_2m"],
        "windspeed_kmh":         hourly["windspeed_10m"],
        "precipitation_mm":      hourly["precipitation"],
        "weathercode":           hourly["weathercode"],
    })

    # --- Type coercion ---
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"])

    # Convert local time to UTC and store as string for BigQuery compatibility
    df["timestamp_utc"] = (
        df["timestamp_local"]
        .dt.tz_localize(config["location"]["timezone"])
        .dt.tz_convert("UTC")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    df["timestamp_local"] = df["timestamp_local"].dt.strftime("%Y-%m-%d %H:%M:%S")

    numeric_cols = [
        "temperature_c",
        "apparent_temperature_c",
        "humidity_pct",
        "windspeed_kmh",
        "precipitation_mm",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["weathercode"] = df["weathercode"].astype("Int64")  # nullable int

    # --- Handle nulls ---
    null_counts = df[numeric_cols].isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            logger.warning(f"Column '{col}' has {count} null values — forward filling")
            df[col] = df[col].ffill()

    # --- Derived fields ---

    # 1. Feels-like delta: how much hotter/colder it feels vs actual temp
    #    Positive = feels hotter, Negative = feels cooler
    df["feels_like_delta_c"] = (
        df["apparent_temperature_c"] - df["temperature_c"]
    ).round(2)

    # 2. Heat stress category based on apparent temperature
    #    Useful for understanding comfort/risk levels across hours
    df["heat_stress_category"] = df["apparent_temperature_c"].apply(_heat_stress_category)

    # 3. Precipitation flag
    df["is_raining"] = df["precipitation_mm"] > 0

    # 4. Location metadata from config
    df["location_name"] = config["location"]["name"]
    df["latitude"]      = config["location"]["latitude"]
    df["longitude"]     = config["location"]["longitude"]

    logger.info(f"Transform complete — {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Heat stress distribution:\n{df['heat_stress_category'].value_counts().to_string()}")

    return df


def _heat_stress_category(apparent_temp: float) -> str:
    """
    Categorise apparent temperature into heat stress levels.
    Based on standard meteorological comfort thresholds.
    """
    if pd.isnull(apparent_temp):
        return "unknown"
    elif apparent_temp < 18:
        return "comfortable"
    elif apparent_temp < 28:
        return "moderate"
    elif apparent_temp < 35:
        return "hot"
    elif apparent_temp < 42:
        return "very_hot"
    else:
        return "extreme_heat"