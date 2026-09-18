# --------------------------------------------------
# Public Access
# --------------------------------------------------

output "bastion_public_ip" {
  description = "Elastic IP address of the management bastion host"
  value       = aws_eip.bastion.public_ip
}

output "wireguard_public_ip" {
  description = "Elastic IP address of the WireGuard VPN gateway"
  value       = aws_eip.wireguard.public_ip
}


# --------------------------------------------------
# Core Private Infrastructure
# --------------------------------------------------

output "monitoring_private_ip" {
  description = "Private IP address of the monitoring server"
  value       = aws_instance.monitoring.private_ip
}

output "ai_backend_private_ip" {
  description = "Private IP address of the AI backend server"
  value       = aws_instance.ai_backend.private_ip
}

output "splunk_private_ip" {
  description = "Private IP address of the Splunk server"
  value       = aws_instance.splunk.private_ip
}

output "automation_private_ip" {
  description = "Private IP address of the automation server"
  value       = aws_instance.automation.private_ip
}

output "managed_server_private_ip" {
  description = "Private IP address of the managed server"
  value       = aws_instance.managed_server.private_ip
}


# --------------------------------------------------
# Network
# --------------------------------------------------

output "vpc_id" {
  description = "VPC ID of the hybrid monitoring lab"
  value       = aws_vpc.main.id
}

output "wireguard_primary_eni_id" {
  description = "Primary ENI used by the WireGuard gateway for hybrid routing"
  value       = aws_instance.wireguard.primary_network_interface_id
}