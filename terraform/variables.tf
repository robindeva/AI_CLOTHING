variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "bucket_name" {
  description = "S3 bucket name for storing images"
  type        = string
  default     = "ai-clothing-images-unique-12345"
}

variable "lambda_zip_path" {
  description = "Path to Lambda deployment package"
  type        = string
  default     = "../deployment.zip"
}
