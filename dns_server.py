#!/usr/bin/env python3
"""
Simple DNS Server that responds to queries by decoding the base64 label
contained before the .com suffix and returning it in a TXT record.
"""

import socket
import base64
import requests
import math
import protocol
from scapy.all import DNS, DNSQR, DNSRR

# Configuration
DNS_PORT = 53  # Standard DNS port (requires root privileges)
LISTEN_IP = "0.0.0.0"  # Listen on all interfaces
CHUNK_SIZE = 150  # Reduced to fit in DNS TXT record (255 byte limit) after base64 encoding

sessions = {}
id2seq = {}
id2data = {}
def parse_dns_query(data):
    """Parse DNS query using scapy."""
    try:
        dns_packet = DNS(data)
        return dns_packet
    except Exception as e:
        print(f"Error parsing DNS packet: {e}")
        return None

#NOTE: Claude created this SCAPY skeleton
def create_dns_response(query_packet, src_addr):
    """Create a DNS response packet using scapy."""
    try:
        # Extract the query details
        qname = query_packet[DNSQR].qname
        qtype = query_packet[DNSQR].qtype
        qclass = query_packet[DNSQR].qclass

        print(f"Query for: {qname.decode() if isinstance(qname, bytes) else qname}")
        print(f"Query type: {qtype}")

        print(f"Decoded payload: {qname}")

        answer = handle_query(qname, src_addr)

        checksum = generate_checksum(answer) #answer in bytes rn

        # Determine sequence number: use "DONE" for last chunk, otherwise use alternating bit (0 or 1)
        session_id = sessions[src_addr]
        current_seq = id2seq[session_id]
        if current_seq == len(id2data[session_id]) - 1:
            seq_to_send = "DONE"
        else:
            seq_to_send = current_seq % 2

        answer = protocol.encode_chunk(answer, seq_to_send, checksum)

        print(answer)


        # Create the response
        response = DNS(
            id=query_packet.id,
            qr=1,  # This is a response
            aa=1,  # Authoritative answer
            rd=query_packet.rd,
            qd=query_packet.qd,  # Copy the query
            an=DNSRR(
                rrname=qname,
                type='TXT',  # Return decoded payload as TXT record
                ttl=300,
                rdata=answer.encode()
            )
        )

        return bytes(response)
    except Exception as e:
        print(f"Error creating DNS response: {e}")
        return None


def generate_checksum(data) -> str:
    print(data)
    if len(data) % 2 == 1:
        data = data + b'\x00'
    sum = 0x0000
    for i in range(0, len(data), 2):
        sum = sum + ((data[i] << 8) + data[i+1])
        sum = (sum & 0xFFFF) + (sum >> 16)
    sum = (sum & 0xFFFF) + (sum >> 16)
    checksum = f"{(sum ^ 0xFFFF):04x}"
    print(checksum)
    return checksum

    

def handle_get(query: str) -> str:
    """
    Handles initial GET request. Uses requests library to make appropriate request.
    Chunks data and returns list of chunks.

    Returns:
        [DATA]
    """
    print("making request to ", query)

    response = requests.get("http://" + query) #TODO: Only http for now

    print("resp", response)
    if response.status_code == 200:

        print("HTTP GET", response.text)
        content_bytes = response.content

        data = []
        num_chunks = math.ceil(len(content_bytes)/CHUNK_SIZE)
        #NOTE: Claude pointed out bytes is a system name
        for i in range(num_chunks):
            if i != num_chunks - 1:
                data.append(content_bytes[i*CHUNK_SIZE:(i+1)*CHUNK_SIZE])
            else: #last chunk may or may not be evenly CHUNK_SIZE
                data.append(content_bytes[i*CHUNK_SIZE:])

        return data

    else:
        print("BAD REQUEST?") #TODO: gotta handle this

    print("FETCHED PAGE", response)

def handle_query(query_bytes: str, src_dst: str) -> str:
    """
    Routes incoming query to GET or ACK handler.

    Args:
        query_string: e.g., "GET-index-html.abc123.tunnel.local"

    Returns:
        TXT record response string
    """
    query_string = query_bytes.decode()
    print("Checking for starts with", query_string)
    if query_string.startswith("GET"): #NOTE: Current any new GET request will reset the session for a client
       query, session_id, tunnel, local, _ = query_string[4:].split(".")#GET- is 4 char

       sessions[src_dst] = session_id

       id2seq[session_id] = 0


       id2data[session_id] = handle_get(query.replace("-", "."))

       print(id2data)

       return id2data[session_id][0]
    elif query_string.startswith("ACK"):

        seq = int(query_string[4])


        _, session_id, tunnel, local, _  = query_string.split(".") #ACK-0 , seq is 5th car
        print(seq,id2seq[session_id])
        if seq == id2seq[session_id] % 2: #client acked the packet we sent!
            id2seq[session_id] += 1 #increment sequence number & send the next data chunk
        #NOTE: doesnt handle fringe cases where ACK is some weird number not 0 or 1
        print(seq,id2seq[session_id])
        return id2data[session_id][id2seq[session_id]]

    else:
        print("Unknown flag", query_string[:3])

#NOTE: Claude created this basic socket server. This is the UDP version of our Lab 2 Code.
def start_dns_server():
    """Start the DNS server."""
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Allow reuse of address
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind to the DNS port
    try:
        sock.bind((LISTEN_IP, DNS_PORT))
        print(f"DNS Server started on {LISTEN_IP}:{DNS_PORT}")
        print("Responding to queries with decoded base64 payloads (TXT records)")
        print("Waiting for DNS queries...")
    except PermissionError:
        print(f"Error: Permission denied. Please run with sudo to bind to port {DNS_PORT}")
        return
    except Exception as e:
        print(f"Error binding to port: {e}")
        return

    # Main server loop
    while True:
        try:
            # Receive DNS query
            data, addr = sock.recvfrom(512)  # DNS packets are typically 512 bytes max
            print(f"\n{'='*50}")
            print(f"Received query from {addr[0]}:{addr[1]}")

            # Parse the query
            query = parse_dns_query(data)
            if query is None:
                continue
            # Create response
            response = create_dns_response(query, addr[0])
            
            if response is None:
                continue
            # Send response
            sock.sendto(response, addr)
            print("Sent response with TXT payload")

        except KeyboardInterrupt:
            print("\n\nShutting down DNS server...")
            break
        except Exception as e:
            print(f"Error handling request: {e}")
            continue

    sock.close()
    print("DNS Server stopped.")

if __name__ == "__main__":
    start_dns_server()
