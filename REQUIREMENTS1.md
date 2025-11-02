1. Project overview

We are building a small experimental network that allows a laptop to access a remote website through DNS — even when all normal Internet traffic is blocked.

Our system will use a Raspberry Pi as a Wi-Fi access point (acting like a locked public hotspot) and a Linux server in our dorm that runs as the DNS nameserver and tunneling endpoint. When the client connects to the Pi’s SSID, the only thing it can do is make DNS requests. Those requests are routed to our dorm server, which carries actual web data back and forth through the DNS protocol.

To make this connection reliable, we will build our own lightweight transport features (similar to TCP) — such as sequence numbers, acknowledgments, timeouts, and retransmissions — so that data arrives in order and without loss.

The final goal is for the client to type a command like:

$ python tunnel_client.py http://example.com

and receive the HTML content of that page, even though HTTP and HTTPS are blocked.

⸻

2. Motivation

Captive or filtered networks — such as airport Wi-Fi or campus guest networks — often block all outgoing traffic except DNS. We want to reproduce this scenario safely and legally on our own hardware to understand:
	•	how such restrictions work,
	•	what it takes to pass data through DNS, and
	•	how reliability can be achieved when using an unreliable protocol.

The project demonstrates that even when only DNS is available, it’s possible to build a working data transfer system — and shows the security and performance trade-offs such systems create.

⸻

3. Main components

Component	Description
Access Point (Raspberry Pi)	Runs hostapd and dnsmasq to create a Wi-Fi network (e.g., Captive-Pi). It provides DHCP and forwards all DNS traffic to our dorm server, but blocks every other protocol. This simulates a public hotspot that only allows DNS until login.
Client (Laptop)	Connects to the Pi’s Wi-Fi. Runs a small program that sends data inside DNS queries and receives replies through DNS TXT responses. It reassembles these pieces to form complete files or HTML pages.
DNS Server / Tunnel Endpoint (Dorm Server)	A Linux box running a custom DNS responder that decodes data sent in DNS queries, retrieves requested web pages locally, and returns the data in DNS responses. It also tracks sessions, assigns sequence numbers, sends ACKs, and manages retransmissions.
Target Website (on the dorm server or local network)	Hosts a few HTML pages to demonstrate that real HTTP data can be tunneled through DNS.


⸻

4. Functional requirements
	1.	Network simulation
	•	The Pi acts as an isolated Wi-Fi hotspot with no Internet access.
	•	Only DNS (UDP 53) traffic is forwarded to the dorm server; all other packets are dropped.
	•	The dorm server acts as both the DNS resolver and tunnel endpoint.
	2.	Handshake and session setup
	•	The client begins with a simple three-step handshake (SYN → SYN-ACK → ACK) to open a session.
	•	Each session has a random ID and defined limits such as packet size and timeout.
	3.	Reliable data transfer
	•	Every data packet includes a sequence number and checksum.
	•	The server replies with ACKs confirming receipt.
	•	Lost packets are retransmitted after a timeout.
	•	The client and server use a fixed-size sliding window to keep multiple packets in flight.
	4.	Caching avoidance
	•	Queries include a random label (nonce) so that caching resolvers never return stale responses.
	5.	Application behavior
	•	The client requests an HTML page (e.g., /index.html).
	•	The server fetches that page from the dorm web host and sends it back over DNS in small pieces.
	•	The client reconstructs the page and saves it to disk.
	6.	Testing and reliability
	•	We will test on a closed network, using tc netem on the Pi to introduce simulated packet loss and latency.
	•	Transfers must complete correctly under up to 5 % simulated packet loss.

⸻

5. Success criteria
	•	The client can retrieve a simple HTML file (≈ 10 KB) over DNS with full integrity.
	•	Packets are ordered correctly, and retransmissions occur when simulated loss is introduced.
	•	Logging shows sequence numbers, ACKs, and timing data.
	•	The network environment behaves like a real captive Wi-Fi: users can connect but have no normal Internet access.

⸻

6. Plan for development and testing

Week 1–2: Set up Raspberry Pi AP and firewall; confirm only DNS is allowed.
Week 3: Write minimal DNS tunnel server on dorm machine; implement client handshake.
Week 4: Add reliability features (ACKs, timeouts, retransmissions).
Week 5: Integrate simple web fetch: server retrieves a fixed HTML page and returns via tunnel.
Week 6: Test under packet loss and record results; finalize report and demo.

⸻

7. Risks and constraints
	•	We will not use university networks or real captive portals — all traffic stays within our own devices.
	•	DNS message size limits (≈ 255 bytes per name) restrict throughput; this is acceptable for demonstration.
	•	Real Internet DNS servers are not used — the dorm server acts as the authoritative nameserver for a test domain.

⸻

8. Deliverables
	•	Requirements.md (this document)
	•	Implementation.md with protocol details
	•	Code: client, server, and AP setup scripts
	•	Demo video: showing the Pi hotspot, client connecting, and HTML page retrieved through DNS


