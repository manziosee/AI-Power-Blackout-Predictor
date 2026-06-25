variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (production, staging, dev)"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name used for resource naming"
  type        = string
  default     = "blackout-predictor"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnets" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "blackout_predictor"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "bpadmin"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password (use SSM or Secrets Manager in production)"
  type        = string
  sensitive   = true
}

variable "ecs_cpu" {
  description = "ECS Fargate CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "ECS Fargate memory in MiB"
  type        = number
  default     = 2048
}

variable "backend_image" {
  description = "Docker image URI for the backend service"
  type        = string
  default     = "ghcr.io/manziosee/ai-power-blackout-predictor/backend:latest"
}

variable "desired_count" {
  description = "Desired number of ECS task instances"
  type        = number
  default     = 2
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (leave empty to skip HTTPS)"
  type        = string
  default     = ""
}
