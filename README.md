# Local Data Pipeline Development Environment

A fully functional local data pipeline development environment built from scratch, featuring Kubernetes, Apache Airflow, and AWS-compatible storage simulation.

## Overview
This project demonstrates how to set up a complete local data engineering infrastructure including:
- Local Kubernetes cluster using Minikube
- Apache Airflow v3 deployed on Kubernetes via Helm
- E-commerce order data pipeline with validation, transformation, and Parquet output
- LocalStack S3 + IAM managed via Terraform

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Local Kubernetes | Minikube | v1.38.0 |
| Container Runtime | Docker Engine | v29.2.0 |
| Package Manager | Helm | v3.20.1 |
| Airflow | Apache Airflow | v3.1.8 |
| Data Processing | Pandas + PyArrow | Latest |
| IaC | Terraform | v1.14.8 |
| Local AWS | LocalStack | v3.0.0 |

## Project Structure

```
data-pipeline-local-dev/
├── part-a/                    # Local Kubernetes Bootstrap
│   ├── setup.sh               # One-command cluster bootstrap
│   ├── Makefile               # Cluster management commands
│   ├── README.md
│   └── scripts/
│       └── healthcheck.sh     # Automated cluster health check
│
├── part-b/                    # Airflow + Data Pipeline
│   ├── README.md
│   ├── helm/
│   │   └── values.yaml        # Airflow Helm configuration
│   ├── dags/
│   │   └── orders_pipeline.py # E-commerce data pipeline DAG
│   └── data/
│       ├── raw/               # Sample JSON input files
│       └── processed/         # Parquet output files
│
└── part-c/                    # LocalStack S3 + IaC
    ├── README.md
    ├── docker-compose.localstack.yaml
    └── terraform/
        ├── provider.tf
        ├── variables.tf
        ├── main.tf
        └── outputs.tf
```

## Architecture

```
Raw JSON Files
      ↓
Airflow DAG (on Kubernetes)
      ├── Task 1: Validate & Ingest
      ├── Task 2: Transform (flatten, enrich)
      ├── Task 3: Save as Parquet → Local + S3
      └── Task 4: Quality Check
            ↓
      LocalStack S3 (via Terraform)
```

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- macOS or Linux (WSL2 supported)
- Minimum 8GB RAM, 4GB allocated to Minikube

### Install Required Tools (macOS)
```bash
brew install kubectl helm minikube awscli python3
brew tap hashicorp/tap && brew install hashicorp/tap/terraform
brew install --cask docker
```

### Part A — Start Kubernetes Cluster
```bash
cd part-a/
./setup.sh
make healthcheck
```

### Part B — Deploy Airflow + Run Pipeline
```bash
# Start minikube mount
minikube mount ~/data-pipeline-local-dev/part-b:/data &

# Add Airflow Helm repo
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Deploy Airflow
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --values part-b/helm/values.yaml

# Wait for all pods to be running
kubectl get pods -n airflow

# Access Airflow UI
kubectl port-forward svc/airflow-api-server 8080:8080 \
  --namespace airflow

# Open browser: http://localhost:8080
# Username: admin | Password: admin
# Trigger orders_pipeline DAG
```

### Part C — LocalStack + Terraform
```bash
# Start LocalStack
docker compose -f part-c/docker-compose.localstack.yaml up -d

# Apply Terraform
cd part-c/terraform/
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
terraform init
terraform apply

# Set Airflow Variables for S3
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow variables set S3_ENDPOINT_URL "http://$(hostname -I | awk '{print $1}'):4566"
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow variables set S3_BUCKET_NAME "data-lake-processed"
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow variables set AWS_ACCESS_KEY_ID "test"
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow variables set AWS_SECRET_ACCESS_KEY "test"
```

## Key Features
- **One-command setup** — `./setup.sh` bootstraps entire Kubernetes cluster
- **Automated health checks** — verifies cluster readiness before deployment
- **Idempotent pipeline** — re-running produces same results without duplicates
- **Dual output** — Parquet files saved to both local filesystem and S3
- **Least privilege IAM** — minimal permissions following security best practices
- **Infrastructure as Code** — all AWS resources managed via Terraform

## Pipeline Details

### Input
E-commerce order JSON files with nested items array:
```json
{
  "order_id": "ORD-12345",
  "customer_id": "CUST-678",
  "items": [
    {"sku": "SKU-A", "qty": 2, "price": 29.99},
    {"sku": "SKU-B", "qty": 1, "price": 14.50}
  ],
  "total_amount": 74.48,
  "currency": "USD",
  "status": "completed",
  "event_timestamp": "2026-03-15T10:30:00Z"
}
```

### Validation Rules
- Required fields: `order_id`, `customer_id`, `total_amount`, `event_timestamp`
- Reject records where `order_id` is null
- Reject records where `total_amount` is negative
- Log all rejected records with reasons

### Transformation
- Flatten nested `items` array → 1 row per item per order
- Extract `order_date` from `event_timestamp`
- Type casting for all numeric fields

### Output
Parquet files partitioned by date:
```
data/processed/
└── dt=2026-03-15/
    └── orders.parquet    # flattened, validated data
```

### Quality Checks
- Row count > 0
- No null `order_id` in output
- Log summary: total orders, total items, total revenue

## Verify Output

### Local Parquet
```bash
python3 -c "
import pandas as pd
df = pd.read_parquet('part-b/data/processed/dt=2026-03-15/orders.parquet')
print(f'Total rows: {len(df)}')
print(df.to_string())
"
```

### S3 LocalStack
```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
aws --endpoint-url=http://localhost:4566 s3 ls s3://data-lake-processed/ --recursive
```

## Troubleshooting

### Airflow UI CSRF Error
Set static secret key and disable CSRF for local development:
```yaml
env:
  - name: AIRFLOW__WEBSERVER__SECRET_KEY
    value: "my_secret_key_for_local_dev"
  - name: AIRFLOW__CORE__CSRF_ENABLED
    value: "False"
```

### Terraform S3 Timeout
Ensure `s3_use_path_style = true` in `provider.tf` and use AWS provider `~> 4.0`.

### LocalStack Not Accessible from Kubernetes Pod
LocalStack runs in Docker network, separate from Kubernetes network.
Use host IP instead of hostname:
```bash
# Get host IP
hostname -I | awk '{print $1}'

# Update Airflow variable
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow variables set S3_ENDPOINT_URL "http://<HOST_IP>:4566"
```
