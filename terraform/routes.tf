# Main route table - Internet access
resource "aws_route" "main_default" {
  route_table_id         = aws_route_table.main.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Public subnet - Internet access
resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public_a.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Private subnet - Internet route
# Note: Instances still require a public IPv4/EIP to actually use the IGW.
resource "aws_route" "private_default" {
  route_table_id         = aws_route_table.private_a.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# AWS -> WireGuard tunnel network
resource "aws_route" "wireguard_transit" {
  route_table_id         = aws_route_table.private_a.id
  destination_cidr_block = "10.200.0.0/24"
  #  network_interface_id   = "eni-0fd74d1c95da892a8"
  network_interface_id = aws_instance.wireguard.primary_network_interface_id
}

# AWS -> Local VMware LAN through WireGuard
resource "aws_route" "local_vmware_lan" {
  route_table_id         = aws_route_table.private_a.id
  destination_cidr_block = "192.168.16.0/24"
  # network_interface_id   = "eni-0fd74d1c95da892a8"
  network_interface_id = aws_instance.wireguard.primary_network_interface_id
}