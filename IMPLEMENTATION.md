# IMPLEMENTATION.md

## DNS Tunnel with Stop-and-Wait Protocol

## 1. System Architecture

We're using a client/server architecture where all communication goes through DNS packets that we send from a client through a server that will only accept DNS formatted packets. The system consists of three components: a Raspberry Pi acting as a restricted Wi-Fi access point (only allows DNS), a client laptop, and a dorm server running a custom DNS server.

The client sends a GET request as a DNS query through the Pi to our dorm server. The server loads the requested webpage, chunks it so that it'll fit into DNS, and uses Stop-and-Wait protocol (with an alternating bit flag to determine that we are sending the next packet) to reliably send the chunks back to the client, which reassembles them.

### Data Flow:
1. Client sends http GET request as DNS query
2. Server receives request, reads the specified file from its local file system, then and chunks it to send back to the user
3. Server sends chunk 0 with seq=0 (sequence number) as DNS TXT response. 
4. Client checks the checksum on the packet from the server (to make sure no corruption), if correct sends ACK-0 (where 0 is the seq number of the incoming packet) as DNS query back to server
5. Custom server waits until it receives the ACK-0, then sends another chunk with seq=1. We only alternate to the next one AFTER receiving the ack-0
6. Process continues until the server finishes sending all packets. After all the packets are sent we send a DONE packet
7. Client then reassembles file and saves the webpage to the disk

### File Structure:
```
protocol.py - Shared functions to encode / decode DNS messages
tunnel_client.py - All client code (main runner, DNS, Stop-and-Wait technique to receive)
tunnel_server.py - All server code (main runner, DNS, Stop-and-Wait send technique)
```

## 2. Module Specifications

### `protocol.py` - Shared Protocol Utilities

These constants define the protocol parameters and don't change during execution. 

**Key Functions:**


```python
# NOTE: ChatGPT helped format these functions into nicely typed and nicely docstringed python code with examples 
# It also suggested we use '-' as character delimiters between a given chunk of our message and the 'tunnel.local' suffix to distinguish
# between tunnelling queries for our DNS severe. It also generated example arguments for the parameters we pass in and the outputs we 
# specified that we wanted to receive
def encode_get(filename: str, session_id: str) -> str:
    """
    Encodes file request as DNS query string. Inverse of decode_request with expected = GET
    Args:
        filename: ex, "index.html"
        session_id: 6 character alphanumeric string

    Returns:
        Formatted DNS query: ex. "GET-index-html.abc123.tunnel.local"
    """

def encode_ack(seq: int, session_id: str) -> str:
    """
    Encode ACK as DNS query string. Inverse of decode_request with expected = ACK

    Args:
        seq: 0 or 1 (alternating bit for Stop-and-Wait)
        session_id: 6-char alphanumeric string
    Returns:
        ACK DNS query: ex. "ACK-0.abc123.tunnel.local"
    """

def decode_request(query: str, expected: str) -> tuple[str|int, str]:
    """
    Parses DNS request query (GET or ACK). Inverse of encode_ack or encode_get

    Args:
        query: DNS query string (from above functions)
        expected: "GET" or "ACK"

    Returns:
        if expected="GET" => (filename, session_id)
        if expected="ACK" => (seq_num, session_id)
    """

def encode_chunk(data: bytes, seq: int|str, checksum: str) -> str:
    """
    Encodes data chunk as TXT record string.

    Args:
        data: bytes
        seq: 0, 1, or "DONE" (alternating bit for Stop-and-Wait protocol as we defined)
        checksum: 8 charactres long

    Returns:
        TXT record: "[seq]|[data]|[checksum]"
    """

def decode_chunk(txt_record: str) -> tuple[int|str, bytes, str]:
    """
    Parse a DNS TXT record response.

    Args:
        txt_record: e.g., "[seq]|[data]|[checksum]"

    Returns:
        (seq_or_done, data_bytes, checksum_hex)
    """

def calculate_checksum(data: bytes) -> str:
    """
    Calculates CRC32 checksum and returns as 8-char hex string.

    Args:
        data: bytes to checksum

    Returns:
      the hex of the checksum
    """
```

### `tunnel_client.py` - Client Implementation

**Usage:**
```bash
python tunnel_client.py <filename> --server <DNS_SERVER_IP>
```

**Main Function:**
```python
def main():
    """
    Flow:
        1. Parse command line args (filename, server IP)
        2. Generate session ID
        3. Send GET request
        4. Receive file using Stop-and-Wait (receive_file function)
        5. Write file to disk
        6. Print stats (bytes received, time taken, retransmissions)
    """
```

**DNS Communication:**
```python
def send_dns_query(query_string: str, server_ip: str, timeout: float = 5.0) -> str:
    """
    Sends DNS TXT query and waits for response.
    Args:
        query_string: e.g., "GET-index-html.abc123.tunnel.local"
        server_ip: IP address of DNS server
        timeout: seconds to wait
    Returns:
        TXT record response string

    """
```

**Stop-and-Wait Receive Logic:**
```python
def receive_file(session_id: str, server_ip: str) -> bytes:
    """
    Receives file chunks using Stop-and-Wait protocol.

   Args:
      session_id: session id of files we're transmitting
      server_ip: of the server we are looking for 

    Returns:
        Complete file as bytes

    """
```

**Helper for Initial GET:**
```python
def send_initial_request(filename: str, session_id: str, server_ip: str) -> str:
    """
    Sends GET request and waits for first chunk to be sent back

    Returns:
        First TXT record response
    """
```

**Implementation notes:**
- After sending GET, the first chunk comes back as the DNS response
- After that, each ACK request gets the next chunk as its response
- We don't need a separate "wait for response" function - `send_dns_query` handles it and keeps track
- Keep track of stats: bytes received, number of retransmissions detected (duplicate seq numbers)


### `tunnel_server.py` - Server Implementation


**Usage:**
```bash
python tunnel_server.py --port 53 --files-dir ./html_files
```

**Global State:**
```python
# Session storage
active_sessions = {}  # {session_id: SendSession}

class SendSession:
    """Tracks the state for a single file transfer."""
    session_id: str
    filename: str
    chunks: list[bytes]        # File split into CHUNK_SIZE pieces
    current_chunk_idx: int     # Which chunk we're sending
    current_seq: int           # 0 or 1
    last_sent_time: float      # For timeout detection
    retransmit_count: int
```

**Main Function:**
```python
def main():
    """
    Flow:
        1. Parse CLI args 
        2. Start DNS server using dnslib
        3. Register query handler
        4. Start timeout checker thread
        5. Run until person stops it with keyboard interrupt
    """
```

**DNS Server Setup:**
```python
def start_dns_server(port: int, files_dir: str):
    """
    Starts DNS server on specified port using dnslib.
    """
```

**Query Router:**
```python
def handle_query(query_string: str, files_dir: str) -> str:
    """
    Routes incoming query to GET or ACK handler.

    Args:
        query_string: e.g., "GET-index-html.abc123.tunnel.local"
        files_dir: where to find HTML files

    Returns:
        TXT record response string
    """
```

**GET Request Handler:**
```python
def handle_get(query: str, files_dir: str) -> str:
    """
    Handles initial GET request.

    Returns:
        TXT record: "0|<base64_data>|<checksum>"
    """
```

**ACK Request Handler:**
```python
def handle_ack(query: str) -> str:
    """
    Handles ACK from client (Stop-and-Wait logic).

    Returns:
        TXT record with next chunk (or current if duplicate ACK)
    """
```

**Implementation notes:**
- Using dnslib instead of writing DNS parsing from scratch
- Sessions stored in memory (lost if server crashes, but that's okay for now)
- The server doesn't proactively retransmit - it waits for client to re-ACK
- Timeout checker is mainly for cleanup and stats

---

## 3. DNS Packet Format Specification

# NOTE: Used ChatGPT to generate these examples according to our functions above
### GET Request (Client -> Server)
```
DNS Query:
  QNAME: GET-<filename>.<session_id>.tunnel.local
  QTYPE: TXT (16)

Example:
  GET-index-html.abc123.tunnel.local
```

### Data Chunk Response (Server -> Client)
```
DNS Response:
  TXT Record: "<seq>|<base64_data>|<checksum>"

Example:
  "0|SGVsbG8gV29ybGQh|9b8e7f3a"

Decoded:
  seq = 0
  data = b"Hello World!"
  checksum = 0x9b8e7f3a (calculated from raw bytes, not base64)
```

### Last Chunk Response (Server -> Client)
```
TXT Record: "DONE|<base64_data>|<checksum>"

Example:
  "DONE|RW5kIG9mIGZpbGU=|a1b2c3d4"
```

### ACK Request (Client -> Server)
```
DNS Query:
  QNAME: ACK-<seq>.<session_id>.tunnel.local
  QTYPE: TXT (16)

Example:
  ACK-0.abc123.tunnel.local
  ACK-1.abc123.tunnel.local

Server response to ACK:
  Next chunk (or retransmit current if duplicate ACK)
```

### Error Response (Server -> Client)
```
TXT Record: "ERROR|<error_message>"

Examples:
  "ERROR|file_not_found"
  "ERROR|invalid_session"
  "ERROR|internal_error"

Client should print error and exit.
```

