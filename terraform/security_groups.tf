# --------------------------------------------------
# AI Backend Security Group
# --------------------------------------------------
resource "aws_security_group" "ai_backend" {
  name        = "ai-backend-sg"
  description = "launch-wizard-1 created 2026-08-11T05:04:31.902Z"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "ai-backend-sg"
  }
}

# --------------------------------------------------
# Splunk Client Security Group
# --------------------------------------------------
resource "aws_security_group" "splunk_client" {
  name        = "splunk-client-sg"
  description = "sg-splunk-client"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "splunk-client-sg"
  }
}

# --------------------------------------------------
# Automation Security Group
# --------------------------------------------------
resource "aws_security_group" "automation" {
  name        = "mysg-hb-automation"
  description = "Allows access for automation"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "automation-sg"
  }
}

# --------------------------------------------------
# Splunk Server Security Group
# --------------------------------------------------
resource "aws_security_group" "splunk_server" {
  name        = "splunk-server-sg"
  description = "launch-wizard-1 created 2026-08-18T02:49:43.444Z"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "splunk-server-sg"
  }
}

# --------------------------------------------------
# WireGuard Gateway Security Group
# --------------------------------------------------
resource "aws_security_group" "wireguard" {
  name        = "wireguard-gateway-sg"
  description = "Wireguard connection created 2026-09-02T04:26:38.554Z"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "wireguard-sg"
  }
}

# --------------------------------------------------
# Bastion Security Group
# --------------------------------------------------
resource "aws_security_group" "bastion" {
  name        = "mysg-bastion"
  description = "Allow access SSH"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "bastion-sg"
  }
}

# --------------------------------------------------
# Managed Server Security Group
# --------------------------------------------------
resource "aws_security_group" "managed_server" {
  name        = "security-grp-test"
  description = "security-grp-test machine"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "managed-server-sg"
  }
}

# --------------------------------------------------
# Ansible Managed Capability Security Group
# --------------------------------------------------
resource "aws_security_group" "ansible_managed" {
  name        = "ansible-managed-sg"
  description = "ansible-managed-sg"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "ansible-managed-sg"
  }
}

# --------------------------------------------------
# Zabbix Agent Capability Security Group
# --------------------------------------------------
resource "aws_security_group" "zabbix_agent" {
  name        = "zabbix-agent-sg"
  description = "Zabbix passive agent checks"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "zabbix-agent-sg"
  }
}

# --------------------------------------------------
# Monitoring Security Group
# --------------------------------------------------
resource "aws_security_group" "monitoring" {
  name        = "mysg-hb-monitoring"
  description = "Allow internal for private access"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "monitor-sg"
  }
}