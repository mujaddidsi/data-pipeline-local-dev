from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import json
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ── Constants ──────────────────────────────────────────────────────────────────
RAW_DIR       = "/data/raw"
PROCESSED_DIR = "/data/processed"
PARTITION     = "dt=2026-03-15"
REQUIRED_FIELDS = ["order_id", "customer_id", "total_amount", "event_timestamp"]

# ── Default Args ───────────────────────────────────────────────────────────────
default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ── Task 1: Validate & Ingest ──────────────────────────────────────────────────
def validate_ingest(**context):
    raw_path = os.path.join(RAW_DIR, PARTITION)
    logging.info(f"Reading JSON files from {raw_path}")

    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw data directory not found: {raw_path}")

    valid_records   = []
    rejected_records = []

    json_files = [f for f in os.listdir(raw_path) if f.endswith(".json")]
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {raw_path}")

    for filename in json_files:
        filepath = os.path.join(raw_path, filename)
        logging.info(f"Processing file: {filename}")

        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    rejected_records.append({
                        "file": filename,
                        "line": line_num,
                        "reason": f"Invalid JSON: {e}"
                    })
                    continue

                # Check required fields
                missing = [f for f in REQUIRED_FIELDS if f not in record]
                if missing:
                    rejected_records.append({
                        "file": filename,
                        "line": line_num,
                        "record": record,
                        "reason": f"Missing required fields: {missing}"
                    })
                    continue

                # Check order_id not null
                if record.get("order_id") is None:
                    rejected_records.append({
                        "file": filename,
                        "line": line_num,
                        "record": record,
                        "reason": "order_id is null"
                    })
                    continue

                # Check total_amount not negative
                if record.get("total_amount", 0) < 0:
                    rejected_records.append({
                        "file": filename,
                        "line": line_num,
                        "record": record,
                        "reason": f"total_amount is negative: {record['total_amount']}"
                    })
                    continue

                valid_records.append(record)

    # Log rejected records
    logging.info(f"Total valid records   : {len(valid_records)}")
    logging.info(f"Total rejected records: {len(rejected_records)}")
    for r in rejected_records:
        logging.warning(f"REJECTED — {r}")

    if not valid_records:
        raise ValueError("No valid records found after validation!")

    # Pass valid records to next task via XCom
    context["ti"].xcom_push(key="valid_records", value=valid_records)
    logging.info("Validation complete. Valid records pushed to XCom.")

# ── Task 2: Transform ──────────────────────────────────────────────────────────
def transform(**context):
    valid_records = context["ti"].xcom_pull(
        task_ids="validate_ingest",
        key="valid_records"
    )

    if not valid_records:
        raise ValueError("No valid records received from validate_ingest task!")

    logging.info(f"Transforming {len(valid_records)} records...")

    rows = []
    for record in valid_records:
        # Extract order_date from event_timestamp
        event_timestamp = record.get("event_timestamp", "")
        order_date = event_timestamp[:10] if event_timestamp else None

        # Flatten items array — 1 row per item per order
        items = record.get("items", [])
        for item in items:
            rows.append({
                "order_id"        : record["order_id"],
                "customer_id"     : record["customer_id"],
                "currency"        : record.get("currency"),
                "status"          : record.get("status"),
                "total_amount"    : record["total_amount"],
                "event_timestamp" : record["event_timestamp"],
                "order_date"      : order_date,
                "sku"             : item.get("sku"),
                "qty"             : item.get("qty"),
                "price"           : item.get("price"),
            })

    df = pd.DataFrame(rows)

    # Type casting
    df["total_amount"] = df["total_amount"].astype(float)
    df["qty"]          = df["qty"].astype(int)
    df["price"]        = df["price"].astype(float)
    df["order_date"]   = pd.to_datetime(df["order_date"]).dt.date.astype(str)

    logging.info(f"Transformed {len(df)} rows (flattened items)")
    logging.info(f"Columns: {df.columns.tolist()}")

    # Push transformed dataframe to XCom as JSON
    context["ti"].xcom_push(key="transformed_df", value=df.to_json(orient="records"))
    logging.info("Transform complete.")

# ── Task 3: Save as Parquet ────────────────────────────────────────────────────
def save_parquet(**context):
    df_json = context["ti"].xcom_pull(
        task_ids="transform",
        key="transformed_df"
    )

    if not df_json:
        raise ValueError("No transformed data received from transform task!")

    df = pd.read_json(df_json, orient="records")
    logging.info(f"Saving {len(df)} rows to Parquet...")

    # Get order_date for partition
    order_date = df["order_date"].iloc[0]
    output_dir = os.path.join(PROCESSED_DIR, f"dt={order_date}")

    # Overwrite existing partition (idempotent)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "orders.parquet")

    # Save as Parquet
    table = pa.Table.from_pandas(df)
    pq.write_table(table, output_path)

    logging.info(f"Parquet saved to: {output_path}")
    context["ti"].xcom_push(key="output_path", value=output_path)

# ── Task 4: Quality Check ──────────────────────────────────────────────────────
def quality_check(**context):
    from airflow.exceptions import AirflowException

    output_path = context["ti"].xcom_pull(
        task_ids="save_parquet",
        key="output_path"
    )

    if not output_path or not os.path.exists(output_path):
        raise AirflowException(f"Parquet file not found: {output_path}")

    df = pd.read_parquet(output_path)

    # Check row count > 0
    if len(df) == 0:
        raise AirflowException("Quality check failed: output has 0 rows!")

    # Check no null order_id
    null_order_ids = df["order_id"].isnull().sum()
    if null_order_ids > 0:
        raise AirflowException(f"Quality check failed: {null_order_ids} null order_id found!")

    # Log summary
    total_orders  = df["order_id"].nunique()
    total_items   = len(df)
    total_revenue = df["total_amount"].sum()

    logging.info("════════════════════════════════")
    logging.info("  Quality Check PASSED ✅")
    logging.info(f"  Total orders : {total_orders}")
    logging.info(f"  Total items  : {total_items}")
    logging.info(f"  Total revenue: ${total_revenue:.2f}")
    logging.info("════════════════════════════════")

# ── DAG Definition ─────────────────────────────────────────────────────────────
with DAG(
    dag_id="orders_pipeline",
    default_args=default_args,
    description="E-commerce order data pipeline",
    schedule=None,
    start_date=datetime(2026, 3, 15),
    catchup=False,
    tags=["cube", "ecommerce", "data-pipeline"],
) as dag:

    t1 = PythonOperator(
        task_id="validate_ingest",
        python_callable=validate_ingest,
    )

    t2 = PythonOperator(
        task_id="transform",
        python_callable=transform,
    )

    t3 = PythonOperator(
        task_id="save_parquet",
        python_callable=save_parquet,
    )

    t4 = PythonOperator(
        task_id="quality_check",
        python_callable=quality_check,
    )

    t1 >> t2 >> t3 >> t4
