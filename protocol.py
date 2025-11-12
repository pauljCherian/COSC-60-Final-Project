import base64
import struct

def encode_get(filename: str, session_id: str) -> str:
    """
    Encodes file request as DNS query string. Inverse of decode_request with expected = GET
    Args:
        filename: ex, "index.html"
        session_id: 6 character alphanumeric string

    Returns:
        Formatted DNS query: ex. "GET-index-html.abc123.tunnel.local"
    """

    return "GET-" +  filename.replace('.','-') + '.'+ session_id + '.tunnel.local'

def encode_ack(seq: int, session_id: str) -> str:
    """
    Encode ACK as DNS query string. Inverse of decode_request with expected = ACK

    Args:
        seq: 0 or 1 (alternating bit for Stop-and-Wait)
        session_id: 6-char alphanumeric string
    Returns:
        ACK DNS query: ex. "ACK-0.abc123.tunnel.local"
    """

    return 'ACK-'+ str(seq) + '.' + session_id + '.tunnel.local'

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
    # NOTE: ChatGPT suggested I add this check of the suffix before doing any query processing
    if not query.endswith('.tunnel.local'):
        raise ValueError(f"Invalid query format: missing .tunnel.local suffix")
    query = query[:-len('.tunnel.local')]

    chunks = query.split('.')

    if len(chunks) != 2:
        raise ValueError(f"Invalid query format: expected 2 parts, got {len(chunks)}")

    command, session_id = chunks[0], chunks[1]

    command_chunks = command.split('-')

    if expected == "GET":
        # Parse "GET-index-html" -> "index.html"
        if command_chunks[0] != 'GET':
            raise ValueError(f"Expected GET request, got: {command}")

        # Join all parts after GET and replace '-' with '.'
        # GET-index-html -> ["GET", "index", "html"] -> "index.html"
        filename_parts = command_chunks[1:]  # Skip "GET"
        filename = '.'.join(filename_parts)
        return (filename, session_id)

    elif expected == "ACK":
        # Parse "ACK-0" -> 0
        if command_chunks[0] != 'ACK':
            raise ValueError(f"Expected ACK request, got: {command}")
        seq = int(command_chunks[1])
        return (seq, session_id)

    else:
        raise ValueError(f"Unknown expected type: {expected}")

def encode_chunk(data_binary: bytes, seq: int|str, checksum: str) -> str:
    """
    Encodes data chunk as TXT record string. Inverse of decode_chunk

    Args:
        data: bytes
        seq: 0, 1, or "DONE" (alternating bit for Stop-and-Wait protocol as we defined)
        checksum: 4 characters long (16-bit Internet Checksum)

    Returns:
        TXT record: "[seq]|[data]|[checksum]"
    """
    # DNS TXT records need ASCII so we need to convert the binary data of
    # webpage into ASCII. We convert binary -> base64 -> ASCII
    # and then write our DNS text record
    data_base64 = base64.b64encode(data_binary)
    data_ascii = data_base64.decode('ascii')

    # protocol format seq|base64_data|checksum
    return f"{seq}|{data_ascii}|{checksum}"

def decode_chunk(txt_record: str) -> tuple[int|str, bytes, str]:
    """
    Parse a DNS TXT record response. Inverse of encode_chunk

    Args:
        txt_record: e.g., "[seq]|[data]|[checksum]"

    Returns:
        (seq_or_done, data_bytes, checksum_hex)
    """ 
    # split by pipe
    chunks = txt_record.split('|')
    # NOTE: ChatGPT suggested I do this validation check
    if len(chunks) != 3:
        raise ValueError(f"Invalid TXT record format: expected 3 parts, got {len(chunks)}")

    seq, data_base64, checksum = chunks

    # Parse sequence number (could be int or "DONE")
    if seq == "DONE":
        seq = "DONE"
    else:
        seq = int(seq)

    # Decode base64 data
    data_bytes = base64.b64decode(data_base64)

    return (seq, data_bytes, checksum)

def calculate_checksum(bytes_to_checksum: bytes) -> str:
    """
    Calculates the Internet Checksum (same as TCP/UDP/IP) and returns as hex.

    Args:
        data: bytes to checksum

    Returns:
      the hex of the checksum (4 characters for 16-bit checksum)
    """

    # We use the same padding, and packing with struct technique
    # as we used in lab3 to calculate those checksums
    # Pad to even length if needed (same as TCP/UDP)
    if len(bytes_to_checksum) % 2 != 0:
        bytes_to_checksum += b'\x00'

    total = 0

    # Sum all 16-bit words of our bytes
    for i in range(0, len(bytes_to_checksum), 2):
        # Unpack the 2 bytes = 16 bits
        word = struct.unpack('!H', bytes_to_checksum[i:i+2])[0]
        # add the word to our total
        total += word

    # Clamp to 16 bits
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)

    # Then complement and clamp again
    checksum = (~total) & 0xFFFF

    # Return as 4 character string in hexidecimal 
    return f"{checksum:04x}"

