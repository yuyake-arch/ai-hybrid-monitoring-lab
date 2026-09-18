variable "aws_region" {
  description = "AWS region used for the hybrid monitoring lab"
  type        = string
  default     = "us-east-2"
}

variable "vpc_cidr" {
  description = "CIDR block for the main VPC"
  type        = string
  default     = "10.10.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.10.1.0/24"
}

variable "private_subnet_cidr" {
  description = "CIDR block for the private subnet"
  type        = string
  default     = "10.10.10.0/24"
}

variable "management_subnet_cidr" {
  description = "CIDR block for the management subnet"
  type        = string
  default     = "10.10.20.0/24"
}

variable "key_name" {
  description = "Existing EC2 key pair name referenced by the instances"
  type        = string
  default     = "ai-monitoring-lab-ley"
}


# ------------------------------------------------------
# instance type
# ------------------------------------------------------
variable "instance_types" {
  description = "EC2 instance types by server role"
  type        = map(string)

  default = {
    automation     = "t3.micro"
    monitoring     = "t3.small"
    bastion        = "t3.micro"
    managed_server = "t3.micro"
    wireguard      = "t3.micro"
    ai_backend     = "t3.micro"
    splunk         = "t3.small"
  }
}


# ------------------------------------------------------
# Hiding IP
# ------------------------------------------------------
variable "admin_public_ip" {
  description = "Public IPv4 CIDR allowed to access the Bastion host via SSH"
  type        = string
}

variable "wireguard_peer_public_ip" {
  description = "Public IPv4 CIDR allowed to connect to the WireGuard gateway"
  type        = string
}