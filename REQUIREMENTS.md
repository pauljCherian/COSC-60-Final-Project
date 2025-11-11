# REQUIREMENTS.md
## 1. Project overview

We are building a small experimental network that allows a laptop to access a remote website through DNS — even when all normal Internet traffic is blocked. This is known as DNS tunnelling as and is a common data exfiltration method. However, here we are using it as a covert method to access the internet.

Our system will use a one of computers (here after refered to as the AP) as a Wi-Fi access point (acting like a locked public hotspot) and a Linux server in our dorm that runs as the DNS nameserver and tunneling endpoint. When the client connects to the AP's SSID, the only thing it can do is make DNS requests. Those requests are routed to our dorm server, which carries actual web data back and forth through the DNS protocol.

To make this connection reliable, we will implement a Stop-and-Wait protocol with sequence numbers, acknowledgments, timeouts, and retransmissions — ensuring data arrives in order and without loss, one packet at a time. Time permitting we may evolve this into a more sophisticated selective repeat.

The final goal is for the client to type a command like:

$ python tunnel_client.py http://example.com/page.html

and receive the HTML content of that page, even though HTTP and HTTPS are blocked.

## 2. Motivation

Captive networks — such as airport/plane Wi-Fi or campus guest networks —usually block all packets except DNS ones. We want to reproduce this scenario on our own hardware to understand:
	- how such restrictions work,
	- what it takes to pass data through DNS, and
	- how reliability can be achieved over an unreliable protocol using Stop-and-Wait.

This project demonstrates the fundamentals of reliable data transfer, but also applied to a real-world constraint: building a working data channel when only DNS is available. This demonstrates the security considerations of such a system, as well as it's limitations (and why UDP and TCP are MUCH better)


## 3. Main components

Our system has four main parts:

**Laptop Access Point (AP)**: Acts as the restricted WiFi access point. We'll use hostapd and the provided TP-LINK dongle to create the network and iptables to block everything except DNS queries going to our dorm server. This simulates those annoying airport/plane WiFi networks that don't let you do anything until you pay.

**Laptop Client**: Connects to the AP and runs our tunnel_client.py script. This program encodes file requests into DNS queries and receives the file back through DNS TXT responses, reassembling the chunks into the complete file.

**Dorm Server (DNS Server + Tunnel Endpoint - hereafter refered to as server)**: A Linux box running a custom DNS responder. When it receives our special DNS queries, it decodes the request, fetches the requested file, and sends it back through DNS in small chunks using the Stop-and-Wait protocol to ensure reliability. Our biggest innovation here is implementing a custom protocol to transfer large amounts of data through DNS. Since the AP blocks unsolicited DNS replies, our client will have to make a query for every chunk of data it wants snuck in through DNS.

**Target Website**: For our purposes this will be vibrantcloud.org. To test large files, we will set up a simple HTTP server and serve documents like english_words.txt

## 4. Functional requirements
	1.	Network simulation
		*	The Laptop AP acts as an isolated Wi-Fi hotspot with no Internet access.
		*	Only DNS (UDP 53) traffic is forwarded to the dorm server; all other packets are dropped using iptables.
		*	The dorm server acts as both the DNS resolver and tunnel endpoint.
	2.	Reliable data transfer using Stop-and-Wait technique and Custom protocol
		*	We chose Stop-and-Wait because it's the simplest reliable protocol, and with only 2 weeks we need to keep the scope manageable. If we have extra time, we might try adding a sliding window/selective repeat.
		*	The client sends a file request to the server (simple DNS query, doesn't need reliability).
		*	The server fetches the file. Determines how many packets it needs for transport and conveys that to client through a start packet.
			This is required because the DNS protocol forbids unsolicited DNS replies.
		*	After the client recieves the initial number of chunks message from server, it sends a request for the first packet.
			The server sends the file back in chunks using Stop-and-Wait:
			*	Each chunk has an alternating sequence number (0 or 1) and a checksum.
			*	The client sends back ACK-0 or ACK-1 after receiving each chunk.
			*	The server waits for the ACK before sending the next chunk.
			*	If no ACK arrives within a short timeout (probably 2-3 seconds), the server retransmits.
			*	The client ignores duplicate chunks and just re-sends the ACK.
	3.	Data encoding in DNS
		*	We'll encode data in DNS queries and TXT responses using Base64 or similar encoding.
		*	The exact format (how to structure the subdomain labels, where to put sequence numbers, etc.) will be figured out during implementation - we need to stay within DNS size limits (around 500 bytes per message).
		*	Details will be in the implementation spec once we prototype it.
	4.	Session management (simplified)
      	*	Session starts implicitly with the first request (no formal handshake to keep it simple).
      	*	Each session gets a random session ID to keep different requests separate.
      	*	Sessions end after some timeout period of inactivity (exact timeout TBD).
   	5.	Application behavior
      	*	The client requests an HTML page (e.g., /page.html).
      	*	The server fetches that page from a local HTTP server (or file) and sends it back over DNS in chunks.
      	*	The client reconstructs the page and displays/saves it to disk.
	6.	Testing and reliability
      	*	We'll test on a closed network and use packet loss simulation tools to randomly drop packets.
      	*	Transfers should complete correctly even with packet loss, with retransmissions logged.
      	*	We'll test with a small HTML file (2-5 KB) to demonstrate multiple packet transfers and retransmissions.

---

# 5. Success criteria
	*	The client can retrieve a 2-5 KB HTML file over DNS without any corruption.
	*	Packets are ordered correctly using the alternating bit protocol.
	*	Retransmissions if a packet is dropped are sent automatically
	*	Logging clearly shows sequence numbers (0/1), ACKs, timeouts, and retransmissions.
	*	The network environment behaves like a real captive Wi-Fi: users can connect to Laptop AP but cannot access any service except DNS to our dorm server.
	*	Checksum validation detects and rejects corrupted packets (can be tested by manually corrupting data).


## 6. Development Plan (2 weeks)

**Week 1:**
- Get the Laptop AP working as an access point with iptables blocking everything except DNS to our dorm server
- Start building a basic DNS server (probably using Python with a DNS library) that can decode our queries
- Get a simple message to transfer through DNS (no reliability yet, just proof of concept)
- Figure out the exact DNS encoding format that works within size limits

**Week 2:**
- Add the Stop-and-Wait protocol (sequence numbers, ACKs, timeouts, retransmissions)
- Add checksum validation to detect corrupted packets
- Test with packet loss simulation to make sure retransmissions work
- Hook it up to actually fetch an HTML file
- Collect logs showing the protocol in action
- Write up implementation.md and record demo video


## 7. Risks and Open Questions

**Constraints:**
- We're not using university networks or real captive portals — all traffic stays on our own devices to avoid any policy issues.
- DNS message size limits mean we can only send about 500 bytes per round-trip. Stop-and-Wait makes this even slower since we can only have one packet in flight at a time. This is acceptable for demonstration but would be painfully slow for real use.
- Because of these limitations, we'll only demo transferring small files (2-5 KB).

**Open Questions:**
- We need to check if dorm IT allows running a DNS server on port 53. If not, we might need to use a non-standard port or set up differently.
- If iptables on the Laptop AP turns out to be too complicated, we might use a simpler firewall approach.
- Not sure yet whether we'll use CRC32 or a simpler checksum - will decide after testing which works better.
- The exact DNS encoding format and packet structure will be determined during Week 1 prototyping.


## 8. Deliverables
- **Requirements.md** (this document)
- **Implementation.md** with detailed protocol specification, data structures, and function designs
- **Code repository** containing:
  - tunnel_client.py — client implementation
  - tunnel_server.py — DNS server with Stop-and-Wait logic
  - pi_setup.sh — script to configure Laptop AP and firewall
  - test_scripts/ — scripts to introduce packet loss and run tests
  - README.md — setup and usage instructions
- **Demo video** (10 minutes): showing Laptop setup, firewall verification, client connecting, file transfer with packet loss, and logs showing sequence numbers and retransmissions
- **Final report PDF**: updated from our original plan with lessons learned and what we actually built


