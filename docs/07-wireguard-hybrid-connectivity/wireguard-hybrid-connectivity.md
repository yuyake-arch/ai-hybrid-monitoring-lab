# WireGuard Hybrid Connectivity and Private Monitoring Integration


## 1. Overview

WireGuard hybrid connectivity implementation focused on replacing temporary or public-facing connectivity methods with a persistent WireGuard-based hybrid network between the local VMware lab and the AWS private infrastructure.

The main objective was to establish routed, bidirectional connectivity that allows monitoring and logging services to communicate over private IP addresses while keeping administrative web access separated through the Bastion host.

The completed design supports:

- Persistent WireGuard connectivity between the local lab and AWS
- Private Splunk log forwarding without an SSH forwarding tunnel
- Zabbix monitoring over the WireGuard network
- Successful validation of both Zabbix active and passive communication paths
- Passive Zabbix monitoring as the final operating mode
- Bastion-based SSH tunneling for Zabbix and Grafana web administration
- Least-privilege Security Group rules
- Automatic WireGuard recovery after reboot

---

## 2. Architecture

### Hybrid Data Path

```text
Local VMware Environment
192.168.16.0/24
        |
        | Local Ubuntu
        | LAN: 192.168.16.10
        | wg0: 10.200.0.2
        |
        | WireGuard
        |
================ VPN ================
        |
        | wg0: 10.200.0.1
        | aws-vpn-gw-01
        |
        +-----------------------------+
        |                             |
        v                             v
AWS Zabbix Server                AWS Splunk Server
10.10.10.10                     10.10.10.30
Private Subnet                  Private Subnet
```

### Administrative Access

```text
Local Workstation
       |
       | SSH
       v
AWS Bastion Host
       |
       +---- SSH tunnel ----> Zabbix Web :8080
       |
       +---- SSH tunnel ----> Grafana    :3000
```

This separates the monitoring/logging data plane from administrative web access.

---

## 3. WireGuard Gateway Design

A dedicated EC2 instance was deployed as the AWS VPN gateway rather than terminating WireGuard on the Bastion host.

### AWS WireGuard Gateway

```text
Instance:        aws-vpn-gw-01
AWS-side IP:     10.10.1.20
WireGuard IP:    10.200.0.1
Protocol:        UDP
Port:            51820
```

### Local WireGuard Peer

```text
LAN IP:          192.168.16.10
WireGuard IP:    10.200.0.2
Local network:   192.168.16.0/24
```

The dedicated gateway design separates responsibilities:

- Bastion host — administrative SSH access
- WireGuard gateway — hybrid network routing
- Monitoring server — Zabbix and Grafana
- Splunk server — centralized log collection

This provides clearer security boundaries and more closely resembles an enterprise network architecture.

---

## 4. WireGuard Addressing

A dedicated transit network was assigned to the WireGuard tunnel:

```text
10.200.0.0/24
```

Addresses:

```text
AWS WireGuard Gateway     10.200.0.1
Local WireGuard Peer      10.200.0.2
```

The local Ubuntu system therefore has two relevant identities:

```text
ens33 / LAN    192.168.16.10
wg0            10.200.0.2
```

The `192.168.16.0/24` network represents the local site, while `10.200.0.0/24` is used as the VPN transit network.

---

## 5. AWS WireGuard Configuration

Example AWS configuration:

```ini
[Interface]
Address = 10.200.0.1/24
ListenPort = 51820
PrivateKey = <AWS_PRIVATE_KEY>

[Peer]
PublicKey = <LOCAL_PUBLIC_KEY>
AllowedIPs = 10.200.0.2/32, 192.168.16.0/24
```

Private keys are stored only on the corresponding systems and are not committed to the project repository.

---

## 6. Local WireGuard Configuration

Example local configuration:

```ini
[Interface]
Address = 10.200.0.2/24
PrivateKey = <LOCAL_PRIVATE_KEY>

[Peer]
PublicKey = <AWS_PUBLIC_KEY>
Endpoint = <AWS_ELASTIC_IP>:51820
AllowedIPs = 10.200.0.1/32, 10.10.0.0/16
PersistentKeepalive = 25
```

`PersistentKeepalive` helps maintain connectivity when the local system is behind NAT.

---

## 7. Routing and Packet Forwarding

The WireGuard EC2 instance operates as a transit router between the AWS VPC and the local environment.

Linux IP forwarding was enabled:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

The setting was also configured persistently.

AWS Source/Destination Check was disabled on `aws-vpn-gw-01`, allowing the instance to forward traffic that is not addressed directly to its primary network interface.

These are two separate requirements:

- AWS Source/Destination Check controls whether AWS permits the EC2 instance to forward transit packets.
- Linux `net.ipv4.ip_forward` controls whether the Linux kernel performs packet forwarding.

The AWS route table includes routes for the VPN transit and local-site networks through the WireGuard gateway ENI:

```text
10.200.0.0/24   -> aws-vpn-gw-01 ENI
192.168.16.0/24 -> aws-vpn-gw-01 ENI
```

No NAT/masquerading is used for the routed VPN design.

---

## 8. Security Group Design

Security rules were restricted according to traffic purpose rather than broadly exposing services.

### WireGuard Gateway Security Group

```text
UDP 51820 <- Local public Internet IP /32
TCP 10050 <- Zabbix Server Security Group
SSH 22    <- Bastion Security Group
```

TCP 10050 permits the Zabbix Server's passive-check traffic to transit the WireGuard gateway toward the local Zabbix Agent.

### Zabbix Server Security Group

```text
TCP 10051 <- 10.200.0.2/32
```

This rule is retained for the validated Zabbix active-check path.

Both Zabbix paths remain permitted and are documented by purpose:

```text
TCP 10050 = Passive monitoring path
TCP 10051 = Active monitoring path
```

The final monitoring mode for `Ubuntu-VM01` is passive, while the active path remains available for future testing or design changes.

---

## 9. Splunk Migration to WireGuard

Before WireGuard hybrid connectivity implementation, the local Splunk Universal Forwarder relied on an SSH local forwarding path to reach the private Splunk server.

The previous output destination was:

```ini
server = 127.0.0.1:9997
```

After WireGuard connectivity was established, the Universal Forwarder was configured to communicate directly with the Splunk server's private address:

```ini
[tcpout]
defaultGroup = default-autolb-group

[tcpout:default-autolb-group]
server = 10.10.10.30:9997

[tcpout-server://10.10.10.30:9997]
```

The Universal Forwarder was restarted:

```bash
sudo /opt/splunkforwarder/bin/splunk restart
```

Forwarding status was verified with:

```bash
sudo /opt/splunkforwarder/bin/splunk list forward-server
```

The private Splunk server appeared as an active forwarding destination.

---

## 10. Splunk Validation

Log ingestion was verified in Splunk Web using the project indexes.

Example:

```spl
(index=linux_os OR index=linux_security)
| stats count by host, index
```

Additional validation included:

```spl
index=linux_security
```

and:

```spl
index=linux_security ("sshd" OR "ssh")
```

Logs continued to arrive after the SSH forwarding dependency was removed.

This confirmed the new path:

```text
Splunk Universal Forwarder
10.200.0.2
        |
        | WireGuard
        v
Private Splunk Server
10.10.10.30:9997
```

---

## 11. Zabbix Migration to Private Connectivity

The local Zabbix Agent2 had previously used the Monitoring Server's Elastic IP for active checks:

```ini
ServerActive=<OLD_ELASTIC_IP>:10051
```

After private WireGuard connectivity was available, the public endpoint was removed from the Agent2 configuration.

The server was changed to the Zabbix Server private address:

```ini
Server=10.10.10.10
ServerActive=10.10.10.10:10051
Hostname=Ubuntu-VM01
```

This eliminated the monitoring dependency on the former public Elastic IP.

---

## 12. Active and Passive Zabbix Validation

Both Zabbix communication models were tested over WireGuard.

### Active Check

```text
Local Zabbix Agent2
10.200.0.2
      |
      | TCP 10051
      v
AWS Zabbix Server
10.10.10.10
```

For active checks:

```text
Agent -> Server:10051
```

The Zabbix Server Security Group permits TCP 10051 from the local WireGuard peer.

### Passive Check

```text
AWS Zabbix Server
10.10.10.10
      |
      | TCP 10050
      v
WireGuard Gateway
      |
      | WireGuard
      v
Local Zabbix Agent2
10.200.0.2:10050
```

The Agent2 listener was verified:

```bash
sudo ss -lntp | grep 10050
```

The agent was listening on TCP 10050, and the server allowlist was configured as:

```ini
Server=10.10.10.10
```

Connectivity was tested from the AWS monitoring server:

```bash
nc -vz -w 5 10.200.0.2 10050
```

Passive monitoring was successfully established.

---

## 13. Final Zabbix Monitoring Mode

Although both modes were validated, the final configuration uses **passive Zabbix monitoring** for `Ubuntu-VM01`.

Zabbix host configuration:

```text
Host:       Ubuntu-VM01
Template:   Linux by Zabbix agent
Interface:  10.200.0.2
Port:       10050
```

The resulting polling flow is:

```text
Zabbix Server
10.10.10.10
      |
      | TCP 10050
      v
WireGuard VPN
      |
      v
Ubuntu-VM01
10.200.0.2
Zabbix Agent2
```

The active-check network path and TCP 10051 Security Group rule are retained and documented so that active monitoring can be restored or used for future scalability testing without redesigning the VPN connectivity.

---


## 14. Bastion-Based Administrative Access

Administrative web access was standardized through the Bastion host instead of directly exposing the monitoring server.

The Monitoring Server Security Group allows the Bastion Security Group to access:

```text
TCP 8080 -> Zabbix Web
TCP 3000 -> Grafana
```

A local SSH session can forward both services:

```bash
ssh -N \
  -L 8080:10.10.10.10:8080 \
  -L 3000:10.10.10.10:3000 \
  ubuntu@<BASTION_PUBLIC_IP>
```

The services can then be accessed locally through:

```text
Zabbix:  localhost:8080
Grafana: localhost:3000
```

This keeps Zabbix and Grafana private while providing controlled administrative access through a single entry point.

---

## 15. Persistence

WireGuard was configured to start automatically:

```bash
sudo systemctl enable wg-quick@wg0
```

The environment was reboot-tested to confirm that the VPN recovered without manually recreating the tunnel.

Post-reboot validation included:

```bash
sudo wg show
systemctl status wg-quick@wg0 --no-pager
```

The Splunk Universal Forwarder also automatically re-established its connection to the private Splunk server.

This removed the operational dependency on manually recreating SSH forwarding sessions for monitoring data transport.

---

## 16. Troubleshooting and Validation Approach

Connectivity problems were isolated by testing each layer independently rather than changing multiple components simultaneously.

Useful commands included:

```bash
ip route get <destination>
```

```bash
nc -vz -w 5 <destination> <port>
```

```bash
sudo tcpdump -ni wg0 tcp port <port>
```

```bash
sudo tcpdump -ni ens5 tcp port <port>
```

```bash
sudo ss -lntp
```

```bash
sudo wg show
```

This made it possible to distinguish among:

- application configuration
- service listening state
- Security Group filtering
- AWS routing
- Linux forwarding
- WireGuard routing
- tunnel reachability

Packet captures were particularly useful for identifying whether traffic reached the AWS VPN gateway and whether it was forwarded into the WireGuard interface.

---

## 17. Security Improvements

WireGuard hybrid connectivity implementation reduced public exposure and temporary connectivity dependencies.

### Before

```text
Local systems
     |
     +---- Public endpoint / temporary SSH forwarding
     |
     +---- AWS services
```

### After

```text
Monitoring and logging data
Local Site
     |
     +---- WireGuard routed VPN
                  |
                  +---- AWS private services


Administrative access
Local Workstation
     |
     +---- Bastion SSH
              |
              +---- Zabbix Web
              +---- Grafana
```

Key improvements:

- Monitoring traffic uses private AWS addresses.
- Splunk forwarding no longer depends on a local SSH forwarding tunnel.
- Zabbix no longer depends on the Monitoring Server Elastic IP.
- Zabbix passive polling is possible across the hybrid VPN.
- Administrative web interfaces remain private.
- Security Group rules are limited by service and source.
- VPN and Bastion responsibilities are separated.

---

## 18. Final Validation

The following functionality was validated:

- WireGuard handshake between AWS and the local environment
- Bidirectional communication across the WireGuard tunnel
- Automatic WireGuard startup after reboot
- Private Splunk forwarding to `10.10.10.30:9997`
- Continued Splunk log ingestion
- Zabbix active-check connectivity over TCP 10051
- Zabbix passive-check connectivity over TCP 10050
- Passive Zabbix monitoring as the final operating mode
- Zabbix Agent2 availability and data collection
- Bastion-based access to Zabbix Web
- Bastion-based access to Grafana

---

## 19. Key Lessons Learned

### Routed VPN vs. Application Tunneling

SSH forwarding is useful for temporary administrative access, but WireGuard provides a more appropriate foundation for persistent hybrid service communication.

### Source IP Matters

Traffic generated by the local Ubuntu system and routed through `wg0` can use the WireGuard interface address as its source. Security policies therefore need to reflect the actual packet path rather than only the host's LAN address.

### Active and Passive Monitoring Are Directional

Zabbix active and passive checks require different connection directions and ports:

```text
Active  -> TCP 10051 on the Zabbix Server
Passive -> TCP 10050 on the Zabbix Agent
```

Understanding the direction of connection initiation is essential when designing routing and firewall policies.

### Routing and Security Must Both Permit Transit

A valid route alone is not sufficient. The AWS transit gateway instance, Linux forwarding configuration, WireGuard peer configuration, and Security Groups must collectively permit the required traffic.

### Separate Administrative and Service Traffic

WireGuard is used for persistent monitoring/logging communication, while Bastion SSH tunneling is retained for controlled administrative web access.

This creates a clearer separation between data-plane and management-plane connectivity.

---

## 20. WireGuard hybrid connectivity implementation Result

WireGuard hybrid connectivity implementation transformed the hybrid lab from a collection of temporary connectivity mechanisms into a persistent routed hybrid network.

The resulting environment now provides:

```text
Local VMware Site
        |
        | WireGuard
        v
AWS Private Infrastructure
        |
        +---- Zabbix Monitoring
        +---- Splunk Log Collection
        +---- Grafana Visualization
```

The VPN enables private bidirectional communication between the local environment and AWS, while the Bastion host remains the controlled administrative entry point.

This establishes a stronger networking foundation for the next phase of the project, including infrastructure automation and Infrastructure as Code.
