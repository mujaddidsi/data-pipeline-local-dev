# Part C — LocalStack S3 + IaC (Bonus)

## Overview
This part replaces the local filesystem output from Part B with an S3-compatible bucket running on LocalStack, managed by Terraform.

## Technology Choices

| Component | Choice | Reason |
|---|---|---|
| Local AWS simulator | LocalStack 3.0.0 | Free tier, supports S3 + IAM |
| IaC tool | Terraform | Required by assessment |
| Deployment | Docker Compose | Simple local setup |
| AWS SDK | boto3 + s3fs | Well-supported, easy S3 integration |

## Prerequisites
- Docker installed and running
- Terraform installed
- Part A and Part B completed
- Python packages: `pip3 install boto3 s3fs`

## Architecture
```
Airflow DAG (orders_pipeline)
        ↓
Task 3: save_parquet
        ↓
boto3/s3fs (with LocalStack endpoint)
        ↓
LocalStack (localhost:4566)
        ↓
Fake S3 bucket (data-lake-processed)
```

## Setup Instructions

### 1. Start LocalStack
```bash
docker compose -f docker-compose.localstack.yaml up -d

# Verify LocalStack is running
curl http://localhost:4566/_localstack/health
```

### 2. Run Terraform
```bash
cd terraform/

# Initialize provider
terraform init

# Preview changes
terraform plan

# Apply changes
terraform apply
```

### 3. Verify Resources Created
```bash
# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List IAM users
aws --endpoint-url=http://localhost:4566 iam list-users
```

### 4. Get Access Keys
```bash
# Get access key ID
terraform output access_key_id

# Get secret access key
terraform output secret_access_key
```

### 5. Configure Airflow Connection
Add AWS connection in Airflow UI:
- Go to Admin → Connections
- Add connection:
  - Connection ID: `aws_localstack`
  - Connection Type: `Amazon Web Services`
  - Extra: `{"endpoint_url": "http://localstack:4566", "aws_access_key_id": "<access_key_id>", "aws_secret_access_key": "<secret_access_key>"}`

### 6. Trigger DAG
```bash
# Trigger via CLI
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow dags trigger orders_pipeline
```

### 7. Verify Parquet in S3
```bash
aws --endpoint-url=http://localhost:4566 s3 ls s3://data-lake-processed/ --recursive
```

## Terraform Resources

| Resource | Name | Purpose |
|---|---|---|
| `aws_s3_bucket` | data-lake-processed | Store Parquet output |
| `aws_s3_bucket_versioning` | - | Enable versioning |
| `aws_s3_bucket_public_access_block` | - | Block public access |
| `aws_iam_user` | airflow-s3-user | Airflow access user |
| `aws_iam_policy` | airflow-s3-policy | Least privilege policy |
| `aws_iam_access_key` | - | Access credentials |

## IAM Policy — Least Privilege
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::data-lake-processed",
    "arn:aws:s3:::data-lake-processed/*"
  ]
}
```

## Troubleshooting

### S3 Bucket Creation Timeout
If `terraform apply` hangs on S3 bucket creation, ensure:
1. `s3_use_path_style = true` is set in provider.tf
2. AWS provider version is `~> 4.0` (v5.x has compatibility issues with LocalStack 3.0.0)
3. LocalStack container is healthy: `curl http://localhost:4566/_localstack/health`

### LocalStack Not Accessible from Kubernetes Pod
LocalStack runs in Docker network, which is separate from Kubernetes network.
Use the WSL host IP instead of hostname:
```bash
# Get WSL IP
hostname -I | awk '{print $1}'

# Update Airflow variable
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow variables set S3_ENDPOINT_URL "http://<WSL_IP>:4566"
```

## AWS Credentials for LocalStack
LocalStack does not require real AWS credentials. Set dummy values:
```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```
