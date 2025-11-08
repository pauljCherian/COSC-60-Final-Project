Implement a covert file transfer system using DNS tunneling with reliable data transfer. DNS is typically used for domain name resolution, not data transfer. The goal is to tunnel arbitrary file transfers through DNS queries and responses, implementing TCP-like reliability features.

Implement:

DNS Protocol Integration: Encode file requests and acknowledgments as DNS queries (TXT record requests), and file chunks as DNS TXT record responses

Stop-and-Wait Protocol: Implement sequence numbers, ACKs, and retransmissions to ensure reliable ordered delivery over DNS

Packet Chunking and Reassembly: Split files into DNS-compatible chunks (~150 bytes) and reassemble on client side

Error Detection: Add checksums to detect corrupted data in transit

Custom DNS Server: Deploy a DNS server on campus-accessible hardware (e.g., Raspberry Pi in dorm room) that serves as the tunnel endpoint

Captive Network Simulation: Configure a rogue access point using hostapd and a network adapter to simulate captive portal behavior (network connectivity but DNS-only communication, mimicking unauthenticated airport WiFi)

Timeout and Retransmission Logic: Implement both client-side and server-side timeout detection with configurable retry limits


--- Session Management: Handle multiple concurrent file transfer sessions with unique session IDs
