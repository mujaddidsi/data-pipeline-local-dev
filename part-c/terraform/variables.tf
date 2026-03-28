variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "localstack_endpoint" {
  description = "LocalStack endpoint URL"
  type        = string
  default     = "http://localhost:4566"
}

variable "bucket_name" {
  description = "S3 bucket name for processed data"
  type        = string
  default     = "data-lake-processed"
}

variable "iam_username" {
  description = "IAM user name for Airflow access"
  type        = string
  default     = "airflow-s3-user"
}
