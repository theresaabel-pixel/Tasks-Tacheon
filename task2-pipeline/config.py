import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_config(path: str = "config.yaml") -> dict:
    """
    Load and validate pipeline configuration from a YAML file.
    Raises clear errors if required keys are missing.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path.resolve()}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    _validate_config(config)
    logger.info(f"Config loaded successfully from {config_path}")
    return config


def _validate_config(config: dict):
    """
    Validate that all required config keys are present.
    """
    required_keys = {
        "location": ["name", "latitude", "longitude", "timezone"],
        "fetch":    ["days_back", "hourly_variables"],
        "bigquery": ["project_id", "dataset_id", "table_id", "dedup_key"],
    }

    for section, keys in required_keys.items():
        if section not in config:
            raise KeyError(f"Missing config section: '{section}'")
        for key in keys:
            if key not in config[section]:
                raise KeyError(f"Missing key '{key}' under config section '{section}'")

    # Sanity checks
    if config["fetch"]["days_back"] < 1:
        raise ValueError("fetch.days_back must be at least 1")

    if not config["fetch"]["hourly_variables"]:
        raise ValueError("fetch.hourly_variables cannot be empty")

    if config["bigquery"]["project_id"] == "YOUR_GCP_PROJECT_ID":
        raise ValueError("Replace YOUR_GCP_PROJECT_ID in config.yaml with your actual GCP project ID")