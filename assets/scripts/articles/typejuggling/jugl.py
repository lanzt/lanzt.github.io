#!/usr/bin/python3

import hashlib
import string
import random
import signal

# Funciones ---------------------------.
def def_handler(signal, frame):  # Controlamos salida con Ctrl+C
    print()
    exit()

signal.signal(signal.SIGINT, def_handler)

# Inicio del programa -----------------.
dic = string.ascii_letters + string.digits  # abc...xyzABC...WXYZ0123456789
rand_index = list(range(7, 15))  # Generamos array: [7, 8 ... 13, 14]

while True:
    # Elegimos un numero aleatorio, ese numero será el tamaño de la cadena
    # Y la cadena se construye con caracteres aleatorios del diccionario
    random_value = ''.join(random.choices(dic, k=random.choice(rand_index)))
    # Generamos hash MD5 correspondiente al valor random
    hash_random_value = hashlib.md5(random_value.encode('utf-8')).hexdigest()

    # Si el hash empieza con 0e
    if hash_random_value.startswith("0e"):
        # Extraemos todo lo que esta despues del 0e y validamos si su contenido es numerico.
        if hash_random_value[2:].isnumeric():
            # Si es numerico, tenemos el hash del texto que PHP interpreta como flotante
            print(f"[+] Texto: {random_value} - Hash: {hash_random_value}")
            break
