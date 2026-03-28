# Cube Asia — DevOps Engineer Take-Home Assessment

## Candidate
- **Name:** Mujaddid Shibghotul Islam
- **Email:** mujaddid.s.i@gmail.com
- **Role:** DevOps Engineer

## Overview
This repository contains a full end-to-end local data pipeline development environment, including:
- Local Kubernetes cluster (minikube)
- Apache Airflow v3 deployed on Kubernetes
- E-commerce order data pipeline DAG
- LocalStack S3 + Terraform IaC (Bonus)

## Repository Structure
```
cube-devops-assessment/
├── part-a/                    # Local Kubernetes Bootstrap
│   ├── setup.sh               # One-command cluster bootstrap
│   ├── Makefile               # Cluster management commands
│   ├── README.md              # Part A documentation
│   └── scripts/
│       └── healthcheck.sh     # Cluster health check script
│
├── part-b/                    # Airflow + Data Pipeline
│   ├── README.md              # Part B documentation
│   ├── helm/
│   │   └── values.yaml        # Airflow Helm values
│   ├── dags/
│   │   └── orders_pipeline.py # Airflow DAG
│   └── data/
│       ├── raw/               # Sample JSON input files
│       └── processed/         # Parquet output files
│
└── part-c/                    # LocalStack S3 + IaC (Bonus)
    ├── README.md              # Part C documentation
    ├── docker-compose.localstack.yaml
    └── terraform/
        ├── provider.tf
        ├── variables.tf
        ├── main.tf
        └── outputs.tf
```

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Local Kubernetes | Minikube | v1.38.0 |
| Container Runtime | Docker Engine | v29.2.0 |
| Kubernetes | K8s | v1.35.0 |
| Package Manager | Helm | v3.20.1 |
| Airflow | Apache Airflow | v3.1.8 |
| Data Processing | Pandas + PyArrow | Latest |
| IaC | Terraform | v1.14.8 |
| Local AWS | LocalStack | v3.0.0 |
| OS | Ubuntu 22.04 (WSL2) | - |

## Quick Start

### Part A — Start Kubernetes Cluster
```bash
cd part-a/
./setup.sh
make healthcheck
```

### Part B — Deploy Airflow + Run Pipeline
```bash
# Start minikube mount
minikube mount ~/cube-devops-assessment/part-b:/data &

# Deploy Airflow
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --values part-b/helm/values.yaml

# Access Airflow UI
kubectl port-forward svc/airflow-api-server 8080:8080 \
  --namespace airflow --address 0.0.0.0

# Open browser: http://localhost:8080 (admin/admin)
# Trigger orders_pipeline DAG
```

### Part C — LocalStack + Terraform (Bonus)
```bash
# Start LocalStack
docker compose -f part-c/docker-compose.localstack.yaml up -d

# Apply Terraform
cd part-c/terraform/
terraform init
terraform apply
```

## Assumptions
- All services run locally — no real AWS credentials needed
- LocalStack free tier used for S3 and IAM simulation
- Pandas used for data transformation (Polars is a bonus)
- LocalExecutor used for Airflow (simplest for local dev)
- DAG syncing via hostPath volume mount (minikube mount)
