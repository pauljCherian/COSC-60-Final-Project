import argparse
import random
import string
import time
import os
import protocol
from scapy.all import IP, DNSQR, UDP, DNS, sr1


# MACROS for testing. I wanted to directly simulate what happens if you drop or corrupt 
# a packet. This is an integration test with the entire network. If TEST_MODE is true
# Then we may alter the packet sent from the client
# TEST_DROP_RATE is the rate of dropped packets
# TEST_CORRUPT_RATE is the rate of corrupted packets
# NOTE: ChatGPT told me how to pull .env varaibles
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
TEST_DROP_RATE = float(os.getenv('TEST_DROP_RATE', '0.0'))
TEST_CORRUPT_RATE = float(os.getenv('TEST_CORRUPT_RATE', '0.0'))

# Statistics for test mode
test_stats = {
    'packets_received': 0,
    'packets_dropped': 0,
    'packets_corrupted': 0
}

# this is our helper function to corrupt a packet before the client then processes it
# This is simulating either packet dropping or packet corruption. We insert it on inbound 
# traffic to the client from the server
def simulate_network_conditions(packet: bytes) -> bytes:
    # Simulates outbound packet, returns None if dropped, or corrupts it
    # and returns the corrupted packet
    # make sure we're testing mode
    if not TEST_MODE:
        return packet
    # Increment statistics
    test_stats['packets_received'] += 1
    # Simulate packet drop
    if random.random() < TEST_DROP_RATE:
        test_stats['packets_dropped'] += 1
        raise TimeoutError("TEST MODE: Simulated packet drop")
    # Simulate packet corruption
    if random.random() < TEST_CORRUPT_RATE:
        test_stats['packets_corrupted'] += 1
        # flip a byte to corrupt. NOTE: ChatGPT told me how to corrupt a byte from what 
        # we are sending over the network
        packet_array = bytearray(packet)
        if len(packet_array) > 0:
            idx = random.randint(0, len(packet_array) - 1)
            # This flips every bit in the byte
            packet_array[idx] ^= 0xFF 
        # return the corrupted packet
        return bytes(packet_array)

    # return unaltered packet
    return packet

def send_dns_query(query_string: str, server_ip: str, timeout: float = 5.0) -> bytes:
    """
    Sends DNS TXT query and waits for response.

    Args:
        query_string: e.g., "GET-index-html.abc123.tunnel.local"
        server_ip: IP address of DNS server
        timeout: seconds to wait

    Returns:
        TXT record response string
    """
    print(f'SENDING {query_string} to server {server_ip}')
    # Build DNS query packet
    dns_query = DNSQR(qname=query_string, qtype='TXT')
    packet = IP(dst = server_ip) / UDP(sport=random.randint(49152, 65535), dport=53) / DNS(rd=1,qd=dns_query)
   
    # listen for response from SERVER
    response = sr1(packet, timeout=timeout, verbose=False)

    if response is None:
        raise TimeoutError(f"DNS query timed out after {timeout} seconds")
    
    dns_response = response[DNS]

    # Check for DNS errors
    if dns_response.rcode != 0:
        raise ValueError(f"DNS error: rcode={dns_response.rcode}")
    
    # Extract TXT record from answer section
    if dns_response.ancount == 0:
        raise ValueError("No answers in DNS response")

    # NOTE: ChatGPT told me how to extract the TXT record part of a DNS method
    # in the following way
    # Go through the number of DNS answers that we have
    for i in range(dns_response.ancount):
        # Get the answer
        answer = dns_response.an[i]
        # Check if type is 16 => TXT record
        if answer.type == 16:
            # Index into rdata field - return as bytes
            if isinstance(answer.rdata, bytes):
                # we store this in a result variable
                result = answer.rdata
            else:
                # rdata is a list, get first element and encode to bytes
                # store in result variable
                result = answer.rdata[0].encode('utf-8') if isinstance(answer.rdata[0], str) else answer.rdata[0]

            # before returning what the client receives, we need to simulate 
            # either corrupting part of the result OR dropping it entirely. INsert our 
            # in the middle helper function here
            return simulate_network_conditions(result)

    raise ValueError("No TXT record found in DNS response")


def send_initial_request(filename: str, session_id: str, server_ip: str) -> bytes:
    """
    Sends GET request and waits for first chunk to be sent back.

    Args:
        filename: Name of file to request (e.g., "index.html")
        session_id: 6-character session ID
        server_ip: IP address of DNS server

    Returns:
        First TXT record response
    """
    # Use protocol function to create GETquery with filename and session id
    GET_query = protocol.encode_get(filename, session_id)

    # Retry loop for initial request (in case first packet is dropped/corrupted)
    max_retries = 10  # Higher for testing with packet loss
    for attempt in range(max_retries):
        try:
            response = send_dns_query(GET_query, server_ip)
            return response
        except TimeoutError as e:
            if "TEST MODE" in str(e):
                # Simulated drop - retry
                if attempt < max_retries - 1:
                    continue
            raise  # Real timeout or max retries exceeded
        except UnicodeDecodeError:
            # Corruption made invalid UTF-8 - retry
            if attempt < max_retries - 1:
                continue
            raise  # Max retries exceeded

    raise TimeoutError("Failed to get initial response after retries")


def receive_file(first_chunk_txt: bytes, session_id: str, server_ip: str) -> bytes:
    """
    Receives file chunks using Stop-and-Wait protocol.

    Args:
        first_chunk_txt: First TXT record response from send_initial_request()
        session_id: session id of files we're transmitting
        server_ip: of the server we are looking for

    Returns:
        Complete file as bytes
    """
    chunks = []

    # track total bytes and duplicates
    # NOTE: ChatGPT suggested I add these statistics and track them as such
    total_bytes = 0
    duplicate_count = 0

    # first chunk we call the function ith
    expected_seq_type = 0
    try:
        current_txt = first_chunk_txt.decode()
    except UnicodeDecodeError:
        # Corruption made invalid UTF-8 - treat as corrupted packet
        print("First chunk corrupted (invalid UTF-8) - this test is too extreme!")
        raise ValueError("First chunk corrupted - try lower corruption rate")

    print(current_txt)

    # loop while receiving packets
    #TODO: Are we checking for session id anywhere?
    while True:
        # decode current chunk with protocol
        
        seq_type, data_bytes, packet_checksum = protocol.decode_chunk(current_txt)
        # calculate checksum
        checksum = protocol.calculate_checksum(data_bytes)
        # verify checksum
        if checksum == packet_checksum:
            # if checksum is valid and seq type is DONE
            if seq_type == "DONE":
                # were at the last chunk
                chunks.append(data_bytes)
                total_bytes += len(data_bytes)
                # create ACK message and send back to server that we received it
                ACK_message = protocol.encode_ack(expected_seq_type, session_id)
                send_dns_query(ACK_message, server_ip)
                break
            # At this point seq_type must be int (0 or 1), not "DONE"
            assert isinstance(seq_type, int), "seq_type must be int here"
            # Check we alternated correctly
            if seq_type == expected_seq_type:
                # if so add data to chunks
                chunks.append(data_bytes)
                total_bytes += len(data_bytes)
                # toggle seq_type from 0->1 or 1->0
                expected_seq_type = 1 - expected_seq_type #NOTE does this work the way we want?

            else:
                # if seq_type is the same, we received duplicate chunk so increment duplicate
                # we will still ACK the chunk so server knows we have it and can skip sending again
                # in case our ack before was dropped (and caused the server to send the same packet again)
                duplicate_count += 1
                
            # create the ack message and send it to the server so it knows we got it
            ACK_message= protocol.encode_ack(seq_type, session_id)

            # try to send the message several times
            max_attempted = 10  # Higher for testing with packet loss
            for attempt in range(max_attempted):
                try:
                    current_txt = send_dns_query(ACK_message, server_ip).decode()
                    break

                except TimeoutError as e:
                    # If we're in testing mode we know that timeoutError is immediate
                    if "TEST MODE" in str(e):
                        if attempt < max_attempted - 1:
                            continue
                    raise  # Real timeout or max retries exceeded
                except UnicodeDecodeError:
                    # Corruption made invalid UTF-8 - treat as corrupted, retry
                    if attempt < max_attempted - 1:
                        continue
                    raise  # Max retries exceeded

        else:
            # Checksum does not match => data corrupted
            print(f"CHECKSUM MISMATCHED. Expected {checksum}, got {packet_checksum}")

            # Request retransmit by sending ACK for the sequence we're expecting
            # This tells server "I'm still waiting for seq X, please resend"
            retry_ack = protocol.encode_ack(expected_seq_type, session_id)

            # Retry loop for dropped packets
            max_retries = 10  # Higher for testing with packet loss
            for attempt in range(max_retries):
                try:
                    current_txt = send_dns_query(retry_ack, server_ip).decode()
                    break  # Success! Exit retry loop
                except TimeoutError as e:
                    if "TEST MODE" in str(e):
                        # Simulated drop - retry immediately
                        if attempt < max_retries - 1:
                            continue
                    raise  # Real timeout or max retries exceeded
                except UnicodeDecodeError:
                    # Corruption made invalid UTF-8 - treat as corrupted, retry
                    if attempt < max_retries - 1:
                        continue
                    raise  # Max retries exceeded
            continue

    # Print statistics
    print(f"File transferred")
    print(f"# total bytes: {total_bytes}")
    print(f"# duplicate packets: {duplicate_count}")

    # Reassemble all chunks into complete file
    complete_file = b''.join(chunks)

    return complete_file


def main():
    """
    Flow:
        1. Parse command line
        2. Generate session ID for this session
        3. Send GET request to get a webpage
        4. Call receive_file function to receive the file with stop and wait method
        5. After receiving all of the file, assemble it and write it to the disk
        6. Print statistics (bytes received and time)
    """
    # Flow #1. Parse the CLI
    # NOTE: ChatGPT helped me create parse. I specified the arguments that we needed it told me how to parse them
    parser = argparse.ArgumentParser(description='DNS Tunnel Client')
    parser.add_argument('filename', help='File to request (e.g., index.html)')
    parser.add_argument('--server', required=True, help='DNS server IP address')
    args = parser.parse_args()

    filename = args.filename
    server_ip = args.server # 172.25.162.183

    # FLow #2. Create the session ID for this file transfer session
    # NOTE: ChatGPT 
    session_id = ''
    # session number is 6 chars
    for i in range(6):
        # add random lowercase ascii character and concatenate
        session_id += random.choice(string.ascii_lowercase + string.digits)

    print(f"DNS Tunnel Client")
    print(f"-----------------")
    print(f"sequested file: {filename}")
    print(f"dns server ip: {server_ip}")
    print(f"session id: {session_id}")
    print()

    # Start timing
    start_time = time.time()

    # Wrap in try except for saftey
    try:
        # FLOW #3. Send GET initiator
        print(f"sending GET request for file: {filename}...")
        initial_chunk_txt = send_initial_request(filename, session_id, server_ip)
        print(f"Received initial chunk from server => we start file transfer now")
        print()

        # FLOW #4. Receive the file
        file_data = receive_file(initial_chunk_txt, session_id, server_ip)

        # FLOW #5. Write the received to directory
        output_filename = f"received_{filename}.html"
        with open(output_filename, 'wb') as f:
            f.write(file_data)

        # FLOW #6. Print stats
        # NOTE: ChatGPT suggested I add trackers for these statistics and print them as such
        # including the time
        elapsed_time = time.time() - start_time
        print(f"\nFile saved to: {output_filename}")
        print(f"File size: {len(file_data)} bytes")
        print(f"Transfer time: {elapsed_time:.2f} seconds")
        print(f"Throughput: {len(file_data) / elapsed_time:.2f} bytes/sec")

        # Print test mode statistics if enabled
        # NOTE: I had ChatGPT insert these counters to print if were are in test mode
        # and write the below print statements to actually print them
        if TEST_MODE:
            print(f"\n=== TEST MODE STATISTICS ===")
            print(f"Packets received from server: {test_stats['packets_received']}")
            print(f"Packets dropped (simulated): {test_stats['packets_dropped']}")
            print(f"Packets corrupted (simulated): {test_stats['packets_corrupted']}")
            if test_stats['packets_received'] > 0:
                drop_rate = test_stats['packets_dropped'] / test_stats['packets_received']
                corrupt_rate = test_stats['packets_corrupted'] / test_stats['packets_received']
                print(f"Actual drop rate: {drop_rate:.1%}")
                print(f"Actual corrupt rate: {corrupt_rate:.1%}")

    # Fall back for errors
    except Exception as e:
        print(f"\nUnexpected error: {e}")

        # NOTE: ChatGPT suggested I use traceback (library) to
        # print detailled error messages and the call stack of 
        # what caused the error. Very useful
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
