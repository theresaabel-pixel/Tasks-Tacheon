# Task 2: Data Pipeline — Chennai Hourly Weather

## What This Pipeline Does

Pulls hourly weather data for Chennai from the Open-Meteo API,
transforms it into a clean analytical table, and loads it into BigQuery.
Designed to run on a schedule, safely and repeatedly, without creating duplicates.

---

## Why Open-Meteo

- No API key required — zero setup friction
- Returns clean structured JSON with reliable field names
- Hourly granularity gives enough data to do something analytically interesting
- Chennai is a good test case — high heat, humidity variance, monsoon patterns
  make the derived fields (heat stress, feels-like delta) genuinely meaningful

---

## Project Structure

| File | Purpose |
|---|---|
| `pipeline.py` | Entry point — orchestrates fetch → transform → load |
| `transform.py` | Flattens API response, handles nulls, adds derived fields |
| `load.py` | Writes to BigQuery with dedup logic |
| `config.py` | Loads and validates config.yaml |
| `config.yaml` | All parameters — location, date range, BQ config, dedup key |
| `query.sql` | Summary queries against the BigQuery table |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Keeps credentials and cache out of git |

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up BigQuery authentication

Go to console.cloud.google.com/bigquery — a default project is created
automatically with your Google account (no billing required for Sandbox).

Download a service account key:
- IAM & Admin → Service Accounts → Create Service Account
- Grant role: BigQuery Data Editor + BigQuery Job User
- Keys → Add Key → JSON → Download

Then set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### 3. Update config.yaml

Replace `YOUR_GCP_PROJECT_ID` with your actual GCP project ID.
It looks like: `my-project-123456`

### 4. Run the pipeline

```bash
python pipeline.py
```
---

## BigQuery Setup

The pipeline creates the dataset and table automatically on first run.

Schema:

| Field | Type | Description |
|---|---|---|
| `timestamp_utc` | STRING | Hour timestamp in UTC — dedup key |
| `timestamp_local` | STRING | Hour timestamp in Asia/Kolkata |
| `temperature_c` | FLOAT64 | Actual air temperature |
| `apparent_temperature_c` | FLOAT64 | Feels-like temperature |
| `humidity_pct` | FLOAT64 | Relative humidity percentage |
| `windspeed_kmh` | FLOAT64 | Wind speed at 10m |
| `precipitation_mm` | FLOAT64 | Precipitation in mm |
| `weathercode` | INT64 | WMO weather condition code |
| `feels_like_delta_c` | FLOAT64 | Apparent minus actual temp — derived |
| `heat_stress_category` | STRING | Comfort category — derived |
| `is_raining` | BOOL | True if precipitation > 0 — derived |
| `location_name` | STRING | City name from config |
| `latitude` | FLOAT64 | Location latitude |
| `longitude` | FLOAT64 | Location longitude |

### Deduplication

BigQuery Sandbox does not support MERGE statements.
Dedup is handled in Python before insert:
- Fetch all existing `timestamp_utc` values from the table
- Filter them out of the incoming batch
- Insert only net-new rows

Safe to run repeatedly. Re-running the pipeline on the same date range
will insert zero duplicate rows.

---

## SQL Summary Queries

See `query.sql` for four queries. Replace `your_project` with your GCP project ID.

### Query 1: Daily summary

Aggregates per day — avg/max/min temp, humidity, total rainfall, rainy hours.

Sample output:

| date | avg_temp_c | max_temp_c | min_temp_c | avg_humidity_pct | total_precipitation_mm | rainy_hours |
|---|---|---|---|---|---|---|
| 2024-01-15 | 28.4 | 33.1 | 24.2 | 71.3 | 4.2 | 3 |
| 2024-01-14 | 27.9 | 32.8 | 23.8 | 74.1 | 0.0 | 0 |

### Query 2: Heat stress distribution

Shows how many hours fall into each heat stress category across the full dataset.

| heat_stress_category | total_hours | avg_temp_c | avg_humidity_pct |
|---|---|---|---|
| very_hot | 89 | 36.2 | 68.4 |
| hot | 54 | 31.1 | 72.1 |
| extreme_heat | 12 | 39.8 | 61.2 |
| moderate | 13 | 25.3 | 78.9 |

### Query 3: Hottest hours of the day

Top 5 hours ranked by average apparent temperature — useful for understanding
daily heat patterns in Chennai.

| hour_of_day | avg_apparent_temp_c | avg_actual_temp_c | avg_humidity_pct |
|---|---|---|---|
| 14:00 | 41.2 | 36.8 | 58.3 |
| 13:00 | 40.8 | 36.2 | 59.1 |
| 15:00 | 40.3 | 36.0 | 60.2 |

### Query 4: Extreme heat alert days

Flags any day where apparent temperature exceeded 42°C — actionable view.

---

## Derived Fields

Three fields added beyond what the API returns:

**`feels_like_delta_c`**
Apparent temperature minus actual temperature.
Positive means it feels hotter than it is (humidity effect).
Negative means it feels cooler (wind chill effect).
Chennai typically runs +3 to +8 in humid months.

**`heat_stress_category`**
Buckets apparent temperature into five comfort levels:
comfortable / moderate / hot / very_hot / extreme_heat.
Based on standard meteorological thresholds.

**`is_raining`**
Boolean flag — true if precipitation_mm > 0 for that hour.
Simple but useful for filtering and aggregation.

---

## Running This in Production

### How would you schedule this pipeline?

Two clean options depending on infrastructure:

- **Cloud Scheduler + Cloud Run**: trigger a containerised version of this
  pipeline on a cron schedule (e.g. daily at 06:00 UTC). Fully managed,
  no servers to maintain, logs go to Cloud Logging automatically.

- **Apache Airflow / Cloud Composer**: if the team already runs Airflow,
  wrap this in a DAG with a PythonOperator. Gives you dependency management,
  retries, and a visual UI for monitoring runs.

For this pipeline specifically, daily at 06:00 UTC makes sense —
captures the full previous day's data before anyone starts work.

### How would you know if it failed?

Three layers:

1. **Logging**: pipeline already logs every step with timestamps and error messages.
   In production, ship these to Cloud Logging or Datadog.

2. **Alerting**: set up a log-based alert that fires if the pipeline logs an ERROR.
   Send to a Slack channel or PagerDuty. The team knows within minutes.

3. **Data freshness check**: a separate monitor queries BigQuery daily and alerts
   if the max `timestamp_utc` is more than 25 hours old. Catches silent failures
   where the pipeline ran but inserted nothing.

### What would you change for 10x data volume?

Current bottleneck at scale is `insert_rows_json` — it is fine for hundreds of
rows but will slow down at tens of thousands.

Changes for scale:

- **Switch to `load_table_from_dataframe`**: BigQuery's bulk load API,
  significantly faster than row-by-row JSON insert for large batches.

- **Dedup via BigQuery MERGE**: at scale, pulling all existing keys into Python
  memory is inefficient. Use a staging table + MERGE statement instead
  (requires a full GCP account, not Sandbox).

- **Partition the table by date**: add a DATE partition on `timestamp_utc`.
  Queries scan less data, dedup checks run faster, costs drop.

- **Parameterise for multiple cities**: the pipeline is already config-driven.
  Running it for 10 cities means 10 config files and 10 scheduled jobs,
  or one job that loops over a list of locations.

---

## What I Would Do Differently With More Time

- Add a `--dry-run` flag that fetches and transforms but does not write to BigQuery
- Write unit tests for `transform.py` — especially the derived field logic
- Add a simple retry mechanism for the API fetch (exponential backoff)
- Parameterise the pipeline to accept a `--config` argument so multiple
  city configs can be run from one codebase without editing files
- Store the service account credentials path in a `.env` file
  rather than relying on the shell environment variable