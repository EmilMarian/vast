# Wireshark Analysis of Attack Signatures

This document provides detailed technical information about the network traffic patterns observed during different attack scenarios in the VAST framework. These patterns were captured and analyzed using Wireshark, providing valuable insights into the network-level signatures of various attacks.

## Experimental Setup for Analysis

To perform comprehensive traffic analysis, we configured a controlled testing environment consisting of:

- A victim server container running Nginx to serve as the attack target
- Multiple temperature sensor containers capable of participating in attacks
- cAdvisor for container resource metrics visualization
- Wireshark for comprehensive packet capture and protocol analysis
- Portainer for container management and monitoring

Wireshark was configured to capture traffic on the Docker bridge network interface with specific display filters to isolate attack traffic. This allowed for detailed inspection of packet headers, TCP handshake sequences, and attack patterns in real-time.

## DDoS Attack Traffic Analysis

The DDoS capabilities implemented in the temperature sensors produced distinctly different network patterns depending on the attack type:

### HTTP Flood Analysis

Wireshark's protocol dissector revealed the following characteristic patterns during HTTP flood attacks:

- Multiple GET requests from the same source IP but with randomized HTTP headers
- Random query parameters appended to URLs (`/?12345678`)
- Forged X-Forwarded-For headers attempting to mask the true origin
- Short-lived TCP connections that were properly established and terminated
- Wireshark's HTTP statistics showed 95% of requests targeting a single resource

Example packet capture:

```
No.     Time           Source                Destination           Protocol Length Info
12042   24.128901      172.18.0.3            172.18.0.7            HTTP     598    GET /?87654321 HTTP/1.1 
12043   24.129120      172.18.0.7            172.18.0.3            TCP      66     80 → 44682 [SYN, ACK] Seq=0 Ack=1 Win=64240 Len=0 MSS=1460 SACK_PERM=1 TSval=3173637 TSecr=467948
12044   24.129190      172.18.0.3            172.18.0.7            TCP      54     44682 → 80 [ACK] Seq=1 Ack=1 Win=64240 Len=0
12045   24.130012      172.18.0.7            172.18.0.3            HTTP     162    HTTP/1.1 200 OK  (text/html)
12046   24.130224      172.18.0.3            172.18.0.7            TCP      54     44682 → 80 [FIN, ACK] Seq=1 Ack=109 Win=64132 Len=0
12047   24.130325      172.18.0.7            172.18.0.3            TCP      54     80 → 44682 [FIN, ACK] Seq=109 Ack=2 Win=64240 Len=0
12048   24.130401      172.18.0.3            172.18.0.7            TCP      54     44682 → 80 [ACK] Seq=2 Ack=110 Win=64240 Len=0
```

### SYN Flood Analysis

Using Wireshark's TCP Stream graphs, we observed these distinctive patterns during SYN flood attacks:

- Large number of SYN packets without corresponding ACK packets
- TCP connections remaining in SYN_RECEIVED state
- Normal TCP window size in the initial SYN packet
- No payload data transmitted after the initial handshake attempt
- Wireshark's Time-Sequence graph showed numerous connection attempts clustering at the same timestamps

Example packet capture:

```
No.     Time           Source                Destination           Protocol Length Info
15721   45.127801      172.18.0.3            172.18.0.7            TCP      74     49153 → 80 [SYN] Seq=0 Win=64240 Len=0 MSS=1460 SACK_PERM=1 TSval=470947 TSecr=0 WS=128
15722   45.128001      172.18.0.3            172.18.0.7            TCP      74     49154 → 80 [SYN] Seq=0 Win=64240 Len=0 MSS=1460 SACK_PERM=1 TSval=470947 TSecr=0 WS=128
15723   45.128120      172.18.0.7            172.18.0.3            TCP      74     80 → 49153 [SYN, ACK] Seq=0 Ack=1 Win=65160 Len=0 MSS=1460 SACK_PERM=1 TSval=3176636 TSecr=470947 WS=128
15724   45.128201      172.18.0.3            172.18.0.7            TCP      74     49155 → 80 [SYN] Seq=0 Win=64240 Len=0 MSS=1460 SACK_PERM=1 TSval=470947 TSecr=0 WS=128
15725   45.128320      172.18.0.7            172.18.0.3            TCP      74     80 → 49154 [SYN, ACK] Seq=0 Ack=1 Win=65160 Len=0 MSS=1460 SACK_PERM=1 TSval=3176636 TSecr=470947 WS=128
15726   45.128501      172.18.0.3            172.18.0.7            TCP      74     49156 → 80 [SYN] Seq=0 Win=64240 Len=0 MSS=1460 SACK_PERM=1 TSval=470947 TSecr=0 WS=128
15727   45.128620      172.18.0.7            172.18.0.3            TCP      74     80 → 49155 [SYN, ACK] Seq=0 Ack=1 Win=65160 Len=0 MSS=1460 SACK_PERM=1 TSval=3176636 TSecr=470947 WS=128
```

## I/O Graph Visualization

Wireshark's I/O Graph functionality provided quantitative evidence of the attack intensity:

![Wireshark I/O Graph](../images/io-graph-ddos-attack-spikes.png)

*This graph shows packet rate over time during attack demonstration. Note the dramatic increase in packets per second during the attack phase (~30-60s for HTTP attack, and ~110-150s for SYN attack) compared to normal operation.*

## TCP Flow Analysis

Wireshark's TCP flow graphs helped visualize the differences between normal and attack traffic patterns:

### HTTP Flood TCP Flow

HTTP flood attacks showed completed handshakes with GET requests, followed by proper connection termination, but at an abnormally high frequency:

```
TCP flow (simplified):
Client                Server
  |------ SYN -------->|
  |<---- SYN,ACK ------|
  |------ ACK -------->|
  |------ GET -------->|
  |<----- 200 OK ------|
  |------ FIN,ACK ---->|
  |<---- FIN,ACK ------|
  |------ ACK -------->|
```

### SYN Flood TCP Flow

SYN flood attacks showed only the initial SYN packet without completing the handshake, leaving connections in a half-open state:

```
TCP flow (simplified):
Client                Server
  |------ SYN -------->|
  |<---- SYN,ACK ------|
  |                    |  (No ACK sent, connection left half-open)
  |------ SYN -------->|  (New connection attempt)
  |<---- SYN,ACK ------|
  |                    |  (No ACK sent, connection left half-open)
```

## Protocol Distribution Analysis

Wireshark's Protocol Hierarchy Statistics revealed significant differences in protocol distribution during attacks:

### Normal Operation
- TCP: 45.2%
- HTTP: 28.7%
- MQTT: 21.5%
- Other protocols: 4.6%

### During HTTP Flood
- TCP: 38.6%
- HTTP: 58.9%
- MQTT: 2.1%
- Other protocols: 0.4%

### During SYN Flood
- TCP: 99.3%
- HTTP: 0.2%
- MQTT: 0.4%
- Other protocols: 0.1%

This dramatic shift in protocol distribution represents a clear network-level signature that could be used for attack detection.

## Command Injection Traffic Analysis

The command injection vulnerability also produced distinctive network patterns, particularly when establishing the reverse shell:

```
No.     Time           Source                Destination           Protocol Length Info
25421   87.231901      172.18.0.6            172.18.0.3            TCP      74     52841 → 4444 [SYN] Seq=0 Win=64240 Len=0 MSS=1460 SACK_PERM=1 TSval=475050 TSecr=0 WS=128
25422   87.232001      172.18.0.3            172.18.0.6            TCP      74     4444 → 52841 [SYN, ACK] Seq=0 Ack=1 Win=65160 Len=0 MSS=1460 SACK_PERM=1 TSval=475050 TSecr=475050 WS=128
25423   87.232101      172.18.0.6            172.18.0.3            TCP      66     52841 → 4444 [ACK] Seq=1 Ack=1 Win=64240 Len=0 TSval=475050 TSecr=475050
25424   87.232301      172.18.0.6            172.18.0.3            TCP      102    52841 → 4444 [PSH, ACK] Seq=1 Ack=1 Win=64240 Len=36 TSval=475050 TSecr=475050
25425   87.232401      172.18.0.3            172.18.0.6            TCP      66     4444 → 52841 [ACK] Seq=1 Ack=37 Win=65160 Len=0 TSval=475050 TSecr=475050
```

The key distinguishing characteristics of the reverse shell traffic include:

1. Connection initiated from the sensor (target) to the attacker
2. Persistent TCP connection without normal HTTP request/response patterns
3. Regular, low-volume data exchange with PSH flags set
4. Unusual destination port (4444 in this example)

## Resource Exhaustion Traffic Analysis

The resource exhaustion attack showed less distinctive network-level patterns, as the attack primarily targets local resources. However, we did observe:

1. Initial spike in HTTP traffic during the malicious firmware download
2. Substantially delayed responses to MQTT publish operations
3. Increased TCP retransmissions due to delayed processing

## Detection Recommendations Based on Traffic Analysis

Based on our Wireshark analysis, we recommend the following network-based detection approaches:

1. **HTTP Flood Detection**:
   - Monitor for high rates of similar HTTP requests from the same source
   - Look for randomized query parameters that follow patterns (random numbers)
   - Set thresholds for normal HTTP request rates from IoT devices

2. **SYN Flood Detection**:
   - Track TCP connection completion ratios (SYN to SYN-ACK to ACK)
   - Monitor for abnormal increases in SYN packets without completed handshakes
   - Set alerts for containers generating outbound SYN packets above defined thresholds

3. **Command Injection/Reverse Shell Detection**:
   - Monitor for outbound connections from sensors to unusual ports
   - Look for persistent TCP connections with irregular traffic patterns
   - Identify connections where the sensor initiates the connection to external systems

4. **Resource Exhaustion Detection**:
   - Focus on application-level metrics rather than network patterns
   - Monitor for increased TCP retransmissions or delayed responses
   - Set baselines for normal response times and alert on significant deviations

These detection recommendations can be implemented using network monitoring tools that support Wireshark-like packet analysis or through custom scripts that analyze network traffic patterns.