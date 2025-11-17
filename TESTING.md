# Testing Packet Loss and Corruption

## What Gets Simulated

**Corruption/drops happen to packets the CLIENT RECEIVES from the server:**

```
Server → Network → [Simulation happens here] → Client processes
                    ↑
                Packets may be:
                - Dropped (client retries)
                - Corrupted (checksum fails, client retries)
```

**NOT simulated:** Packets client sends to server (those go through normally)

## How to Test

### 1. Start the server
```bash
sudo python dns_server.py
```

### 2. Run the client normally
```bash
python tunnel_client.py vibrantcloud.org --server 127.0.0.1
```

Check the received file:
```bash
cat received_vibrantcloud.org
```

### 3. Run with 30% packet loss
```bash
TEST_MODE=true TEST_DROP_RATE=0.3 python tunnel_client.py vibrantcloud.org --server 127.0.0.1
```

You'll see at the end:
```
=== TEST MODE STATISTICS ===
Packets received from server: 15
Packets dropped (simulated): 4
Packets corrupted (simulated): 0
Actual drop rate: 26.7%
```

Check the file is still correct:
```bash
cat received_vibrantcloud.org
```

### 4. Run with 20% packet corruption
```bash
TEST_MODE=true TEST_CORRUPT_RATE=0.2 python tunnel_client.py vibrantcloud.org --server 127.0.0.1
```

### 5. Run with both (hostile network)
```bash
TEST_MODE=true TEST_DROP_RATE=0.15 TEST_CORRUPT_RATE=0.1 python tunnel_client.py vibrantcloud.org --server 127.0.0.1
```

## What the Statistics Tell You

```
=== TEST MODE STATISTICS ===
Packets received from server: 20        ← Total packets server sent
Packets dropped (simulated): 6          ← These were "lost", client retried
Packets corrupted (simulated): 2        ← These had bad checksum, client retried
Actual drop rate: 30.0%
Actual corrupt rate: 10.0%
```

This proves your Stop-and-Wait protocol successfully retransmitted the failed packets!

## Quick Reference

| Test | Command |
|------|---------|
| Normal | `python tunnel_client.py vibrantcloud.org --server 127.0.0.1` |
| 30% loss | `TEST_MODE=true TEST_DROP_RATE=0.3 python tunnel_client.py vibrantcloud.org --server 127.0.0.1` |
| 20% corrupt | `TEST_MODE=true TEST_CORRUPT_RATE=0.2 python tunnel_client.py vibrantcloud.org --server 127.0.0.1` |
| Hostile | `TEST_MODE=true TEST_DROP_RATE=0.15 TEST_CORRUPT_RATE=0.1 python tunnel_client.py vibrantcloud.org --server 127.0.0.1` |

⚠️ **Note:** Very high corruption rates (>50%) may cause failures because corrupted bytes might not be valid UTF-8. Use reasonable rates (10-30%) for realistic testing.
