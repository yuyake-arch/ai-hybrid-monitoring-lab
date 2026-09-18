# Local Virtualization Environment

## Overview

This document describes the local VMware-based Ubuntu environment used as the on-premises side of the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The VM was configured with persistent storage, static networking, DNS, VMware guest integration, and a stable network identity. It later became part of the hybrid environment through WireGuard and participates in centralized monitoring and log forwarding.

## Environment

| Component | Configuration |
|---|---|
| Hypervisor | VMware Workstation |
| Guest OS | Ubuntu 26.04 |
| Virtual Disk | 40 GB |
| Network Interface | `ens33` |
| VMware Network | NAT |
| Local Subnet | `192.168.16.0/24` |
| Static IP | `192.168.16.10/24` |
| Default Gateway | `192.168.16.2` |
| DNS | `8.8.8.8` |
| Network Renderer | NetworkManager |

## Local Network Role

The Ubuntu VM represents the local/on-premises endpoint of the hybrid lab:

```text
Windows Host
    |
VMware Workstation
    |
Ubuntu VM
192.168.16.10
    |
WireGuard
10.200.0.2
    |
AWS WireGuard Gateway
10.200.0.1
    |
AWS VPC
```

This VM provides a practical endpoint for testing monitoring, logging, routing, and hybrid connectivity across the AWS/local boundary.

## Persistent Ubuntu Installation

During initial deployment, Ubuntu appeared operational but package upgrades failed with:

```text
No space left on device
```

`df -h` showed `/cow`, while `lsblk` showed the 40 GB virtual disk without installed partitions.

The VM was running from the Live ISO rather than the virtual disk.

Ubuntu was therefore installed onto `/dev/sda`, and the ISO was removed from the normal boot path. This established persistent storage on the allocated VMware disk.

## Static IPv4 Configuration

A predictable local address was required because monitoring and hybrid-routing components depend on stable network identity.

The final local configuration is:

```text
Interface:       ens33
IP Address:      192.168.16.10/24
Default Gateway: 192.168.16.2
DNS Server:      8.8.8.8
```

IPv4 DHCP was disabled.

## Netplan Configuration

The active persistent configuration is maintained in:

```text
/etc/netplan/10-static-network.yaml
```

```yaml
network:
  version: 2
  renderer: NetworkManager

  ethernets:
    ens33:
      renderer: NetworkManager
      match: {}

      addresses:
        - 192.168.16.10/24

      routes:
        - to: default
          via: 192.168.16.2

      nameservers:
        addresses:
          - 8.8.8.8

      dhcp4: false
      dhcp6: false
```

Configuration can be validated with:

```bash
sudo netplan generate
sudo netplan apply
sudo netplan get
```

Unused Netplan definitions were preserved as backups so the active configuration has a clear single source of truth.

## DNS Troubleshooting

After the static address was first configured, `apt update` reported name-resolution failures.

The IP address and gateway were correct, but no DNS resolver had been specified.

Configuring `8.8.8.8` resolved the issue and reinforced the distinction:

```text
IP connectivity != DNS resolution
```

A useful diagnostic sequence is:

```bash
ping 8.8.8.8
ping google.com
```

If the first succeeds and the second fails, DNS should be investigated separately from routing.

## VMware NAT Subnet Troubleshooting

At one point the VM used:

```text
192.168.10.10/24
Gateway 192.168.10.2
```

while the actual VMware NAT network was:

```text
192.168.16.0/24
Gateway 192.168.16.2
```

The mismatch prevented network connectivity.

Correcting the Ubuntu configuration to `192.168.16.10/24` and gateway `192.168.16.2` restored the expected local routing.

## Netplan and NetworkManager Conflict

A further issue occurred when the Netplan YAML contained the correct address but the active interface still used the previous network.

`nmcli connection show` revealed multiple NetworkManager profiles. The old profile remained attached to `ens33`, while the Netplan-generated profile contained the desired configuration.

Activating the correct profile resolved the discrepancy:

```bash
sudo nmcli connection up netplan-ens33
```

This established the configuration chain:

```text
10-static-network.yaml
        ↓
      Netplan
        ↓
 NetworkManager
        ↓
 netplan-ens33
        ↓
      ens33
```

A correct YAML file alone does not prove that the expected runtime profile is active.

## Network Verification

The final configuration can be checked progressively:

```bash
ip -4 addr show ens33
ip route
ping -c 3 192.168.16.2
ping -c 3 8.8.8.8
ping -c 3 google.com
sudo apt update
```

Expected network values include:

```text
Address: 192.168.16.10/24
Gateway: 192.168.16.2
Network: VMware NAT
```

## VMware Guest Integration

VMware guest tools were installed with:

```bash
sudo apt update
sudo apt install -y open-vm-tools open-vm-tools-desktop
```

This improves clipboard integration, display resizing, mouse behavior, and other host/guest usability features.

## Hybrid Integration

The local VM was later connected to AWS using WireGuard.

Its final hybrid role includes:

- Local VMware endpoint
- WireGuard peer `10.200.0.2`
- Zabbix-monitored Linux system
- Splunk log-forwarding source
- Hybrid connectivity validation target

Detailed WireGuard routing and gateway configuration is documented separately in the hybrid-connectivity implementation phase.

## Lessons Learned

- A virtual disk can exist even when the operating system is still running from a Live ISO.
- Static networking requires address, prefix, gateway, and DNS configuration.
- Routing failures and DNS failures should be diagnosed separately.
- Guest addressing must match the actual VMware virtual network.
- Netplan and NetworkManager operate at different configuration layers.
- Persistent configuration and active runtime state should both be verified.
- A stable local address is important once monitoring and VPN routing depend on the VM.

## Result

The local Ubuntu VM provides a stable VMware-based on-premises endpoint at `192.168.16.10/24`. Its storage and networking were validated before it was integrated into the final WireGuard-based hybrid monitoring and logging environment.
