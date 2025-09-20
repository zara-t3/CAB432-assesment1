terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket with suffix to avoid naming conflicts
resource "aws_s3_bucket" "imagelab_bucket" {
  bucket = "${var.student_number}-imagelab-bucket-${var.resource_suffix}"

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

# S3 Bucket CORS Configuration
resource "aws_s3_bucket_cors_configuration" "imagelab_bucket_cors" {
  bucket = aws_s3_bucket.imagelab_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "POST", "PUT"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# DynamoDB Images Table with suffix
resource "aws_dynamodb_table" "imagelab_images" {
  name           = "${var.student_number}-imagelab-images-${var.resource_suffix}"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "qut-username"
  range_key      = "image_id"

  attribute {
    name = "qut-username"
    type = "S"
  }

  attribute {
    name = "image_id"
    type = "S"
  }

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

# DynamoDB Jobs Table with suffix
resource "aws_dynamodb_table" "imagelab_jobs" {
  name           = "${var.student_number}-imagelab-jobs-${var.resource_suffix}"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "qut-username"
  range_key      = "job_id"

  attribute {
    name = "qut-username"
    type = "S"
  }

  attribute {
    name = "job_id"
    type = "S"
  }

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

# Secrets Manager Secret with suffix
resource "aws_secretsmanager_secret" "imagelab_secrets" {
  name                    = "${var.student_number}-imagelab-secrets-${var.resource_suffix}"
  description             = "ImageLab application secrets (Terraform managed)"
  recovery_window_in_days = 7

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

resource "aws_secretsmanager_secret_version" "imagelab_secrets_version" {
  secret_id = aws_secretsmanager_secret.imagelab_secrets.id
  secret_string = jsonencode({
    cognito_client_secret = var.cognito_client_secret
    jwt_secret           = var.jwt_secret
  })
}

# Parameter Store Parameters with suffix in path
resource "aws_ssm_parameter" "app_url" {
  name  = "/${var.student_number}/imagelab-${var.resource_suffix}/app-url"
  type  = "String"
  value = var.app_url

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

resource "aws_ssm_parameter" "s3_bucket_name" {
  name  = "/${var.student_number}/imagelab-${var.resource_suffix}/s3-bucket-name"
  type  = "String"
  value = aws_s3_bucket.imagelab_bucket.bucket

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

resource "aws_ssm_parameter" "dynamodb_images_table" {
  name  = "/${var.student_number}/imagelab-${var.resource_suffix}/dynamodb-images-table"
  type  = "String"
  value = aws_dynamodb_table.imagelab_images.name

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}

resource "aws_ssm_parameter" "dynamodb_jobs_table" {
  name  = "/${var.student_number}/imagelab-${var.resource_suffix}/dynamodb-jobs-table"
  type  = "String"
  value = aws_dynamodb_table.imagelab_jobs.name

  tags = {
    "qut-username" = var.qut_username
    "purpose"      = "assessment-2"
  }
}