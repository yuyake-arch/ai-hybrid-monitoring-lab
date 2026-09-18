# --------------------------------------------------
# Automation Server
# --------------------------------------------------
resource "aws_instance" "automation" {
  ami           = "ami-0fe18bc3cfa53a248"
  instance_type = var.instance_types["automation"]

  subnet_id  = aws_subnet.management_a.id
  private_ip = "10.10.20.10"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.automation.id,
    aws_security_group.splunk_client.id,
    aws_security_group.zabbix_agent.id,
  ]

  source_dest_check = true
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 10
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-auto-core-01"
  }
}

# --------------------------------------------------
# Monitoring Server
# --------------------------------------------------
resource "aws_instance" "monitoring" {
  ami           = "ami-0fe18bc3cfa53a248"
  instance_type = var.instance_types["monitoring"]

  subnet_id  = aws_subnet.private_a.id
  private_ip = "10.10.10.10"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.ansible_managed.id,
    aws_security_group.splunk_client.id,
    aws_security_group.monitoring.id,
  ]

  source_dest_check = true
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-mon-core-01"
  }
}

# --------------------------------------------------
# AI Backend Server
# --------------------------------------------------
resource "aws_instance" "ai_backend" {
  ami           = "ami-06e27ac813380118a"
  instance_type = var.instance_types["ai_backend"]

  subnet_id  = aws_subnet.private_a.id
  private_ip = "10.10.10.20"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.ansible_managed.id,
    aws_security_group.splunk_client.id,
    aws_security_group.ai_backend.id,
    aws_security_group.zabbix_agent.id,
  ]

  source_dest_check = true
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-ai-svr-01"
  }
}

# --------------------------------------------------
# Splunk Server
# --------------------------------------------------
resource "aws_instance" "splunk" {
  ami           = "ami-0e5497a77ef21b5ac"
  instance_type = var.instance_types["splunk"]

  subnet_id  = aws_subnet.private_a.id
  private_ip = "10.10.10.30"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.ansible_managed.id,
    aws_security_group.splunk_server.id,
    aws_security_group.zabbix_agent.id,
  ]

  source_dest_check = true
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-splunk-svr-01"
  }
}

# --------------------------------------------------
# Bastion Server
# --------------------------------------------------
resource "aws_instance" "bastion" {
  ami           = "ami-0fe18bc3cfa53a248"
  instance_type = var.instance_types["bastion"]

  subnet_id  = aws_subnet.public_a.id
  private_ip = "10.10.1.10"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.splunk_client.id,
    aws_security_group.bastion.id,
    aws_security_group.zabbix_agent.id,
     aws_security_group.ansible_managed.id,
  ]

  source_dest_check = true
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-mgmt-bastion-01"
  }
}

# --------------------------------------------------
# Managed Server
# --------------------------------------------------
resource "aws_instance" "managed_server" {
  ami           = "ami-028ba4d4ccb4b7b72"
  instance_type = var.instance_types["managed_server"]

  subnet_id  = aws_subnet.private_a.id
  private_ip = "10.10.10.65"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.managed_server.id,
    aws_security_group.splunk_client.id,
    aws_security_group.zabbix_agent.id,
    aws_security_group.ansible_managed.id,
  ]

  source_dest_check = true
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-managed-svr-01"
  }
}

# --------------------------------------------------
# WireGuard Gateway
# --------------------------------------------------
resource "aws_instance" "wireguard" {
  ami           = "ami-0e5497a77ef21b5ac"
  instance_type = var.instance_types["wireguard"]

  subnet_id  = aws_subnet.public_a.id
  private_ip = "10.10.1.20"
  key_name   = var.key_name

  vpc_security_group_ids = [
    aws_security_group.wireguard.id,
    aws_security_group.splunk_client.id,
    aws_security_group.zabbix_agent.id,
    aws_security_group.ansible_managed.id,
  ]

  source_dest_check = false
  ebs_optimized     = true
  monitoring        = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 8
    iops                  = 3000
    throughput            = 125
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "aws-vpn-gw-01"
  }
}