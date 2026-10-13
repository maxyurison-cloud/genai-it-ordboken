variable "region" {
  type        = string
  description = "AWS region"
  default     = "eu-north-1"
}

variable "ec2_type" {
  type        = string
  description = "EC2 instance type"
  default     = "t3.micro"
}

variable "ec2_name" {
  type        = string
  description = "Name tag of the EC2 host"
  default     = "genai-it-ordboken"
}

variable "gemini_api_key" {
  type        = string
  description = "Gemini API key. No default: Terraform asks for it at apply. Never commit it."
  sensitive   = true
}
