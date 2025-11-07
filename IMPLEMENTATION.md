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
6. This process continues until the server finishes sending all the packets. At which point it sends DONE message
1. Client reassembles file and saves to disk

### File Structure:
```
protocol.py - Shared functions to encode / decode DNS messages
tunnel_client.py - All client code (main runnner, DNS, Stop-and-Wait technique to receive)
tunnel_server.py  - All server code (main runner, DNS, Stop-and-Wait send technique)
```

## 2. Module Specifications

### `protocol.py` - Shared Protocol Utilities

**Purpose:** All the encoding/decoding functions and constants that both client and server need.

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

**Purpose:** Complete client - handles CL args, sends DNS queries, receives file chunks using Stop-and-Wait.

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

**Purpose:** Complete server - listens for DNS queries, handles GET/ACK requests, sends file chunks using Stop-and-Wait.

**Usage:**
```bash
python tunnel_server.py --port 53 --files-dir ./html_files
```

**Global State:**
```python
# Session storage
active_sessions = {}  # {session_id: SendSession}

class SendSession:
    """Tracks state for one file transfer."""
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
    Main entry point.

    Flow:
        1. Parse command line args (port, files directory)
        2. Start DNS server using dnslib
        3. Register query handler
        4. Start timeout checker thread
        5. Run until Ctrl-C

    Uses dnslib.DNSServer to handle DNS protocol details.
    """
```

**DNS Server Setup:**
```python
def start_dns_server(port: int, files_dir: str):
    """
    Starts DNS server on specified port using dnslib.

    Implementation approach:
        from dnslib.server import DNSServer, BaseResolver
        from dnslib import RR, QTYPE, TXT

        class TunnelResolver(BaseResolver):
            def resolve(self, request, handler):
                qname = str(request.q.qname)  # e.g., "GET-index-html.abc123.tunnel.local"

                # Handle query
                txt_response = handle_query(qname, files_dir)

                # Build DNS response with TXT record
                reply = request.reply()
                reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT(txt_response)))
                return reply

        server = DNSServer(TunnelResolver(), port=port, address='0.0.0.0')
        server.start()

    This abstracts away DNS packet parsing - dnslib handles it.
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

    Logic:
        if query starts with "GET-":
            return handle_get(query, files_dir)
        elif query starts with "ACK-":
            return handle_ack(query)
        else:
            return "ERROR|invalid_query"
    """
```

**GET Request Handler:**
```python
def handle_get(query: str, files_dir: str) -> str:
    """
    Handles initial GET request.

    Algorithm:
        1. Parse query to get filename and session_id
        2. Check if session already exists:
            - If yes: reset it (client retrying)
        3. Read file from files_dir/filename
        4. Split into chunks of CHUNK_SIZE bytes
        5. Create SendSession:
            session = SendSession(
                session_id=session_id,
                filename=filename,
                chunks=chunks,
                current_chunk_idx=0,
                current_seq=0,
                last_sent_time=time.time(),
                retransmit_count=0
            )
        6. Store in active_sessions[session_id]
        7. Return first chunk with seq=0

    Returns:
        TXT record: "0|<base64_data>|<checksum>"

    Error handling:
        - File not found: return "ERROR|file_not_found"
        - File too large: still transfer it (might take a while)
    """
```

**ACK Request Handler:**
```python
def handle_ack(query: str) -> str:
    """
    Handles ACK from client (Stop-and-Wait logic).

    Algorithm:
        1. Parse ACK to get seq and session_id
        2. Look up session in active_sessions
        3. If session not found:
            return "ERROR|invalid_session" (stale ACK)

        4. If seq == session.current_seq (expected ACK):
            # Good ACK - move to next chunk
            session.retransmit_count = 0
            session.current_chunk_idx += 1
            session.current_seq = 1 - session.current_seq  # Toggle

            if session.current_chunk_idx < len(session.chunks):
                # More chunks to send
                chunk_data = session.chunks[session.current_chunk_idx]
                checksum = calculate_checksum(chunk_data)
                session.last_sent_time = time.time()
                return encode_chunk(chunk_data, session.current_seq, checksum)
            else:
                # All done - send DONE chunk
                last_chunk = session.chunks[-1]
                checksum = calculate_checksum(last_chunk)
                del active_sessions[session_id]  # Cleanup
                return encode_chunk(last_chunk, "DONE", checksum)

        else:
            # Duplicate or wrong ACK - re-send current chunk
            chunk_data = session.chunks[session.current_chunk_idx]
            checksum = calculate_checksum(chunk_data)
            session.last_sent_time = time.time()
            return encode_chunk(chunk_data, session.current_seq, checksum)

    Returns:
        TXT record with next chunk (or current if duplicate ACK)
    """
```

**Timeout Handler:**
```python
def check_timeouts():
    """
    Background thread that checks for timed-out sessions.
    Runs every 0.5 seconds.

    For each active session:
        if (time.time() - session.last_sent_time) > TIMEOUT_SERVER:
            session.retransmit_count += 1

            if session.retransmit_count > MAX_RETRIES:
                print(f"Session {session_id} timed out, giving up")
                del active_sessions[session_id]
            else:
                print(f"Timeout on session {session_id}, would retransmit...")
                # Note: We can't actually retransmit from here because
                # DNS is request-response. We just wait for client to
                # re-send ACK (which it will after its timeout).
                # Just track that timeout occurred for logging.

    This is mainly for cleanup and logging. The actual retransmits happen
    when client re-sends ACK after timeout.
    """
```

**Implementation notes:**
- Using dnslib instead of writing DNS parsing from scratch
- Sessions stored in memory (lost if server crashes, but that's okay for now)
- The server doesn't proactively retransmit - it waits for client to re-ACK
- Timeout checker is mainly for cleanup and stats

---

## 3. DNS Packet Format Specification

### GET Request (Client -> Server)
```
DNS Query:
  QNAME: GET-<filename>.<session_id>.tunnel.local
  QTYPE: TXT (16)

Example:
  GET-index-html.abc123.tunnel.local

Filename encoding:
  - Remove leading slash if present
  - Replace dots with dashes (index.html -> index-html)
  - Replace other special chars with dashes
  - Convert to lowercase

Session ID:
  - 6 random alphanumeric characters
  - Generated by client
  - Used to match requests/responses
```

### Data Chunk Response (Server -> Client)
```
DNS Response:
  TXT Record: "<seq>|<base64_data>|<checksum>"

Fields:
  seq: "0" or "1" (single character)
  base64_data: Base64-encoded chunk (max ~150 bytes before encoding)
  checksum: 8-character hex string (CRC32 of raw data bytes)

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

Same format as data chunk, but seq is replaced with "DONE" literal string.
This signals to client that transfer is complete.

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

---

## 4. Stop-and-Wait States

### Client States

```
States:
  IDLE
  WAITING_FOR_FIRST_CHUNK (sent GET, waiting)
  RECEIVING (receiving chunks with Stop-and-Wait)
  DONE

Transitions:
  IDLE -> WAITING_FOR_FIRST_CHUNK
    Trigger: User runs tunnel_client.py
    Action: Send GET request, start timeout timer

  WAITING_FOR_FIRST_CHUNK -> RECEIVING
    Trigger: Receive first chunk (seq=0)
    Action: Validate checksum, send ACK-0, set expected_seq=1

  WAITING_FOR_FIRST_CHUNK -> IDLE
    Trigger: Timeout (5 seconds)
    Action: Retry GET request, or fail after 3 retries

  RECEIVING -> RECEIVING
    Trigger: Receive chunk with expected seq
    Action: Validate checksum, append data, send ACK, toggle expected_seq

  RECEIVING -> RECEIVING (duplicate)
    Trigger: Receive chunk with wrong seq
    Action: Ignore data, re-send ACK for that seq

  RECEIVING -> DONE
    Trigger: Receive chunk with DONE flag
    Action: Send final ACK, write file to disk

Variables:
  expected_seq: int (0 or 1)
  chunks_received: list[bytes]
```

### Server State Machine

```
States (per session):
  IDLE (no session)
  SENDING_CHUNK_0 (sent chunk with seq=0, waiting for ACK-0)
  SENDING_CHUNK_1 (sent chunk with seq=1, waiting for ACK-1)
  DONE

Transitions:
  IDLE -> SENDING_CHUNK_0
    Trigger: Receive GET request
    Action: Read file, split into chunks, send first chunk (seq=0), start timeout

  SENDING_CHUNK_0 -> SENDING_CHUNK_1
    Trigger: Receive ACK-0
    Action: Send next chunk (seq=1), start timeout

  SENDING_CHUNK_0 -> SENDING_CHUNK_0 (timeout)
    Trigger: No ACK received within TIMEOUT_SERVER seconds
    Action: Wait for client to re-ACK (log timeout)

  SENDING_CHUNK_1 -> SENDING_CHUNK_0
    Trigger: Receive ACK-1
    Action: Send next chunk (seq=0), start timeout

  SENDING_CHUNK_1 -> SENDING_CHUNK_1 (timeout)
    Trigger: No ACK received within TIMEOUT_SERVER seconds
    Action: Wait for client to re-ACK (log timeout)

  SENDING_CHUNK_0/1 -> DONE
    Trigger: Receive ACK for last chunk (after sending DONE)
    Action: Clean up session (delete from active_sessions)

  Any state -> IDLE
    Trigger: Too many timeouts (>5) or 60 seconds of inactivity
    Action: Clean up session, log error

Variables (per session):
  current_seq: int (0 or 1)
  current_chunk_idx: int
  chunks: list[bytes]
  last_sent_time: float
  retransmit_count: int
```

---

## 5. Error Handling and Edge Cases

### Client-side errors:
1. **Timeout waiting for first chunk**: Retry GET request up to 3 times with same session_id
2. **Timeout waiting for chunk**: Re-send last ACK (server might have missed it)
3. **Checksum failure**: Ignore packet, don't send ACK, let server timeout and retransmit
4. **Receive ERROR response**: Print error message and exit
5. **Keyboard interrupt (Ctrl-C)**: Save partial file with .partial extension

### Server-side errors:
1. **File not found**: Return ERROR|file_not_found response
2. **No ACK received (timeout)**: Log timeout, wait for client to retry
3. **Invalid session_id in ACK**: Return ERROR|invalid_session
4. **Malformed DNS query**: Log error, return ERROR|invalid_query
5. **Too many timeouts (>5)**: Clean up session

### Edge cases:
1. **Client receives duplicate chunks**: Ignore data, re-send ACK
2. **Server receives duplicate ACK**: Re-send current chunk (idempotent)
3. **Session cleanup**: Remove from memory after transfer complete or 60 seconds of inactivity
4. **Very small file (< CHUNK_SIZE)**: Send single chunk with DONE flag
5. **Empty file**: Send DONE chunk with empty data

