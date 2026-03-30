from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import os
import json
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ── Constants ──────────────────────────────────────────────────────────────────
RAW_DIR         = "/data/raw"
PROCESSED_DIR   = "/data/processed"
PARTITION       = "dt=2026-03-15"
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

    valid_records    = []
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
                        "file": filename, "line": line_num,
                        "reason": f"Invalid JSON: {e}"
                    })
                    continue

                # Check required fields
                missing = [f for f in REQUIRED_FIELDS if f not in record]
                if missing:
                    rejected_records.append({
                        "file": filename, "line": line_num,
                        "record": record,
                        "reason": f"Missing required fields: {missing}"
                    })
                    continue

                # Check order_id not null
                if record.get("order_id") is None:
                    rejected_records.append({
                        "file": filename, "line": line_num,
                        "record": record, "reason": "order_id is null"
                    })
                    continue

                # Check total_amount not negative
                if record.get("total_amount", 0) < 0:
                    rejected_records.append({
                        "file": filename, "line": line_num,
                        "record": record,
                        "reason": f"total_amount is negative: {record['total_amount']}"
                    })
                    continue

                valid_records.append(record)

    logging.info(f"Total valid records   : {len(valid_records)}")
    logging.info(f"Total rejected records: {len(rejected_records)}")
    for r in rejected_records:
        logging.warning(f"REJECTED — {r}")

    if not valid_records:
        raise ValueError("No valid records found after validation!")

    context["ti"].xcom_push(key="valid_records", value=valid_records)
    logging.info("Validation complete.")

# ── Task 2: Transform ──────────────────────────────────────────────────────────
def transform(**context):
    valid_records = context["ti"].xcom_pull(
        task_ids="validate_ingest", key="valid_records"
    )

    if not valid_records:
        raise ValueError("No valid records received!")

    logging.info(f"Transforming {len(valid_records)} records...")

    rows = []
    for record in valid_records:
        event_timestamp = record.get("event_timestamp", "")
        order_date      = event_timestamp[:10] if event_timestamp else None

        for item in record.get("items", []):
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
    df["total_amount"] = df["total_amount"].astype(float)
    df["qty"]          = df["qty"].astype(int)
    df["price"]        = df["price"].astype(float)
    df["order_date"]   = pd.to_datetime(df["order_date"]).dt.date.astype(str)

    logging.info(f"Transformed {len(df)} rows")
    context["ti"].xcom_push(key="transformed_df", value=df.to_json(orient="records"))

# ── Task 3: Save as Parquet (local + S3) ───────────────────────────────────────
def save_parquet(**context):
    df_json = context["ti"].xcom_pull(task_ids="transform", key="transformed_df")

    if not df_json:
        raise ValueError("No transformed data received!")

    df         = pd.read_json(df_json, orient="records")
    order_date = df["order_date"].iloc[0]
    table      = pa.Table.from_pandas(df)

    # ── Save to local filesystem ───────────────────────────────────────────────
    output_dir  = os.path.join(PROCESSED_DIR, f"dt={order_date}")
    os.makedirs(output_dir, exist_ok=True)
    local_path  = os.path.join(output_dir, "orders.parquet")
    pq.write_table(table, local_path)
    logging.info(f"Parquet saved locally: {local_path}")

    # ── Save to S3 (LocalStack) ────────────────────────────────────────────────
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Get S3 config from Airflow Variables
        s3_endpoint    = Variable.get("S3_ENDPOINT_URL",    default_var="http://localstack:4566")
        s3_bucket      = Variable.get("S3_BUCKET_NAME",     default_var="data-lake-processed")
        aws_access_key = Variable.get("AWS_ACCESS_KEY_ID",  default_var="test")
        aws_secret_key = Variable.get("AWS_SECRET_ACCESS_KEY", default_var="test")

        s3_client = boto3.client(
            "s3",
            endpoint_url          = s3_endpoint,
            aws_access_key_id     = aws_access_key,
            aws_secret_access_key = aws_secret_key,
            region_name           = "us-east-1",
        )

        s3_key = f"dt={order_date}/orders.parquet"
        s3_client.upload_file(local_path, s3_bucket, s3_key)
        logging.info(f"Parquet uploaded to S3: s3://{s3_bucket}/{s3_key}")

        context["ti"].xcom_push(key="s3_path", value=f"s3://{s3_bucket}/{s3_key}")

    except Exception as e:
        logging.warning(f"S3 upload skipped (LocalStack may not be running): {e}")

    context["ti"].xcom_push(key="output_path", value=local_path)

# ── Task 4: Quality Check ──────────────────────────────────────────────────────
def quality_check(**context):
    from airflow.exceptions import AirflowException

    output_path = context["ti"].xcom_pull(task_ids="save_parquet", key="output_path")

    if not output_path or not os.path.exists(output_path):
        raise AirflowException(f"Parquet file not found: {output_path}")

    df = pd.read_parquet(output_path)

    if len(df) == 0:
        raise AirflowException("Quality check failed: output has 0 rows!")

    null_order_ids = df["order_id"].isnull().sum()
    if null_order_ids > 0:
        raise AirflowException(f"Quality check failed: {null_order_ids} null order_id found!")

    total_orders  = df["order_id"].nunique()
    total_items   = len(df)
    total_revenue = df["total_amount"].sum()

    logging.info("════════════════════════════════")
    logging.info("  Quality Check PASSED ✅")
    logging.info(f"  Total orders : {total_orders}")
    logging.info(f"  Total items  : {total_items}")
    logging.info(f"  Total revenue: ${total_revenue:.2f}")
    logging.info("════════════════════════════════")

    # Check S3 upload result
    s3_path = context["ti"].xcom_pull(task_ids="save_parquet", key="s3_path")
    if s3_path:
        logging.info(f"  S3 output    : {s3_path}")

# ── DAG Definition ─────────────────────────────────────────────────────────────
with DAG(
    dag_id="orders_pipeline",
    default_args=default_args,
    description="E-commerce order data pipeline with S3 output",
    schedule=None,
    start_date=datetime(2026, 3, 15),
    catchup=False,
    tags=["cube", "ecommerce", "data-pipeline"],
) as dag:

    t1 = PythonOperator(task_id="validate_ingest", python_callable=validate_ingest)
    t2 = PythonOperator(task_id="transform",       python_callable=transform)
    t3 = PythonOperator(task_id="save_parquet",    python_callable=save_parquet)
    t4 = PythonOperator(task_id="quality_check",   python_callable=quality_check)

    t1 >> t2 >> t3 >> t4
