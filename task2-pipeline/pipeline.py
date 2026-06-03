import logging
import requests
from datetime import datetime, timedelta
from config import load_config
from transform import transform
from load import load

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch(config: dict) -> dict:
    """
    Fetch hourly weather data from Open-Meteo API.
    Parameterised from config — no hardcoded values.
    Handles API errors gracefully with clear messages.
    """
    location = config["location"]
    fetch_cfg = config["fetch"]

    end_date   = datetime.utcnow().date()
    start_date = end_date - timedelta(days=fetch_cfg["days_back"])

    params = {
        "latitude":        location["latitude"],
        "longitude":       location["longitude"],
        "hourly":          ",".join(fetch_cfg["hourly_variables"]),
        "timezone":        location["timezone"],
        "start_date":      start_date.isoformat(),
        "end_date":        end_date.isoformat(),
    }

    url = "https://api.open-meteo.com/v1/forecast"

    logger.info(f"Fetching weather data for {location['name']}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Variables: {fetch_cfg['hourly_variables']}")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Open-Meteo API request timed out after 30 seconds")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to Open-Meteo API — check your network")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Open-Meteo API returned an error: {e.response.status_code} — {e.response.text}")

    raw = response.json()

    # Sanity check — make sure we got hourly data back
    if "hourly" not in raw:
        raise ValueError(f"Unexpected API response structure — 'hourly' key missing. Got: {list(raw.keys())}")

    total_records = len(raw["hourly"]["time"])
    logger.info(f"Fetched {total_records} hourly records from Open-Meteo")

    return raw


def run():
    """
    Main pipeline entry point.
    Orchestrates: load config → fetch → transform → load into BigQuery.
    """
    logger.info("=" * 60)
    logger.info("Pipeline starting")
    logger.info("=" * 60)

    try:
        # Step 1: Load config
        logger.info("Step 1/4 — Loading config")
        config = load_config("config.yaml")

        # Step 2: Fetch
        logger.info("Step 2/4 — Fetching data from Open-Meteo")
        raw = fetch(config)

        # Step 3: Transform
        logger.info("Step 3/4 — Transforming raw data")
        df = transform(raw, config)

        # Step 4: Load
        logger.info("Step 4/4 — Loading into BigQuery")
        load(df, config)

        logger.info("=" * 60)
        logger.info("Pipeline completed successfully")
        logger.info("=" * 60)

    except FileNotFoundError as e:
        logger.error(f"Config error: {e}")
        raise
    except KeyError as e:
        logger.error(f"Config validation error: {e}")
        raise
    except RuntimeError as e:
        logger.error(f"Pipeline error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()