# ── S3 Bucket ─────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "data_lake" {
  bucket = var.bucket_name

  tags = {
    Name        = var.bucket_name
    Environment = "local"
    Project     = "data-pipeline-local-dev"
  }
}

resource "aws_s3_bucket_versioning" "data_lake_versioning" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake_public_access" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── IAM User ──────────────────────────────────────────────────────────────────
resource "aws_iam_user" "airflow_user" {
  name = var.iam_username

  tags = {
    Name    = var.iam_username
    Project = "data-pipeline-local-dev"
  }
}

# ── IAM Policy — least privilege ──────────────────────────────────────────────
resource "aws_iam_policy" "airflow_s3_policy" {
  name        = "airflow-s3-policy"
  description = "Least privilege policy for Airflow to access S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.bucket_name}",
          "arn:aws:s3:::${var.bucket_name}/*"
        ]
      }
    ]
  })
}

# ── Attach Policy to User ─────────────────────────────────────────────────────
resource "aws_iam_user_policy_attachment" "airflow_policy_attach" {
  user       = aws_iam_user.airflow_user.name
  policy_arn = aws_iam_policy.airflow_s3_policy.arn
}

# ── IAM Access Keys ───────────────────────────────────────────────────────────
resource "aws_iam_access_key" "airflow_access_key" {
  user = aws_iam_user.airflow_user.name
}
