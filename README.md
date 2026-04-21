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

\`\`\`
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
\`\`\`

## Architecture

\`\`\`
Raw JSON Files
      ↓
Airflow DAG (on Kubernetes)
      ├── Task 1: Validate & Ingest
      ├── Task 2: Transform (flatten, enrich)
      ├── Task 3: Save as Parquet → Local + S3
      └── Task 4: Quality Check
            ↓
      LocalStack S3 (via Terraform)
\`\`\`

## Quick Start

### Part A — Start Kubernetes Cluster
\`\`\`bash
cd part-a/
./setup.sh
make healthcheck
\`\`\`

### Part B — Deploy Airflow + Run Pipeline
\`\`\`bash
# Start minikube mount
minikube mount ~/data-pipeline-local-dev/part-b:/data &

# Deploy Airflow
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --values part-b/helm/values.yaml

# Access Airflow UI
kubectl port-forward svc/airflow-api-server 8080:8080 \
  --namespace airflow

# Open browser: http://localhost:8080 (admin/admin)
# Trigger orders_pipeline DAG
\`\`\`

### Part C — LocalStack + Terraform
\`\`\`bash
# Start LocalStack
docker compose -f part-c/docker-compose.localstack.yaml up -d

# Apply Terraform
cd part-c/terraform/
terraform init
terraform apply
\`\`\`

## Key Features
- **One-command setup** — \`./setup.sh\` bootstraps entire Kubernetes cluster
- **Automated health checks** — verifies cluster readiness before deployment
- **Idempotent pipeline** — re-running produces same results without duplicates
- **Dual output** — Parquet files saved to both local filesystem and S3
- **Least privilege IAM** — minimal permissions following security best practices
- **Infrastructure as Code** — all AWS resources managed via Terraform

## Pipeline Details

### Input
E-commerce order JSON files with nested items array:
\`\`\`json
{
  "order_id": "ORD-12345",
  "customer_id": "CUST-678",
  "items": [
    {"sku": "SKU-A", "qty": 2, "price": 29.99}
  ],
  "total_amount": 74.48,
  "status": "completed",
  "event_timestamp": "2026-03-15T10:30:00Z"
}
\`\`\`

### Validation Rules
- Required fields: \`order_id\`, \`customer_id\`, \`total_amount\`, \`event_timestamp\`
- Reject records where \`order_id\` is null
- Reject records where \`total_amount\` is negative

### Output
Parquet files partitioned by date:
\`\`\`
data/processed/
└── dt=2026-03-15/
    └── orders.parquet
\`\`\`
