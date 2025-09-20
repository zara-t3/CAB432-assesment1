variable "student_number" {
  description = "QUT student number"
  type        = string
  default     = "n11544309"
}

variable "qut_username" {
  description = "QUT username with domain"
  type        = string
  default     = "n11544309@qut.edu.au"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "resource_suffix" {
  description = "Suffix to avoid naming conflicts with existing resources"
  type        = string
  default     = "tf"
}

variable "cognito_client_secret" {
  description = "Cognito client secret (will be stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret for application"
  type        = string
  sensitive   = true
  default     = "supersecretjwtkey123!"
}

variable "app_url" {
  description = "Application URL"
  type        = string
  default     = "http://localhost:8080"
}