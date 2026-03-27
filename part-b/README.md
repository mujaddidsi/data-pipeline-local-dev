# Part B — Airflow Deployment + Data Pipeline

## Overview
Apache Airflow v3 deployed on Kubernetes using Helm chart, with a data pipeline DAG that ingests e-commerce JSON data, transforms it, and outputs Parquet files.

## Technology Choices

| Component | Choice | Reason |
|---|---|---|
| Airflow version | v3.1.8 | Latest stable version |
| Executor | LocalExecutor | Simplest for local dev, no Redis needed |
| DAG sync | hostPath volume | Simple for local dev, no git-sync needed |
| Data library | Pandas + PyArrow | Widely used, well-documented |
| Python deps | Pre-installed in pod | Simple approach for local dev |

## Prerequisites
- Part A completed (minikube running, airflow namespace created)
- Helm installed
- `minikube mount` running in background

## Deployment

### 1. Start minikube mount (keep running in background)
```bash
minikube mount /home/mujaddidsi/cube-devops-assessment/part-b:/data &
```

### 2. Add Airflow Helm repo
```bash
helm repo add apache-airflow https://airflow.apache.org
helm repo update
```

### 3. Deploy Airflow
```bash
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --values helm/values.yaml \
  --timeout 10m
```

### 4. Verify all pods are running
```bash
kubectl get pods -n airflow
```

Expected output:
```
NAME                                     READY   STATUS    RESTARTS   AGE
airflow-api-server-xxx                   1/1     Running   0          Xm
airflow-dag-processor-xxx                2/2     Running   0          Xm
airflow-postgresql-0                     1/1     Running   0          Xm
airflow-scheduler-0                      2/2     Running   0          Xm
airflow-statsd-xxx                       1/1     Running   0          Xm
```

### 5. Access Airflow UI
```bash
kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow --address 0.0.0.0
```

Open browser: http://localhost:8080
- Username: `admin`
- Password: `admin`

## DAG Syncing Approach
DAG files are synced using **hostPath volume mount** via `minikube mount`. The local directory `/home/mujaddidsi/cube-devops-assessment/part-b/dags` is mounted into the minikube VM as `/data/dags`, which is then mounted into the Airflow pods at `/opt/airflow/dags`.

## Python Dependencies
Pandas and PyArrow are available in the Airflow pod as they are pre-installed in the default Airflow image.

## Pipeline Flow
```
Raw JSON files (/data/raw/dt=2026-03-15/)
        ↓
Task 1: validate_ingest
        - Read JSON files
        - Check required fields
        - Reject null order_id and negative total_amount
        ↓
Task 2: transform
        - Flatten items array (1 row per item per order)
        - Extract order_date from event_timestamp
        ↓
Task 3: save_parquet
        - Write to /data/processed/dt=YYYY-MM-DD/orders.parquet
        - Overwrite existing partition (idempotent)
        ↓
Task 4: quality_check
        - Verify row count > 0
        - Verify no null order_id
        - Log summary (total orders, items, revenue)
```

## Trigger the DAG

### Via Airflow UI:
1. Open http://localhost:8080
2. Go to **DAGs**
3. Find `orders_pipeline`
4. Click **Trigger** button

### Via CLI:
```bash
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow dags trigger orders_pipeline
```

## Verify Parquet Output

### Check file exists:
```bash
ls -la ~/cube-devops-assessment/part-b/data/processed/dt=2026-03-15/
```

### Read Parquet contents:
```bash
python3 -c "
import pandas as pd
df = pd.read_parquet('data/processed/dt=2026-03-15/orders.parquet')
print(f'Total rows: {len(df)}')
print(df.to_string())
"
```

### Expected output:
- 8 rows (flattened items)
- Bad records excluded (null order_id, negative total_amount)
- Columns: order_id, customer_id, currency, status, total_amount, event_timestamp, order_date, sku, qty, price
