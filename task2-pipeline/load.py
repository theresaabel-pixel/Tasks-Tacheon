import logging
import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)


def load(df: pd.DataFrame, config: dict):
    """
    Load transformed DataFrame into BigQuery.
    Deduplicates against existing rows using the configured dedup key
    before inserting — safe to run repeatedly without creating duplicates.
    """
    bq_cfg     = config["bigquery"]
    project_id = bq_cfg["project_id"]
    dataset_id = bq_cfg["dataset_id"]
    table_id   = bq_cfg["table_id"]
    dedup_key  = bq_cfg["dedup_key"]

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    client        = bigquery.Client(project=project_id)

    # --- Ensure dataset exists ---
    _ensure_dataset(client, project_id, dataset_id)

    # --- Ensure table exists ---
    _ensure_table(client, full_table_id)

    # --- Dedup: fetch existing keys, filter them out ---
    df_clean = _deduplicate(client, df, full_table_id, dedup_key)

    if df_clean.empty:
        logger.info("No new rows to insert — all records already exist in BigQuery")
        return

    # --- Insert net-new rows ---
    errors = client.insert_rows_json(
        full_table_id,
        df_clean.to_dict(orient="records")
    )

    if errors:
        logger.error(f"BigQuery insert errors: {errors}")
        raise RuntimeError(f"Failed to insert rows into BigQuery: {errors}")

    logger.info(f"Inserted {len(df_clean)} new rows into {full_table_id}")


def _ensure_dataset(client: bigquery.Client, project_id: str, dataset_id: str):
    """
    Create the dataset if it does not already exist.
    """
    dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset_ref.location = "US"

    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset '{dataset_id}' already exists")
    except Exception:
        client.create_dataset(dataset_ref, exists_ok=True)
        logger.info(f"Created dataset '{dataset_id}'")


def _ensure_table(client: bigquery.Client, full_table_id: str):
    """
    Create the table with explicit schema if it does not already exist.
    """
    schema = [
        bigquery.SchemaField("timestamp_utc",            "STRING",  mode="REQUIRED"),
        bigquery.SchemaField("timestamp_local",          "STRING",  mode="NULLABLE"),
        bigquery.SchemaField("temperature_c",            "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("apparent_temperature_c",   "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("humidity_pct",             "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("windspeed_kmh",            "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("precipitation_mm",         "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("weathercode",              "INT64",   mode="NULLABLE"),
        bigquery.SchemaField("feels_like_delta_c",       "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("heat_stress_category",     "STRING",  mode="NULLABLE"),
        bigquery.SchemaField("is_raining",               "BOOL",    mode="NULLABLE"),
        bigquery.SchemaField("location_name",            "STRING",  mode="NULLABLE"),
        bigquery.SchemaField("latitude",                 "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("longitude",                "FLOAT64", mode="NULLABLE"),
    ]

    table = bigquery.Table(full_table_id, schema=schema)

    try:
        client.get_table(full_table_id)
        logger.info(f"Table '{full_table_id}' already exists")
    except Exception:
        client.create_table(table)
        logger.info(f"Created table '{full_table_id}'")


def _deduplicate(
    client: bigquery.Client,
    df: pd.DataFrame,
    full_table_id: str,
    dedup_key: str
) -> pd.DataFrame:
    """
    Pull existing dedup key values from BigQuery.
    Return only rows from df whose key is not already in the table.
    """
    try:
        query  = f"SELECT DISTINCT `{dedup_key}` FROM `{full_table_id}`"
        result = client.query(query).result()
        existing_keys = {row[dedup_key] for row in result}
        logger.info(f"Found {len(existing_keys)} existing keys in BigQuery")
    except Exception as e:
        # Table may be empty or brand new — treat as no existing keys
        logger.warning(f"Could not fetch existing keys (table may be empty): {e}")
        existing_keys = set()

    before = len(df)
    df_clean = df[~df[dedup_key].isin(existing_keys)].copy()
    dropped  = before - len(df_clean)

    if dropped > 0:
        logger.info(f"Dedup: dropped {dropped} already-existing rows, {len(df_clean)} new rows remain")

    return df_clean