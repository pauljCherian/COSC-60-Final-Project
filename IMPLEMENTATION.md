# IMPLEMENTATION.md

## DNS Tunnel with Stop-and-Wait Protocol

## 1. System Architecture

We're using a client/server architecture where all communication goes through DNS packets. We're making a client to send a GET requests as a DNS query. This will then be read by our custom DNS server which will then load the webpage, and then chunk it and use a stop-and-wait-protocol to send the chunks to the client which will then be read by the client as parts of the webpage.


### Data Flow:
1. Client sends GET request as DNS query
2. Server receives request, reads the specified file, and chunks it
3. Server sends chunk 0 with seq=0 (sequence number) as DNS TXT response
4. Client validates checksum on the packet from the server, if correct sends ACK-0 as DNS query back to server
5. Server waits until it receives the ACK-0, then sends chunk 1 with seq=1
6. This process continues until the server finishes sending all the packets. At which point it sends a DONE message
7. Client reassembles file and saves to disk

### File Structure:
```
protocol.py - Shared functions to encode / decode DNS messages
tunnel_client.py - All client code (main runnner, DNS, Stop-and-Wait technique to receive)
tunnel_server.py  - All server code (main runner, DNS, Stop-and-Wait send technique)
```

## 2. Module Specifications

### `protocol.py` - Shared Protocol Utilities

**MACROS:**
```python
CHUNK_SIZE = 150          # Bytes per chunk
TIMEOUT_SERVER = 2.5      # Server waits this long for ACK 
TIMEOUT_CLIENT = 5.0      # Client waits this long for initial response
TUNNEL_DOMAIN = "tunnel.local"
SESSION_ID_LENGTH = 6
MAX_RETRIES = 5           # Max retransmissions before giving up
```
These macros don't change. They are specified in advance for our protocol 

**Key Functions:**

```python
def encode_request(filename: str, session_id: str) -> str:
    """
    Encodes a file request as DNS query string.
    Args:
        filename: ex, "index.html"
        session_id: 6 number string

    Returns:
        Formatted DNS query: ex. "GET-index-html.abc123.tunnel.local"
    """

def encode_ack(seq: int, session_id: str) -> str:
    """
    Encode ACK as DNS query string.

    Args:
        seq: 0,1,2,3,4,...
        session_id: 6 number string
    Returns:
        ACK DNS query: ex. "ACK-0.abc123.tunnel.local"
    """

def decode_request(query: str, expected: str) -> tuple[str|int, str]:
    """
    Parses DNS request query (GET or ACK).

    Args:
        query: DNS query string (from above functions)
        expected: "GET" or "ACK"

    Returns:
        if expected="GET" => (filename, session_id)
        if expected="ACK" => (seq_num, session_id)

    Raises:
        ValueError if query doesn't match expected format
    """

def encode_chunk(data: bytes, seq: int|str, checksum: str) -> str:
    """
    Encodes data chunk as TXT record string.

    Args:
        data: bytes
        seq: 0, 1,2,3,... or "DONE"
        checksum: 8 chars long

    Returns:
        TXT record: "[seq]|[data]|[checksum]"
    """

def decode_chunk(txt_record: str) -> tuple[int|str, bytes, str]:
    """
    Parses TXT record response.

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
      the hex
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
      session_id: sesssion id of files we're transmitting 
      server_ip: of the sever we are looking for 

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

