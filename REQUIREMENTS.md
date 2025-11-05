1. Project overview

We are building a small experimental network that allows a laptop to access a remote website through DNS — even when all normal Internet traffic is blocked.

Our system will use a Raspberry Pi as a Wi-Fi access point (acting like a locked public hotspot) and a Linux server in our dorm that runs as the DNS nameserver and tunneling endpoint. When the client connects to the Pi's SSID, the only thing it can do is make DNS requests. Those requests are routed to our dorm server, which carries actual web data back and forth through the DNS protocol.

To make this connection reliable, we will implement a Stop-and-Wait protocol  with sequence numbers, acknowledgments, timeouts, and retransmissions — ensuring data arrives in order and without loss, one packet at a time.

The final goal is for the client to type a command like:

$ python tunnel_client.py http://example.com/page.html

and receive the HTML content of that page, even though HTTP and HTTPS are blocked.

⸻

2. Motivation

Captive networks — such as airport/plane Wi-Fi or campus guest networks —usually block all packets except DNS ones. We want to reproduce this scenario on our own hardware to understand:
	- how such restrictions work,
	- what it takes to pass data through DNS, and
	- how reliability can be achieved over an unreliable protocol using Stop-and-Wait.

This project demonstrates the fundamentals of reliable data transfer, but also applied to a real-world constraint: building a working data channel when only DNS is available. This demonstrates the security considerations of such a system, as well as it's limitations (and why UDP and TCP are MUCH better)

⸻

1. Main components

Component Description

* Access Point (Raspberry Pi)	
  * Runs hostapd and dnsmasq to create a Wi-Fi network (Captive-Pi). It provides DHCP and forwards all DNS traffic to our dorm server, but blocks every other protocol. This simulates a public hotspot that only allows DNS until actually login (like plane wifi).
* Client (laptop)
  * Connects to the Ras Pi’s Wi-Fi. Runs a small program that sends data inside DNS queries and receives replies through DNS TXT responses. It reassembles these pieces to form complete files or HTML pages.
* DNS Server / Tunnel Endpoint (Dorm Server) 
  * A Linux box running a custom DNS responder that decodes data sent in DNS queries, retrieves requested web pages locally, and returns the data in DNS responses. It also tracks sessions, assigns sequence numbers, sends ACKs, and manages retransmissions.
* Target Website (on the dorm server or local network). Hosts a few HTML pages to demonstrate that real HTTP data can be tunneled through DNS.


⸻

1. Functional requirements
	1.	Network simulation
		*	The Pi acts as an isolated Wi-Fi hotspot with no Internet access.
		*	Only DNS (UDP 53) traffic is forwarded to the dorm server; all other packets are dropped using iptables.
		*	The dorm server acts as both the DNS resolver and tunnel endpoint.
	2.	Reliable data transfer using Stop-and-Wait technique
		*	Every data packet includes an alternating sequence number (0 or 1) and some simple checksum to detect errors.
		*	The server replies with ACK-0 or ACK-1 to confirm receipt of the corresponding packet.
		*	The sender waits for ACK before sending the next packet (one packet in flight at a time).
		*	If no ACK is received within 2 seconds, the sender retransmits the same packet.
		*	The receiver ignores duplicate packets (same sequence number) and re-sends the ACK.
	3.	Data encoding in DNS
		*	Client encodes data as Base64 in subdomain labels: <b64_data>.<seq>.<session_id>.tunnel.local
		*	Server responds with TXT records containing Base64-encoded response data and ACK flag.
		*	Maximum chunk size: ~200 bytes per DNS query/response to stay within DNS limits.
	4.	Session management (simplified)
      	*	Session starts implicitly with first request (no formal handshake).
      	*	Session ends when client sends FIN packet or after 60 seconds of inactivity.
   	5.	Application behavior
      	*	The client requests an HTML page (e.g., /page.html).
      	*	The server fetches that page from a local HTTP server (or file) and sends it back over DNS in chunks.
      	*	The client reconstructs the page and displays/saves it to disk.
	6.	Testing and reliability
      	*	We will test on a closed network, and drop some percentage of packets to test of reliability.
      	*	Transfers must complete correctly with visible retransmissions logged.
      	*	Test with a small (~2-5 KB) HTML file to demonstrate multiple packet transfers.

⸻

1. Success criteria
	*	The client can retrieve a 2-5 KB HTML file over DNS without any corruption.
	*	Packets are ordered correctly using the alternating bit protocol.
	*	Retransmissions if a packet is dropped are sent automatically
	*	Logging clearly shows sequence numbers (0/1), ACKs, timeouts, and retransmissions.
	*	The network environment behaves like a real captive Wi-Fi: users can connect to Pi but cannot access any service except DNS to our dorm server.
	*	Checksum validation detects and rejects corrupted packets (can be tested by manually corrupting data).

⸻

1. Plan for development and testing (2-week timeline)

Days 1-3 (Pi Network Setup):
	*	Configure Raspberry Pi as AP using hostapd and dnsmasq.
	*	Set up iptables to allow only DNS to dorm server IP, block everything else.
	*	Test: client connects to Pi Wi-Fi but cannot ping/browse internet; DNS queries to dorm server succeed.

Days 4-6 (Basic DNS Tunneling):
	*	Implement DNS server on dorm machine using Python + dnslib library.
	*	Implement basic client that encodes request in DNS query subdomain.
	*	Server decodes query and responds with TXT record containing simple response.
	*	Test: transfer a single text message without reliability features.

Days 7-10 (Stop-and-Wait Protocol):
	*	Add alternating sequence numbers (0/1) to client and server.
	*	Implement ACK/NAK logic in TXT responses.
	*	Add 2-second timeout and retransmit on client side.
	*	Add CRC32 checksum to detect corruption.
	*	Test: transfer small file with manual packet dropping to verify retransmissions.

Days 11-12 (Integration & Testing):
	*	Integrate with simple HTML page retrieval from local HTTP server or file.
	*	Use tc netem to introduce 5-10% packet loss on Pi forwarding interface.
	*	Run tests and collect logs showing retransmissions working correctly.
	*	Verify file integrity with checksums.

Days 13-14 (Documentation & Demo):
	*	Finalize requirements.md and implementation.md documents.
	*	Record 10-minute demo video showing: Pi setup, network restrictions, client connecting, file transfer with packet loss, logs showing retransmissions.
	*	Prepare final presentation.

⸻

7. Risks and constraints
	*	Not using university networks or real captive portals — all traffic on our own devices
	*	DNS message size limits (63 bytes per label, 253 chars total domain name) restrict throughput to ~200 bytes per round-trip. Stop-and-Wait makes this even slower (~1 packet per RTT). This is acceptable for demonstration but not practical for real use.
	*	Stop-and-Wait verification is slow (no pipelining), so means large files would take prohibitively long. We will only demo getting 2-5 KB files.

⸻

1. Deliverables
	*	Requirements.md 
	*	Implementation.md with detailed protocol specification, data structures, and API definitions
	*	Code repository with:
		*	tunnel_client.py — client implementation
		*	tunnel_server.py — DNS server with Stop-and-Wait logic
		*	pi_setup.sh — script to configure Raspberry Pi AP and firewall
		*	test_scripts/ — scripts to introduce packet loss and run tests
		*	README.md — setup and usage instructions
	*	Demo (10 minute vid): showing Pi hotspot, firewall verification, client connecting, file transfer with packet loss, detailed logs showing sequence numbers and retransmissions
	*	Final report PDF: updated requirements and lessons learned


