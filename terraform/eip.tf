# --------------------------------------------------
# Bastion Elastic IP
# --------------------------------------------------
resource "aws_eip" "bastion" {
  domain = "vpc"
}

resource "aws_eip_association" "bastion" {
  allocation_id = aws_eip.bastion.id
  instance_id   = aws_instance.bastion.id
}


# --------------------------------------------------
# WireGuard Elastic IP
# --------------------------------------------------
resource "aws_eip" "wireguard" {
  domain = "vpc"
}

resource "aws_eip_association" "wireguard" {
  allocation_id = aws_eip.wireguard.id
  instance_id   = aws_instance.wireguard.id
}