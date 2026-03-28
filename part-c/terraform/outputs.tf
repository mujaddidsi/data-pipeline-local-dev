output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.data_lake.bucket
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.data_lake.arn
}

output "iam_user_name" {
  description = "IAM user name"
  value       = aws_iam_user.airflow_user.name
}

output "access_key_id" {
  description = "IAM access key ID for Airflow"
  value       = aws_iam_access_key.airflow_access_key.id
}

output "secret_access_key" {
  description = "IAM secret access key for Airflow"
  value       = aws_iam_access_key.airflow_access_key.secret
  sensitive   = true
}
