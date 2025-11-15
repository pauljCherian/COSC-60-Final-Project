import argparse
import random
import string
import time
import protocol
from scapy.all import IP, DNSQR, UDP, DNS, sr1

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
            # Index into rdata field
            txt_data = None
            if isinstance(answer.rdata, bytes):
                txt_data = answer.rdata.decode('utf-8')
            else: 
                txt_data = answer.rdata[0]
                print(txt_data)
            return txt_data

    raise ValueError("No TXT record found in DNS response")


def send_initial_request(filename: str, session_id: str, server_ip: str) -> str:
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

    # send the GET query and wait for the sever response
    # Uses the send DNS query function we just made
    response = send_dns_query(GET_query, server_ip)

    return response


def receive_file(first_chunk_txt: str, session_id: str, server_ip: str) -> bytes:
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
    current_txt = first_chunk_txt.decode()

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
            current_txt = send_dns_query(ACK_message, server_ip)

        else:
            # Checksum does not match => data corrupted
            print(f"CHECKSUM MISMATCHED. Expected {checksum}, got {packet_checksum}")

            # Request retransmit by sending ACK for the sequence we're expecting
            # This tells server "I'm still waiting for seq X, please resend"
            retry_ack = protocol.encode_ack(expected_seq_type, session_id)
            current_txt = send_dns_query(retry_ack, server_ip)
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
        output_filename = f"received_{filename}"
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
