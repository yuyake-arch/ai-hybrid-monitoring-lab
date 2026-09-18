# ============================================================
# Security Group Ingress Rules
# ============================================================

# ------------------------------------------------------------
# Splunk
# ------------------------------------------------------------

# Splunk Universal Forwarders -> Splunk Server
resource "aws_vpc_security_group_ingress_rule" "splunk_forwarder" {
  security_group_id            = aws_security_group.splunk_server.id
  referenced_security_group_id = aws_security_group.splunk_client.id

  ip_protocol = "tcp"
  from_port   = 9997
  to_port     = 9997

  description = "Universal Forwarder"
}

# AI Backend -> Splunk Management API
resource "aws_vpc_security_group_ingress_rule" "splunk_api_from_ai" {
  security_group_id            = aws_security_group.splunk_server.id
  referenced_security_group_id = aws_security_group.ai_backend.id

  ip_protocol = "tcp"
  from_port   = 8089
  to_port     = 8089
}

# Local Ubuntu Forwarder -> Splunk Server
resource "aws_vpc_security_group_ingress_rule" "splunk_forwarder_local" {
  security_group_id = aws_security_group.splunk_server.id
  cidr_ipv4         = "10.200.0.2/32"

  ip_protocol = "tcp"
  from_port   = 9997
  to_port     = 9997
}

# Bastion -> Splunk Web
resource "aws_vpc_security_group_ingress_rule" "splunk_web_from_bastion" {
  security_group_id            = aws_security_group.splunk_server.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 8000
  to_port     = 8000

  description = "Splunk Web"
}

# Bastion -> Splunk SSH
resource "aws_vpc_security_group_ingress_rule" "splunk_ssh_from_bastion" {
  security_group_id            = aws_security_group.splunk_server.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22

  description = "SSH"
}


# ------------------------------------------------------------
# Monitoring / Zabbix / Grafana
# ------------------------------------------------------------

# Bastion -> Monitoring Server SSH
resource "aws_vpc_security_group_ingress_rule" "monitoring_ssh_from_bastion" {
  security_group_id            = aws_security_group.monitoring.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22

  description = "from baston"
}

# Bastion -> Zabbix Web
resource "aws_vpc_security_group_ingress_rule" "zabbix_web_from_bastion" {
  security_group_id            = aws_security_group.monitoring.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 8080
  to_port     = 8080

  description = "Dashboard through baston"
}

# Bastion -> Grafana
resource "aws_vpc_security_group_ingress_rule" "grafana_from_bastion" {
  security_group_id            = aws_security_group.monitoring.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 3000
  to_port     = 3000
}

# Local Zabbix Agent active-check path
resource "aws_vpc_security_group_ingress_rule" "zabbix_active_local" {
  security_group_id = aws_security_group.monitoring.id
  cidr_ipv4         = "10.200.0.2/32"

  ip_protocol = "tcp"
  from_port   = 10051
  to_port     = 10051

  description = "For local agent active mode"
}

# Monitoring Server -> Passive Zabbix Agents
resource "aws_vpc_security_group_ingress_rule" "zabbix_passive" {
  security_group_id            = aws_security_group.zabbix_agent.id
  referenced_security_group_id = aws_security_group.monitoring.id

  ip_protocol = "tcp"
  from_port   = 10050
  to_port     = 10050

  description = "Zabbix passive agent"
}


# ------------------------------------------------------------
# Ansible / Automation
# ------------------------------------------------------------

# Automation Server -> Ansible-managed hosts
resource "aws_vpc_security_group_ingress_rule" "ansible_management" {
  security_group_id            = aws_security_group.ansible_managed.id
  referenced_security_group_id = aws_security_group.automation.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22

  description = "Ansible management"
}

# Bastion -> Automation Server
resource "aws_vpc_security_group_ingress_rule" "automation_ssh_from_bastion" {
  security_group_id            = aws_security_group.automation.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22
}

# AI Backend -> Automation Remediation API
resource "aws_vpc_security_group_ingress_rule" "remediation_api" {
  security_group_id            = aws_security_group.automation.id
  referenced_security_group_id = aws_security_group.ai_backend.id

  ip_protocol = "tcp"
  from_port   = 8443
  to_port     = 8443

   description = "Remediation API request from backend"
}


# ------------------------------------------------------------
# AI Backend
# ------------------------------------------------------------

# Monitoring/Zabbix Webhook -> AI Backend
resource "aws_vpc_security_group_ingress_rule" "ai_webhook_from_monitoring" {
  security_group_id            = aws_security_group.ai_backend.id
  referenced_security_group_id = aws_security_group.monitoring.id

  ip_protocol = "tcp"
  from_port   = 8000
  to_port     = 8000

  description = "Zabbix Webhook to FastAPI AI Backend"
}

# Bastion -> AI Backend SSH
resource "aws_vpc_security_group_ingress_rule" "ai_ssh_from_bastion" {
  security_group_id            = aws_security_group.ai_backend.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22

  description = "SSH from Bastion"
}


# ------------------------------------------------------------
# WireGuard
# ------------------------------------------------------------

# Bastion -> WireGuard Gateway SSH
resource "aws_vpc_security_group_ingress_rule" "wireguard_ssh_from_bastion" {
  security_group_id            = aws_security_group.wireguard.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22

  description = "SSH administration"
}

# Home/Public IP -> WireGuard
resource "aws_vpc_security_group_ingress_rule" "wireguard_vpn" {
  security_group_id = aws_security_group.wireguard.id
  cidr_ipv4         = var.wireguard_peer_public_ip

  ip_protocol = "udp"
  from_port   = 51820
  to_port     = 51820

  description = "WireGuard"
}


# ------------------------------------------------------------
# Bastion / Managed Server
# ------------------------------------------------------------

# Administrator -> Bastion
resource "aws_vpc_security_group_ingress_rule" "bastion_ssh" {
  security_group_id = aws_security_group.bastion.id
  cidr_ipv4         = var.admin_public_ip

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22
}

# Bastion -> Managed Server
resource "aws_vpc_security_group_ingress_rule" "managed_server_ssh_from_bastion" {
  security_group_id            = aws_security_group.managed_server.id
  referenced_security_group_id = aws_security_group.bastion.id

  ip_protocol = "tcp"
  from_port   = 22
  to_port     = 22
}

# ----------------------------------------------------------
# Egress rule
# ----------------------------------------------------------

# ============================================================
# Security Group Egress Rules
# ============================================================

resource "aws_vpc_security_group_egress_rule" "ai_backend_all" {
  security_group_id = aws_security_group.ai_backend.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "splunk_client_all" {
  security_group_id = aws_security_group.splunk_client.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "automation_all" {
  security_group_id = aws_security_group.automation.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "splunk_server_all" {
  security_group_id = aws_security_group.splunk_server.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "wireguard_all" {
  security_group_id = aws_security_group.wireguard.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "bastion_all" {
  security_group_id = aws_security_group.bastion.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "managed_server_all" {
  security_group_id = aws_security_group.managed_server.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "ansible_managed_all" {
  security_group_id = aws_security_group.ansible_managed.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "zabbix_agent_all" {
  security_group_id = aws_security_group.zabbix_agent.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "monitoring_all" {
  security_group_id = aws_security_group.monitoring.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}